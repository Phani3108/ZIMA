"""
Artifact Library — versioned approved outputs with shareable links and comments.

Every approved workflow stage output, manually saved asset, or exported content
becomes an artifact with version history, comment threads, and token-based sharing.

Usage:
    from zeta_ima.memory.artifacts import artifact_store, init_artifacts_db

    await init_artifacts_db()
    aid = await artifact_store.create(
        team_id="t1", title="Q3 Blog Post",
        content="...", content_type="markdown",
        created_by="user-1", source_workflow_id="wf-123",
    )
    token = await artifact_store.create_share_link(aid, created_by="user-1")
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

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
    delete,
    func,
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

# ── Tables ────────────────────────────────────────────────────────────────────

artifacts_table = Table(
    "artifacts",
    _metadata,
    Column("id", String, primary_key=True),
    Column("team_id", String, nullable=False),
    Column("title", String, nullable=False),
    Column("content", Text, nullable=False),
    Column("content_type", String, nullable=False, default="markdown"),  # markdown, html, text, json
    Column("version", Integer, nullable=False, default=1),
    Column("parent_id", String, nullable=True),  # previous version
    Column("source_workflow_id", String, nullable=True),
    Column("source_stage_id", String, nullable=True),
    Column("skill_id", String, nullable=True),
    Column("tags", JSONB, default=[]),
    Column("created_by", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("is_latest", Boolean, nullable=False, default=True),
    Column("metadata", JSONB, default={}),
)

artifact_comments_table = Table(
    "artifact_comments",
    _metadata,
    Column("id", String, primary_key=True),
    Column("artifact_id", String, nullable=False),
    Column("author", String, nullable=False),
    Column("body", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("is_external", Boolean, default=False),  # came from external review
)

artifact_share_links_table = Table(
    "artifact_share_links",
    _metadata,
    Column("id", String, primary_key=True),
    Column("artifact_id", String, nullable=False),
    Column("token", String, nullable=False, unique=True),
    Column("created_by", String, nullable=False),
    Column("expires_at", DateTime, nullable=True),
    Column("allow_comments", Boolean, default=True),
    Column("allow_approve", Boolean, default=False),
    Column("created_at", DateTime, nullable=False),
    Column("is_revoked", Boolean, default=False),
)


async def init_artifacts_db() -> None:
    """Create artifact tables. Idempotent."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("Artifacts DB initialized")


# ── Artifact Store ────────────────────────────────────────────────────────────


class ArtifactStore:

    async def create(
        self,
        team_id: str,
        title: str,
        content: str,
        content_type: str = "markdown",
        created_by: str = "system",
        source_workflow_id: str | None = None,
        source_stage_id: str | None = None,
        skill_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Create a new artifact. Returns artifact ID."""
        aid = f"art-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        async with _Session() as s:
            await s.execute(artifacts_table.insert().values(
                id=aid,
                team_id=team_id,
                title=title,
                content=content,
                content_type=content_type,
                version=1,
                parent_id=None,
                source_workflow_id=source_workflow_id,
                source_stage_id=source_stage_id,
                skill_id=skill_id,
                tags=tags or [],
                created_by=created_by,
                created_at=now,
                updated_at=now,
                is_latest=True,
                metadata=metadata or {},
            ))
            await s.commit()
        log.info("Created artifact %s: %s", aid, title)
        return aid

    async def create_version(
        self,
        artifact_id: str,
        content: str,
        updated_by: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Create a new version of an existing artifact. Returns new version ID."""
        parent = await self.get(artifact_id)
        if not parent:
            raise ValueError(f"Artifact {artifact_id} not found")

        new_id = f"art-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        new_version = parent["version"] + 1

        async with _Session() as s:
            # Mark old as not latest
            await s.execute(
                update(artifacts_table)
                .where(artifacts_table.c.id == artifact_id)
                .values(is_latest=False, updated_at=now)
            )
            # Create new version
            await s.execute(artifacts_table.insert().values(
                id=new_id,
                team_id=parent["team_id"],
                title=title or parent["title"],
                content=content,
                content_type=parent["content_type"],
                version=new_version,
                parent_id=artifact_id,
                source_workflow_id=parent.get("source_workflow_id"),
                source_stage_id=parent.get("source_stage_id"),
                skill_id=parent.get("skill_id"),
                tags=tags if tags is not None else parent.get("tags", []),
                created_by=updated_by,
                created_at=now,
                updated_at=now,
                is_latest=True,
                metadata=parent.get("metadata", {}),
            ))
            await s.commit()
        log.info("Created version %d of artifact %s → %s", new_version, artifact_id, new_id)
        return new_id

    async def get(self, artifact_id: str) -> dict | None:
        """Fetch a single artifact by ID."""
        async with _Session() as s:
            row = (await s.execute(
                select(artifacts_table).where(artifacts_table.c.id == artifact_id)
            )).mappings().first()
            if not row:
                return None
            return {**row}

    async def get_by_token(self, token: str) -> dict | None:
        """Fetch an artifact via a share token. Returns None if expired/revoked."""
        async with _Session() as s:
            link = (await s.execute(
                select(artifact_share_links_table)
                .where(artifact_share_links_table.c.token == token)
                .where(artifact_share_links_table.c.is_revoked == False)
            )).mappings().first()
            if not link:
                return None
            if link["expires_at"] and link["expires_at"] < datetime.now(timezone.utc):
                return None
            artifact = await self.get(link["artifact_id"])
            if artifact:
                artifact["_share_permissions"] = {
                    "allow_comments": link["allow_comments"],
                    "allow_approve": link["allow_approve"],
                }
            return artifact

    async def list_artifacts(
        self,
        team_id: str,
        latest_only: bool = True,
        tags: list[str] | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List artifacts for a team."""
        q = select(artifacts_table).where(artifacts_table.c.team_id == team_id)
        if latest_only:
            q = q.where(artifacts_table.c.is_latest == True)
        if tags:
            q = q.where(artifacts_table.c.tags.contains(tags))
        if search:
            q = q.where(
                artifacts_table.c.title.ilike(f"%{search}%")
                | artifacts_table.c.content.ilike(f"%{search}%")
            )
        q = q.order_by(artifacts_table.c.updated_at.desc()).offset(offset).limit(limit)
        async with _Session() as s:
            rows = (await s.execute(q)).mappings().all()
            return [
                {k: v for k, v in r.items() if k != "content"}  # Exclude content from list
                for r in rows
            ]

    async def get_version_history(self, artifact_id: str) -> list[dict]:
        """Get full version chain for an artifact."""
        artifact = await self.get(artifact_id)
        if not artifact:
            return []
        # Walk back through parent chain
        chain = [artifact]
        current = artifact
        while current.get("parent_id"):
            parent = await self.get(current["parent_id"])
            if not parent:
                break
            chain.append(parent)
            current = parent
        return list(reversed(chain))

    async def delete_artifact(self, artifact_id: str) -> bool:
        async with _Session() as s:
            result = await s.execute(
                delete(artifacts_table).where(artifacts_table.c.id == artifact_id)
            )
            await s.commit()
            return result.rowcount > 0

    # ── Comments ──────────────────────────────────────────────────────

    async def add_comment(
        self,
        artifact_id: str,
        author: str,
        body: str,
        is_external: bool = False,
    ) -> str:
        cid = f"cmt-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        async with _Session() as s:
            await s.execute(artifact_comments_table.insert().values(
                id=cid,
                artifact_id=artifact_id,
                author=author,
                body=body,
                created_at=now,
                is_external=is_external,
            ))
            await s.commit()
        return cid

    async def list_comments(self, artifact_id: str, limit: int = 100) -> list[dict]:
        async with _Session() as s:
            rows = (await s.execute(
                select(artifact_comments_table)
                .where(artifact_comments_table.c.artifact_id == artifact_id)
                .order_by(artifact_comments_table.c.created_at.asc())
                .limit(limit)
            )).mappings().all()
            return [dict(r) for r in rows]

    # ── Share Links ───────────────────────────────────────────────────

    async def create_share_link(
        self,
        artifact_id: str,
        created_by: str,
        expires_hours: int | None = 72,
        allow_comments: bool = True,
        allow_approve: bool = False,
    ) -> str:
        """Create a token-based share link. Returns the token."""
        token = secrets.token_urlsafe(32)
        link_id = f"shr-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_hours) if expires_hours else None
        async with _Session() as s:
            await s.execute(artifact_share_links_table.insert().values(
                id=link_id,
                artifact_id=artifact_id,
                token=token,
                created_by=created_by,
                expires_at=expires_at,
                allow_comments=allow_comments,
                allow_approve=allow_approve,
                created_at=now,
                is_revoked=False,
            ))
            await s.commit()
        return token

    async def revoke_share_link(self, token: str) -> bool:
        async with _Session() as s:
            result = await s.execute(
                update(artifact_share_links_table)
                .where(artifact_share_links_table.c.token == token)
                .values(is_revoked=True)
            )
            await s.commit()
            return result.rowcount > 0

    async def list_share_links(self, artifact_id: str) -> list[dict]:
        async with _Session() as s:
            rows = (await s.execute(
                select(artifact_share_links_table)
                .where(artifact_share_links_table.c.artifact_id == artifact_id)
                .where(artifact_share_links_table.c.is_revoked == False)
                .order_by(artifact_share_links_table.c.created_at.desc())
            )).mappings().all()
            return [dict(r) for r in rows]

    # ── Stats ─────────────────────────────────────────────────────────

    async def count(self, team_id: str) -> int:
        async with _Session() as s:
            result = await s.execute(
                select(func.count())
                .select_from(artifacts_table)
                .where(artifacts_table.c.team_id == team_id)
                .where(artifacts_table.c.is_latest == True)
            )
            return result.scalar() or 0


artifact_store = ArtifactStore()
