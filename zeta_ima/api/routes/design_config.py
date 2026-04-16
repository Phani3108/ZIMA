"""
Design engine configuration routes — Manager-only CRUD for tool routing,
platform presets, and design rules.

GET  /design/config/tools          → all tool configs
PUT  /design/config/tools          → upsert a tool config
GET  /design/config/presets        → all presets (optionally filtered by skill)
PUT  /design/config/presets        → upsert a preset
GET  /design/config/rules          → global design rules
PUT  /design/config/rules          → update design rules
"""

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.agents.design_config import (
    DesignRules,
    Preset,
    ToolConfig,
    design_config,
)

router = APIRouter(prefix="/design/config", tags=["design-config"])

# ── Pydantic models for request bodies ──────────────────────────────────────


class ToolConfigBody(BaseModel):
    skill_id: str
    primary_tool: str
    backup_tool: str
    enabled: bool = True


class PresetBody(BaseModel):
    skill_id: str
    platform: str
    label: str = ""
    width: int
    height: int
    aspect_ratio: str = "1:1"
    resolution: str = "1K"
    format: str = "png"


class RulesBody(BaseModel):
    max_iterations: int = 3
    default_quality: str = "hd"
    auto_review: bool = True
    auto_approve_min_score: int = 8
    style_prompt_prefix: str = ""


# ── Tool routing ────────────────────────────────────────────────────────────


@router.get("/tools")
async def list_tool_configs(user: dict = Depends(get_current_user)) -> list[dict]:
    configs = await design_config.get_all_tool_configs()
    return [asdict(c) for c in configs]


@router.put("/tools")
async def upsert_tool_config(
    body: ToolConfigBody,
    user: dict = Depends(get_current_user),
) -> dict:
    VALID_TOOLS = {"gemini", "dalle", "canva", "figma", "midjourney"}
    if body.primary_tool not in VALID_TOOLS:
        raise HTTPException(400, f"Invalid primary_tool. Must be one of: {', '.join(sorted(VALID_TOOLS))}")
    if body.backup_tool not in VALID_TOOLS:
        raise HTTPException(400, f"Invalid backup_tool. Must be one of: {', '.join(sorted(VALID_TOOLS))}")

    tc = ToolConfig(
        skill_id=body.skill_id,
        primary_tool=body.primary_tool,
        backup_tool=body.backup_tool,
        enabled=body.enabled,
    )
    await design_config.save_tool_config(tc, user_id=user.get("sub", ""))
    return {"ok": True, **asdict(tc)}


# ── Platform presets ────────────────────────────────────────────────────────


@router.get("/presets")
async def list_presets(
    skill_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    if skill_id:
        presets = await design_config.get_presets(skill_id)
    else:
        presets = await design_config.get_all_presets()
    return [asdict(p) for p in presets]


@router.put("/presets")
async def upsert_preset(
    body: PresetBody,
    user: dict = Depends(get_current_user),
) -> dict:
    if body.width < 16 or body.height < 16:
        raise HTTPException(400, "Width and height must be at least 16px")

    preset = Preset(
        skill_id=body.skill_id,
        platform=body.platform,
        label=body.label,
        width=body.width,
        height=body.height,
        aspect_ratio=body.aspect_ratio,
        resolution=body.resolution,
        format=body.format,
    )
    await design_config.save_preset(preset, user_id=user.get("sub", ""))
    return {"ok": True, **asdict(preset)}


# ── Design rules ────────────────────────────────────────────────────────────


@router.get("/rules")
async def get_rules(user: dict = Depends(get_current_user)) -> dict:
    rules = await design_config.get_rules()
    return asdict(rules)


@router.put("/rules")
async def update_rules(
    body: RulesBody,
    user: dict = Depends(get_current_user),
) -> dict:
    if body.max_iterations < 1 or body.max_iterations > 10:
        raise HTTPException(400, "max_iterations must be between 1 and 10")

    rules = DesignRules(
        max_iterations=body.max_iterations,
        default_quality=body.default_quality,
        auto_review=body.auto_review,
        auto_approve_min_score=body.auto_approve_min_score,
        style_prompt_prefix=body.style_prompt_prefix,
    )
    await design_config.save_rules(rules, user_id=user.get("sub", ""))
    return {"ok": True, **asdict(rules)}
