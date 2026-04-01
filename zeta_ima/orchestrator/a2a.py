"""
Agent-to-Agent (A2A) Communication Protocol.

Defines structured messages that agents exchange during handoffs.
Each agent reads incoming messages from previous agents and appends
its own for the next agent in the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class AgentMessage:
    """Structured message passed between agents in a pipeline."""

    from_agent: str                     # e.g. "pm", "copy", "design"
    to_agent: str                       # e.g. "copy", "design", "review"
    message_type: str                   # "handoff" | "request" | "response" | "feedback"
    payload: dict = field(default_factory=dict)
    """
    Payload varies by message type:
    - handoff: {"sub_task": str, "instructions": str, "context_summary": str, "constraints": list}
    - request: {"action": str, "params": dict}
    - response: {"output": str, "metadata": dict}
    - feedback: {"scores": dict, "suggestions": list, "passed": bool}
    """
    context_summary: str = ""           # Brief summary of accumulated context
    handoff_instructions: str = ""      # Specific instructions for the receiving agent
    created_at: str = ""                # ISO timestamp

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "payload": self.payload,
            "context_summary": self.context_summary,
            "handoff_instructions": self.handoff_instructions,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AgentMessage:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def get_latest_handoff(agent_messages: list[dict], to_agent: str) -> Optional[AgentMessage]:
    """Get the most recent handoff message addressed to a specific agent."""
    for msg in reversed(agent_messages):
        if msg.get("to_agent") == to_agent and msg.get("message_type") == "handoff":
            return AgentMessage.from_dict(msg)
    return None


def build_context_from_messages(agent_messages: list[dict]) -> str:
    """Build a context string from all agent messages for injection into prompts."""
    if not agent_messages:
        return ""

    parts = []
    for msg in agent_messages:
        from_agent = msg.get("from_agent", "unknown")
        msg_type = msg.get("message_type", "")
        content = msg.get("handoff_instructions") or msg.get("context_summary") or ""
        if content:
            parts.append(f"[{from_agent} → {msg_type}]: {content}")

    return "\n".join(parts)
