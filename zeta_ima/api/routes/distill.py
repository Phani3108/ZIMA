"""
Distill routes — Genesis v2

POST /distill/session/{session_id}   → manually trigger distillation for a session
GET  /distill/signals                → list directional signals
POST /distill/sprint                 → trigger sprint compaction (manager+)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.memory.distiller import distill_conversation, compact_sprint

router = APIRouter(prefix="/distill", tags=["distill"])


class DistillPayload(BaseModel):
    messages: list[dict]     # [{role: str, content: str}, ...]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/session/{session_id}")
async def distill_session(
    session_id: str,
    payload: DistillPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    """Manually trigger knowledge distillation for a conversation session."""
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    items = await distill_conversation(
        messages=payload.messages,
        user_id=user["sub"],
        user_role=user.get("role", "member"),
        session_id=session_id,
    )
    return {
        "session_id": session_id,
        "items_extracted": len(items),
        "items": [
            {
                "type": item.type,
                "level": item.level,
                "text": item.text,
                "confidence": item.confidence,
                "category": item.category,
                "tags": item.tags,
            }
            for item in items
        ],
    }


@router.get("/signals")
async def get_signals(
    level: str = Query("zeta"),
    top_k: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Retrieve directional learning signals."""
    from zeta_ima.memory.learning import get_directional_signals
    return await get_directional_signals(level=level, top_k=top_k)


@router.post("/sprint")
async def run_sprint_compact(
    days_back: int = Query(7, le=90),
    user: dict = Depends(get_current_user),
) -> dict:
    """Sprint compaction — synthesise recent signals into durable rules."""
    if user.get("role") not in ("admin", "manager", "strategist"):
        raise HTTPException(status_code=403, detail="Sprint compaction requires manager role")
    return await compact_sprint(days_back=days_back)
