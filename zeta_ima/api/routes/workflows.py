"""
Workflow routes — CRUD, advance, approve/reject, retry.

GET    /workflows                              → list workflows (filterable)
POST   /workflows                              → create from template
GET    /workflows/templates                    → list available templates
GET    /workflows/{id}                         → workflow detail with stages
POST   /workflows/{id}/advance                 → execute next stage
POST   /workflows/{id}/stages/{sid}/approve    → approve a stage
POST   /workflows/{id}/stages/{sid}/reject     → reject a stage
POST   /workflows/{id}/stages/{sid}/retry      → retry a failed stage
POST   /workflows/{id}/stages/{sid}/edit       → update stage output via chat
DELETE /workflows/{id}                         → cancel a workflow
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.workflows.engine import workflow_engine
from zeta_ima.workflows.models import (
    get_workflow,
    list_workflows,
    update_stage,
    update_workflow_status,
)
from zeta_ima.workflows.templates import list_templates

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ─── Payloads ───────────────────────────────────────────────────────

class CreateWorkflowPayload(BaseModel):
    template_id: str
    variables: dict[str, str]
    name: Optional[str] = None
    campaign_id: Optional[str] = None
    auto_start: bool = True  # Auto-advance the first stage


class ApprovePayload(BaseModel):
    comment: str = ""


class RejectPayload(BaseModel):
    comment: str = ""


class RetryPayload(BaseModel):
    llm_override: Optional[str] = None  # e.g. "claude", "openai", "gemini"


class EditStagePayload(BaseModel):
    """Chat-based editing of stage output."""
    instruction: str   # e.g. "Make it more casual"
    field: str = "text"  # which output field to edit


# ─── Helpers ────────────────────────────────────────────────────────

def _serialize_workflow(wf: dict) -> dict:
    """Convert datetime fields to ISO strings for JSON serialization."""
    result = dict(wf)
    for key in ("created_at", "updated_at"):
        if result.get(key) and isinstance(result[key], datetime):
            result[key] = result[key].isoformat()

    if "stages" in result:
        serialized_stages = []
        for s in result["stages"]:
            s = dict(s)
            for key in ("started_at", "completed_at"):
                if s.get(key) and isinstance(s[key], datetime):
                    s[key] = s[key].isoformat()
            serialized_stages.append(s)
        result["stages"] = serialized_stages

    return result


# ─── Templates ──────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(user: dict = Depends(get_current_user)) -> list[dict]:
    """List available workflow templates."""
    return list_templates()


# ─── CRUD ───────────────────────────────────────────────────────────

@router.get("")
async def get_workflows(
    status: Optional[str] = Query(None, description="Filter by status: active, completed, cancelled"),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """List workflows, optionally filtered by status."""
    wfs = await list_workflows(
        status=status,
        created_by=user["user_id"],
        limit=limit,
    )
    return [_serialize_workflow(wf) for wf in wfs]


@router.post("")
async def create_workflow_endpoint(
    payload: CreateWorkflowPayload,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """Create a workflow from a template and optionally auto-start it."""
    try:
        wf = await workflow_engine.create_from_template(
            template_id=payload.template_id,
            variables=payload.variables,
            user_id=user["user_id"],
            name=payload.name,
            campaign_id=payload.campaign_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Auto-advance the first stage
    if payload.auto_start:
        async def _run():
            try:
                await workflow_engine.advance(wf["id"])
            except Exception as ex:
                import logging
                logging.getLogger(__name__).error(f"Workflow auto-start failed: {ex}")

        background.add_task(_run)

    return {
        **_serialize_workflow(wf),
        "message": "Workflow created" + (" and first stage started" if payload.auto_start else ""),
    }


@router.get("/{workflow_id}")
async def get_workflow_detail(
    workflow_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Get full workflow detail with all stages."""
    wf = await get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return _serialize_workflow(wf)


@router.delete("/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Cancel a workflow (sets status to 'cancelled')."""
    wf = await get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    await update_workflow_status(workflow_id, "cancelled")
    return {"ok": True, "workflow_id": workflow_id, "status": "cancelled"}


# ─── Stage Operations ──────────────────────────────────────────────

@router.post("/{workflow_id}/advance")
async def advance_workflow(
    workflow_id: str,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """Execute the next pending stage in the workflow."""
    wf = await get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    async def _run():
        try:
            await workflow_engine.advance(workflow_id)
        except Exception as ex:
            import logging
            logging.getLogger(__name__).error(f"Workflow advance failed: {ex}")

    background.add_task(_run)

    return {
        "ok": True,
        "workflow_id": workflow_id,
        "message": "Advancing to next stage...",
    }


@router.post("/{workflow_id}/stages/{stage_id}/approve")
async def approve_stage(
    workflow_id: str,
    stage_id: str,
    payload: ApprovePayload,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """Approve a stage that's awaiting review."""
    try:
        wf = await workflow_engine.approve_stage(
            workflow_id=workflow_id,
            stage_id=stage_id,
            decision="approve",
            comment=payload.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Auto-advance after approval
    async def _auto_advance():
        try:
            updated = await get_workflow(workflow_id)
            if updated and updated["status"] == "active":
                await workflow_engine.advance(workflow_id)
        except Exception as ex:
            import logging
            logging.getLogger(__name__).error(f"Auto-advance after approval failed: {ex}")

    background.add_task(_auto_advance)

    return {
        **_serialize_workflow(wf),
        "message": "Stage approved — advancing to next stage.",
    }


@router.post("/{workflow_id}/stages/{stage_id}/reject")
async def reject_stage(
    workflow_id: str,
    stage_id: str,
    payload: RejectPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    """Reject a stage — marks it as needs_retry."""
    try:
        wf = await workflow_engine.approve_stage(
            workflow_id=workflow_id,
            stage_id=stage_id,
            decision="reject",
            comment=payload.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        **_serialize_workflow(wf),
        "message": f"Stage rejected{': ' + payload.comment if payload.comment else ''}. Retry when ready.",
    }


@router.post("/{workflow_id}/stages/{stage_id}/retry")
async def retry_stage(
    workflow_id: str,
    stage_id: str,
    payload: RetryPayload,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """Retry a failed or rejected stage, optionally with a different LLM."""
    async def _run():
        try:
            await workflow_engine.retry_stage(
                workflow_id=workflow_id,
                stage_id=stage_id,
                llm_override=payload.llm_override,
            )
        except Exception as ex:
            import logging
            logging.getLogger(__name__).error(f"Stage retry failed: {ex}")

    background.add_task(_run)

    return {
        "ok": True,
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "message": f"Retrying stage{' with ' + payload.llm_override if payload.llm_override else ''}...",
    }


@router.post("/{workflow_id}/stages/{stage_id}/edit")
async def edit_stage_output(
    workflow_id: str,
    stage_id: str,
    payload: EditStagePayload,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Edit a stage's output via natural-language instruction.

    Re-runs the agent with the original output + user instruction as context.
    """
    from zeta_ima.agents.pool import agent_pool

    wf = await get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    stage = next((s for s in wf["stages"] if s["id"] == stage_id), None)
    if stage is None:
        raise HTTPException(status_code=404, detail=f"Stage '{stage_id}' not found")

    if not stage.get("output"):
        raise HTTPException(status_code=400, detail="Stage has no output to edit")

    original_output = stage["output"].get("text", "") if isinstance(stage["output"], dict) else str(stage["output"])

    async def _run():
        try:
            edit_prompt = f"""Here is the original content:

---
{original_output}
---

The user wants the following change: {payload.instruction}

Please rewrite the content with the requested change applied. Keep everything else the same.
Output ONLY the revised content, no explanations."""

            result = await agent_pool.execute(
                agent_name=stage["agent_name"],
                skill_id=wf["skill_id"],
                prompt_id="edit_override",
                variables={"_raw_prompt": edit_prompt},
                context={},
            )

            if result.status == "success":
                await update_stage(
                    stage_id,
                    status="awaiting_review",
                    output={"text": result.output, "metadata": {
                        **(result.metadata or {}),
                        "edit_instruction": payload.instruction,
                        "previous_version": original_output[:500],
                    }},
                    llm_used=result.llm_used,
                    completed_at=result.completed_at,
                )
        except Exception as ex:
            import logging
            logging.getLogger(__name__).error(f"Stage edit failed: {ex}")

    background.add_task(_run)

    return {
        "ok": True,
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "message": f"Editing output: '{payload.instruction}'...",
    }
