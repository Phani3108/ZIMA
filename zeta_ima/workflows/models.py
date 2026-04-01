"""
Workflow & Stage PostgreSQL models + data access layer.

Workflows are persistent multi-stage pipelines stored in PostgreSQL.
Each workflow maps to a skill + template and tracks stage-by-stage progress.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
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

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

workflows = Table(
    "workflows",
    _metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("skill_id", String, nullable=False),
    Column("template_id", String),
    Column("campaign_id", String),
    Column("created_by", String, nullable=False),
    Column("status", String, nullable=False, default="active"),
    Column("variables", JSONB, default={}),
    Column("current_stage_index", Integer, default=0),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

workflow_stages = Table(
    "workflow_stages",
    _metadata,
    Column("id", String, primary_key=True),
    Column("workflow_id", String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
    Column("stage_index", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("agent_name", String, nullable=False),
    Column("skill_id", String),
    Column("prompt_id", String),
    Column("status", String, nullable=False, default="pending"),
    Column("owner", String),
    Column("output", JSONB),
    Column("preview_type", String),
    Column("preview_url", String),
    Column("error", Text),
    Column("requires_approval", Boolean, default=False),
    Column("llm_used", String),
    Column("started_at", DateTime),
    Column("completed_at", DateTime),
)

workflow_escalations = Table(
    "workflow_escalations",
    _metadata,
    Column("id", String, primary_key=True),
    Column("workflow_id", String, ForeignKey("workflows.id")),
    Column("stage_id", String, ForeignKey("workflow_stages.id")),
    Column("jira_ticket_id", String),
    Column("jira_url", String),
    Column("pings_sent", Integer, default=0),
    Column("last_ping_at", DateTime),
    Column("escalated_to_manager", Boolean, default=False),
    Column("resolved", Boolean, default=False),
    Column("created_at", DateTime),
)


async def init_workflow_db() -> None:
    """Create workflow tables if they don't exist."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

async def create_workflow(
    name: str,
    skill_id: str,
    template_id: Optional[str],
    created_by: str,
    variables: dict,
    stages: list[dict],
    campaign_id: Optional[str] = None,
) -> dict:
    """Create a workflow + its stages in one transaction."""
    wf_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    async with _Session() as session:
        await session.execute(
            workflows.insert().values(
                id=wf_id,
                name=name,
                skill_id=skill_id,
                template_id=template_id,
                campaign_id=campaign_id,
                created_by=created_by,
                status="active",
                variables=variables,
                current_stage_index=0,
                created_at=now,
                updated_at=now,
            )
        )

        for idx, stage in enumerate(stages):
            await session.execute(
                workflow_stages.insert().values(
                    id=str(uuid.uuid4()),
                    workflow_id=wf_id,
                    stage_index=idx,
                    name=stage["name"],
                    agent_name=stage["agent"],
                    skill_id=stage.get("skill_id", skill_id),
                    prompt_id=stage.get("prompt"),
                    status="pending",
                    owner=stage.get("owner"),
                    requires_approval=stage.get("requires_approval", False),
                )
            )
        await session.commit()

    return await get_workflow(wf_id)


async def get_workflow(workflow_id: str) -> Optional[dict]:
    """Fetch a workflow with all its stages."""
    async with _Session() as session:
        wf_row = await session.execute(
            select(workflows).where(workflows.c.id == workflow_id)
        )
        wf = wf_row.fetchone()
        if wf is None:
            return None

        stages_rows = await session.execute(
            select(workflow_stages)
            .where(workflow_stages.c.workflow_id == workflow_id)
            .order_by(workflow_stages.c.stage_index)
        )

        return {
            **dict(wf._mapping),
            "stages": [dict(s._mapping) for s in stages_rows.fetchall()],
        }


async def list_workflows(
    status: Optional[str] = None,
    created_by: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List workflows with optional filters."""
    async with _Session() as session:
        q = select(workflows).order_by(workflows.c.updated_at.desc()).limit(limit)
        if status:
            q = q.where(workflows.c.status == status)
        if created_by:
            q = q.where(workflows.c.created_by == created_by)

        result = await session.execute(q)
        wf_list = []
        for wf in result.fetchall():
            # Fetch stages count and current stage info
            stages_result = await session.execute(
                select(workflow_stages)
                .where(workflow_stages.c.workflow_id == wf.id)
                .order_by(workflow_stages.c.stage_index)
            )
            stages = [dict(s._mapping) for s in stages_result.fetchall()]
            wf_list.append({**dict(wf._mapping), "stages": stages})

        return wf_list


async def update_stage(
    stage_id: str,
    **kwargs,
) -> None:
    """Update a stage's fields (status, output, error, llm_used, etc.)."""
    async with _Session() as session:
        await session.execute(
            workflow_stages.update()
            .where(workflow_stages.c.id == stage_id)
            .values(**kwargs, )
        )
        # Also update the parent workflow's updated_at
        stage_row = await session.execute(
            select(workflow_stages.c.workflow_id).where(workflow_stages.c.id == stage_id)
        )
        row = stage_row.fetchone()
        if row:
            await session.execute(
                workflows.update()
                .where(workflows.c.id == row.workflow_id)
                .values(updated_at=datetime.now(timezone.utc))
            )
        await session.commit()


async def update_workflow_status(workflow_id: str, status: str) -> None:
    """Update workflow status."""
    async with _Session() as session:
        await session.execute(
            workflows.update()
            .where(workflows.c.id == workflow_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )
        await session.commit()


async def advance_current_stage(workflow_id: str) -> None:
    """Increment the current_stage_index."""
    async with _Session() as session:
        wf = await session.execute(
            select(workflows.c.current_stage_index).where(workflows.c.id == workflow_id)
        )
        row = wf.fetchone()
        if row:
            await session.execute(
                workflows.update()
                .where(workflows.c.id == workflow_id)
                .values(
                    current_stage_index=row.current_stage_index + 1,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        await session.commit()
