"""
Proactive Recall — "You've Done This Before" engine.

Searches brand_voice, conversation_archive, and campaign_scores to find
similar prior work. Returns a ranked list so the user can choose to reuse
an approach, modify it, or start fresh.

Ranking formula: similarity × score_boost × recency_decay

Usage::

    from zeta_ima.memory.recall import check_prior_work
    result = await check_prior_work(team_id="t1", brief="Launch email for Q2 promo")
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

# Decay half-life in days — older work gets lower weight
RECENCY_HALF_LIFE_DAYS = 90
# Minimum similarity to include
MIN_SIMILARITY = 0.55
# Confidence threshold for proactive recommendation
CONFIDENCE_THRESHOLD = 0.7


@dataclass
class PriorWorkItem:
    id: str
    source: str  # "brand_voice" | "conversation_archive" | "campaign_score"
    brief: str
    text_preview: str
    similarity: float
    campaign_score: float = 0.0
    recency_days: float = 0.0
    final_rank: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class PriorWorkResult:
    similar_briefs: list[PriorWorkItem]
    recommendation: str  # "reuse" | "modify" | "start_fresh" | "none"
    confidence: float
    message: str


def _recency_decay(days_old: float) -> float:
    """Exponential decay based on age in days."""
    return math.exp(-0.693 * days_old / RECENCY_HALF_LIFE_DAYS)


def _score_boost(campaign_score: float) -> float:
    """Boost factor from campaign performance score (0-100 scale)."""
    if campaign_score <= 0:
        return 1.0  # No score data = neutral
    # Normalize to 0.5 - 1.5 range
    return 0.5 + (campaign_score / 100.0)


def _days_since(iso_date: str) -> float:
    """Parse ISO date and return days since."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    except Exception:
        return 365.0  # Default to ~1 year old if unparseable


async def check_prior_work(
    team_id: str,
    brief: str,
    top_k: int = 5,
) -> PriorWorkResult:
    """
    Search all memory sources for similar past work.

    Returns ranked items + an overall recommendation.
    """
    if not brief.strip():
        return PriorWorkResult(
            similar_briefs=[], recommendation="none", confidence=0.0,
            message="No brief provided.",
        )

    items: list[PriorWorkItem] = []

    # 1. Search conversation archive
    try:
        from zeta_ima.memory.conversation_archive import get_similar_sessions
        sessions = await get_similar_sessions(team_id=team_id, brief=brief, limit=top_k)
        for s in sessions:
            items.append(PriorWorkItem(
                id=s["id"],
                source="conversation_archive",
                brief=s.get("brief", ""),
                text_preview=s.get("brief", "")[:200],
                similarity=s.get("score", 0.0),
                recency_days=_days_since(s.get("created_at", "")),
                metadata={"pipeline_id": s.get("pipeline_id", ""), "outcome": s.get("outcome", "")},
            ))
    except Exception as e:
        log.debug("Recall: conversation archive search failed: %s", e)

    # 2. Search brand voice examples
    try:
        from zeta_ima.memory.brand import _embed
        from zeta_ima.infra.vector_store import get_vector_store
        vector = await _embed(brief[:2000])
        vs = get_vector_store()
        brand_hits = vs.search(
            collection=settings.qdrant_collection,
            query_vector=vector,
            top_k=top_k,
            score_threshold=MIN_SIMILARITY,
        )
        for h in brand_hits:
            payload = h.get("payload", {})
            items.append(PriorWorkItem(
                id=h["id"],
                source="brand_voice",
                brief=payload.get("brief", ""),
                text_preview=payload.get("text", "")[:200],
                similarity=h["score"],
                recency_days=_days_since(payload.get("approved_at", payload.get("created_at", ""))),
                metadata={"channel": payload.get("channel", "")},
            ))
    except Exception as e:
        log.debug("Recall: brand voice search failed: %s", e)

    # 3. Enrich with campaign scores (if available)
    try:
        from zeta_ima.infra.document_store import get_document_store
        ds = get_document_store()
        for item in items:
            if item.source == "conversation_archive" and item.id:
                scores = await ds.query(
                    "campaign_scores",
                    filters={"workflow_id": item.id, "team_id": team_id},
                    limit=1,
                )
                if scores:
                    item.campaign_score = scores[0].get("composite_score", 0.0)
    except Exception as e:
        log.debug("Recall: score enrichment failed: %s", e)

    # 4. Compute final ranking
    for item in items:
        decay = _recency_decay(item.recency_days)
        boost = _score_boost(item.campaign_score)
        item.final_rank = item.similarity * boost * decay

    # Sort by final rank, deduplicate by brief similarity
    items.sort(key=lambda x: x.final_rank, reverse=True)
    seen_briefs: set[str] = set()
    unique_items: list[PriorWorkItem] = []
    for item in items:
        brief_key = item.brief[:100].lower().strip()
        if brief_key and brief_key in seen_briefs:
            continue
        seen_briefs.add(brief_key)
        unique_items.append(item)
        if len(unique_items) >= top_k:
            break

    # 5. Generate recommendation
    if not unique_items:
        return PriorWorkResult(
            similar_briefs=[], recommendation="start_fresh", confidence=0.0,
            message="No similar past work found. Starting fresh.",
        )

    best = unique_items[0]
    if best.final_rank >= CONFIDENCE_THRESHOLD and best.campaign_score >= 70:
        recommendation = "reuse"
        confidence = min(best.final_rank, 1.0)
        message = (
            f"Found strong match (score: {best.final_rank:.0%}). "
            f"Campaign scored {best.campaign_score:.0f}/100. Recommend reusing this approach."
        )
    elif best.final_rank >= MIN_SIMILARITY:
        recommendation = "modify"
        confidence = min(best.final_rank, 1.0)
        message = (
            f"Found {len(unique_items)} similar past briefs (best match: {best.final_rank:.0%}). "
            "Consider modifying a previous approach."
        )
    else:
        recommendation = "start_fresh"
        confidence = 1.0 - best.final_rank
        message = "Past work found but not closely matching. Recommend starting fresh."

    return PriorWorkResult(
        similar_briefs=unique_items,
        recommendation=recommendation,
        confidence=confidence,
        message=message,
    )
