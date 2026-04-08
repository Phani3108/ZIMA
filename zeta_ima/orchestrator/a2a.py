"""
Agent-to-Agent (A2A) Communication Protocol.

Defines structured messages that agents exchange during handoffs,
discussions, delegations, and status updates.  Every message carries
the sender's role metadata (title + avatar) so UIs can render rich
agent-identity timelines without a separate lookup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


# All recognised message types
MESSAGE_TYPES = (
    "handoff",          # Agent passes work to the next agent
    "request",          # Agent asks another agent to do something
    "response",         # Agent returns output to a requester
    "feedback",         # Review scores / suggestions
    "discussion",       # Meeting or planning conversation
    "delegation",       # Agent delegates a sub-task to another
    "question",         # Agent asks a clarifying question
    "status_update",    # Progress report during execution
    # ── Future: step-level visibility ──
    "step_started",     # Agent begins a named step (for live execution UI)
    "step_completed",   # Agent finishes a named step
    "plan_announced",   # Pipeline plan broadcast at execution start
)


@dataclass
class AgentMessage:
    """Structured message passed between agents in a pipeline."""

    from_agent: str                     # Node name: "pm", "copy", "design"
    to_agent: str                       # Node name or "all" for broadcasts
    message_type: str                   # One of MESSAGE_TYPES
    payload: dict = field(default_factory=dict)
    """
    Payload varies by message type:
    - handoff:       {"sub_task": str, "instructions": str, "context_summary": str, "constraints": list}
    - request:       {"action": str, "params": dict}
    - response:      {"output": str, "metadata": dict}
    - feedback:      {"scores": dict, "suggestions": list, "passed": bool}
    - discussion:    {"topic": str, "stance": str}
    - delegation:    {"sub_task": str, "deadline": str}
    - question:      {"question": str, "options": list}
    - status_update: {"step": str, "progress_pct": int, "note": str}
    """
    context_summary: str = ""           # Brief summary of accumulated context
    handoff_instructions: str = ""      # Specific instructions for the receiving agent
    # Agent identity (populated automatically when using emit())
    agent_title: str = ""               # Human-readable: "Senior Copywriter"
    avatar_emoji: str = ""              # "✍️"
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
            "agent_title": self.agent_title,
            "avatar_emoji": self.avatar_emoji,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentMessage":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Convenience builder ─────────────────────────────────────────────────────

def emit(
    from_node: str,
    to_node: str,
    message_type: str,
    *,
    payload: dict | None = None,
    context_summary: str = "",
    handoff_instructions: str = "",
) -> AgentMessage:
    """Create an AgentMessage pre-populated with role identity from the registry."""
    from zeta_ima.agents.roles import role_registry

    role = role_registry.get_by_node(from_node)
    return AgentMessage(
        from_agent=from_node,
        to_agent=to_node,
        message_type=message_type,
        payload=payload or {},
        context_summary=context_summary,
        handoff_instructions=handoff_instructions,
        agent_title=role.title if role else from_node,
        avatar_emoji=role.avatar_emoji if role else "🤖",
    )


# ── Query helpers ────────────────────────────────────────────────────────────

def get_latest_handoff(agent_messages: list[dict], to_agent: str) -> Optional[AgentMessage]:
    """Get the most recent handoff message addressed to a specific agent."""
    for msg in reversed(agent_messages):
        if msg.get("to_agent") == to_agent and msg.get("message_type") == "handoff":
            return AgentMessage.from_dict(msg)
    return None


def get_messages_by_type(
    agent_messages: list[dict],
    message_type: str,
    *,
    from_agent: str | None = None,
    to_agent: str | None = None,
) -> List[AgentMessage]:
    """Filter messages by type, optionally narrowed to specific sender/receiver."""
    out: List[AgentMessage] = []
    for msg in agent_messages:
        if msg.get("message_type") != message_type:
            continue
        if from_agent and msg.get("from_agent") != from_agent:
            continue
        if to_agent and msg.get("to_agent") != to_agent:
            continue
        out.append(AgentMessage.from_dict(msg))
    return out


def get_latest_feedback(agent_messages: list[dict], from_agent: str = "review") -> Optional[AgentMessage]:
    """Get the most recent feedback message from the review agent."""
    for msg in reversed(agent_messages):
        if msg.get("from_agent") == from_agent and msg.get("message_type") == "feedback":
            return AgentMessage.from_dict(msg)
    return None


def build_context_from_messages(agent_messages: list[dict]) -> str:
    """Build a context string from all agent messages for injection into prompts."""
    if not agent_messages:
        return ""

    parts = []
    for msg in agent_messages:
        from_agent = msg.get("from_agent", "unknown")
        title = msg.get("agent_title") or from_agent
        avatar = msg.get("avatar_emoji", "")
        msg_type = msg.get("message_type", "")
        content = msg.get("handoff_instructions") or msg.get("context_summary") or ""
        if content:
            prefix = f"{avatar} {title}" if avatar else title
            parts.append(f"[{prefix} → {msg_type}]: {content}")

    return "\n".join(parts)


def emit_step(
    from_node: str,
    step_name: str,
    step_index: int,
    total_steps: int,
    status: str = "started",
    preview: str = "",
) -> AgentMessage:
    """Create a step-level visibility event for the execution UI.

    Args:
        from_node: The agent node emitting the step.
        step_name: Human-readable step name (e.g. "Loading brand context").
        step_index: 0-based index of this step within the agent's work.
        total_steps: Total steps this agent will perform.
        status: "started" or "completed".
        preview: Optional short preview of step output.
    """
    msg_type = "step_started" if status == "started" else "step_completed"
    return emit(
        from_node,
        "all",
        msg_type,
        payload={
            "step_name": step_name,
            "step_index": step_index,
            "total_steps": total_steps,
            "status": status,
            "preview": preview[:200] if preview else "",
        },
        context_summary=f"{step_name} ({status})",
    )


def build_execution_timeline(agent_messages: list[dict]) -> List[dict]:
    """Return a timeline-friendly list of A2A events for frontend rendering."""
    timeline = []
    for msg in agent_messages:
        timeline.append({
            "agent": msg.get("from_agent", "unknown"),
            "title": msg.get("agent_title", ""),
            "avatar": msg.get("avatar_emoji", "🤖"),
            "type": msg.get("message_type", ""),
            "summary": msg.get("context_summary", "")[:200],
            "timestamp": msg.get("created_at", ""),
        })
    return timeline
