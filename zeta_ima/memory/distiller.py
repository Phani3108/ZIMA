"""
Conversation Distiller — Phase 2.2

Extracts persistent knowledge from a finished conversation session and routes it to:
  - Agency Brain  (directional / strategic insights)
  - Learning Memory  (tacticial copy/design patterns)

Distillation triggers:
  1. On conversation end  → called from session lifecycle in app.py
  2. On-demand button     → POST /api/sessions/{id}/distill
  3. Sprint compaction    → scheduled compact_sprint() at brain_compact_hour
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from zeta_ima.config import settings
from zeta_ima.integrations.vault import vault

# ── Prompt ──────────────────────────────────────────────────────────────────

_DISTILL_SYSTEM = """You are a knowledge distiller for a marketing AI agency.
Given a conversation transcript, extract ONLY durable knowledge items
that should persist and inform future work.

Return a JSON array.  Each item:
{
  "type": "directional" | "tactical",
  "level": "zeta" | "team" | "personal",
  "text": "concise knowledge statement",
  "confidence": 0.0–1.0,
  "category": "brand_voice" | "copy_pattern" | "design_guideline" | "process" | "client_preference" | "market_insight",
  "tags": ["tag1", "tag2"]
}

Directional: strategic rules, brand positioning, recurring preferences, process improvements.
Tactical: prompt patterns that worked, copy formulas, design choices that were approved.
Personal level: tagged to a specific user's style.
Team level: applies to this team/account.
Zeta level: applies across the whole agency.

Skip transient conversation noise. Only include items with confidence ≥ 0.70.
Return [] if nothing meaningful is found.
"""


@dataclass
class DistilledKnowledge:
    type: str           # "directional" | "tactical"
    level: str          # "zeta" | "team" | "personal"
    text: str
    confidence: float
    category: str
    tags: list[str] = field(default_factory=list)
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Core distiller ───────────────────────────────────────────────────────────

async def distill_conversation(
    messages: list[dict[str, Any]],
    user_id: str,
    user_role: str = "member",
    session_id: str | None = None,
) -> list[DistilledKnowledge]:
    """
    Distill a list of chat messages into persistent knowledge items.

    Args:
        messages:   Chat turns — each dict with "role" and "content" keys.
        user_id:    The primary user of the session.
        user_role:  Used to weight directional signals.
        session_id: Optional — stored as source_interaction_id.

    Returns:
        List of DistilledKnowledge items (already persisted to brain + learning).
    """
    if not messages:
        return []

    transcript = _format_transcript(messages)
    if len(transcript) < 100:
        return []

    raw_items = await _call_llm_distill(transcript)
    if not raw_items:
        return []

    items: list[DistilledKnowledge] = []
    for raw in raw_items:
        if raw.get("confidence", 0) < 0.70:
            continue
        items.append(
            DistilledKnowledge(
                type=raw.get("type", "tactical"),
                level=raw.get("level", "personal"),
                text=raw.get("text", "").strip(),
                confidence=float(raw.get("confidence", 0.75)),
                category=raw.get("category", "copy_pattern"),
                tags=raw.get("tags", []),
            )
        )

    # Persist in parallel
    await asyncio.gather(
        *[_persist_item(item, user_id, user_role, session_id) for item in items],
        return_exceptions=True,
    )
    return items


async def should_distill(message_count: int, has_approval: bool) -> bool:
    """Return True when a session is worth distilling."""
    return has_approval or message_count >= 8


# ── Sprint compaction ────────────────────────────────────────────────────────

async def compact_sprint(days_back: int = 7) -> dict[str, int]:
    """
    Nightly compaction: summarise the last N days of directional signals
    into durable agency-level rules.  Called by the scheduler at brain_compact_hour.

    Returns count dict {"compacted": N, "new_brain_entries": M}.
    """
    try:
        from zeta_ima.memory.learning import get_directional_signals
        from zeta_ima.memory.brain import agency_brain

        signals = await get_directional_signals(level="zeta", top_k=200)
        if not signals:
            return {"compacted": 0, "new_brain_entries": 0}

        combined = "\n".join(f"- {s['signal_text']}" for s in signals[:100])
        compact_items = await _call_llm_compact(combined)

        new_entries = 0
        for item in compact_items:
            await agency_brain.contribute(
                {
                    "text": item.get("text", ""),
                    "category": item.get("category", "process"),
                    "level": "zeta",
                    "confidence": item.get("confidence", 0.80),
                    "tags": item.get("tags", ["compacted"]),
                },
                user_id="system",
            )
            new_entries += 1

        return {"compacted": len(signals), "new_brain_entries": new_entries}
    except Exception as exc:
        return {"compacted": 0, "new_brain_entries": 0, "error": str(exc)}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_transcript(messages: list[dict]) -> str:
    parts = []
    for m in messages[-40:]:  # last 40 turns maximum
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        parts.append(f"{role.upper()}: {content}")
    return "\n".join(parts)


async def _call_llm_distill(transcript: str) -> list[dict]:
    import json
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    resp = await client.chat.completions.create(
        model=settings.signal_extraction_model,
        messages=[
            {"role": "system", "content": _DISTILL_SYSTEM},
            {"role": "user", "content": f"TRANSCRIPT:\n{transcript}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=1500,
    )
    text = resp.choices[0].message.content or "[]"
    data = json.loads(text)
    return data if isinstance(data, list) else data.get("items", [])


async def _call_llm_compact(signals_text: str) -> list[dict]:
    import json
    from openai import AsyncOpenAI

    compact_prompt = (
        "Synthesise the following learning signals into 5–15 durable agency-level rules.\n"
        "Return JSON array with same schema as the distiller.\n"
        f"SIGNALS:\n{signals_text}"
    )
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    resp = await client.chat.completions.create(
        model=settings.signal_extraction_model,
        messages=[
            {"role": "system", "content": _DISTILL_SYSTEM},
            {"role": "user", "content": compact_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=1000,
    )
    text = resp.choices[0].message.content or "[]"
    data = json.loads(text)
    return data if isinstance(data, list) else data.get("items", [])


async def _persist_item(
    item: DistilledKnowledge,
    user_id: str,
    user_role: str,
    session_id: str | None,
) -> None:
    """Route a distilled item to the correct storage backend."""
    if item.type == "directional":
        from zeta_ima.memory.learning import record_directional_signal
        await record_directional_signal(
            signal_text=item.text,
            level=item.level,
            source_user_id=user_id,
            confidence=item.confidence,
            tags=item.tags,
            source_interaction_id=session_id,
        )
    else:
        # Tactical → agency brain as well (contributes to shared knowledge)
        from zeta_ima.memory.brain import agency_brain
        await agency_brain.contribute(
            {
                "text": item.text,
                "category": item.category,
                "level": item.level,
                "confidence": item.confidence,
                "tags": item.tags,
            },
            user_id=user_id,
        )
