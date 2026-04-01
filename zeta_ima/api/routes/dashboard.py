"""
Dashboard routes — program manager overview with aggregated metrics.

GET /dashboard/summary        → top-level KPIs (active, completed, stuck workflows)
GET /dashboard/activity       → recent activity feed across all workflows
GET /dashboard/stuck          → workflows/stages that are stuck (needs escalation)
GET /dashboard/agents         → agent health + LLM provider status
GET /dashboard/skills-usage   → which skills/prompts are used most
"""

from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from zeta_ima.api.auth import get_current_user
from zeta_ima.agents.llm_router import check_available_providers
from zeta_ima.workflows.models import list_workflows, get_workflow

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

STUCK_THRESHOLD_HOURS = 4  # Stage is "stuck" if in_progress > 4 hours


def _serialize_dt(val) -> Optional[str]:
    if val and isinstance(val, datetime):
        return val.isoformat()
    return val


# ─── Summary KPIs ──────────────────────────────────────────────────

@router.get("/summary")
async def dashboard_summary(user: dict = Depends(get_current_user)) -> dict:
    """Top-level dashboard KPIs for program managers."""
    all_wfs = await list_workflows(limit=500)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=STUCK_THRESHOLD_HOURS)

    total = len(all_wfs)
    active = 0
    completed = 0
    cancelled = 0
    stuck_count = 0
    awaiting_review = 0
    total_stages = 0
    completed_stages = 0
    failed_stages = 0

    for wf in all_wfs:
        if wf["status"] == "active":
            active += 1
        elif wf["status"] == "completed":
            completed += 1
        elif wf["status"] == "cancelled":
            cancelled += 1

        for stage in wf.get("stages", []):
            total_stages += 1
            if stage["status"] == "approved":
                completed_stages += 1
            elif stage["status"] == "needs_retry":
                failed_stages += 1
            elif stage["status"] == "awaiting_review":
                awaiting_review += 1
            elif stage["status"] == "in_progress":
                started = stage.get("started_at")
                if started and isinstance(started, datetime) and started < cutoff:
                    stuck_count += 1

    return {
        "workflows": {
            "total": total,
            "active": active,
            "completed": completed,
            "cancelled": cancelled,
        },
        "stages": {
            "total": total_stages,
            "completed": completed_stages,
            "failed": failed_stages,
            "awaiting_review": awaiting_review,
            "stuck": stuck_count,
        },
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
        "stage_success_rate": round(completed_stages / total_stages * 100, 1) if total_stages > 0 else 0,
    }


# ─── Activity Feed ─────────────────────────────────────────────────

@router.get("/activity")
async def dashboard_activity(
    limit: int = Query(30, ge=1, le=100),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Recent activity across all workflows — sorted by most recent."""
    all_wfs = await list_workflows(limit=100)

    events = []
    for wf in all_wfs:
        for stage in wf.get("stages", []):
            if stage["status"] == "pending":
                continue

            timestamp = stage.get("completed_at") or stage.get("started_at") or wf.get("created_at")
            events.append({
                "workflow_id": wf["id"],
                "workflow_name": wf["name"],
                "stage_id": stage["id"],
                "stage_name": stage["name"],
                "stage_status": stage["status"],
                "agent": stage.get("agent_name", ""),
                "llm_used": stage.get("llm_used"),
                "error": stage.get("error"),
                "timestamp": _serialize_dt(timestamp),
            })

    # Sort by timestamp descending
    events.sort(key=lambda e: e["timestamp"] or "", reverse=True)
    return events[:limit]


# ─── Stuck Stages ──────────────────────────────────────────────────

@router.get("/stuck")
async def dashboard_stuck(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return stages that are stuck (in_progress or needs_retry for too long)."""
    all_wfs = await list_workflows(status="active", limit=200)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=STUCK_THRESHOLD_HOURS)

    stuck = []
    for wf in all_wfs:
        for stage in wf.get("stages", []):
            is_stuck = False
            reason = ""

            if stage["status"] == "in_progress":
                started = stage.get("started_at")
                if started and isinstance(started, datetime) and started < cutoff:
                    is_stuck = True
                    hours = (now - started).total_seconds() / 3600
                    reason = f"In progress for {hours:.1f} hours"

            elif stage["status"] == "needs_retry":
                is_stuck = True
                reason = f"Failed: {stage.get('error', 'Unknown error')}"

            elif stage["status"] == "awaiting_review":
                completed = stage.get("completed_at")
                if completed and isinstance(completed, datetime) and completed < cutoff:
                    is_stuck = True
                    hours = (now - completed).total_seconds() / 3600
                    reason = f"Awaiting review for {hours:.1f} hours"

            if is_stuck:
                stuck.append({
                    "workflow_id": wf["id"],
                    "workflow_name": wf["name"],
                    "stage_id": stage["id"],
                    "stage_name": stage["name"],
                    "stage_status": stage["status"],
                    "agent": stage.get("agent_name", ""),
                    "reason": reason,
                    "owner": stage.get("owner"),
                    "started_at": _serialize_dt(stage.get("started_at")),
                })

    return stuck


# ─── Agent & LLM Health ────────────────────────────────────────────

@router.get("/agents")
async def dashboard_agents(user: dict = Depends(get_current_user)) -> dict:
    """Show agent health and LLM provider availability."""
    providers = await check_available_providers()

    # Compute LLM usage stats from recent workflows
    all_wfs = await list_workflows(limit=100)
    llm_usage: Counter = Counter()
    agent_usage: Counter = Counter()

    for wf in all_wfs:
        for stage in wf.get("stages", []):
            if stage.get("llm_used"):
                llm_usage[stage["llm_used"]] += 1
            if stage.get("agent_name"):
                agent_usage[stage["agent_name"]] += 1

    return {
        "providers": providers,
        "llm_usage": dict(llm_usage.most_common(10)),
        "agent_usage": dict(agent_usage.most_common(10)),
        "agents": [
            {"name": "copy", "description": "Copywriting & content generation", "status": "active"},
            {"name": "seo", "description": "SEO analysis & optimization", "status": "active"},
            {"name": "research", "description": "Market & competitive research", "status": "active"},
            {"name": "design", "description": "Design briefs & visual generation", "status": "active"},
            {"name": "jira", "description": "Jira ticket management", "status": "active"},
            {"name": "confluence", "description": "Confluence page management", "status": "active"},
        ],
    }


# ─── Skills Usage Analytics ────────────────────────────────────────

@router.get("/skills-usage")
async def dashboard_skills_usage(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Show which skills are used most frequently."""
    all_wfs = await list_workflows(limit=500)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    skill_stats: dict[str, dict] = {}
    for wf in all_wfs:
        created = wf.get("created_at")
        if created and isinstance(created, datetime) and created < cutoff:
            continue

        sid = wf.get("skill_id", "unknown")
        if sid not in skill_stats:
            skill_stats[sid] = {
                "skill_id": sid,
                "workflow_count": 0,
                "completed": 0,
                "active": 0,
                "failed_stages": 0,
            }
        skill_stats[sid]["workflow_count"] += 1
        if wf["status"] == "completed":
            skill_stats[sid]["completed"] += 1
        elif wf["status"] == "active":
            skill_stats[sid]["active"] += 1

        for stage in wf.get("stages", []):
            if stage["status"] == "needs_retry":
                skill_stats[sid]["failed_stages"] += 1

    result = sorted(skill_stats.values(), key=lambda x: x["workflow_count"], reverse=True)
    return result
