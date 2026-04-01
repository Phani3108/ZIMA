"""
Structured Feedback — collects user ratings, tags, and comments on outputs.

Wired into the approval flow: after approve/reject, feedback is recorded and
contributes to team learning profiles and prompt evolution.

Usage::

    from zeta_ima.memory.feedback import record_feedback, get_feedback_summary
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

FEEDBACK_CONTAINER = "feedback_entries"

# Standard feedback tags (multi-select in approval card)
FEEDBACK_TAGS = [
    "Tone perfect",
    "Great CTA",
    "On-brand",
    "Too formal",
    "Too casual",
    "Off-brand",
    "Too long",
    "Too short",
    "Wrong format",
    "Missing key info",
    "Great structure",
    "Needs more data",
]


async def record_feedback(
    team_id: str,
    user_id: str,
    workflow_id: str = "",
    stage_id: str = "",
    skill_id: str = "",
    rating: int = 0,
    tags: list[str] | None = None,
    free_text: str = "",
) -> str:
    """
    Record structured feedback from a user.

    Called from approval_node when processing approve/reject card data.
    """
    from zeta_ima.infra.document_store import get_document_store

    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    ds = get_document_store()
    await ds.upsert(FEEDBACK_CONTAINER, {
        "id": entry_id,
        "team_id": team_id,
        "user_id": user_id,
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "skill_id": skill_id,
        "rating": max(0, min(5, rating)),
        "tags": tags or [],
        "free_text": free_text,
        "created_at": now.isoformat(),
    })

    log.info(
        "Recorded feedback %s: team=%s rating=%d tags=%s",
        entry_id, team_id, rating, tags,
    )
    return entry_id


async def get_feedback_summary(
    team_id: str,
    skill_id: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """
    Aggregate feedback for a team (optionally filtered by skill).

    Returns: {avg_rating, total_count, tag_counts, recent_comments}
    """
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    filters: dict[str, Any] = {"team_id": team_id}
    if skill_id:
        filters["skill_id"] = skill_id

    entries = await ds.query(FEEDBACK_CONTAINER, filters=filters, limit=limit)

    if not entries:
        return {"avg_rating": 0.0, "total_count": 0, "tag_counts": {}, "recent_comments": []}

    ratings = [e.get("rating", 0) for e in entries if e.get("rating", 0) > 0]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

    tag_counts: dict[str, int] = {}
    for entry in entries:
        for tag in entry.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    recent_comments = [
        {"text": e["free_text"], "rating": e.get("rating", 0), "created_at": e.get("created_at")}
        for e in entries[:10]
        if e.get("free_text")
    ]

    return {
        "avg_rating": round(avg_rating, 1),
        "total_count": len(entries),
        "tag_counts": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)),
        "recent_comments": recent_comments,
    }


async def get_feedback_trend(
    team_id: str,
    skill_id: str = "",
    limit: int = 100,
) -> list[dict]:
    """Return recent feedback entries for trend analysis."""
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    filters: dict[str, Any] = {"team_id": team_id}
    if skill_id:
        filters["skill_id"] = skill_id

    return await ds.query(FEEDBACK_CONTAINER, filters=filters, limit=limit)
