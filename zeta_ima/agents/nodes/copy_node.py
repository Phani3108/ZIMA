"""
Copy Agent node — draft generation.

Flow:
  1. Pull top-K brand examples from Qdrant (the "learned" context)
  2. Inject learning guidance (common edits, rejection patterns, directional signals)
  3. Read A2A handoff instructions from PM agent
  4. Optionally compress session history if > 10 turns (prevents token bloat)
  5. Call GPT-4o with system prompt + brand examples + learning + session history + brief
  6. Return updated state with the new draft + A2A response message
"""

import logging
from pathlib import Path

from openai import AsyncOpenAI

from zeta_ima.agents.state import AgentState
from zeta_ima.config import settings
from zeta_ima.memory.brand import search_brand_examples
from zeta_ima.orchestrator.a2a import AgentMessage, get_latest_handoff, build_context_from_messages

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "copy_agent.md"


async def _compress_history(messages: list, client: AsyncOpenAI) -> list:
    """
    After 10 turns, summarise old turns to a 3-bullet system message and keep
    the last 3 verbatim. This prevents context bloat on long sessions.
    """
    if len(messages) <= 10:
        return messages

    to_compress = messages[:-3]
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": (
                    "Summarise this conversation in 3 bullet points. "
                    "Keep: the brief, key decisions, approved/rejected drafts. "
                    "Discard: pleasantries, filler.\n\n"
                    f"{to_compress}"
                ),
            }
        ],
    )
    summary = resp.choices[0].message.content
    return [
        {"role": "system", "content": f"[Session summary]: {summary}"},
        *messages[-3:],
    ]


async def copy_node(state: AgentState) -> dict:
    """Generate a copy draft using GPT-4o + brand context + learning guidance + A2A context."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # 1. Brand context from long-term memory
    brand_examples = await search_brand_examples(state["current_brief"])

    # 2. Learning guidance (common edits, rejection patterns, directional signals)
    learning_block = ""
    try:
        from zeta_ima.memory.learning import get_learning_guidance
        learning_block = await get_learning_guidance(
            skill_id=state.get("intent", "copy"),
            brief=state["current_brief"],
        )
    except Exception as e:
        log.debug("Learning guidance unavailable: %s", e)

    # 3. A2A handoff instructions from PM
    a2a_context = ""
    agent_messages = list(state.get("agent_messages", []))
    handoff = get_latest_handoff(agent_messages, "copy")
    if handoff and handoff.handoff_instructions:
        a2a_context = f"\n\nPM INSTRUCTIONS:\n{handoff.handoff_instructions}"
    elif agent_messages:
        a2a_context_text = build_context_from_messages(agent_messages)
        if a2a_context_text:
            a2a_context = f"\n\nPIPELINE CONTEXT:\n{a2a_context_text}"

    # 4. Compress history if needed
    history = await _compress_history(list(state.get("messages", [])), client)

    # 5. Build messages for GPT-4o
    system_prompt = _PROMPT_PATH.read_text()
    brand_block = "\n\n".join(
        f"Example {i + 1}:\n{ex}" for i, ex in enumerate(brand_examples)
    ) if brand_examples else "No prior examples yet — apply the brand voice guidelines above."

    # Revision context: include feedback from previous rejection if present
    revision_note = ""
    if state.get("approval_comment") and state.get("stage") == "drafting" and state.get("iteration_count", 0) > 0:
        revision_note = f"\n\nUser feedback on previous draft: {state['approval_comment']}\nPlease revise accordingly."

    # Brain context from research node
    brain_block = ""
    if state.get("brain_context"):
        brain_block = "\n\nAGENCY BRAIN CONTEXT:\n" + "\n".join(state["brain_context"][:3])

    messages = [
        {"role": "system", "content": system_prompt},
        *history[-6:],  # Last 6 turns (or compressed summary)
        {
            "role": "user",
            "content": (
                f"Brand examples from approved past work:\n{brand_block}"
                + (f"\n\n{learning_block}" if learning_block else "")
                + brain_block
                + a2a_context
                + f"\n\nBrief: {state['current_brief']}"
                + revision_note
            ),
        },
    ]

    # 6. Generate
    resp = await client.chat.completions.create(
        model=settings.llm_copy,
        messages=messages,
    )
    draft_text = resp.choices[0].message.content
    iteration = state.get("iteration_count", 0) + 1

    # 7. A2A: send response to next agent in pipeline
    agent_messages.append(AgentMessage(
        from_agent="copy",
        to_agent="review",
        message_type="response",
        payload={"draft_iteration": iteration},
        context_summary=f"Draft #{iteration} generated ({len(draft_text or '')} chars)",
        handoff_instructions=f"Review this draft against the brief: {state['current_brief'][:200]}",
    ).to_dict())

    return {
        "current_draft": {"text": draft_text, "iteration": iteration},
        "drafts": list(state.get("drafts", [])) + [{"text": draft_text, "iteration": iteration}],
        "iteration_count": iteration,
        "brand_examples": brand_examples,
        "stage": "reviewing",
        "agent_messages": agent_messages,
        "messages": [{"role": "assistant", "content": f"[Draft #{iteration} generated]"}],
    }
