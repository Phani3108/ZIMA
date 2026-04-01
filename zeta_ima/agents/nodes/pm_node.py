"""
PM (Project Manager) Agent Node — decomposes briefs into sub-tasks and
sequences downstream agents via A2A handoff messages.

The PM node reads the brief, analyzes it, and creates structured handoff
instructions for each downstream agent in the pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from openai import AsyncOpenAI

from zeta_ima.agents.state import AgentState
from zeta_ima.config import settings
from zeta_ima.orchestrator.a2a import AgentMessage

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "pm_agent.md"

_SYSTEM_FALLBACK = """You are a senior marketing project manager. Your job is to:
1. Analyze the creative brief
2. Break it down into clear sub-tasks for the team
3. Provide specific instructions for each agent (copy writer, designer, reviewer)

For each downstream agent, output a JSON object with:
{
  "copy_instructions": "Specific instructions for the copy writer",
  "design_instructions": "Specific instructions for the designer",
  "review_criteria": "What the reviewer should focus on",
  "context_summary": "Key context that all agents need",
  "constraints": ["List of constraints or requirements"]
}

Be specific, actionable, and concise. Reference brand guidelines and knowledge base context when available."""


async def pm_node(state: AgentState) -> dict:
    """Decompose the brief and create A2A handoff messages for downstream agents."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    brief = state.get("current_brief", "")

    # Build context from research + brain
    kb_context = "\n".join(state.get("kb_context", [])[:3])
    brain_context = "\n".join(state.get("brain_context", [])[:3])
    brand_examples = "\n".join(state.get("brand_examples", [])[:2])

    # Load PM prompt
    try:
        system_prompt = _PROMPT_PATH.read_text()
    except FileNotFoundError:
        system_prompt = _SYSTEM_FALLBACK

    user_prompt = f"""Brief: {brief}

Knowledge Base Context:
{kb_context or "None available."}

Agency Brain Context:
{brain_context or "None available."}

Brand Examples:
{brand_examples or "None available."}

Pipeline: {state.get("pipeline", [])}

Decompose this brief into specific instructions for downstream agents.
Return a JSON object with copy_instructions, design_instructions, review_criteria, context_summary, and constraints."""

    resp = await client.chat.completions.create(
        model=settings.llm_copy,  # Use capable model for PM reasoning
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    raw = resp.choices[0].message.content or ""

    # Parse PM output
    try:
        # Extract JSON from response (may be wrapped in markdown)
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            decomposition = json.loads(raw[json_start:json_end])
        else:
            decomposition = {"context_summary": raw, "constraints": []}
    except (json.JSONDecodeError, ValueError):
        decomposition = {"context_summary": raw, "constraints": []}

    # Create A2A handoff messages for downstream agents
    agent_messages = list(state.get("agent_messages", []))
    pipeline = state.get("pipeline", [])

    # Handoff to copy agent
    if "copy" in pipeline:
        agent_messages.append(AgentMessage(
            from_agent="pm",
            to_agent="copy",
            message_type="handoff",
            payload=decomposition,
            context_summary=decomposition.get("context_summary", ""),
            handoff_instructions=decomposition.get("copy_instructions", brief),
        ).to_dict())

    # Handoff to design agent
    if "design" in pipeline:
        agent_messages.append(AgentMessage(
            from_agent="pm",
            to_agent="design",
            message_type="handoff",
            payload=decomposition,
            context_summary=decomposition.get("context_summary", ""),
            handoff_instructions=decomposition.get("design_instructions", f"Create visuals for: {brief}"),
        ).to_dict())

    # Handoff to review agent
    if "review" in pipeline:
        agent_messages.append(AgentMessage(
            from_agent="pm",
            to_agent="review",
            message_type="handoff",
            payload={"review_criteria": decomposition.get("review_criteria", "")},
            context_summary=decomposition.get("context_summary", ""),
            handoff_instructions=decomposition.get("review_criteria", "Standard review"),
        ).to_dict())

    return {
        "agent_messages": agent_messages,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"[PM] Brief decomposed. "
                    f"Context: {decomposition.get('context_summary', '')[:200]}"
                ),
            }
        ],
    }
