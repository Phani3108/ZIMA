"""
Future Approvals routes — manage approval routing per team and view personal queue.

GET    /future/approvals/mine                         → pending approvals for current user
GET    /future/teams/{team_id}/approval-routing      → list routing rules
PUT    /future/teams/{team_id}/approval-routing      → set/update a routing rule
DELETE /future/teams/{team_id}/approval-routing/{agent_type} → delete a rule
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from zeta_ima.api.auth import get_current_user
from zeta_ima.teams_collab import teams_service

router = APIRouter(prefix="/future", tags=["future-approvals"])


class ApprovalRoutingPayload(BaseModel):
    agent_type: str
    approver_user_id: str
    approver_display_name: str = ""
    approver_email: str = ""
    fallback_approver_user_id: Optional[str] = None


# ─── Personal Queue ─────────────────────────────────────────────────

@router.get("/approvals/mine")
async def my_approvals(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return all pending approvals assigned to the current user."""
    from zeta_ima.workflows.models import list_pending_approvals
    pending = await list_pending_approvals(approver_id=user["sub"])
    return pending


# ─── Team Routing ───────────────────────────────────────────────────

@router.get("/teams/{team_id}/approval-routing")
async def list_routing(team_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    """List all approval routing rules for a team."""
    rules = await teams_service.list_approval_routing(team_id)
    return rules


@router.put("/teams/{team_id}/approval-routing")
async def set_routing(
    team_id: str,
    payload: ApprovalRoutingPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    """Create or update an approval routing rule."""
    await teams_service.set_approval_routing(
        team_id=team_id,
        agent_type=payload.agent_type,
        approver_user_id=payload.approver_user_id,
        approver_display_name=payload.approver_display_name,
        approver_email=payload.approver_email,
        fallback_approver_user_id=payload.fallback_approver_user_id,
    )
    return {"status": "ok", "team_id": team_id, "agent_type": payload.agent_type}


@router.delete("/teams/{team_id}/approval-routing/{agent_type}")
async def delete_routing(
    team_id: str,
    agent_type: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Delete an approval routing rule."""
    await teams_service.delete_approval_routing(team_id, agent_type)
    return {"status": "deleted"}
