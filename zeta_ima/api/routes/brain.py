"""
Agency Brain routes — Genesis v2

GET    /brain/query               → semantic search across the brain
POST   /brain/contribute          → add a knowledge item
GET    /brain/conflicts           → list items needing manual resolution
POST   /brain/conflicts/{id}/resolve  → accept or reject a conflicting item
POST   /brain/compact             → trigger sprint compaction (admin only)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.memory.brain import agency_brain

router = APIRouter(prefix="/brain", tags=["brain"])


class ContributePayload(BaseModel):
    text: str
    category: str = "general"
    level: str = "zeta"
    confidence: float = 0.75
    tags: list[str] = []


class ResolvePayload(BaseModel):
    resolution: str   # "accept" | "reject"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/query")
async def query_brain(
    q: str = Query(..., min_length=2),
    category: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tag filter"),
    top_k: int = Query(8, le=30),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return await agency_brain.query(
        query_text=q,
        category=category,
        level=level,
        tags=tag_list,
        top_k=top_k,
    )


@router.post("/contribute", status_code=201)
async def contribute(
    payload: ContributePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    result = await agency_brain.contribute(
        item=payload.model_dump(),
        user_id=user["sub"],
        user_role=user.get("role", "member"),
    )
    return result


class BatchContributePayload(BaseModel):
    items: list[ContributePayload]


@router.post("/contribute/batch", status_code=201)
async def batch_contribute(
    payload: BatchContributePayload,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await agency_brain.batch_contribute(
        items=[i.model_dump() for i in payload.items],
        user_id=user["sub"],
        user_role=user.get("role", "member"),
    )


@router.get("/conflicts")
async def list_conflicts(
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await agency_brain.list_conflicts()


@router.post("/conflicts/{entry_id}/resolve", status_code=200)
async def resolve_conflict(
    entry_id: str,
    payload: ResolvePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    if payload.resolution not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="resolution must be 'accept' or 'reject'")
    await agency_brain.resolve_conflict(
        entry_id=entry_id,
        resolution=payload.resolution,
        resolved_by=user["sub"],
    )
    return {"id": entry_id, "resolution": payload.resolution}


@router.post("/compact")
async def compact_brain(
    user: dict = Depends(get_current_user),
) -> dict:
    # Restrict to admin/manager
    if user.get("role") not in ("admin", "manager", "strategist"):
        raise HTTPException(status_code=403, detail="Compaction requires manager role or above")
    return await agency_brain.compact()


@router.get("/stats")
async def brain_stats(
    user: dict = Depends(get_current_user),
) -> dict:
    return await agency_brain.statistics()
