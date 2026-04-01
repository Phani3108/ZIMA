"""
Analytics routes — output history, approval stats, and advanced analytics.

GET /analytics/outputs       → paginated list of approved outputs
GET /analytics/stats         → aggregate stats (total, avg iterations, approval rate)
GET /analytics/summary       → executive summary for last N days
GET /analytics/llm           → LLM provider performance comparison
GET /analytics/bottlenecks   → pipeline stage bottleneck analysis
GET /analytics/quality-trend → first-pass approval rate over time
GET /analytics/skills        → skill leaderboard
GET /analytics/campaigns     → campaign efficiency metrics
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from zeta_ima.api.auth import get_current_user
from zeta_ima.memory.campaign import AsyncSessionLocal, approved_outputs
from zeta_ima.analytics import analytics_engine

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/outputs")
async def get_outputs(
    campaign_id: str = Query(None),
    channel: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        q = select(approved_outputs).order_by(approved_outputs.c.approved_at.desc())
        if campaign_id:
            q = q.where(approved_outputs.c.campaign_id == campaign_id)
        if channel:
            q = q.where(approved_outputs.c.channel == channel)
        q = q.limit(limit).offset(offset)
        result = await session.execute(q)
        rows = [dict(r._mapping) for r in result.fetchall()]
        for r in rows:
            if r.get("approved_at"):
                r["approved_at"] = str(r["approved_at"])
        return rows


@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)) -> dict:
    async with AsyncSessionLocal() as session:
        total_q = await session.execute(select(func.count()).select_from(approved_outputs))
        total = total_q.scalar() or 0

        avg_q = await session.execute(select(func.avg(approved_outputs.c.iterations_needed)))
        avg_iter = round(avg_q.scalar() or 0, 1)

    return {
        "total_approved_outputs": total,
        "avg_iterations_to_approval": avg_iter,
    }


@router.get("/summary")
async def get_summary(
    days: int = Query(30, le=365),
    user: dict = Depends(get_current_user),
) -> dict:
    return await analytics_engine.summary(days=days)


@router.get("/llm")
async def llm_performance(
    days: int = Query(30, le=365),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await analytics_engine.llm_performance(days=days)


@router.get("/bottlenecks")
async def bottlenecks(
    days: int = Query(30, le=365),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await analytics_engine.pipeline_bottlenecks(days=days)


@router.get("/quality-trend")
async def quality_trend(
    days: int = Query(90, le=365),
    bucket: str = Query("week", regex="^(week|month)$"),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await analytics_engine.quality_trend(days=days, bucket=bucket)


@router.get("/skills")
async def skill_leaderboard(
    days: int = Query(30, le=365),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await analytics_engine.skill_leaderboard(days=days)


@router.get("/campaigns")
async def campaign_efficiency(
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await analytics_engine.campaign_efficiency()
