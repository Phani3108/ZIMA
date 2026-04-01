"""
Tasks (Orchestrator Queue) routes — Genesis v2

GET    /tasks                     → list tasks (filterable by status / pipeline / assignee)
POST   /tasks                     → create + enqueue a new task
GET    /tasks/{task_id}           → get single task
PATCH  /tasks/{task_id}           → update task status / priority
DELETE /tasks/{task_id}           → cancel a task
GET    /tasks/pipelines           → list available pipeline definitions
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.orchestrator.queue import (
    create_task,
    get_task,
    list_tasks,
    update_task,
)
from zeta_ima.orchestrator.router import route_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskPayload(BaseModel):
    title: str
    description: str
    priority: int = 2           # 1=high, 2=normal, 3=low
    pipeline_name: Optional[str] = None   # Override auto-routing
    assignee_agent: Optional[str] = None


class UpdateTaskPayload(BaseModel):
    status: Optional[str] = None
    priority: Optional[int] = None
    assignee_agent: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
async def get_tasks(
    status: Optional[str] = Query(None),
    pipeline: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await list_tasks(status=status, pipeline_name=pipeline, limit=limit)


@router.post("", status_code=201)
async def post_task(
    payload: CreateTaskPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    # Auto-route if no pipeline specified
    routing = None
    if not payload.pipeline_name:
        routing = await route_task(
            f"{payload.title}. {payload.description}"
        )

    task_id = await create_task(
        title=payload.title,
        description=payload.description,
        requester_id=user["sub"],
        priority=payload.priority,
        pipeline_name=routing.pipeline_name if routing else payload.pipeline_name,
        pipeline=routing.pipeline if routing else None,
        routing_rationale=routing.rationale if routing else None,
        assignee_agent=payload.assignee_agent,
    )
    return {"id": task_id, "status": "queued", "routing": routing.__dict__ if routing else None}


@router.get("/pipelines")
async def get_pipelines(user: dict = Depends(get_current_user)) -> dict:
    import yaml
    from pathlib import Path
    yaml_path = Path(__file__).parent.parent.parent / "orchestrator" / "pipelines.yaml"
    with yaml_path.open() as f:
        return yaml.safe_load(f)


@router.get("/{task_id}")
async def get_task_by_id(
    task_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}")
async def patch_task(
    task_id: str,
    payload: UpdateTaskPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    await update_task(task_id, **updates)
    return {"id": task_id, "updated": list(updates.keys())}


@router.delete("/{task_id}", status_code=204)
async def cancel_task(
    task_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    await update_task(task_id, status="cancelled")
