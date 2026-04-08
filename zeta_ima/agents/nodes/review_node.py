"""
Review Agent node — Actor-Critic quality gate (Genesis v2).

Flow:
  1. Read A2A handoff from copy/design agents for context
  2. Actor-Critic ReflectionLoop polishes the draft (up to 3 iterations, threshold 7.5).
  3. Final cheap scorer (gpt-4o-mini) assigns rubric scores + PASS/FAIL.
  4. Persist reflection insights to learning memory (closes the loop).
  5. Emit A2A feedback message for downstream agents.
  6. PASS → await_approval; FAIL (after max revisions) → still forward to human.

Scoring rubric (0–10 each):
  - brand_fit:    Does it match the tone/voice in the brand examples?
  - clarity:      Is the message clear and jargon-free?
  - cta_strength: Is the call-to-action compelling and specific?
"""

import logging
import re
from pathlib import Path

from zeta_ima.agents.state import AgentState
from zeta_ima.agents.roles import role_registry
from zeta_ima.agents.reflection import make_reflection_loop
from zeta_ima.config import settings, get_openai_client
from zeta_ima.orchestrator.a2a import AgentMessage, emit, emit_step, get_latest_handoff

log = logging.getLogger(__name__)

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
    """Actor-Critic reflection pass, then final scoring, then persist insights."""
    brand_sample = "\n".join(state.get("brand_examples", [])[:2]) or "No examples available."
    brief = state["current_brief"]
    draft_text = state["current_draft"]["text"]
    iteration = state.get("iteration_count", 0)
    agent_messages = list(state.get("agent_messages", []))

    # ── Read A2A review criteria from PM ────────────────────────────────────
    extra_criteria = ""
    handoff = get_latest_handoff(agent_messages, "review")
    if handoff and handoff.handoff_instructions:
        extra_criteria = f"\n\nPM Review Criteria: {handoff.handoff_instructions}"

    # ── Phase 1: Actor-Critic Reflection ────────────────────────────────────
    agent_messages.append(emit_step("review", "Running reflection loop", 0, 4, "started").to_dict())
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
    agent_messages.append(emit_step("review", "Running reflection loop", 0, 4, "completed",
        f"{reflection_result.iterations_used} iterations, score {reflection_result.final_score:.1f}" if reflection_result else "Skipped").to_dict())

    # ── Phase 2: Final rubric scoring ────────────────────────────────────────    agent_messages.append(emit_step("review", "Scoring against rubric", 1, 4, "started").to_dict())    client = get_openai_client()
    base_prompt = _PROMPT_PATH.read_text()
    role = role_registry.get_by_node("review")
    system_prompt = f"{role.system_prompt_prefix()}\n\n{base_prompt}" if role else base_prompt

    prompt = (
        f"Brief: {brief}\n\n"
        f"Draft:\n{polished_draft}\n\n"
        f"Brand examples used:\n{brand_sample}\n\n"
        + extra_criteria +
        "\nScore each dimension (0-10):\n"
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
    agent_messages.append(emit_step("review", "Scoring against rubric", 1, 4, "completed",
        f"{'PASS' if review['passed'] else 'FAIL'} — brand_fit:{review['scores'].get('brand_fit')}").to_dict())

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
        # Serialize reflection steps for persistence in memory_node
        review["_reflection_steps"] = [
            {
                "iteration": s.iteration,
                "critique": s.critique,
                "score": s.score,
                "passed": s.passed,
                "improvements": s.improvements,
            }
            for s in reflection_result.steps
        ]

    # ── Phase 3: Persist reflection insights immediately ─────────────────────
    if reflection_result and reflection_result.steps:
        try:
            from zeta_ima.memory.learning import persist_reflection_insights
            await persist_reflection_insights(
                skill_id=state.get("intent", "copy"),
                reflection_steps=review.get("_reflection_steps", []),
                brief=brief,
                user_id=state.get("user_id", "system"),
            )
        except Exception as e:
            log.debug("Reflection persistence failed: %s", e)

    # ── Phase 4: Emit A2A feedback message ───────────────────────────────────
    agent_messages.append(emit(
        "review", "approval", "feedback",
        payload={
            "scores": review.get("scores", {}),
            "passed": review.get("passed", False),
            "reason": review.get("reason", ""),
        },
        context_summary=(
            f"Review {'PASS' if review['passed'] else 'FAIL'}: {review.get('reason', '')}"
        ),
    ).to_dict())

    # ── Phase 5: Confidence-gated auto-approval ──────────────────────────────    agent_messages.append(emit_step("review", "Checking auto-approval", 2, 4, "started").to_dict())    auto_approved = False
    if review["passed"] and settings.auto_approve_enabled:
        scores = review.get("scores", {})
        all_above_min = all(
            (v or 0) >= settings.auto_approve_min_score
            for v in scores.values()
            if v is not None
        )
        brand_fit_ok = (scores.get("brand_fit") or 0) >= settings.auto_approve_brand_fit
        if all_above_min and brand_fit_ok:
            auto_approved = True
            next_stage = "done"
            agent_messages.append(emit(
                "review", "all", "status_update",
                payload={"auto_approved": True, "scores": scores},
                context_summary="Auto-approved: all scores exceeded thresholds.",
            ).to_dict())

    agent_messages.append(emit_step("review", "Checking auto-approval", 2, 4, "completed",
        "Auto-approved" if auto_approved else "Requires human approval").to_dict())
    agent_messages.append(emit_step("review", "Review complete", 3, 4, "completed",
        f"{'PASS' if review['passed'] else 'FAIL'} — {review.get('reason', '')[:100]}").to_dict())

    result = {
        "review_result": review,
        "stage": next_stage,
        "current_draft": {**state["current_draft"], "text": polished_draft},
        "agent_messages": agent_messages,
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
                    + (" ✅ Auto-approved (high confidence)" if auto_approved else "")
                ),
            }
        ],
    }
    if auto_approved:
        result["approval_decision"] = "approve"
    return result
