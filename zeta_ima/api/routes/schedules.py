"""
Schedule routes — CRUD for recurring workflow triggers.

POST   /schedules               → create a new schedule
GET    /schedules               → list all schedules
GET    /schedules/{id}          → get schedule details
PATCH  /schedules/{id}          → update a schedule (cron, variables, enabled)
DELETE /schedules/{id}          → delete a schedule
POST   /schedules/{id}/toggle   → enable/disable a schedule
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.orchestrator.scheduler import scheduler

router = APIRouter(prefix="/schedules", tags=["schedules"])


class CreateSchedulePayload(BaseModel):
    name: str
    cron_expr: str
    template_id: str
    variables: dict[str, Any] = {}
    campaign_id: Optional[str] = None
    max_runs: int = 0


class UpdateSchedulePayload(BaseModel):
    name: Optional[str] = None
    cron_expr: Optional[str] = None
    template_id: Optional[str] = None
    variables: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None
    max_runs: Optional[int] = None


class TogglePayload(BaseModel):
    enabled: bool


@router.post("", status_code=201)
async def create_schedule(
    payload: CreateSchedulePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    try:
        return await scheduler.create(
            name=payload.name,
            cron_expr=payload.cron_expr,
            template_id=payload.template_id,
            variables=payload.variables,
            created_by=user["sub"],
            campaign_id=payload.campaign_id,
            max_runs=payload.max_runs,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_schedules(
    mine: bool = Query(False, description="Show only my schedules"),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    created_by = user["sub"] if mine else None
    return await scheduler.list_schedules(created_by=created_by)


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    sched = await scheduler.get_schedule(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return sched


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    payload: UpdateSchedulePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        result = await scheduler.update_schedule(schedule_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return result


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    deleted = await scheduler.delete_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(
    schedule_id: str,
    payload: TogglePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    result = await scheduler.toggle(schedule_id, payload.enabled)
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return result
