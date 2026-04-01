"""
Task Queue — PostgreSQL-backed task table + Redis sorted set for priority dispatch.

Tasks decouple "request" from "execution": a user/system creates a task,
the OrchestratorRouter classifies it, and the TaskDispatcher picks it up.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, DateTime, Integer, MetaData, String, Table, Text, select, update,
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

tasks = Table(
    "tasks",
    _metadata,
    Column("id", String, primary_key=True),
    Column("title", String, nullable=False),
    Column("description", Text, default=""),
    Column("requester_id", String, nullable=False),
    Column("assignee_agent", String, default=""),         # Set by router
    Column("priority", Integer, default=2),               # 1=low, 2=medium, 3=high
    Column("status", String, nullable=False, default="queued"),
    # Status: queued | assigned | in_progress | review | done | escalated | cancelled
    Column("pipeline", JSONB, default=[]),                # e.g. ["research","pm","copy","design","review","approval"]
    Column("pipeline_name", String, default=""),
    Column("routing_rationale", Text, default=""),        # Why this pipeline was chosen
    Column("workflow_id", String, default=""),             # Linked workflow once created
    Column("metadata", JSONB, default={}),                # Arbitrary extra data
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)


async def init_task_db() -> None:
    """Create the tasks table."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("Task queue DB initialized")


async def create_task(
    title: str,
    description: str,
    requester_id: str,
    priority: int = 2,
    pipeline_name: str | None = None,
    pipeline: list[str] | None = None,
    routing_rationale: str | None = None,
    assignee_agent: str | None = None,
    metadata: dict | None = None,
) -> str:
    """Insert a new task in 'queued' status. Returns task_id."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    row = {
        "id": task_id,
        "title": title,
        "description": description,
        "requester_id": requester_id,
        "assignee_agent": assignee_agent or "",
        "priority": priority,
        "status": "queued",
        "pipeline": pipeline or [],
        "pipeline_name": pipeline_name or "",
        "routing_rationale": routing_rationale or "",
        "workflow_id": "",
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }

    async with _Session() as session:
        await session.execute(tasks.insert().values(**row))
        await session.commit()

    # Push to Redis sorted set for priority dispatch
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        # Score = priority * 1e12 - timestamp (higher priority, older tasks first)
        score = priority * 1_000_000_000_000 - int(now.timestamp())
        await r.zadd("task_queue", {task_id: score})
        await r.aclose()
    except Exception as e:
        log.warning(f"Redis push failed (task will still be in DB): {e}")

    return task_id


async def get_task(task_id: str) -> Optional[dict]:
    """Fetch a single task by ID."""
    async with _Session() as session:
        result = await session.execute(select(tasks).where(tasks.c.id == task_id))
        row = result.mappings().first()
        return dict(row) if row else None


async def list_tasks(
    requester_id: str | None = None,
    status: str | None = None,
    pipeline_name: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List tasks with optional filters."""
    q = select(tasks).order_by(tasks.c.created_at.desc()).limit(limit)
    if requester_id:
        q = q.where(tasks.c.requester_id == requester_id)
    if status:
        q = q.where(tasks.c.status == status)
    if pipeline_name:
        q = q.where(tasks.c.pipeline_name == pipeline_name)

    async with _Session() as session:
        result = await session.execute(q)
        return [dict(row) for row in result.mappings().fetchall()]


async def update_task(task_id: str, **fields) -> Optional[dict]:
    """Update task fields. Returns updated task."""
    fields["updated_at"] = datetime.now(timezone.utc)
    async with _Session() as session:
        await session.execute(
            update(tasks).where(tasks.c.id == task_id).values(**fields)
        )
        await session.commit()
    return await get_task(task_id)


async def pop_next_task() -> Optional[dict]:
    """
    Pop the highest-priority task from the Redis queue and return it.
    Returns None if queue is empty.
    """
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)

        # ZPOPMAX returns the highest-score member (highest priority)
        result = await r.zpopmax("task_queue", count=1)
        await r.aclose()

        if not result:
            return None

        task_id = result[0][0]
        if isinstance(task_id, bytes):
            task_id = task_id.decode("utf-8")

        return await get_task(task_id)

    except Exception as e:
        log.warning(f"Redis pop failed: {e}")
        # Fallback: query DB for oldest queued task
        async with _Session() as session:
            result = await session.execute(
                select(tasks)
                .where(tasks.c.status == "queued")
                .order_by(tasks.c.priority.desc(), tasks.c.created_at.asc())
                .limit(1)
            )
            row = result.mappings().first()
            return dict(row) if row else None
