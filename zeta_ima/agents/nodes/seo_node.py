"""
SEO Specialist Agent Node — keyword research, meta-tag generation,
and SEO optimization of draft copy.

Reads the current draft (if any) and brief, then:
  1. Suggests target keywords from the brief + KB context
  2. Optimises the draft for search (headings, meta-description, alt-text hints)
  3. Emits A2A handoff to the next agent in the pipeline
"""

from __future__ import annotations

import logging
from pathlib import Path

from zeta_ima.agents.state import AgentState
from zeta_ima.agents.roles import role_registry
from zeta_ima.config import settings, get_openai_client
from zeta_ima.orchestrator.a2a import emit, emit_step, get_latest_handoff

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "seo_agent.md"

_SYSTEM_FALLBACK = """You are an SEO Specialist at a digital marketing agency.
Your job is to:
1. Identify primary and secondary target keywords for the given brief.
2. If a draft is provided, rewrite or annotate it with SEO improvements:
   - Optimised headline with primary keyword
   - Meta description (≤155 chars, includes CTA)
   - Suggested H2/H3 sub-headings
   - Internal/external link placement hints
   - Image alt-text suggestions
3. If no draft yet, output a keyword strategy document with search volume estimates.

Be data-driven, concise, and refer to brand context when available."""


async def seo_node(state: AgentState) -> dict:
    """Perform SEO analysis and optimisation."""
    client = get_openai_client()
    brief = state.get("current_brief", "")
    agent_messages = list(state.get("agent_messages", []))

    # Step 1/3: Keyword analysis
    agent_messages.append(emit_step("seo", "Keyword analysis", 0, 3, "started").to_dict())

    # PM instructions
    handoff = get_latest_handoff(agent_messages, "seo")
    extra = f"\n\nPM Instructions: {handoff.handoff_instructions}" if handoff and handoff.handoff_instructions else ""

    # Existing draft to optimise
    draft_text = state.get("current_draft", {}).get("text", "")
    draft_block = f"\n\nExisting draft to optimise:\n{draft_text[:3000]}" if draft_text else ""

    # KB context
    kb_block = "\n".join(state.get("kb_context", [])[:3])

    # System prompt
    try:
        base_prompt = _PROMPT_PATH.read_text()
    except FileNotFoundError:
        base_prompt = _SYSTEM_FALLBACK
    role = role_registry.get_by_node("seo")
    system_prompt = f"{role.system_prompt_prefix()}\n\n{base_prompt}" if role else base_prompt

    user_prompt = f"Brief: {brief}{extra}\n\nKB Context:\n{kb_block or 'None.'}{draft_block}"
    agent_messages.append(emit_step("seo", "Keyword analysis", 0, 3, "completed", "Context gathered").to_dict())

    # Step 2/3: Optimizing content
    agent_messages.append(emit_step("seo", "Optimizing content", 1, 3, "started").to_dict())
    resp = await client.chat.completions.create(
        model=settings.llm_copy,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    seo_output = resp.choices[0].message.content or ""
    agent_messages.append(emit_step("seo", "Optimizing content", 1, 3, "completed", f"SEO analysis: {len(seo_output)} chars").to_dict())
    agent_messages.append(emit_step("seo", "SEO complete", 2, 3, "completed").to_dict())

    # A2A: emit to the next agent
    agent_messages.append(emit(
        "seo", "copy" if "copy" in state.get("pipeline", []) else "review", "response",
        payload={"seo_analysis": seo_output[:2000]},
        context_summary=f"SEO analysis complete ({len(seo_output)} chars)",
        handoff_instructions=f"Incorporate these SEO recommendations: {seo_output[:500]}",
    ).to_dict())

    # If there's a draft, we update it with SEO annotations
    updated_draft = state.get("current_draft", {})
    if draft_text:
        updated_draft = {**updated_draft, "seo_annotations": seo_output[:2000]}

    return {
        "current_draft": updated_draft,
        "tool_results": {**state.get("tool_results", {}), "seo": {"output": seo_output[:2000]}},
        "agent_messages": agent_messages,
        "messages": [{"role": "assistant", "content": f"[SEO] Analysis complete. Keywords and recommendations generated."}],
    }
