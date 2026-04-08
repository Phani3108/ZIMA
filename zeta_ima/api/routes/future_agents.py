"""
Future Agents routes — browse agent profiles, job history, and suggestions.

GET  /future/agents                       → list all agents with role info
GET  /future/agents/{name}                → agent profile (role + stats)
GET  /future/agents/{name}/jobs           → recent jobs for this agent
GET  /future/agents/{name}/suggestions    → suggested prior outputs to reuse
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from zeta_ima.api.auth import get_current_user
from zeta_ima.agents.roles import RoleRegistry
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
