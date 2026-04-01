"""
Scheduler — cron-like recurring workflow triggers.

Stores schedule definitions in PostgreSQL and runs an asyncio background loop
that checks for due schedules every 60 seconds.

Each schedule triggers workflow creation via the WorkflowEngine.

Usage:
    from zeta_ima.orchestrator.scheduler import scheduler

    # Create a schedule
    await scheduler.create(
        name="Weekly LinkedIn Post",
        cron_expr="0 9 * * 1",       # Every Monday 9am UTC
        template_id="linkedin_post",
        variables={"brief": "Share a thought leadership post"},
        created_by="user-123",
    )

    # Start the background loop (called at app startup)
    await scheduler.start()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from croniter import croniter
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    select,
    update,
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

schedules = Table(
    "schedules",
    _metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("cron_expr", String, nullable=False),
    Column("template_id", String, nullable=False),
    Column("variables", JSONB, default={}),
    Column("created_by", String, nullable=False),
    Column("campaign_id", String, default=""),
    Column("enabled", Boolean, default=True),
    Column("last_run_at", DateTime),
    Column("next_run_at", DateTime, nullable=False),
    Column("run_count", Integer, default=0),
    Column("max_runs", Integer, default=0),           # 0 = unlimited
    Column("last_workflow_id", String, default=""),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)


async def init_scheduler_db() -> None:
    """Create the schedules table."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("Scheduler DB initialized")


class Scheduler:
    """Background scheduler that creates workflows on cron schedules."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        log.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        log.info("Scheduler stopped")

    async def _loop(self) -> None:
        """Check for due schedules every 60 seconds."""
        while self._running:
            try:
                await self._tick()
            except Exception:
                log.exception("Scheduler tick error")
            await asyncio.sleep(60)

    async def _tick(self) -> None:
        """Fire all schedules that are due."""
        now = datetime.now(timezone.utc)
        async with _Session() as session:
            result = await session.execute(
                select(schedules).where(
                    schedules.c.enabled == True,  # noqa: E712
                    schedules.c.next_run_at <= now,
                )
            )
            due = result.fetchall()

        for row in due:
            try:
                await self._fire(row._mapping)
            except Exception:
                log.exception("Failed to fire schedule %s", row.id)

    async def _fire(self, sched: dict) -> None:
        """Create a workflow for a due schedule and advance next_run_at."""
        from zeta_ima.workflows.engine import WorkflowEngine

        sched_id = sched["id"]
        cron = sched["cron_expr"]
        now = datetime.now(timezone.utc)

        engine = WorkflowEngine()
        wf = await engine.create_from_template(
            template_id=sched["template_id"],
            variables=sched.get("variables") or {},
            user_id=sched["created_by"],
            name=f"[Scheduled] {sched['name']}",
            campaign_id=sched.get("campaign_id") or None,
        )
        log.info("Schedule %s fired → workflow %s", sched_id, wf["id"])

        # Auto-advance the new workflow
        try:
            await engine.advance(wf["id"])
        except Exception as e:
            log.warning("Auto-advance for scheduled workflow failed: %s", e)

        # Compute next run
        cron_iter = croniter(cron, now)
        next_run = cron_iter.get_next(datetime)
        new_run_count = (sched.get("run_count") or 0) + 1
        max_runs = sched.get("max_runs") or 0

        # If max_runs exceeded, disable
        enabled = True
        if max_runs > 0 and new_run_count >= max_runs:
            enabled = False
            log.info("Schedule %s reached max_runs=%d, disabling", sched_id, max_runs)

        async with _Session() as session:
            await session.execute(
                update(schedules)
                .where(schedules.c.id == sched_id)
                .values(
                    last_run_at=now,
                    next_run_at=next_run,
                    run_count=new_run_count,
                    last_workflow_id=wf["id"],
                    enabled=enabled,
                    updated_at=now,
                )
            )
            await session.commit()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(
        self,
        name: str,
        cron_expr: str,
        template_id: str,
        variables: dict[str, Any],
        created_by: str,
        campaign_id: str | None = None,
        max_runs: int = 0,
    ) -> dict[str, Any]:
        """Create a new schedule. Returns the schedule dict."""
        # Validate cron expression
        if not croniter.is_valid(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        # Validate template exists
        from zeta_ima.workflows.templates import WORKFLOW_TEMPLATES
        if template_id not in WORKFLOW_TEMPLATES:
            raise ValueError(f"Template '{template_id}' not found")

        now = datetime.now(timezone.utc)
        cron_iter = croniter(cron_expr, now)
        next_run = cron_iter.get_next(datetime)

        sched_id = str(uuid.uuid4())
        row = {
            "id": sched_id,
            "name": name,
            "cron_expr": cron_expr,
            "template_id": template_id,
            "variables": variables,
            "created_by": created_by,
            "campaign_id": campaign_id or "",
            "enabled": True,
            "next_run_at": next_run,
            "run_count": 0,
            "max_runs": max_runs,
            "last_workflow_id": "",
            "created_at": now,
            "updated_at": now,
        }

        async with _Session() as session:
            await session.execute(schedules.insert().values(**row))
            await session.commit()

        log.info("Schedule created: %s (%s) → next run %s", name, cron_expr, next_run.isoformat())
        return row

    async def list_schedules(self, created_by: str | None = None) -> list[dict]:
        """List all schedules, optionally filtered by creator."""
        stmt = select(schedules).order_by(schedules.c.next_run_at.asc())
        if created_by:
            stmt = stmt.where(schedules.c.created_by == created_by)
        async with _Session() as session:
            result = await session.execute(stmt)
            return [dict(r._mapping) for r in result.fetchall()]

    async def get_schedule(self, schedule_id: str) -> dict | None:
        """Get a single schedule by ID."""
        async with _Session() as session:
            result = await session.execute(
                select(schedules).where(schedules.c.id == schedule_id)
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def update_schedule(
        self,
        schedule_id: str,
        **kwargs: Any,
    ) -> dict | None:
        """Update a schedule. Pass any column as a keyword argument."""
        now = datetime.now(timezone.utc)
        kwargs["updated_at"] = now

        # If cron_expr changed, recompute next_run_at
        if "cron_expr" in kwargs:
            if not croniter.is_valid(kwargs["cron_expr"]):
                raise ValueError(f"Invalid cron expression: {kwargs['cron_expr']}")
            cron_iter = croniter(kwargs["cron_expr"], now)
            kwargs["next_run_at"] = cron_iter.get_next(datetime)

        async with _Session() as session:
            await session.execute(
                update(schedules)
                .where(schedules.c.id == schedule_id)
                .values(**kwargs)
            )
            await session.commit()
        return await self.get_schedule(schedule_id)

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule. Returns True if found and deleted."""
        async with _Session() as session:
            result = await session.execute(
                schedules.delete().where(schedules.c.id == schedule_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def toggle(self, schedule_id: str, enabled: bool) -> dict | None:
        """Enable or disable a schedule."""
        return await self.update_schedule(schedule_id, enabled=enabled)


# Singleton
scheduler = Scheduler()
