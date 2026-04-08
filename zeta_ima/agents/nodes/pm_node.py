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

from zeta_ima.agents.state import AgentState
from zeta_ima.agents.roles import role_registry
from zeta_ima.config import settings, get_openai_client
from zeta_ima.orchestrator.a2a import AgentMessage, emit, emit_step

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
    client = get_openai_client()
    brief = state.get("current_brief", "")
    agent_messages = list(state.get("agent_messages", []))

    # Step 1/3: Decomposing brief
    agent_messages.append(emit_step("pm", "Decomposing brief", 0, 3, "started").to_dict())

    # Build context from research + brain
    kb_context = "\n".join(state.get("kb_context", [])[:3])
    brain_context = "\n".join(state.get("brain_context", [])[:3])
    brand_examples = "\n".join(state.get("brand_examples", [])[:2])

    # Load PM prompt
    try:
        base_prompt = _PROMPT_PATH.read_text()
    except FileNotFoundError:
        base_prompt = _SYSTEM_FALLBACK
    role = role_registry.get_by_node("pm")
    system_prompt = f"{role.system_prompt_prefix()}\n\n{base_prompt}" if role else base_prompt

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
    agent_messages.append(emit_step("pm", "Decomposing brief", 0, 3, "completed", f"Analysis: {len(raw)} chars").to_dict())

    # Step 2/3: Creating agent instructions
    agent_messages.append(emit_step("pm", "Creating agent instructions", 1, 3, "started").to_dict())

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
    pipeline = state.get("pipeline", [])

    # Handoff to copy agent
    if "copy" in pipeline:
        agent_messages.append(emit(
            "pm", "copy", "handoff",
            payload=decomposition,
            context_summary=decomposition.get("context_summary", ""),
            handoff_instructions=decomposition.get("copy_instructions", brief),
        ).to_dict())

    # Handoff to design agent
    if "design" in pipeline:
        agent_messages.append(emit(
            "pm", "design", "handoff",
            payload=decomposition,
            context_summary=decomposition.get("context_summary", ""),
            handoff_instructions=decomposition.get("design_instructions", f"Create visuals for: {brief}"),
        ).to_dict())

    # Handoff to review agent
    if "review" in pipeline:
        agent_messages.append(emit(
            "pm", "review", "handoff",
            payload={"review_criteria": decomposition.get("review_criteria", "")},
            context_summary=decomposition.get("context_summary", ""),
            handoff_instructions=decomposition.get("review_criteria", "Standard review"),
        ).to_dict())

    # Handoff to SEO agent
    if "seo" in pipeline:
        agent_messages.append(emit(
            "pm", "seo", "handoff",
            payload=decomposition,
            context_summary=decomposition.get("context_summary", ""),
            handoff_instructions=decomposition.get("seo_instructions", f"Optimize for: {brief[:200]}"),
        ).to_dict())

    # Status update broadcast
    agent_messages.append(emit_step("pm", "Creating agent instructions", 1, 3, "completed", f"Briefed {len([a for a in ('copy', 'design', 'review', 'seo') if a in pipeline])} agents").to_dict())
    agent_messages.append(emit_step("pm", "PM briefing complete", 2, 3, "completed").to_dict())
    agent_messages.append(emit(
        "pm", "all", "status_update",
        payload={
            "agents_briefed": [a for a in ("copy", "design", "review", "seo") if a in pipeline],
            "constraints": decomposition.get("constraints", []),
        },
        context_summary=f"PM decomposed brief into tasks for {len(pipeline)} agents.",
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
