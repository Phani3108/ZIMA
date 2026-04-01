"""
Ingestion pipeline — orchestrates extract → chunk → embed → Qdrant.

All jobs run as FastAPI BackgroundTasks (non-blocking).
Job status is tracked in PostgreSQL `ingest_jobs` table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from qdrant_client.models import PointStruct
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings
from zeta_ima.ingest.chunker import chunk_text, Chunk
from zeta_ima.memory.brand import _qdrant, _openai, EMBEDDING_DIMS, ensure_collection

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()
ingest_jobs = Table(
    "ingest_jobs",
    _metadata,
    Column("id", String, primary_key=True),
    Column("source_type", String),
    Column("source_name", String),
    Column("status", String),     # pending | processing | done | error
    Column("chunks_created", Integer, default=0),
    Column("error_message", Text),
    Column("created_at", DateTime),
    Column("completed_at", DateTime),
)


async def init_ingest_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)

    # Ensure knowledge_base Qdrant collection exists
    existing = {c.name for c in _qdrant.get_collections().collections}
    if settings.qdrant_kb_collection not in existing:
        from qdrant_client.models import VectorParams, Distance
        _qdrant.create_collection(
            collection_name=settings.qdrant_kb_collection,
            vectors_config=VectorParams(size=EMBEDDING_DIMS, distance=Distance.COSINE),
        )


async def _update_job(job_id: str, status: str, chunks: int = 0, error: str = None):
    async with _Session() as session:
        completed = datetime.now(timezone.utc) if status in ("done", "error") else None
        await session.execute(
            ingest_jobs.update()
            .where(ingest_jobs.c.id == job_id)
            .values(status=status, chunks_created=chunks, error_message=error, completed_at=completed)
        )
        await session.commit()


async def _embed_and_store(chunks: list[Chunk]) -> int:
    """Embed chunks and upsert into Qdrant knowledge_base. Returns count stored."""
    texts = [c.text for c in chunks]
    resp = await _openai.embeddings.create(model="text-embedding-3-small", input=texts)
    vectors = [r.embedding for r in resp.data]

    points = [
        PointStruct(
            id=chunk.chunk_id,
            vector=vectors[i],
            payload={
                "text": chunk.text,
                "source_type": chunk.source_type,
                "source_name": chunk.source_name,
                "source_url": chunk.source_url,
                "ingested_at": chunk.ingested_at,
            },
        )
        for i, chunk in enumerate(chunks)
    ]

    _qdrant.upsert(collection_name=settings.qdrant_kb_collection, points=points)
    return len(points)


async def ingest_file_bytes(job_id: str, file_bytes: bytes, filename: str):
    """Background task: extract → chunk → embed a file."""
    await _update_job(job_id, "processing")
    try:
        from zeta_ima.ingest.extractors.file import extract_text
        text = extract_text(file_bytes, filename)
        chunks = chunk_text(text, source_type="file", source_name=filename)
        count = await _embed_and_store(chunks)
        await _update_job(job_id, "done", chunks=count)
    except Exception as e:
        await _update_job(job_id, "error", error=str(e))


async def ingest_url(job_id: str, url: str):
    """Background task: scrape URL → chunk → embed."""
    await _update_job(job_id, "processing")
    try:
        from zeta_ima.ingest.extractors.url import extract_url
        text = await extract_url(url)
        chunks = chunk_text(text, source_type="url", source_name=url, source_url=url)
        count = await _embed_and_store(chunks)
        await _update_job(job_id, "done", chunks=count)
    except Exception as e:
        await _update_job(job_id, "error", error=str(e))


async def ingest_confluence_page(job_id: str, page_id: str):
    """Background task: pull Confluence page → chunk → embed."""
    await _update_job(job_id, "processing")
    try:
        from zeta_ima.ingest.extractors.confluence import extract_page
        title, text = await extract_page(page_id)
        chunks = chunk_text(text, source_type="confluence", source_name=title)
        count = await _embed_and_store(chunks)
        await _update_job(job_id, "done", chunks=count)
    except Exception as e:
        await _update_job(job_id, "error", error=str(e))


async def ingest_teams_chat(job_id: str, json_bytes: bytes, export_name: str):
    """Background task: parse Teams chat export → chunk → embed."""
    await _update_job(job_id, "processing")
    try:
        from zeta_ima.ingest.extractors.teams_chat import extract_teams_chat
        text = extract_teams_chat(json_bytes)
        chunks = chunk_text(text, source_type="teams_chat", source_name=export_name)
        count = await _embed_and_store(chunks)
        await _update_job(job_id, "done", chunks=count)
    except Exception as e:
        await _update_job(job_id, "error", error=str(e))


async def create_job(source_type: str, source_name: str) -> str:
    """Create a new ingest job record. Returns job_id."""
    job_id = str(uuid.uuid4())
    async with _Session() as session:
        await session.execute(
            ingest_jobs.insert().values(
                id=job_id,
                source_type=source_type,
                source_name=source_name,
                status="pending",
                chunks_created=0,
                created_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
    return job_id


async def list_jobs(limit: int = 20) -> list[dict]:
    from sqlalchemy import select, desc
    async with _Session() as session:
        result = await session.execute(
            select(ingest_jobs).order_by(desc(ingest_jobs.c.created_at)).limit(limit)
        )
        return [dict(r._mapping) for r in result.fetchall()]
