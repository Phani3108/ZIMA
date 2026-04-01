"""
Copy Agent node — draft generation.

Flow:
  1. Pull top-K brand examples from Qdrant (the "learned" context)
  2. Optionally compress session history if > 10 turns (prevents token bloat)
  3. Call GPT-4o with system prompt + brand examples + session history + brief
  4. Return updated state with the new draft
"""

from pathlib import Path

from openai import AsyncOpenAI

from zeta_ima.agents.state import AgentState
from zeta_ima.config import settings
from zeta_ima.memory.brand import search_brand_examples

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
    """Generate a copy draft using GPT-4o + brand context from Qdrant."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # 1. Brand context from long-term memory
    brand_examples = await search_brand_examples(state["current_brief"])

    # 2. Compress history if needed
    history = await _compress_history(list(state.get("messages", [])), client)

    # 3. Build messages for GPT-4o
    system_prompt = _PROMPT_PATH.read_text()
    brand_block = "\n\n".join(
        f"Example {i + 1}:\n{ex}" for i, ex in enumerate(brand_examples)
    ) if brand_examples else "No prior examples yet — apply the brand voice guidelines above."

    # Revision context: include feedback from previous rejection if present
    revision_note = ""
    if state.get("approval_comment") and state.get("stage") == "drafting" and state.get("iteration_count", 0) > 0:
        revision_note = f"\n\nUser feedback on previous draft: {state['approval_comment']}\nPlease revise accordingly."

    messages = [
        {"role": "system", "content": system_prompt},
        *history[-6:],  # Last 6 turns (or compressed summary)
        {
            "role": "user",
            "content": (
                f"Brand examples from approved past work:\n{brand_block}"
                f"\n\nBrief: {state['current_brief']}"
                f"{revision_note}"
            ),
        },
    ]

    # 4. Generate
    resp = await client.chat.completions.create(
        model=settings.llm_copy,
        messages=messages,
    )
    draft_text = resp.choices[0].message.content
    iteration = state.get("iteration_count", 0) + 1

    return {
        "current_draft": {"text": draft_text, "iteration": iteration},
        "drafts": list(state.get("drafts", [])) + [{"text": draft_text, "iteration": iteration}],
        "iteration_count": iteration,
        "brand_examples": brand_examples,
        "stage": "reviewing",
        "messages": [{"role": "assistant", "content": f"[Draft #{iteration} generated]"}],
    }
