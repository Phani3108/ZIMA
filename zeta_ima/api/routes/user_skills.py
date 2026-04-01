"""
User Skills routes — Genesis v2 codable skills

GET    /user-skills              → list skills visible to user
POST   /user-skills              → create a new skill
GET    /user-skills/{id}         → get skill with code
PUT    /user-skills/{id}         → update skill (creator only)
DELETE /user-skills/{id}         → delete skill (creator only)
POST   /user-skills/{id}/execute → execute skill in sandbox
POST   /user-skills/validate     → validate skill code before saving
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.skills.executor import (
    execute_user_skill,
    validate_skill_code,
    save_user_skill,
    get_user_skill,
    list_user_skills,
    delete_user_skill,
)

router = APIRouter(prefix="/user-skills", tags=["user-skills"])


class CreateSkillPayload(BaseModel):
    name: str
    description: str = ""
    code: str
    is_shared: bool = False
    tags: list[str] = []


class UpdateSkillPayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    is_shared: Optional[bool] = None
    tags: Optional[list[str]] = None


class ExecutePayload(BaseModel):
    inputs: dict = {}


class ValidatePayload(BaseModel):
    code: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
async def get_user_skills(
    include_shared: bool = Query(True),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await list_user_skills(user_id=user["sub"], include_shared=include_shared)


@router.post("", status_code=201)
async def create_user_skill(
    payload: CreateSkillPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    # Validate before saving
    validation = validate_skill_code(payload.code)
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail=f"Invalid skill code: {validation['error']}")

    skill_id = await save_user_skill(
        name=payload.name,
        description=payload.description,
        code=payload.code,
        created_by=user["sub"],
        is_shared=payload.is_shared,
        tags=payload.tags,
    )
    return {"id": skill_id, "name": payload.name, "created": True}


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    skill = await get_user_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    # Only creator or admin can see code
    include_code = (
        skill["created_by"] == user["sub"]
        or user.get("role") in ("admin", "manager")
        or skill["is_shared"]
    )
    if not include_code:
        skill.pop("code", None)
    return skill


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str,
    payload: UpdateSkillPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    skill = await get_user_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill["created_by"] != user["sub"] and user.get("role") not in ("admin",):
        raise HTTPException(status_code=403, detail="Only the creator can update this skill")

    updates = payload.model_dump(exclude_none=True)
    if "code" in updates:
        validation = validate_skill_code(updates["code"])
        if not validation["ok"]:
            raise HTTPException(status_code=422, detail=f"Invalid skill code: {validation['error']}")

    await save_user_skill(
        name=updates.get("name", skill["name"]),
        description=updates.get("description", skill.get("description", "")),
        code=updates.get("code", skill["code"]),
        created_by=skill["created_by"],
        is_shared=updates.get("is_shared", skill["is_shared"]),
        tags=updates.get("tags", []),
        skill_id=skill_id,
    )
    return {"id": skill_id, "updated": True}


@router.delete("/{skill_id}", status_code=204)
async def remove_skill(
    skill_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    deleted = await delete_user_skill(skill_id, requesting_user=user["sub"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found or not owned by you")


@router.post("/{skill_id}/execute")
async def execute_skill(
    skill_id: str,
    payload: ExecutePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    skill = await get_user_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if not skill["is_shared"] and skill["created_by"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await execute_user_skill(
        code=skill["code"],
        inputs=payload.inputs,
        user_id=user["sub"],
        skill_id=skill_id,
    )
    if not result["ok"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@router.post("/validate")
async def validate_skill(
    payload: ValidatePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    return validate_skill_code(payload.code)
