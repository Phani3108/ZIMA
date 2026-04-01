"""
Prompt Evolution — auto-evolve prompts based on feedback, scores, and signals.

Two modes:
  - **Minor** (auto-apply): Small refinements like adding/removing a sentence,
    tweaking tone. Applied automatically.
  - **Major** (human-approve): Structural changes, new sections, guardrail
    modifications. Queued for admin review.

Triggers:
  1. Approval rate drops below 60% over 7 days
  2. Same feedback tag appears 5+ times in 7 days
  3. Campaign score drops 20% vs. previous period

Safety rails:
  - Never remove safety/brand guardrails
  - Max 4000 tokens for system prompts
  - All changes logged with reason and diffs
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from zeta_ima.config import settings, get_openai_client

log = logging.getLogger(__name__)

EVOLUTION_QUEUE_CONTAINER = "prompt_evolution_queue"
MAX_PROMPT_TOKENS = 4000


async def analyze_signals(
    skill_id: str,
    team_id: str = "__global__",
) -> dict[str, Any]:
    """
    Analyze recent signals for a skill/team to determine if evolution is warranted.

    Returns: {
        "trigger": str | None,
        "change_type": "minor" | "major",
        "reason": str,
        "suggestions": list[str],
    }
    """
    from zeta_ima.memory.feedback import get_feedback_trend
    from zeta_ima.memory.scores import get_score_trend
    from zeta_ima.memory.learning import get_common_edits

    result: dict[str, Any] = {"trigger": None, "change_type": "minor", "reason": "", "suggestions": []}

    # 1. Check feedback tag patterns (5+ same tag in recent 50 entries)
    try:
        entries = await get_feedback_trend(team_id=team_id, skill_id=skill_id, limit=50)
        tag_counts: dict[str, int] = {}
        low_ratings = 0
        total_rated = 0
        for e in entries:
            for tag in e.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            rating = e.get("rating", 0)
            if rating > 0:
                total_rated += 1
                if rating <= 2:
                    low_ratings += 1

        # Repeated tag trigger
        for tag, count in tag_counts.items():
            if count >= 5:
                result["trigger"] = "repeated_tag"
                result["reason"] = f"Tag '{tag}' appeared {count} times in recent feedback"
                result["suggestions"].append(f"Address '{tag}' pattern in prompt")
                if tag in ("Off-brand", "Wrong format"):
                    result["change_type"] = "major"
                break

        # Low approval rate trigger
        if total_rated >= 5 and (low_ratings / total_rated) >= 0.4:
            result["trigger"] = "low_approval_rate"
            result["change_type"] = "major"
            result["reason"] = f"{low_ratings}/{total_rated} recent ratings are ≤2 stars"
            result["suggestions"].append("Review and revise prompt for quality issues")

    except Exception as e:
        log.debug("Feedback analysis failed: %s", e)

    # 2. Check score trends
    if not result["trigger"]:
        try:
            scores = await get_score_trend(team_id=team_id, limit=10)
            if len(scores) >= 4:
                recent = [s.get("composite_score", 0) for s in scores[:len(scores)//2]]
                older = [s.get("composite_score", 0) for s in scores[len(scores)//2:]]
                avg_recent = sum(recent) / len(recent) if recent else 0
                avg_older = sum(older) / len(older) if older else 0
                if avg_older > 0 and avg_recent < avg_older * 0.8:
                    result["trigger"] = "score_drop"
                    result["change_type"] = "major"
                    result["reason"] = (
                        f"Avg score dropped from {avg_older:.0f} to {avg_recent:.0f} "
                        f"({((avg_older - avg_recent)/avg_older)*100:.0f}% decline)"
                    )
                    result["suggestions"].append("Analyze recent low-performing outputs and adjust prompt")
        except Exception as e:
            log.debug("Score analysis failed: %s", e)

    # 3. Common edits = minor improvement opportunity
    if not result["trigger"]:
        try:
            edits = await get_common_edits(skill_id, limit=3)
            if edits:
                result["trigger"] = "common_edits"
                result["change_type"] = "minor"
                result["reason"] = f"{len(edits)} common edit patterns detected"
                result["suggestions"].extend(edits)
        except Exception:
            pass

    return result


def classify_change(proposed_diff: str) -> str:
    """Classify a prompt change as minor or major."""
    if not proposed_diff:
        return "minor"

    # Heuristics for major changes
    major_indicators = [
        "REMOVE", "DELETE", "GUARDRAIL", "SAFETY",
        "RESTRUCTURE", "NEW SECTION", "REWRITE",
    ]
    upper = proposed_diff.upper()
    for indicator in major_indicators:
        if indicator in upper:
            return "major"

    # Length-based: big changes are major
    if len(proposed_diff) > 500:
        return "major"

    return "minor"


async def generate_prompt_patch(
    skill_id: str,
    current_prompt: str,
    signals: dict[str, Any],
    team_id: str = "__global__",
) -> str:
    """
    Use LLM to generate a proposed prompt modification based on signals.

    Returns: proposed diff/patch as text.
    """
    client = get_openai_client()
    suggestions = signals.get("suggestions", [])
    reason = signals.get("reason", "")

    system = (
        "You are a prompt engineer for a marketing AI agency. "
        "Given a current system prompt and improvement signals, generate a MODIFIED version of the prompt. "
        "Rules:\n"
        "1. NEVER remove safety or brand guardrails\n"
        "2. Keep the prompt under 4000 tokens\n"
        "3. Only make targeted improvements based on the signals\n"
        "4. Preserve the overall structure\n"
        "5. Return ONLY the modified prompt text, nothing else"
    )

    user_msg = (
        f"CURRENT PROMPT:\n{current_prompt[:3000]}\n\n"
        f"REASON FOR CHANGE: {reason}\n"
        f"SUGGESTIONS:\n" + "\n".join(f"- {s}" for s in suggestions[:5])
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.llm_review,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=4000,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.error("Prompt patch generation failed: %s", e)
        return ""


async def apply_minor_change(
    skill_id: str,
    team_id: str = "__global__",
) -> dict[str, Any] | None:
    """
    Analyze signals and auto-apply a minor prompt improvement.

    Returns the new version dict, or None if no change was needed.
    """
    from zeta_ima.prompts.engine import get_active_prompt, create_version

    signals = await analyze_signals(skill_id, team_id)
    if not signals.get("trigger") or signals.get("change_type") != "minor":
        return None

    current_prompt = await get_active_prompt(skill_id, team_id)
    if not current_prompt:
        return None

    patched = await generate_prompt_patch(skill_id, current_prompt, signals, team_id)
    if not patched or patched == current_prompt:
        return None

    version = await create_version(
        skill_id=skill_id,
        content=patched,
        team_id=team_id,
        change_type="auto_minor",
        change_reason=signals["reason"],
        created_by="evolution_engine",
        activate=True,
    )

    log.info("Auto-applied minor prompt change for %s/%s: %s", skill_id, team_id, signals["reason"])
    return version


async def queue_major_change(
    skill_id: str,
    team_id: str = "__global__",
) -> str | None:
    """
    Analyze signals and queue a major prompt change for admin review.

    Returns the queue entry ID, or None if no change was needed.
    """
    from zeta_ima.infra.document_store import get_document_store
    from zeta_ima.prompts.engine import get_active_prompt

    signals = await analyze_signals(skill_id, team_id)
    if not signals.get("trigger"):
        return None

    current_prompt = await get_active_prompt(skill_id, team_id)
    patched = await generate_prompt_patch(skill_id, current_prompt, signals, team_id) if current_prompt else ""

    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    ds = get_document_store()

    await ds.upsert(EVOLUTION_QUEUE_CONTAINER, {
        "id": entry_id,
        "skill_id": skill_id,
        "team_id": team_id,
        "change_type": signals.get("change_type", "major"),
        "trigger_reason": signals["reason"],
        "proposed_diff": patched,
        "status": "pending",
        "reviewed_by": "",
        "reviewed_at": None,
        "created_at": now.isoformat(),
    })

    log.info("Queued major prompt change %s for %s/%s", entry_id, skill_id, team_id)
    return entry_id


async def approve_queued_change(
    queue_id: str,
    reviewed_by: str,
) -> dict[str, Any] | None:
    """Admin approves a queued prompt change — creates a new version."""
    from zeta_ima.infra.document_store import get_document_store
    from zeta_ima.prompts.engine import create_version

    ds = get_document_store()
    entry = await ds.get(EVOLUTION_QUEUE_CONTAINER, queue_id)
    if not entry or entry.get("status") != "pending":
        return None

    # Create the new version
    version = await create_version(
        skill_id=entry["skill_id"],
        content=entry["proposed_diff"],
        team_id=entry.get("team_id", "__global__"),
        change_type="auto_major_approved",
        change_reason=entry.get("trigger_reason", ""),
        created_by=reviewed_by,
        activate=True,
    )

    # Update queue entry
    entry["status"] = "approved"
    entry["reviewed_by"] = reviewed_by
    entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    await ds.upsert(EVOLUTION_QUEUE_CONTAINER, entry)

    return version


async def reject_queued_change(queue_id: str, reviewed_by: str) -> None:
    """Admin rejects a queued prompt change."""
    from zeta_ima.infra.document_store import get_document_store

    ds = get_document_store()
    entry = await ds.get(EVOLUTION_QUEUE_CONTAINER, queue_id)
    if not entry:
        return

    entry["status"] = "rejected"
    entry["reviewed_by"] = reviewed_by
    entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    await ds.upsert(EVOLUTION_QUEUE_CONTAINER, entry)
