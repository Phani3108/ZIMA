"""
Product Marketing Agent Node — crafts positioning, messaging frameworks,
and go-to-market narratives.

Takes competitive intelligence, brand context, and brief to produce
product-focused marketing deliverables: positioning statements,
value props, messaging matrices, and launch narratives.
"""

from __future__ import annotations

import logging
from pathlib import Path

from zeta_ima.agents.state import AgentState
from zeta_ima.agents.roles import role_registry
from zeta_ima.config import settings, get_openai_client
from zeta_ima.orchestrator.a2a import emit, get_latest_handoff, build_context_from_messages

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "product_marketing_agent.md"

_SYSTEM_FALLBACK = """You are a Product Marketer at a marketing agency.
Your job is to:
1. Craft a clear positioning statement using the brief and competitive context.
2. Build a messaging framework: headline, sub-headline, 3 key value props.
3. Suggest audience segments and their primary pain points.
4. Recommend launch narrative and campaign angles.

Output a structured document with:
- Positioning statement (one sentence)
- Messaging matrix (audience × value prop × proof point)
- Launch narrative (3-5 sentences)
- Recommended channels

Be strategic, customer-centric, and concise."""


async def product_marketing_node(state: AgentState) -> dict:
    """Generate positioning, messaging framework, and GTM narrative."""
    client = get_openai_client()
    brief = state.get("current_brief", "")
    agent_messages = list(state.get("agent_messages", []))

    # PM instructions
    handoff = get_latest_handoff(agent_messages, "product_marketing")
    extra = ""
    if handoff and handoff.handoff_instructions:
        extra = f"\n\nPM Instructions: {handoff.handoff_instructions}"

    # Competitive intel from pipeline
    pipeline_context = build_context_from_messages(agent_messages)

    # KB + brain + brand
    kb_block = "\n".join(state.get("kb_context", [])[:3])
    brain_block = "\n".join(state.get("brain_context", [])[:3])
    brand_block = "\n".join(state.get("brand_examples", [])[:2])

    # System prompt
    try:
        base_prompt = _PROMPT_PATH.read_text()
    except FileNotFoundError:
        base_prompt = _SYSTEM_FALLBACK
    role = role_registry.get_by_node("product_marketing")
    system_prompt = f"{role.system_prompt_prefix()}\n\n{base_prompt}" if role else base_prompt

    user_prompt = (
        f"Brief: {brief}{extra}"
        f"\n\nPipeline Context:\n{pipeline_context or 'None.'}"
        f"\n\nKB Context:\n{kb_block or 'None.'}"
        f"\n\nBrain Context:\n{brain_block or 'None.'}"
        f"\n\nBrand Examples:\n{brand_block or 'None.'}"
    )

    resp = await client.chat.completions.create(
        model=settings.llm_copy,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    pm_output = resp.choices[0].message.content or ""

    # A2A: emit to copy or next agent
    next_agent = "copy" if "copy" in state.get("pipeline", []) else "review"
    agent_messages.append(emit(
        "product_marketing", next_agent, "handoff",
        payload={"positioning": pm_output[:2000]},
        context_summary=f"Product marketing framework complete ({len(pm_output)} chars)",
        handoff_instructions=f"Use this positioning and messaging framework: {pm_output[:500]}",
    ).to_dict())

    return {
        "tool_results": {
            **state.get("tool_results", {}),
            "product_marketing": {"output": pm_output[:2000]},
        },
        "agent_messages": agent_messages,
        "messages": [{"role": "assistant", "content": "[Product Marketing] Positioning and messaging framework complete."}],
    }
