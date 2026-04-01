"""
Audit Trail — records all significant actions for compliance.

Every workflow state change, approval/rejection, integration call,
and escalation is logged with actor, action, and details.

Usage:
    from zeta_ima.memory.audit import audit_log

    await audit_log.record(
        actor="dev-user",
        action="approved",
        resource_type="stage",
        resource_id="stage-123",
        details={"comment": "Looks good", "workflow_id": "wf-456"},
    )
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

audit_entries = Table(
    "audit_log",
    _metadata,
    Column("id", String, primary_key=True),
    Column("timestamp", DateTime, nullable=False),
    Column("actor", String, nullable=False),        # user_id or agent name
    Column("action", String, nullable=False),        # created, approved, rejected, published, etc.
    Column("resource_type", String, nullable=False),  # workflow, stage, integration, program
    Column("resource_id", String, nullable=False),
    Column("details", JSONB),                         # Before/after, comments, context
)


async def init_audit_db() -> None:
    """Create audit_log table if it doesn't exist."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)


class AuditLog:
    """Records and queries audit trail entries."""

    async def record(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict | None = None,
    ) -> str:
        """
        Record an audit event.

        Args:
            actor: Who performed the action (user_id, agent name, or "system")
            action: What happened (created, updated, approved, rejected,
                     published, escalated, configured, deleted)
            resource_type: What kind of resource (workflow, stage, integration,
                           program, skill)
            resource_id: ID of the affected resource
            details: Additional context (JSONB)

        Returns:
            audit entry ID
        """
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        try:
            async with _Session() as session:
                await session.execute(
                    audit_entries.insert().values(
                        id=entry_id,
                        timestamp=now,
                        actor=actor,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details or {},
                    )
                )
                await session.commit()
        except Exception as e:
            log.warning(f"Failed to record audit entry: {e}")

        return entry_id

    async def get_for_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """Get audit trail for a specific resource."""
        async with _Session() as session:
            result = await session.execute(
                select(audit_entries)
                .where(
                    audit_entries.c.resource_type == resource_type,
                    audit_entries.c.resource_id == resource_id,
                )
                .order_by(audit_entries.c.timestamp.desc())
                .limit(limit)
            )
            return [
                {**dict(r._mapping), "timestamp": r.timestamp.isoformat()}
                for r in result.fetchall()
            ]

    async def get_for_workflow(self, workflow_id: str, limit: int = 200) -> list[dict]:
        """Get all audit entries related to a workflow (by resource_id or in details)."""
        async with _Session() as session:
            # Get entries where resource_id is the workflow
            result = await session.execute(
                select(audit_entries)
                .where(audit_entries.c.resource_id == workflow_id)
                .order_by(audit_entries.c.timestamp.desc())
                .limit(limit)
            )
            entries = [
                {**dict(r._mapping), "timestamp": r.timestamp.isoformat()}
                for r in result.fetchall()
            ]

            # Also get stage-level entries that reference this workflow
            result2 = await session.execute(
                select(audit_entries)
                .where(
                    audit_entries.c.resource_type == "stage",
                    audit_entries.c.details["workflow_id"].as_string() == workflow_id,
                )
                .order_by(audit_entries.c.timestamp.desc())
                .limit(limit)
            )
            entries.extend([
                {**dict(r._mapping), "timestamp": r.timestamp.isoformat()}
                for r in result2.fetchall()
            ])

            # Sort by timestamp
            entries.sort(key=lambda e: e["timestamp"], reverse=True)
            return entries[:limit]

    async def get_recent(
        self,
        limit: int = 50,
        action: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> list[dict]:
        """Get recent audit entries with optional filters."""
        async with _Session() as session:
            q = select(audit_entries).order_by(audit_entries.c.timestamp.desc()).limit(limit)
            if action:
                q = q.where(audit_entries.c.action == action)
            if actor:
                q = q.where(audit_entries.c.actor == actor)

            result = await session.execute(q)
            return [
                {**dict(r._mapping), "timestamp": r.timestamp.isoformat()}
                for r in result.fetchall()
            ]


# Module-level singleton
audit_log = AuditLog()
