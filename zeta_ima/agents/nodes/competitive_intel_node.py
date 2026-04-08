"""
Competitive Intelligence Agent Node — analyses competitors
and provides market positioning insights.

Uses KB context + optional SEMrush integration to gather competitor data
and inform strategic decisions for campaigns.
"""

from __future__ import annotations

import logging
from pathlib import Path

from zeta_ima.agents.state import AgentState
from zeta_ima.agents.roles import role_registry
from zeta_ima.config import settings, get_openai_client
from zeta_ima.orchestrator.a2a import emit, emit_step, get_latest_handoff

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "competitive_intel_agent.md"

_SYSTEM_FALLBACK = """You are a Competitive Intelligence Analyst at a marketing agency.
Your job is to:
1. Analyse the competitive landscape for the given brief/product/campaign.
2. Identify 3-5 key competitors and their positioning.
3. Highlight gaps and opportunities our client can exploit.
4. Suggest differentiation strategies and messaging angles.
5. If SEMrush data is available, incorporate traffic/keyword insights.

Output a structured competitive brief with:
- Competitor overview (name, positioning, strengths, weaknesses)
- Market gap analysis
- Recommended positioning
- Messaging angles to test

Be concise and data-driven."""


async def competitive_intel_node(state: AgentState) -> dict:
    """Gather competitive intelligence and produce a positioning brief."""
    client = get_openai_client()
    brief = state.get("current_brief", "")
    agent_messages = list(state.get("agent_messages", []))

    # Step 1/3: Gathering market data
    agent_messages.append(emit_step("competitive_intel", "Gathering market data", 0, 3, "started").to_dict())

    # PM instructions
    handoff = get_latest_handoff(agent_messages, "competitive_intel")
    extra = ""
    if handoff and handoff.handoff_instructions:
        extra = f"\n\nPM Instructions: {handoff.handoff_instructions}"

    # KB + brain context
    kb_block = "\n".join(state.get("kb_context", [])[:3])
    brain_block = "\n".join(state.get("brain_context", [])[:3])

    # Try SEMrush integration if available
    semrush_data = ""
    try:
        from zeta_ima.integrations.semrush import get_competitor_overview
        raw = await get_competitor_overview(brief)
        if raw:
            semrush_data = f"\n\nSEMrush Data:\n{raw[:2000]}"
    except Exception as e:
        log.debug("SEMrush not available: %s", e)

    # System prompt
    try:
        base_prompt = _PROMPT_PATH.read_text()
    except FileNotFoundError:
        base_prompt = _SYSTEM_FALLBACK
    role = role_registry.get_by_node("competitive_intel")
    system_prompt = f"{role.system_prompt_prefix()}\n\n{base_prompt}" if role else base_prompt

    user_prompt = (
        f"Brief: {brief}{extra}"
        f"\n\nKB Context:\n{kb_block or 'None.'}"
        f"\n\nBrain Context:\n{brain_block or 'None.'}"
        f"{semrush_data}"
    )
    agent_messages.append(emit_step("competitive_intel", "Gathering market data", 0, 3, "completed", "Context assembled").to_dict())

    # Step 2/3: Analyzing competitors
    agent_messages.append(emit_step("competitive_intel", "Analyzing competitors", 1, 3, "started").to_dict())

    resp = await client.chat.completions.create(
        model=settings.llm_copy,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    intel_output = resp.choices[0].message.content or ""
    agent_messages.append(emit_step("competitive_intel", "Analyzing competitors", 1, 3, "completed", f"Analysis: {len(intel_output)} chars").to_dict())
    agent_messages.append(emit_step("competitive_intel", "Analysis complete", 2, 3, "completed").to_dict())

    # A2A: emit findings for downstream agents
    next_agent = "pm" if "pm" in state.get("pipeline", []) else "copy"
    agent_messages.append(emit(
        "competitive_intel", next_agent, "response",
        payload={"competitive_brief": intel_output[:2000]},
        context_summary=f"Competitive analysis complete — {len(intel_output)} chars",
        handoff_instructions=f"Use these competitive insights: {intel_output[:500]}",
    ).to_dict())

    return {
        "tool_results": {**state.get("tool_results", {}), "competitive_intel": {"output": intel_output[:2000]}},
        "agent_messages": agent_messages,
        "brain_context": list(state.get("brain_context", [])) + [intel_output[:500]],
        "messages": [{"role": "assistant", "content": "[Competitive Intel] Analysis complete. Positioning insights generated."}],
    }
