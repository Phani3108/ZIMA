"""
Team collaboration routes.

POST   /teams                       → create a team
GET    /teams                       → list teams (my teams if mine=true)
GET    /teams/{id}                  → get team details with members
PATCH  /teams/{id}                  → update team info
DELETE /teams/{id}                  → delete a team (admin only)
POST   /teams/{id}/members          → add a member
DELETE /teams/{id}/members/{uid}    → remove a member
PATCH  /teams/{id}/members/{uid}    → update member role
GET    /teams/me                    → get current user's team memberships
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.teams_collab import teams_service

router = APIRouter(prefix="/teams", tags=["teams"])


class CreateTeamPayload(BaseModel):
    name: str
    description: str = ""


class AddMemberPayload(BaseModel):
    user_id: str
    role: str = "member"
    display_name: str = ""
    email: str = ""


class UpdateRolePayload(BaseModel):
    role: str


class UpdateTeamPayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# ── Team CRUD ────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_team(
    payload: CreateTeamPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    return await teams_service.create_team(
        name=payload.name,
        created_by=user["sub"],
        description=payload.description,
    )


@router.get("/me")
async def my_teams(user: dict = Depends(get_current_user)) -> list[dict]:
    return await teams_service.get_user_teams(user["sub"])


@router.get("")
async def list_teams(
    mine: bool = Query(False),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    user_id = user["sub"] if mine else None
    return await teams_service.list_teams(user_id=user_id)


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    team = await teams_service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = await teams_service.list_members(team_id)
    return {**team, "members": members}


@router.patch("/{team_id}")
async def update_team(
    team_id: str,
    payload: UpdateTeamPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    if not await teams_service.is_team_admin(team_id, user["sub"]):
        raise HTTPException(status_code=403, detail="Only team admins can update the team")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await teams_service.update_team(team_id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    return result


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    if not await teams_service.is_team_admin(team_id, user["sub"]):
        raise HTTPException(status_code=403, detail="Only team admins can delete the team")
    deleted = await teams_service.delete_team(team_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Team not found")


# ── Membership ───────────────────────────────────────────────────────────

@router.post("/{team_id}/members", status_code=201)
async def add_member(
    team_id: str,
    payload: AddMemberPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    if not await teams_service.is_team_admin(team_id, user["sub"]):
        raise HTTPException(status_code=403, detail="Only team admins can add members")
    try:
        return await teams_service.add_member(
            team_id=team_id,
            user_id=payload.user_id,
            role=payload.role,
            display_name=payload.display_name,
            email=payload.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}/members/{member_user_id}", status_code=204)
async def remove_member(
    team_id: str,
    member_user_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    if not await teams_service.is_team_admin(team_id, user["sub"]):
        raise HTTPException(status_code=403, detail="Only team admins can remove members")
    removed = await teams_service.remove_member(team_id, member_user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")


@router.patch("/{team_id}/members/{member_user_id}")
async def update_role(
    team_id: str,
    member_user_id: str,
    payload: UpdateRolePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    if not await teams_service.is_team_admin(team_id, user["sub"]):
        raise HTTPException(status_code=403, detail="Only team admins can change roles")
    try:
        updated = await teams_service.update_member_role(team_id, member_user_id, payload.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"team_id": team_id, "user_id": member_user_id, "role": payload.role}
