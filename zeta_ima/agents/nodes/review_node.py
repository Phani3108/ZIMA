"""
Review Agent node — Actor-Critic quality gate (Genesis v2).

Flow:
  1. Actor-Critic ReflectionLoop polishes the draft (up to 3 iterations, threshold 7.5).
  2. Final cheap scorer (gpt-4o-mini) assigns rubric scores + PASS/FAIL.
  3. PASS → await_approval; FAIL (after max revisions) → still forward to human.

Scoring rubric (0–10 each):
  - brand_fit:    Does it match the tone/voice in the brand examples?
  - clarity:      Is the message clear and jargon-free?
  - cta_strength: Is the call-to-action compelling and specific?
"""

import re
from pathlib import Path

from openai import AsyncOpenAI

from zeta_ima.agents.state import AgentState
from zeta_ima.agents.reflection import make_reflection_loop
from zeta_ima.config import settings

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "review_agent.md"
MAX_AUTO_REVISIONS = 2  # After this many FAIL loops, force it to await_approval anyway


def _parse_review(raw: str) -> dict:
    """
    Extract structured fields from the review LLM output.
    Falls back gracefully if the model doesn't follow the format exactly.
    """
    scores = {}
    for field in ("brand_fit", "clarity", "cta_strength"):
        m = re.search(rf"{field}[:\s]+(\d+)", raw, re.IGNORECASE)
        scores[field] = int(m.group(1)) if m else None

    passed = bool(re.search(r"\bPASS\b", raw, re.IGNORECASE))
    reason_m = re.search(r"Reason[:\s]+(.+)", raw, re.IGNORECASE)
    reason = reason_m.group(1).strip() if reason_m else ""

    return {"raw": raw, "passed": passed, "scores": scores, "reason": reason}


async def review_node(state: AgentState) -> dict:
    """Actor-Critic reflection pass, then final scoring."""
    brand_sample = "\n".join(state.get("brand_examples", [])[:2]) or "No examples available."
    brief = state["current_brief"]
    draft_text = state["current_draft"]["text"]
    iteration = state.get("iteration_count", 0)

    # ── Phase 1: Actor-Critic Reflection ────────────────────────────────────
    reflection_result = None
    polished_draft = draft_text
    try:
        loop = make_reflection_loop(mode="multi", max_iterations=3, threshold=7.5)
        reflection_result = await loop.run(
            draft=draft_text,
            brief=brief,
            brand_guidelines=brand_sample,
            lenses=["brand", "audience"],
        )
        polished_draft = reflection_result.final_draft
    except Exception:
        pass  # Fallback to original draft if reflection fails

    # ── Phase 2: Final rubric scoring ────────────────────────────────────────
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    system_prompt = _PROMPT_PATH.read_text()

    prompt = (
        f"Brief: {brief}\n\n"
        f"Draft:\n{polished_draft}\n\n"
        f"Brand examples used:\n{brand_sample}\n\n"
        "Score each dimension (0-10):\n"
        "  brand_fit: <score>\n"
        "  clarity: <score>\n"
        "  cta_strength: <score>\n"
        "Decision: PASS | FAIL\n"
        "Reason: <one sentence>"
    )

    resp = await client.chat.completions.create(
        model=settings.llm_review,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    raw = resp.choices[0].message.content
    review = _parse_review(raw)

    # Force to human review after MAX_AUTO_REVISIONS even if FAIL
    force_human = iteration > MAX_AUTO_REVISIONS
    next_stage = "awaiting_approval" if (review["passed"] or force_human) else "drafting"

    # Attach reflection metadata to review result
    if reflection_result:
        review["reflection"] = {
            "iterations": reflection_result.iterations_used,
            "converged": reflection_result.converged,
            "final_score": reflection_result.final_score,
        }

    return {
        "review_result": review,
        "stage": next_stage,
        "current_draft": {**state["current_draft"], "text": polished_draft},
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"[Review #{iteration}] "
                    f"{'PASS' if review['passed'] else 'FAIL'} — {review['reason']}"
                    + (
                        f" (reflection: {reflection_result.iterations_used} iterations, "
                        f"score {reflection_result.final_score:.1f})"
                        if reflection_result else ""
                    )
                    + (" (forcing human review after max revisions)" if force_human and not review["passed"] else "")
                ),
            }
        ],
    }
