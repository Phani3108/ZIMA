"""
Team Learning Profile — per-team aggregated preferences and patterns.

Each team has a profile that summarises:
  - Tone & format preferences (from feedback tags)
  - Common edit patterns (from workflow outcomes)
  - Top performing content (from campaign scores)
  - Feedback averages
  - Signal count

Profiles are rebuilt periodically or on demand.

Usage::

    from zeta_ima.memory.team_profile import get_or_create_profile, get_team_guidance
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

PROFILE_CONTAINER = "team_learning_profiles"


async def get_or_create_profile(team_id: str) -> dict[str, Any]:
    """Get the team's learning profile, creating it if it doesn't exist."""
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    profiles = await ds.query(PROFILE_CONTAINER, filters={"team_id": team_id}, limit=1)
    if profiles:
        return profiles[0]

    # Create new empty profile
    profile = {
        "id": str(uuid.uuid4()),
        "team_id": team_id,
        "tone_preferences": {},
        "format_preferences": {},
        "common_edits": [],
        "top_performing": [],
        "feedback_summary": {},
        "score_averages": {},
        "signal_count": 0,
        "last_rebuilt_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await ds.upsert(PROFILE_CONTAINER, profile)
    return profile


async def rebuild_profile(team_id: str) -> dict[str, Any]:
    """
    Rebuild the team profile from all available signals.

    Aggregates:
    1. Feedback tags → tone/format preferences
    2. Workflow outcomes → common edits
    3. Campaign scores → top performers + averages
    4. Learning signals → signal count
    """
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    profile = await get_or_create_profile(team_id)
    now = datetime.now(timezone.utc)

    # 1. Feedback analysis
    feedback_entries = await ds.query("feedback_entries", filters={"team_id": team_id}, limit=200)
    tone_prefs: dict[str, int] = {}
    format_prefs: dict[str, int] = {}
    tone_tags = {"Tone perfect", "Too formal", "Too casual", "On-brand", "Off-brand"}
    format_tags = {"Too long", "Too short", "Great structure", "Missing key info", "Great CTA", "Wrong format"}

    ratings: list[int] = []
    for entry in feedback_entries:
        if entry.get("rating", 0) > 0:
            ratings.append(entry["rating"])
        for tag in entry.get("tags", []):
            if tag in tone_tags:
                tone_prefs[tag] = tone_prefs.get(tag, 0) + 1
            elif tag in format_tags:
                format_prefs[tag] = format_prefs.get(tag, 0) + 1

    # 2. Campaign scores
    score_entries = await ds.query("campaign_scores", filters={"team_id": team_id}, limit=100)
    score_values = [s.get("composite_score", 0) for s in score_entries if s.get("composite_score", 0) > 0]

    top_performing = sorted(
        [s for s in score_entries if s.get("composite_score", 0) >= 70],
        key=lambda x: x.get("composite_score", 0),
        reverse=True,
    )[:5]

    # 3. Common edits (from workflow_outcomes via learning.py)
    common_edits: list[str] = []
    try:
        from zeta_ima.memory.learning import get_common_edits
        common_edits = await get_common_edits("copy", limit=10)
    except Exception:
        pass

    # 4. Count signals
    signal_count = len(feedback_entries) + len(score_entries)

    # Update profile
    updated = {
        "id": profile["id"],
        "team_id": team_id,
        "tone_preferences": dict(sorted(tone_prefs.items(), key=lambda x: x[1], reverse=True)),
        "format_preferences": dict(sorted(format_prefs.items(), key=lambda x: x[1], reverse=True)),
        "common_edits": common_edits,
        "top_performing": [
            {"campaign_id": t.get("campaign_id"), "score": t.get("composite_score")}
            for t in top_performing
        ],
        "feedback_summary": {
            "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
            "total_feedback": len(feedback_entries),
        },
        "score_averages": {
            "avg_composite": round(sum(score_values) / len(score_values), 1) if score_values else 0.0,
            "total_scored": len(score_values),
        },
        "signal_count": signal_count,
        "last_rebuilt_at": now.isoformat(),
        "created_at": profile.get("created_at", now.isoformat()),
        "updated_at": now.isoformat(),
    }

    await ds.upsert(PROFILE_CONTAINER, updated)
    log.info("Rebuilt team profile for %s: %d signals", team_id, signal_count)
    return updated


async def get_team_guidance(team_id: str) -> str:
    """
    Build a guidance block for injection into agent prompts.

    Combines team profile insights with learning guidance.
    """
    profile = await get_or_create_profile(team_id)
    parts: list[str] = []

    # Tone preferences
    tone = profile.get("tone_preferences", {})
    if tone:
        positive = [k for k, v in tone.items() if k in ("Tone perfect", "On-brand") and v >= 2]
        negative = [k for k, v in tone.items() if k in ("Too formal", "Too casual", "Off-brand") and v >= 2]
        if positive:
            parts.append(f"TEAM TONE (liked): {', '.join(positive)}")
        if negative:
            parts.append(f"TEAM TONE (avoid): {', '.join(negative)}")

    # Format preferences
    fmt = profile.get("format_preferences", {})
    if fmt:
        issues = [k for k, v in fmt.items() if v >= 2]
        if issues:
            parts.append(f"TEAM FORMAT NOTES: {', '.join(issues)}")

    # Common edits
    edits = profile.get("common_edits", [])
    if edits:
        parts.append("TEAM COMMON CORRECTIONS:")
        for i, edit in enumerate(edits[:5], 1):
            parts.append(f"  {i}. {edit}")

    # Score insight
    scores = profile.get("score_averages", {})
    avg = scores.get("avg_composite", 0)
    if avg > 0:
        parts.append(f"TEAM AVG CAMPAIGN SCORE: {avg}/100 (from {scores.get('total_scored', 0)} campaigns)")

    return "\n".join(parts) if parts else ""
