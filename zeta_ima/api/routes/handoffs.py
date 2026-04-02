"""
Handoffs API — cross-team workflow triggers.

  GET    /handoffs                → list handoff rules
  POST   /handoffs                → create rule
  GET    /handoffs/:id            → get rule detail
  PATCH  /handoffs/:id            → update rule
  DELETE /handoffs/:id            → delete rule
  POST   /handoffs/:id/toggle     → enable/disable rule
  GET    /handoffs/log            → execution log
  POST   /handoffs/trigger        → manually trigger a handoff
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.orchestrator.handoffs import handoff_engine

router = APIRouter(prefix="/handoffs", tags=["handoffs"])


class CreateRuleRequest(BaseModel):
    name: str
    source_team_id: str
    trigger_event: str = "stage_approved"
    target_team_id: str
    target_template_id: str
    created_by: str = "user"
    trigger_skill_id: str | None = None
    variable_mapping: dict | None = None
    auto_start: bool = True


class UpdateRuleRequest(BaseModel):
    name: str | None = None
    trigger_event: str | None = None
    trigger_skill_id: str | None = None
    target_template_id: str | None = None
    variable_mapping: dict | None = None
    auto_start: bool | None = None


class ToggleRequest(BaseModel):
    enabled: bool


class ManualTriggerRequest(BaseModel):
    rule_id: str
    source_workflow_id: str
    source_stage_id: str | None = None
    context: dict = {}


@router.get("")
async def list_rules(
    team_id: str = Query(""),
    enabled_only: bool = Query(True),
):
    rules = await handoff_engine.list_rules(
        team_id=team_id or None,
        enabled_only=enabled_only,
    )
    return {"rules": rules, "count": len(rules)}


@router.post("")
async def create_rule(req: CreateRuleRequest):
    rid = await handoff_engine.create_rule(
        name=req.name,
        source_team_id=req.source_team_id,
        trigger_event=req.trigger_event,
        target_team_id=req.target_team_id,
        target_template_id=req.target_template_id,
        created_by=req.created_by,
        trigger_skill_id=req.trigger_skill_id,
        variable_mapping=req.variable_mapping,
        auto_start=req.auto_start,
    )
    return {"id": rid, "status": "created"}


@router.get("/log")
async def get_log(
    rule_id: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
):
    entries = await handoff_engine.get_log(
        rule_id=rule_id or None,
        limit=limit,
    )
    return {"log": entries, "count": len(entries)}


@router.get("/{rule_id}")
async def get_rule(rule_id: str):
    rule = await handoff_engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.patch("/{rule_id}")
async def update_rule(rule_id: str, req: UpdateRuleRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    rule = await handoff_engine.update_rule(rule_id, **updates)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str):
    ok = await handoff_engine.delete_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "deleted"}


@router.post("/{rule_id}/toggle")
async def toggle_rule(rule_id: str, req: ToggleRequest):
    rule = await handoff_engine.toggle_rule(rule_id, req.enabled)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("/trigger")
async def manual_trigger(req: ManualTriggerRequest):
    """Manually trigger a handoff rule."""
    rule = await handoff_engine.get_rule(req.rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    log_id = await handoff_engine.execute_handoff(
        rule=rule,
        source_workflow_id=req.source_workflow_id,
        source_stage_id=req.source_stage_id,
        context=req.context,
    )
    return {"log_id": log_id, "status": "triggered"}
