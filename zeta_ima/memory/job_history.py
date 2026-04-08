"""
Agent Job History — records every completed job for per-template history and suggestions.

Stores the output of each approved/rejected job per agent+task_template combination.
Supports querying recent jobs (global or per-user) and returning the last N approved
jobs as "suggestions" for reuse.

Usage:
    from zeta_ima.memory.job_history import job_history, init_job_history_db

    await init_job_history_db()
    await job_history.record_job(...)
    recent = await job_history.get_recent_jobs("copy", "linkedin_post", limit=5)
    suggestions = await job_history.get_suggestions("copy", "linkedin_post", limit=2)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

log = logging.getLogger(__name__)

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

agent_job_history = Table(
    "agent_job_history",
    _metadata,
    Column("id", String, primary_key=True),
    Column("task_template_id", String, nullable=False, index=True),
    Column("agent_name", String, nullable=False, index=True),
    Column("user_id", String, nullable=False),
    Column("team_id", String, default=""),
    Column("brief", Text, default=""),
    Column("output_text", Text, default=""),
    Column("output_metadata", JSONB, default={}),
    Column("review_scores", JSONB, default={}),
    Column("status", String, nullable=False, default="approved"),  # approved|rejected|discarded
    Column("workflow_id", String, default=""),
    Column("stage_id", String, default=""),
    Column("created_at", DateTime, nullable=False),
)


async def init_job_history_db() -> None:
    """Create the agent_job_history table if it doesn't exist."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("Job history DB initialized")


class JobHistoryService:
    """Manages agent job history storage and retrieval."""

    async def init(self) -> None:
        """Create the DB table if needed."""
        await init_job_history_db()

    async def record_job(
        self,
        agent_name: str,
        task_template_id: str,
        user_id: str,
        team_id: str = "",
        brief: str = "",
        output_text: str = "",
        output_metadata: dict | None = None,
        review_scores: dict | None = None,
        status: str = "approved",
        workflow_id: str = "",
        stage_id: str = "",
    ) -> str:
        """Record a completed job. Returns the job ID."""
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        async with _Session() as session:
            await session.execute(
                agent_job_history.insert().values(
                    id=job_id,
                    task_template_id=task_template_id,
                    agent_name=agent_name,
                    user_id=user_id,
                    team_id=team_id,
                    brief=brief,
                    output_text=output_text,
                    output_metadata=output_metadata or {},
                    review_scores=review_scores or {},
                    status=status,
                    workflow_id=workflow_id,
                    stage_id=stage_id,
                    created_at=now,
                )
            )
            await session.commit()

        log.info("Recorded job %s for agent=%s template=%s", job_id, agent_name, task_template_id)
        return job_id

    async def get_recent_jobs(
        self,
        agent_name: str,
        task_template_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Get recent jobs for an agent. Optionally filter by template and user."""
        stmt = (
            select(agent_job_history)
            .where(agent_job_history.c.agent_name == agent_name)
            .order_by(agent_job_history.c.created_at.desc())
            .limit(limit)
        )
        if task_template_id:
            stmt = stmt.where(agent_job_history.c.task_template_id == task_template_id)
        if user_id:
            stmt = stmt.where(agent_job_history.c.user_id == user_id)

        async with _Session() as session:
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def get_suggestions(
        self,
        agent_name: Optional[str] = None,
        task_template_id: Optional[str] = None,
        template_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 2,
    ) -> list[dict]:
        """Get the last N approved jobs as reuse suggestions."""
        effective_template = task_template_id or template_id
        stmt = (
            select(agent_job_history)
            .where(agent_job_history.c.status == "approved")
            .order_by(agent_job_history.c.created_at.desc())
            .limit(limit)
        )
        if agent_name:
            stmt = stmt.where(agent_job_history.c.agent_name == agent_name)
        if effective_template:
            stmt = stmt.where(agent_job_history.c.task_template_id == effective_template)
        if user_id:
            stmt = stmt.where(agent_job_history.c.user_id == user_id)

        async with _Session() as session:
            result = await session.execute(stmt)
            rows = result.fetchall()
            return [self._row_to_dict(r) for r in rows]

    async def get_job(self, job_id: str) -> dict | None:
        """Get a single job by ID."""
        async with _Session() as session:
            result = await session.execute(
                select(agent_job_history).where(agent_job_history.c.id == job_id)
            )
            row = result.fetchone()
            return self._row_to_dict(row) if row else None

    def _row_to_dict(self, row) -> dict:
        d = dict(row._mapping)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        return d


# Module-level singleton
job_history = JobHistoryService()
