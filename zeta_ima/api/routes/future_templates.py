"""
Future Templates routes — browse task templates and start workflows from them.

GET  /future/templates              → list all task templates
GET  /future/templates/{id}         → get a single template with details
POST /future/templates/{id}/start   → start a workflow from a template
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from zeta_ima.api.auth import get_current_user
from zeta_ima.skills.task_templates import template_registry
from zeta_ima.workflows.engine import workflow_engine

router = APIRouter(prefix="/future/templates", tags=["future-templates"])


class StartPayload(BaseModel):
    brief: str
    variables: dict[str, str] = {}
    name: Optional[str] = None
    campaign_id: Optional[str] = None
    team_id: Optional[str] = None


# ─── List / Detail ──────────────────────────────────────────────────

@router.get("")
async def list_templates(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return all task templates."""
    return [t.to_api_dict() for t in template_registry.list_all()]


@router.get("/{template_id}")
async def get_template(template_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Return a single template with full details."""
    tmpl = template_registry.get(template_id)
    if tmpl is None:
        raise HTTPException(404, f"Template '{template_id}' not found")
    return tmpl.to_api_dict()


# ─── Execute ────────────────────────────────────────────────────────

@router.post("/{template_id}/start")
async def start_template(
    template_id: str,
    payload: StartPayload,
    bg: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """Create and start a workflow from a task template."""
    tmpl = template_registry.get(template_id)
    if tmpl is None:
        raise HTTPException(404, f"Template '{template_id}' not found")

    variables = {**payload.variables, "brief": payload.brief}

    wf = await workflow_engine.create_from_task_template(
        task_template_id=template_id,
        variables=variables,
        user_id=user["sub"],
        name=payload.name,
        campaign_id=payload.campaign_id,
        team_id=payload.team_id,
    )

    # Kick off execution in background
    bg.add_task(workflow_engine.advance, wf["id"])

    return {"workflow_id": wf["id"], "template_id": template_id, "status": "started"}
