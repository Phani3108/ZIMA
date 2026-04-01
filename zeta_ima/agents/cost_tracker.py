"""
Cost Tracker & Rate Limiter — monitors LLM token usage and enforces spending limits.

Tracks every LLM call with token counts and estimated cost.
Uses Redis for real-time rate windows and PostgreSQL for historical records.

Pricing is approximate and configurable. Updated to April 2026 pricing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import redis.asyncio as aioredis
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

log = logging.getLogger(__name__)

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

# Cost per 1K tokens (approximate)
TOKEN_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "gemini-2.5-flash": {"input": 0.00015, "output": 0.0006},
}

llm_usage = Table(
    "llm_usage",
    _metadata,
    Column("id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("provider", String, nullable=False),
    Column("model", String, nullable=False),
    Column("input_tokens", Integer, default=0),
    Column("output_tokens", Integer, default=0),
    Column("estimated_cost_usd", Float, default=0.0),
    Column("skill_id", String, default=""),
    Column("workflow_id", String, default=""),
    Column("created_at", DateTime),
)


async def init_cost_db() -> None:
    """Create the llm_usage table."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("Cost tracking DB initialized")


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a single LLM call."""
    rates = TOKEN_COSTS.get(model, {"input": 0.001, "output": 0.002})
    return round(
        (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"],
        6,
    )


class CostTracker:
    """Tracks LLM costs and enforces rate limits via Redis sliding windows."""

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None

    async def init(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.redis_url
        self._redis = aioredis.from_url(url, decode_responses=True)

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            await self.init()
        return self._redis  # type: ignore

    async def record(
        self,
        user_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        skill_id: str = "",
        workflow_id: str = "",
    ) -> dict[str, Any]:
        """Record an LLM usage event. Returns the record with estimated cost."""
        cost = estimate_cost(model, input_tokens, output_tokens)
        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Persist to PostgreSQL for historical analysis
        async with _Session() as session:
            await session.execute(
                llm_usage.insert().values(
                    id=record_id,
                    user_id=user_id,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=cost,
                    skill_id=skill_id,
                    workflow_id=workflow_id,
                    created_at=now,
                )
            )
            await session.commit()

        # Update Redis sliding window counters
        r = await self._get_redis()
        day_key = f"cost:daily:{user_id}:{now.strftime('%Y-%m-%d')}"
        month_key = f"cost:monthly:{user_id}:{now.strftime('%Y-%m')}"

        pipe = r.pipeline()
        pipe.incrbyfloat(day_key, cost)
        pipe.expire(day_key, 86400 * 2)          # 2-day TTL
        pipe.incrbyfloat(month_key, cost)
        pipe.expire(month_key, 86400 * 35)        # 35-day TTL
        await pipe.execute()

        return {
            "id": record_id,
            "cost_usd": cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    async def check_rate_limit(
        self,
        user_id: str,
        daily_limit_usd: float = 10.0,
        monthly_limit_usd: float = 200.0,
    ) -> dict[str, Any]:
        """
        Check if a user is within spending limits.

        Returns: {"allowed": bool, "daily_spent": float, "monthly_spent": float, "reason": str}
        """
        r = await self._get_redis()
        now = datetime.now(timezone.utc)
        day_key = f"cost:daily:{user_id}:{now.strftime('%Y-%m-%d')}"
        month_key = f"cost:monthly:{user_id}:{now.strftime('%Y-%m')}"

        daily_raw = await r.get(day_key)
        monthly_raw = await r.get(month_key)
        daily_spent = float(daily_raw) if daily_raw else 0.0
        monthly_spent = float(monthly_raw) if monthly_raw else 0.0

        if daily_spent >= daily_limit_usd:
            return {
                "allowed": False,
                "daily_spent": round(daily_spent, 4),
                "monthly_spent": round(monthly_spent, 4),
                "reason": f"Daily limit ${daily_limit_usd} exceeded",
            }
        if monthly_spent >= monthly_limit_usd:
            return {
                "allowed": False,
                "daily_spent": round(daily_spent, 4),
                "monthly_spent": round(monthly_spent, 4),
                "reason": f"Monthly limit ${monthly_limit_usd} exceeded",
            }
        return {
            "allowed": True,
            "daily_spent": round(daily_spent, 4),
            "monthly_spent": round(monthly_spent, 4),
            "reason": "",
        }

    async def usage_report(
        self,
        user_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Aggregate usage report: total cost, tokens, per-model breakdown."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        where_clause = "WHERE created_at >= :cutoff"
        params: dict[str, Any] = {"cutoff": cutoff}
        if user_id:
            where_clause += " AND user_id = :user_id"
            params["user_id"] = user_id

        summary_q = text(f"""
            SELECT
                count(*)                                AS total_calls,
                coalesce(sum(input_tokens), 0)          AS total_input_tokens,
                coalesce(sum(output_tokens), 0)         AS total_output_tokens,
                round(coalesce(sum(estimated_cost_usd), 0)::numeric, 4) AS total_cost_usd
            FROM llm_usage
            {where_clause}
        """)
        by_model_q = text(f"""
            SELECT
                model,
                provider,
                count(*)                                AS calls,
                coalesce(sum(input_tokens), 0)          AS input_tokens,
                coalesce(sum(output_tokens), 0)         AS output_tokens,
                round(coalesce(sum(estimated_cost_usd), 0)::numeric, 4) AS cost_usd
            FROM llm_usage
            {where_clause}
            GROUP BY model, provider
            ORDER BY cost_usd DESC
        """)

        async with _Session() as session:
            result = await session.execute(summary_q, params)
            summary = dict(result.fetchone()._mapping)

            result = await session.execute(by_model_q, params)
            by_model = [dict(r._mapping) for r in result.fetchall()]

        return {
            "period_days": days,
            **summary,
            "by_model": by_model,
        }

    async def daily_breakdown(
        self,
        user_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Daily cost breakdown for charting."""
        where_clause = "WHERE created_at >= now() - (:days || ' days')::interval"
        params: dict[str, Any] = {"days": str(days)}
        if user_id:
            where_clause += " AND user_id = :user_id"
            params["user_id"] = user_id

        query = text(f"""
            SELECT
                date_trunc('day', created_at) AS day,
                count(*) AS calls,
                round(coalesce(sum(estimated_cost_usd), 0)::numeric, 4) AS cost_usd,
                coalesce(sum(input_tokens + output_tokens), 0) AS total_tokens
            FROM llm_usage
            {where_clause}
            GROUP BY day
            ORDER BY day
        """)
        async with _Session() as session:
            result = await session.execute(query, params)
            rows = [dict(r._mapping) for r in result.fetchall()]
            for r in rows:
                if r.get("day"):
                    r["day"] = r["day"].isoformat()
            return rows


cost_tracker = CostTracker()
