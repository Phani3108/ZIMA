"""
Prompts API — version management + evolution queue.

GET  /prompts/versions          → version history
POST /prompts/versions          → create new version
POST /prompts/rollback          → rollback to previous version
GET  /prompts/evolution/queue   → pending evolution changes
POST /prompts/evolution/approve → approve a queued change
POST /prompts/evolution/reject  → reject a queued change
POST /prompts/evolution/trigger → manually trigger evolution analysis
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/prompts", tags=["prompts"])


class CreateVersionInput(BaseModel):
    skill_id: str
    content: str
    team_id: str = "__global__"
    change_reason: str = ""
    created_by: str = "admin"


class RollbackInput(BaseModel):
    skill_id: str
    team_id: str = "__global__"
    to_version: int = 0


class ReviewInput(BaseModel):
    queue_id: str
    reviewed_by: str


class TriggerInput(BaseModel):
    skill_id: str
    team_id: str = "__global__"


@router.get("/versions")
async def list_versions(
    skill_id: str = Query(...),
    team_id: str = Query("__global__"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get version history for a prompt."""
    from zeta_ima.prompts.engine import get_version_history
    versions = await get_version_history(skill_id=skill_id, team_id=team_id, limit=limit)
    return {"versions": versions, "count": len(versions)}


@router.post("/versions")
async def create_version_endpoint(body: CreateVersionInput):
    """Create a new prompt version."""
    from zeta_ima.prompts.engine import create_version
    version = await create_version(
        skill_id=body.skill_id,
        content=body.content,
        team_id=body.team_id,
        change_type="manual",
        change_reason=body.change_reason,
        created_by=body.created_by,
    )
    return {"version": version}


@router.post("/rollback")
async def rollback_endpoint(body: RollbackInput):
    """Rollback to a previous prompt version."""
    from zeta_ima.prompts.engine import rollback
    result = await rollback(
        skill_id=body.skill_id,
        team_id=body.team_id,
        to_version=body.to_version,
    )
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Version not found")
    return {"rolled_back_to": result}


@router.get("/evolution/queue")
async def list_queue(
    status: str = Query("pending"),
    limit: int = Query(20, ge=1, le=100),
):
    """List pending evolution queue entries."""
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()
    entries = await ds.query("prompt_evolution_queue", filters={"status": status}, limit=limit)
    return {"queue": entries, "count": len(entries)}


@router.post("/evolution/approve")
async def approve_change(body: ReviewInput):
    """Approve a queued prompt evolution change."""
    from zeta_ima.prompts.evolution import approve_queued_change
    version = await approve_queued_change(queue_id=body.queue_id, reviewed_by=body.reviewed_by)
    if not version:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Queue entry not found or already reviewed")
    return {"approved": True, "version": version}


@router.post("/evolution/reject")
async def reject_change(body: ReviewInput):
    """Reject a queued prompt evolution change."""
    from zeta_ima.prompts.evolution import reject_queued_change
    await reject_queued_change(queue_id=body.queue_id, reviewed_by=body.reviewed_by)
    return {"rejected": True}


@router.post("/evolution/trigger")
async def trigger_evolution(body: TriggerInput):
    """Manually trigger evolution analysis for a skill."""
    from zeta_ima.prompts.evolution import analyze_signals, apply_minor_change, queue_major_change

    signals = await analyze_signals(skill_id=body.skill_id, team_id=body.team_id)
    if not signals.get("trigger"):
        return {"action": "none", "reason": "No evolution triggers detected"}

    if signals["change_type"] == "minor":
        result = await apply_minor_change(skill_id=body.skill_id, team_id=body.team_id)
        return {"action": "auto_applied", "version": result}
    else:
        queue_id = await queue_major_change(skill_id=body.skill_id, team_id=body.team_id)
        return {"action": "queued", "queue_id": queue_id, "reason": signals["reason"]}
