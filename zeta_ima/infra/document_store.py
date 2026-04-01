"""
Document Store Abstraction — unified interface over PostgreSQL and Azure Cosmos DB.

Toggle via ``settings.learning_store`` ("postgres" | "cosmos").

Cosmos DB containers share partition key ``/team_id``.

Usage::

    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()
    await ds.upsert("conversation_archive", {"id": "abc", "team_id": "t1", ...})
    rows = await ds.query("feedback_entries", filters={"team_id": "t1"}, limit=10)
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

_instance: "DocumentStore | None" = None


def get_document_store() -> "DocumentStore":
    """Return the configured document store singleton."""
    global _instance
    if _instance is None:
        backend = settings.learning_store
        if backend == "cosmos":
            _instance = CosmosDocStore()
        else:
            _instance = PostgresDocStore()
        log.info("Document store backend: %s", backend)
    return _instance


# ── Interface ─────────────────────────────────────────────────────────────────


class DocumentStore(ABC):
    """Minimal document-store contract for learning/memory tables."""

    @abstractmethod
    async def init(self) -> None:
        """Create tables/containers. Idempotent."""

    @abstractmethod
    async def upsert(self, container: str, doc: dict[str, Any]) -> None:
        """Insert or replace a document. ``doc`` must have ``id``."""

    @abstractmethod
    async def upsert_batch(self, container: str, docs: list[dict[str, Any]]) -> None:
        """Batch insert/replace."""

    @abstractmethod
    async def get(self, container: str, doc_id: str, partition_key: str = "") -> dict[str, Any] | None:
        """Fetch a single document by ID."""

    @abstractmethod
    async def query(
        self,
        container: str,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at DESC",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query documents with simple equality filters."""

    @abstractmethod
    async def delete(self, container: str, doc_id: str, partition_key: str = "") -> None:
        """Delete a single document."""

    @abstractmethod
    async def count(self, container: str, filters: dict[str, Any] | None = None) -> int:
        """Count documents matching filters."""


# ── PostgreSQL Backend ────────────────────────────────────────────────────────

# Table definitions for the new learning tables.
# These map 1:1 with Cosmos containers.
POSTGRES_SCHEMAS: dict[str, str] = {
    "conversation_archive": """
        CREATE TABLE IF NOT EXISTS conversation_archive (
            id            TEXT PRIMARY KEY,
            team_id       TEXT NOT NULL,
            user_id       TEXT NOT NULL,
            brief         TEXT NOT NULL DEFAULT '',
            pipeline_id   TEXT NOT NULL DEFAULT '',
            messages_json TEXT NOT NULL DEFAULT '[]',
            outcome       TEXT NOT NULL DEFAULT '',
            blob_url      TEXT NOT NULL DEFAULT '',
            tags          JSONB NOT NULL DEFAULT '[]',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
    "team_learning_profiles": """
        CREATE TABLE IF NOT EXISTS team_learning_profiles (
            id                  TEXT PRIMARY KEY,
            team_id             TEXT NOT NULL UNIQUE,
            tone_preferences    JSONB NOT NULL DEFAULT '{}',
            format_preferences  JSONB NOT NULL DEFAULT '{}',
            common_edits        JSONB NOT NULL DEFAULT '[]',
            top_performing      JSONB NOT NULL DEFAULT '[]',
            feedback_summary    JSONB NOT NULL DEFAULT '{}',
            score_averages      JSONB NOT NULL DEFAULT '{}',
            signal_count        INTEGER NOT NULL DEFAULT 0,
            last_rebuilt_at     TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
    "feedback_entries": """
        CREATE TABLE IF NOT EXISTS feedback_entries (
            id                  TEXT PRIMARY KEY,
            team_id             TEXT NOT NULL,
            user_id             TEXT NOT NULL,
            workflow_id         TEXT NOT NULL DEFAULT '',
            stage_id            TEXT NOT NULL DEFAULT '',
            skill_id            TEXT NOT NULL DEFAULT '',
            rating              INTEGER NOT NULL DEFAULT 0,
            tags                JSONB NOT NULL DEFAULT '[]',
            free_text           TEXT NOT NULL DEFAULT '',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
    "campaign_scores": """
        CREATE TABLE IF NOT EXISTS campaign_scores (
            id              TEXT PRIMARY KEY,
            team_id         TEXT NOT NULL,
            campaign_id     TEXT NOT NULL DEFAULT '',
            workflow_id     TEXT NOT NULL DEFAULT '',
            source          TEXT NOT NULL DEFAULT 'manual',
            metrics         JSONB NOT NULL DEFAULT '{}',
            composite_score FLOAT NOT NULL DEFAULT 0.0,
            ingested_by     TEXT NOT NULL DEFAULT '',
            notes           TEXT NOT NULL DEFAULT '',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
    "prompt_versions": """
        CREATE TABLE IF NOT EXISTS prompt_versions (
            id              TEXT PRIMARY KEY,
            skill_id        TEXT NOT NULL,
            team_id         TEXT NOT NULL DEFAULT '__global__',
            version         INTEGER NOT NULL DEFAULT 1,
            content         TEXT NOT NULL,
            change_type     TEXT NOT NULL DEFAULT 'manual',
            change_reason   TEXT NOT NULL DEFAULT '',
            parent_id       TEXT NOT NULL DEFAULT '',
            is_active       BOOLEAN NOT NULL DEFAULT FALSE,
            performance     JSONB NOT NULL DEFAULT '{}',
            created_by      TEXT NOT NULL DEFAULT 'system',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
    "prompt_evolution_queue": """
        CREATE TABLE IF NOT EXISTS prompt_evolution_queue (
            id              TEXT PRIMARY KEY,
            skill_id        TEXT NOT NULL,
            team_id         TEXT NOT NULL DEFAULT '__global__',
            change_type     TEXT NOT NULL DEFAULT 'minor',
            trigger_reason  TEXT NOT NULL DEFAULT '',
            proposed_diff   TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            reviewed_by     TEXT NOT NULL DEFAULT '',
            reviewed_at     TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
}

# Indexes for common query patterns
POSTGRES_INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_conv_archive_team ON conversation_archive(team_id)",
    "CREATE INDEX IF NOT EXISTS idx_conv_archive_user ON conversation_archive(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_conv_archive_created ON conversation_archive(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_team ON feedback_entries(team_id)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_skill ON feedback_entries(skill_id)",
    "CREATE INDEX IF NOT EXISTS idx_scores_team ON campaign_scores(team_id)",
    "CREATE INDEX IF NOT EXISTS idx_scores_campaign ON campaign_scores(campaign_id)",
    "CREATE INDEX IF NOT EXISTS idx_prompt_ver_skill ON prompt_versions(skill_id, team_id)",
    "CREATE INDEX IF NOT EXISTS idx_prompt_ver_active ON prompt_versions(is_active) WHERE is_active = TRUE",
    "CREATE INDEX IF NOT EXISTS idx_prompt_evo_status ON prompt_evolution_queue(status)",
]


class PostgresDocStore(DocumentStore):
    """PostgreSQL-backed document store using asyncpg."""

    def __init__(self) -> None:
        self._pool: Any = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                dsn=settings.database_url, min_size=2, max_size=10,
            )
        return self._pool

    async def init(self) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            for table_name, ddl in POSTGRES_SCHEMAS.items():
                await conn.execute(ddl)
                log.info("Ensured table: %s", table_name)
            for idx_sql in POSTGRES_INDEXES:
                await conn.execute(idx_sql)

    async def upsert(self, container: str, doc: dict[str, Any]) -> None:
        pool = await self._get_pool()
        doc_id = doc.get("id")
        if not doc_id:
            raise ValueError("Document must have 'id' field")

        columns = list(doc.keys())
        # Serialize dict/list values to JSON strings for JSONB columns
        values = []
        for v in doc.values():
            if isinstance(v, (dict, list)):
                values.append(json.dumps(v))
            else:
                values.append(v)

        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        cols_str = ", ".join(columns)
        update_parts = ", ".join(
            f"{c} = EXCLUDED.{c}" for c in columns if c != "id"
        )

        sql = f"""
            INSERT INTO {container} ({cols_str})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET {update_parts}
        """
        async with pool.acquire() as conn:
            await conn.execute(sql, *values)

    async def upsert_batch(self, container: str, docs: list[dict[str, Any]]) -> None:
        for doc in docs:
            await self.upsert(container, doc)

    async def get(self, container: str, doc_id: str, partition_key: str = "") -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {container} WHERE id = $1", doc_id
            )
            return dict(row) if row else None

    async def query(
        self,
        container: str,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at DESC",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        where_parts: list[str] = []
        params: list[Any] = []
        idx = 1
        if filters:
            for k, v in filters.items():
                where_parts.append(f"{k} = ${idx}")
                params.append(v)
                idx += 1

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        sql = f"SELECT * FROM {container} {where_clause} ORDER BY {order_by} LIMIT ${idx} OFFSET ${idx+1}"
        params.extend([limit, offset])

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(r) for r in rows]

    async def delete(self, container: str, doc_id: str, partition_key: str = "") -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(f"DELETE FROM {container} WHERE id = $1", doc_id)

    async def count(self, container: str, filters: dict[str, Any] | None = None) -> int:
        pool = await self._get_pool()
        where_parts: list[str] = []
        params: list[Any] = []
        idx = 1
        if filters:
            for k, v in filters.items():
                where_parts.append(f"{k} = ${idx}")
                params.append(v)
                idx += 1
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        sql = f"SELECT count(*) FROM {container} {where_clause}"
        async with pool.acquire() as conn:
            return await conn.fetchval(sql, *params)


# ── Cosmos DB Backend ─────────────────────────────────────────────────────────

# Container configs: (name, partition_key_path)
COSMOS_CONTAINERS: list[tuple[str, str]] = [
    ("conversation_archive", "/team_id"),
    ("team_learning_profiles", "/team_id"),
    ("feedback_entries", "/team_id"),
    ("campaign_scores", "/team_id"),
    ("prompt_versions", "/team_id"),
    ("prompt_evolution_queue", "/team_id"),
]


class CosmosDocStore(DocumentStore):
    """Azure Cosmos DB-backed document store."""

    def __init__(self) -> None:
        from azure.cosmos.aio import CosmosClient
        from azure.core.credentials import AzureKeyCredential

        self._client = CosmosClient(
            url=settings.azure_cosmos_endpoint,
            credential=settings.azure_cosmos_key,
        )
        self._db_name = settings.azure_cosmos_database
        self._db = None

    async def _get_db(self):
        if self._db is None:
            self._db = self._client.get_database_client(self._db_name)
        return self._db

    async def _get_container(self, name: str):
        db = await self._get_db()
        return db.get_container_client(name)

    async def init(self) -> None:
        db = await self._get_db()
        from azure.cosmos import PartitionKey
        for container_name, pk_path in COSMOS_CONTAINERS:
            try:
                await db.create_container_if_not_exists(
                    id=container_name,
                    partition_key=PartitionKey(path=pk_path),
                )
                log.info("Ensured Cosmos container: %s", container_name)
            except Exception as e:
                log.warning("Cosmos container %s init: %s", container_name, e)

    async def upsert(self, container: str, doc: dict[str, Any]) -> None:
        c = await self._get_container(container)
        await c.upsert_item(doc)

    async def upsert_batch(self, container: str, docs: list[dict[str, Any]]) -> None:
        c = await self._get_container(container)
        for doc in docs:
            await c.upsert_item(doc)

    async def get(self, container: str, doc_id: str, partition_key: str = "") -> dict[str, Any] | None:
        c = await self._get_container(container)
        try:
            return await c.read_item(item=doc_id, partition_key=partition_key or doc_id)
        except Exception:
            return None

    async def query(
        self,
        container: str,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at DESC",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        c = await self._get_container(container)
        where_parts: list[str] = []
        params: list[dict] = []
        if filters:
            for i, (k, v) in enumerate(filters.items()):
                param_name = f"@p{i}"
                where_parts.append(f"c.{k} = {param_name}")
                params.append({"name": param_name, "value": v})

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        # Map SQL-style order_by to Cosmos format
        cosmos_order = order_by.replace(" ", " c.").replace("c.DESC", "DESC").replace("c.ASC", "ASC")
        if not cosmos_order.startswith("c."):
            cosmos_order = f"c.{cosmos_order}"

        query_str = f"SELECT * FROM c {where_clause} ORDER BY {cosmos_order} OFFSET {offset} LIMIT {limit}"

        items = []
        async for item in c.query_items(query=query_str, parameters=params):
            items.append(item)
        return items

    async def delete(self, container: str, doc_id: str, partition_key: str = "") -> None:
        c = await self._get_container(container)
        try:
            await c.delete_item(item=doc_id, partition_key=partition_key or doc_id)
        except Exception:
            pass

    async def count(self, container: str, filters: dict[str, Any] | None = None) -> int:
        c = await self._get_container(container)
        where_parts: list[str] = []
        params: list[dict] = []
        if filters:
            for i, (k, v) in enumerate(filters.items()):
                param_name = f"@p{i}"
                where_parts.append(f"c.{k} = {param_name}")
                params.append({"name": param_name, "value": v})
        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        query_str = f"SELECT VALUE COUNT(1) FROM c {where_clause}"
        async for item in c.query_items(query=query_str, parameters=params):
            return item
        return 0
