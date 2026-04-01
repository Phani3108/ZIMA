"""
Analytics Engine — advanced performance analytics for the marketing agency.

Provides:
  - LLM performance analysis (cost, speed, approval rates per provider)
  - Workflow pipeline analysis (bottleneck stages, avg completion time)
  - Content quality trends (iterations over time, first-pass approval trends)
  - Contributor leaderboard
  - Campaign ROI metrics (outputs per campaign, efficiency)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy import func, select, text, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

log = logging.getLogger(__name__)

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


class AnalyticsEngine:
    """Aggregates performance data from workflow_outcomes, workflows, and approved_outputs."""

    async def llm_performance(self, days: int = 30) -> list[dict[str, Any]]:
        """
        Compare LLM providers: approval rate, avg iterations, avg execution time.

        Returns one row per LLM used in the given time window.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = text("""
            SELECT
                llm_used,
                count(*)                                        AS total_runs,
                round(avg(CASE WHEN approved_first_try THEN 1 ELSE 0 END)::numeric * 100, 1) AS first_pass_pct,
                round(avg(iterations_needed)::numeric, 2)       AS avg_iterations,
                round(avg(execution_time_ms)::numeric, 0)       AS avg_time_ms,
                round(avg(final_output_length)::numeric, 0)     AS avg_output_len
            FROM workflow_outcomes
            WHERE created_at >= :cutoff AND llm_used != ''
            GROUP BY llm_used
            ORDER BY first_pass_pct DESC
        """)
        async with _Session() as session:
            result = await session.execute(query, {"cutoff": cutoff})
            return [dict(r._mapping) for r in result.fetchall()]

    async def pipeline_bottlenecks(self, days: int = 30) -> list[dict[str, Any]]:
        """
        Identify which workflow stages take the longest or fail the most.

        Returns one row per (agent_name, stage name) pair.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = text("""
            SELECT
                s.name                                          AS stage_name,
                s.agent_name,
                count(*)                                        AS total,
                count(*) FILTER (WHERE s.status = 'completed')  AS completed,
                count(*) FILTER (WHERE s.status = 'failed')     AS failed,
                round(avg(EXTRACT(EPOCH FROM (s.completed_at - s.started_at)))::numeric, 1) AS avg_duration_sec,
                max(EXTRACT(EPOCH FROM (s.completed_at - s.started_at)))::numeric           AS max_duration_sec
            FROM workflow_stages s
            JOIN workflows w ON w.id = s.workflow_id
            WHERE w.created_at >= :cutoff
            GROUP BY s.name, s.agent_name
            ORDER BY avg_duration_sec DESC NULLS LAST
        """)
        async with _Session() as session:
            result = await session.execute(query, {"cutoff": cutoff})
            return [dict(r._mapping) for r in result.fetchall()]

    async def quality_trend(self, days: int = 90, bucket: str = "week") -> list[dict[str, Any]]:
        """
        Content quality trend: first-pass approval rate and avg iterations
        bucketed by week or month.
        """
        if bucket not in ("week", "month"):
            bucket = "week"
        query = text(f"""
            SELECT
                date_trunc(:bucket, created_at)            AS period,
                count(*)                                   AS total,
                round(avg(CASE WHEN approved_first_try THEN 1 ELSE 0 END)::numeric * 100, 1) AS first_pass_pct,
                round(avg(iterations_needed)::numeric, 2)  AS avg_iterations
            FROM workflow_outcomes
            WHERE created_at >= now() - (:days || ' days')::interval
            GROUP BY period
            ORDER BY period
        """)
        async with _Session() as session:
            result = await session.execute(query, {"bucket": bucket, "days": str(days)})
            rows = [dict(r._mapping) for r in result.fetchall()]
            for r in rows:
                if r.get("period"):
                    r["period"] = r["period"].isoformat()
            return rows

    async def skill_leaderboard(self, days: int = 30) -> list[dict[str, Any]]:
        """
        Rank skills by usage, approval rate, and efficiency.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = text("""
            SELECT
                skill_id,
                count(*)                                        AS total_runs,
                round(avg(CASE WHEN approved_first_try THEN 1 ELSE 0 END)::numeric * 100, 1) AS first_pass_pct,
                round(avg(iterations_needed)::numeric, 2)       AS avg_iterations,
                round(avg(execution_time_ms)::numeric, 0)       AS avg_time_ms
            FROM workflow_outcomes
            WHERE created_at >= :cutoff AND skill_id != ''
            GROUP BY skill_id
            ORDER BY total_runs DESC
        """)
        async with _Session() as session:
            result = await session.execute(query, {"cutoff": cutoff})
            return [dict(r._mapping) for r in result.fetchall()]

    async def campaign_efficiency(self) -> list[dict[str, Any]]:
        """
        Per-campaign metrics: output count, avg iterations, workflow count.
        """
        query = text("""
            SELECT
                c.id                                         AS campaign_id,
                c.name                                       AS campaign_name,
                c.status,
                count(DISTINCT w.id)                         AS workflow_count,
                count(DISTINCT ao.id)                        AS output_count,
                round(avg(ao.iterations_needed)::numeric, 2) AS avg_iterations
            FROM campaigns c
            LEFT JOIN workflows w ON w.campaign_id = c.id
            LEFT JOIN approved_outputs ao ON ao.campaign_id = c.id
            GROUP BY c.id, c.name, c.status
            ORDER BY output_count DESC
        """)
        async with _Session() as session:
            result = await session.execute(query)
            return [dict(r._mapping) for r in result.fetchall()]

    async def summary(self, days: int = 30) -> dict[str, Any]:
        """
        Executive summary: key metrics for the last N days.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = text("""
            SELECT
                count(*)                                        AS total_outputs,
                round(avg(CASE WHEN approved_first_try THEN 1 ELSE 0 END)::numeric * 100, 1) AS first_pass_pct,
                round(avg(iterations_needed)::numeric, 2)       AS avg_iterations,
                round(avg(execution_time_ms)::numeric, 0)       AS avg_time_ms
            FROM workflow_outcomes
            WHERE created_at >= :cutoff
        """)
        wf_query = text("""
            SELECT
                count(*)                                        AS total_workflows,
                count(*) FILTER (WHERE status = 'completed')    AS completed,
                count(*) FILTER (WHERE status = 'blocked')      AS blocked
            FROM workflows
            WHERE created_at >= :cutoff
        """)
        async with _Session() as session:
            result = await session.execute(query, {"cutoff": cutoff})
            outcome_row = dict(result.fetchone()._mapping)

            wf_result = await session.execute(wf_query, {"cutoff": cutoff})
            wf_row = dict(wf_result.fetchone()._mapping)

        return {
            "period_days": days,
            **outcome_row,
            **wf_row,
        }


analytics_engine = AnalyticsEngine()
