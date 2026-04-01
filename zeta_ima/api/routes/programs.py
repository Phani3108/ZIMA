"""
Program Management routes — group related workflows into campaigns.

GET    /programs                → list all programs
POST   /programs                → create a program
GET    /programs/{id}           → program detail with child workflows
GET    /programs/{id}/timeline  → Gantt-style timeline data
POST   /programs/{id}/advance-all → advance all pending stages
DELETE /programs/{id}           → cancel a program
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.api.auth import get_current_user
from zeta_ima.config import settings
from zeta_ima.workflows.engine import workflow_engine
from zeta_ima.workflows.models import list_workflows, get_workflow

router = APIRouter(prefix="/programs", tags=["programs"])

# ─── DB Model ───────────────────────────────────────────────────────

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

programs = Table(
    "programs",
    _metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("description", Text),
    Column("campaign_id", String, nullable=False),
    Column("created_by", String, nullable=False),
    Column("target_date", DateTime),
    Column("status", String, nullable=False, default="active"),
    Column("tags", JSONB, default=[]),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)


async def init_programs_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)


# ─── Payloads ───────────────────────────────────────────────────────

class CreateProgramPayload(BaseModel):
    name: str
    description: str = ""
    target_date: Optional[str] = None
    tags: list[str] = []


# ─── Helpers ────────────────────────────────────────────────────────

def _serialize_dt(val) -> Optional[str]:
    if val and isinstance(val, datetime):
        return val.isoformat()
    return val


async def _get_program(program_id: str) -> Optional[dict]:
    async with _Session() as session:
        result = await session.execute(
            select(programs).where(programs.c.id == program_id)
        )
        row = result.fetchone()
        if row is None:
            return None
        d = dict(row._mapping)
        d["created_at"] = _serialize_dt(d.get("created_at"))
        d["updated_at"] = _serialize_dt(d.get("updated_at"))
        d["target_date"] = _serialize_dt(d.get("target_date"))
        return d


# ─── Endpoints ──────────────────────────────────────────────────────

@router.get("")
async def list_programs(
    status: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """List all programs with workflow counts."""
    async with _Session() as session:
        q = select(programs).order_by(programs.c.updated_at.desc())
        if status:
            q = q.where(programs.c.status == status)
        result = await session.execute(q)
        progs = []
        for row in result.fetchall():
            d = dict(row._mapping)
            d["created_at"] = _serialize_dt(d.get("created_at"))
            d["updated_at"] = _serialize_dt(d.get("updated_at"))
            d["target_date"] = _serialize_dt(d.get("target_date"))

            # Get workflow count
            wfs = await list_workflows(limit=500)
            campaign_wfs = [w for w in wfs if w.get("campaign_id") == d["campaign_id"]]
            d["workflow_count"] = len(campaign_wfs)
            d["completed_count"] = len([w for w in campaign_wfs if w["status"] == "completed"])

            progs.append(d)
        return progs


@router.post("")
async def create_program(
    payload: CreateProgramPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    """Create a new program to group workflows."""
    program_id = str(uuid.uuid4())
    campaign_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    target = None
    if payload.target_date:
        try:
            target = datetime.fromisoformat(payload.target_date)
        except ValueError:
            pass

    async with _Session() as session:
        await session.execute(
            programs.insert().values(
                id=program_id,
                name=payload.name,
                description=payload.description,
                campaign_id=campaign_id,
                created_by=user["user_id"],
                target_date=target,
                status="active",
                tags=payload.tags,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    return {
        "id": program_id,
        "campaign_id": campaign_id,
        "name": payload.name,
        "status": "active",
        "message": f"Program created. Use campaign_id '{campaign_id}' when creating workflows to link them.",
    }


@router.get("/{program_id}")
async def get_program_detail(
    program_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Get program detail with all child workflows and progress."""
    prog = await _get_program(program_id)
    if prog is None:
        raise HTTPException(status_code=404, detail=f"Program '{program_id}' not found")

    # Get all workflows linked to this program's campaign_id
    all_wfs = await list_workflows(limit=500)
    campaign_wfs = [w for w in all_wfs if w.get("campaign_id") == prog["campaign_id"]]

    # Serialize datetime fields
    for wf in campaign_wfs:
        for key in ("created_at", "updated_at"):
            if wf.get(key) and isinstance(wf[key], datetime):
                wf[key] = wf[key].isoformat()
        for stage in wf.get("stages", []):
            for key in ("started_at", "completed_at"):
                if stage.get(key) and isinstance(stage[key], datetime):
                    stage[key] = stage[key].isoformat()

    # Calculate aggregate metrics
    total_stages = sum(len(w.get("stages", [])) for w in campaign_wfs)
    completed_stages = sum(
        len([s for s in w.get("stages", []) if s["status"] == "approved"])
        for w in campaign_wfs
    )
    stuck_stages = sum(
        len([s for s in w.get("stages", []) if s["status"] in ("needs_retry",)])
        for w in campaign_wfs
    )

    return {
        **prog,
        "workflows": campaign_wfs,
        "metrics": {
            "total_workflows": len(campaign_wfs),
            "active_workflows": len([w for w in campaign_wfs if w["status"] == "active"]),
            "completed_workflows": len([w for w in campaign_wfs if w["status"] == "completed"]),
            "total_stages": total_stages,
            "completed_stages": completed_stages,
            "stuck_stages": stuck_stages,
            "progress_pct": round(completed_stages / total_stages * 100, 1) if total_stages > 0 else 0,
        },
    }


@router.get("/{program_id}/timeline")
async def get_program_timeline(
    program_id: str,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """
    Get Gantt-style timeline data.

    Returns each workflow as a row with stages as segments.
    """
    prog = await _get_program(program_id)
    if prog is None:
        raise HTTPException(status_code=404, detail="Program not found")

    all_wfs = await list_workflows(limit=500)
    campaign_wfs = [w for w in all_wfs if w.get("campaign_id") == prog["campaign_id"]]

    timeline = []
    for wf in campaign_wfs:
        segments = []
        for stage in wf.get("stages", []):
            segments.append({
                "name": stage["name"],
                "status": stage["status"],
                "started_at": _serialize_dt(stage.get("started_at")),
                "completed_at": _serialize_dt(stage.get("completed_at")),
                "agent": stage.get("agent_name", ""),
            })
        timeline.append({
            "workflow_id": wf["id"],
            "workflow_name": wf["name"],
            "status": wf["status"],
            "created_at": _serialize_dt(wf.get("created_at")),
            "segments": segments,
        })

    return timeline


@router.post("/{program_id}/advance-all")
async def advance_all_workflows(
    program_id: str,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """Advance all active workflows in this program that have pending stages."""
    prog = await _get_program(program_id)
    if prog is None:
        raise HTTPException(status_code=404, detail="Program not found")

    all_wfs = await list_workflows(status="active", limit=500)
    campaign_wfs = [w for w in all_wfs if w.get("campaign_id") == prog["campaign_id"]]

    advanced = 0
    for wf in campaign_wfs:
        # Skip if current stage needs approval
        stages = wf.get("stages", [])
        idx = wf.get("current_stage_index", 0)
        if idx < len(stages) and stages[idx]["status"] not in ("awaiting_review",):
            async def _adv(wf_id=wf["id"]):
                try:
                    await workflow_engine.advance(wf_id)
                except Exception:
                    pass
            background.add_task(_adv)
            advanced += 1

    return {"ok": True, "program_id": program_id, "workflows_advanced": advanced}


@router.delete("/{program_id}")
async def cancel_program(
    program_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Cancel a program (sets status to cancelled)."""
    prog = await _get_program(program_id)
    if prog is None:
        raise HTTPException(status_code=404, detail="Program not found")

    now = datetime.now(timezone.utc)
    async with _Session() as session:
        await session.execute(
            programs.update()
            .where(programs.c.id == program_id)
            .values(status="cancelled", updated_at=now)
        )
        await session.commit()

    return {"ok": True, "program_id": program_id, "status": "cancelled"}
