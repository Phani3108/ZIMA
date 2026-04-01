"""
Cost & usage routes — LLM spending reports and rate limit status.

GET  /costs/report     → aggregate usage report (total cost, tokens, per-model)
GET  /costs/daily      → daily cost breakdown for charting
GET  /costs/limits     → current user's rate limit status
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from zeta_ima.api.auth import get_current_user
from zeta_ima.agents.cost_tracker import cost_tracker

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("/report")
async def usage_report(
    days: int = Query(30, le=365),
    all_users: bool = Query(False, description="Show all users (admin only)"),
    user: dict = Depends(get_current_user),
) -> dict:
    user_id = None if all_users else user["sub"]
    return await cost_tracker.usage_report(user_id=user_id, days=days)


@router.get("/daily")
async def daily_breakdown(
    days: int = Query(30, le=90),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await cost_tracker.daily_breakdown(user_id=user["sub"], days=days)


@router.get("/limits")
async def rate_limits(
    user: dict = Depends(get_current_user),
) -> dict:
    return await cost_tracker.check_rate_limit(user["sub"])
