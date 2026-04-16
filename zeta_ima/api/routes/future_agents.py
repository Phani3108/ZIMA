"""
Future Agents routes — browse agent profiles, job history, suggestions, activities,
and execute design tasks.

GET   /future/agents                                    → list all agents with role info
GET   /future/agents/{name}                             → agent profile (role + stats)
GET   /future/agents/{name}/jobs                        → recent jobs for this agent
GET   /future/agents/{name}/suggestions                 → suggested prior outputs to reuse
GET   /future/agents/{name}/activities                  → scoped activities for this agent
GET   /future/agents/{name}/activities/{id}             → single activity detail
POST  /future/agents/{name}/activities/{id}/execute     → execute an activity (design task)
"""

import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from dataclasses import asdict
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.agents.roles import RoleRegistry
from zeta_ima.agents.activities import ActivityRegistry
from zeta_ima.memory.job_history import job_history

router = APIRouter(prefix="/future/agents", tags=["future-agents"])

_registry = RoleRegistry()


def _role_to_dict(role) -> dict:
    return {
        "id": role.id,
        "title": role.title,
        "department": role.department,
        "node_name": role.node_name,
        "responsibilities": role.responsibilities,
        "expertise": role.expertise,
        "reports_to": role.reports_to,
        "interacts_with": role.interacts_with,
        "persona_prompt": role.persona_prompt,
        "avatar_emoji": role.avatar_emoji,
    }


# ─── List / Detail ──────────────────────────────────────────────────

@router.get("")
async def list_agents(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return all agents with their role profiles."""
    _registry.ensure_loaded()
    return [_role_to_dict(r) for r in _registry.list_roles()]


@router.get("/{agent_name}")
async def get_agent(agent_name: str, user: dict = Depends(get_current_user)) -> dict:
    """Return full agent profile by role ID or node name."""
    _registry.ensure_loaded()
    role = _registry.get(agent_name) or _registry.get_by_node(agent_name)
    if role is None:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    return _role_to_dict(role)


# ─── Job History ────────────────────────────────────────────────────

@router.get("/{agent_name}/jobs")
async def get_agent_jobs(
    agent_name: str,
    scope: str = Query("user", pattern="^(user|org)$"),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return recent jobs for an agent. scope=user for personal, scope=org for all."""
    user_id = user["sub"] if scope == "user" else None
    jobs = await job_history.get_recent_jobs(
        agent_name=agent_name,
        user_id=user_id,
        limit=limit,
    )
    return jobs


@router.get("/{agent_name}/suggestions")
async def get_agent_suggestions(
    agent_name: str,
    template_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return top 2 suggested prior outputs to reuse or adapt."""
    suggestions = await job_history.get_suggestions(
        agent_name=agent_name,
        user_id=user["sub"],
        template_id=template_id,
        limit=2,
    )
    return suggestions


# ─── Activities ─────────────────────────────────────────────────────

_activity_registry = ActivityRegistry.get_instance()


@router.get("/{agent_name}/activities")
async def list_agent_activities(
    agent_name: str,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return all scoped activities this agent can perform."""
    activities = _activity_registry.list_for_agent(agent_name)
    return [asdict(a) for a in activities]


@router.get("/{agent_name}/activities/{activity_id}")
async def get_agent_activity(
    agent_name: str,
    activity_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Return a single activity definition with full input schema."""
    activity = _activity_registry.get(activity_id)
    if activity is None or activity.agent != agent_name:
        raise HTTPException(404, f"Activity '{activity_id}' not found for agent '{agent_name}'")
    return asdict(activity)


# ── Execution ───────────────────────────────────────────────────────


class ExecuteBody(BaseModel):
    prompt: str
    platform: str = ""          # e.g. "instagram_post"
    options: dict = {}          # Additional overrides (style, variant_count, etc.)


@router.post("/{agent_name}/activities/{activity_id}/execute")
async def execute_activity(
    agent_name: str,
    activity_id: str,
    body: ExecuteBody,
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Execute a design activity end-to-end.

    1. Validates activity exists and belongs to agent
    2. Loads tool config + presets from engine config
    3. Runs design_node with config-driven tool chain
    4. Uploads result to blob storage
    5. Returns image URL, download URL, provider info
    """
    activity = _activity_registry.get(activity_id)
    if activity is None or activity.agent != agent_name:
        raise HTTPException(404, f"Activity '{activity_id}' not found for agent '{agent_name}'")

    if agent_name != "design":
        raise HTTPException(501, f"Execution not yet implemented for agent '{agent_name}'")

    from zeta_ima.agents.nodes.design_node import design_node
    from zeta_ima.agents.state import AgentState

    # Build initial state with config hints for design_node
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": body.prompt}],
        "current_brief": body.prompt,
        "drafts": [],
        "current_draft": {},
        "review_result": {},
        "iteration_count": 0,
        "user_id": user.get("sub", "anonymous"),
        "user_teams_id": "",
        "active_campaign_id": None,
        "stage": "executing",
        "approval_decision": None,
        "approval_comment": None,
        "brand_examples": [],
        "intent": "design",
        "route_to": ["design"],
        "tool_results": {
            "_skill_id": activity_id,
            "_platform": body.platform,
        },
        "kb_context": [],
        "pipeline": ["design"],
        "pipeline_index": 0,
        "agent_messages": [],
        "meeting_transcript": [],
        "meeting_plan": {},
        "plan_status": "",
        "user_plan_modifications": None,
        "brain_context": [],
    }

    result = await design_node(initial_state)
    design_result = result.get("tool_results", {}).get("design", {})

    if not design_result.get("ok"):
        raise HTTPException(500, f"Design generation failed: {design_result.get('error', 'Unknown error')}")

    # Record job
    try:
        await job_history.record_job(
            agent_name=agent_name,
            user_id=user.get("sub", "anonymous"),
            activity_id=activity_id,
            prompt=body.prompt,
            result_summary=design_result.get("revised_prompt", ""),
            output_url=design_result.get("image_url", ""),
        )
    except Exception:
        pass  # Non-fatal

    return {
        "ok": True,
        "image_url": design_result.get("image_url", ""),
        "download_url": design_result.get("download_url", ""),
        "provider": design_result.get("provider", ""),
        "model": design_result.get("model", ""),
        "revised_prompt": design_result.get("revised_prompt", ""),
        "aspect_ratio": design_result.get("aspect_ratio", ""),
        "resolution": design_result.get("resolution", ""),
        "mime_type": design_result.get("mime_type", ""),
        "skill_id": activity_id,
        "platform": body.platform,
    }
