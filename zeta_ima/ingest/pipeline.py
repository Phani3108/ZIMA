"""
Ingestion pipeline — orchestrates extract → chunk → embed → Qdrant.

All jobs run as FastAPI BackgroundTasks (non-blocking).
Job status is tracked in PostgreSQL `ingest_jobs` table with granular progress.
WebSocket notifications are pushed at each step for live frontend updates.
"""

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings, get_embedding_client
from zeta_ima.ingest.chunker import chunk_text, Chunk
from zeta_ima.memory.brand import EMBEDDING_DIMS

log = logging.getLogger(__name__)

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# Avg embedding time per chunk (ms) — updated over time for better estimates
_AVG_MS_PER_CHUNK = 120.0
_EMBED_BATCH_SIZE = 50

_metadata = MetaData()
ingest_jobs = Table(
    "ingest_jobs",
    _metadata,
    Column("id", String, primary_key=True),
    Column("source_type", String),
    Column("source_name", String),
    Column("status", String),             # pending | extracting | chunking | embedding | done | error
    Column("current_step", String),       # extracting | chunking | embedding | done
    Column("progress_pct", Integer, default=0),
    Column("total_chunks", Integer, default=0),
    Column("embedded_chunks", Integer, default=0),
    Column("chunks_created", Integer, default=0),
    Column("error_message", Text),
    Column("estimated_seconds_remaining", Float, default=0),
    Column("created_at", DateTime),
    Column("completed_at", DateTime),
)


async def init_ingest_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)

    # Ensure knowledge_base vector collection exists
    from zeta_ima.infra.vector_store import get_vector_store
    vs = get_vector_store()
    vs.ensure_collection(settings.qdrant_kb_collection, vector_size=EMBEDDING_DIMS)


async def _update_job(
    job_id: str,
    status: str,
    chunks: int = 0,
    error: str = None,
    current_step: str = "",
    progress_pct: int = 0,
    total_chunks: int = 0,
    embedded_chunks: int = 0,
    estimated_seconds: float = 0,
):
    """Update job status and push WebSocket notification."""
    async with _Session() as session:
        completed = datetime.now(timezone.utc) if status in ("done", "error") else None
        values = dict(
            status=status,
            chunks_created=chunks,
            error_message=error,
            completed_at=completed,
            current_step=current_step or status,
            progress_pct=progress_pct,
            total_chunks=total_chunks,
            embedded_chunks=embedded_chunks,
            estimated_seconds_remaining=estimated_seconds,
        )
        await session.execute(
            ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(**values)
        )
        await session.commit()

    # Push notification for live frontend updates
    try:
        from zeta_ima.notify.service import notifications
        await notifications.send(
            user_id="__broadcast__",
            title="Ingestion Update",
            body=f"{current_step or status}: {progress_pct}%",
            action_url=f"/ingest",
            channel="web",
            event_type="ingest_progress",
            extra={
                "job_id": job_id,
                "status": status,
                "current_step": current_step or status,
                "progress_pct": progress_pct,
                "total_chunks": total_chunks,
                "embedded_chunks": embedded_chunks,
                "estimated_seconds_remaining": estimated_seconds,
            },
        )
    except Exception:
        pass  # Notification failure is non-fatal


async def _embed_and_store(
    chunks: list[Chunk],
    job_id: str,
) -> int:
    """Embed chunks in batches, update progress per batch, upsert to Qdrant."""
    global _AVG_MS_PER_CHUNK

    from zeta_ima.infra.vector_store import get_vector_store

    client = get_embedding_client()
    vs = get_vector_store()
    total = len(chunks)
    embedded_count = 0
    all_points = []

    for batch_start in range(0, total, _EMBED_BATCH_SIZE):
        batch = chunks[batch_start:batch_start + _EMBED_BATCH_SIZE]
        texts = [c.text for c in batch]

        import time
        t0 = time.monotonic()
        resp = await client.embeddings.create(model=settings.embedding_model, input=texts)
        elapsed_ms = (time.monotonic() - t0) * 1000

        # Update running average
        _AVG_MS_PER_CHUNK = (_AVG_MS_PER_CHUNK * 0.8) + ((elapsed_ms / len(batch)) * 0.2)

        vectors = [r.embedding for r in resp.data]
        for i, chunk in enumerate(batch):
            all_points.append({
                "id": chunk.chunk_id,
                "vector": vectors[i],
                "payload": {
                    "text": chunk.text,
                    "source_type": chunk.source_type,
                    "source_name": chunk.source_name,
                    "source_url": chunk.source_url,
                    "ingested_at": chunk.ingested_at,
                },
            })

        embedded_count += len(batch)
        remaining = total - embedded_count
        est_seconds = (remaining * _AVG_MS_PER_CHUNK) / 1000
        pct = 40 + int((embedded_count / total) * 55)  # 40-95% during embedding

        await _update_job(
            job_id, "embedding",
            current_step="embedding",
            progress_pct=min(pct, 95),
            total_chunks=total,
            embedded_chunks=embedded_count,
            estimated_seconds=round(est_seconds, 1),
        )

    # Batch upsert to vector store
    vs.upsert_batch(collection=settings.qdrant_kb_collection, points=all_points)
    return len(all_points)


async def _run_ingest(job_id: str, extract_fn, source_name: str, **extract_kwargs):
    """Generic ingest flow: extract → chunk → embed with granular status updates."""
    try:
        # Step 1: Extracting
        await _update_job(job_id, "extracting", current_step="extracting", progress_pct=5)
        text = await extract_fn(**extract_kwargs) if asyncio_iscoroutinefunction(extract_fn) else extract_fn(**extract_kwargs)

        # Step 2: Chunking
        await _update_job(job_id, "chunking", current_step="chunking", progress_pct=25)
        chunks = chunk_text(text, source_type=extract_kwargs.get("source_type", "file"), source_name=source_name)

        if not chunks:
            await _update_job(job_id, "done", chunks=0, current_step="done", progress_pct=100)
            return

        est_seconds = (len(chunks) * _AVG_MS_PER_CHUNK) / 1000
        await _update_job(
            job_id, "embedding",
            current_step="embedding",
            progress_pct=40,
            total_chunks=len(chunks),
            estimated_seconds=round(est_seconds, 1),
        )

        # Step 3: Embedding + storing
        count = await _embed_and_store(chunks, job_id)

        # Step 4: Done
        await _update_job(job_id, "done", chunks=count, current_step="done", progress_pct=100, total_chunks=count, embedded_chunks=count)
    except Exception as e:
        log.exception("Ingestion failed for job %s", job_id)
        await _update_job(job_id, "error", error=str(e), current_step="error")


def asyncio_iscoroutinefunction(fn):
    """Check if fn is an async function."""
    import asyncio
    return asyncio.iscoroutinefunction(fn)


async def ingest_file_bytes(job_id: str, file_bytes: bytes, filename: str):
    """Background task: extract → chunk → embed a file."""
    from zeta_ima.ingest.extractors.file import extract_text

    async def _extract(**kw):
        return extract_text(file_bytes, filename)

    await _run_ingest(job_id, _extract, source_name=filename, source_type="file")


async def ingest_url(job_id: str, url: str):
    """Background task: scrape URL → chunk → embed."""
    from zeta_ima.ingest.extractors.url import extract_url
    await _run_ingest(job_id, extract_url, source_name=url, url=url, source_type="url")


async def ingest_confluence_page(job_id: str, page_id: str):
    """Background task: pull Confluence page → chunk → embed."""
    from zeta_ima.ingest.extractors.confluence import extract_page

    async def _extract(**kw):
        title, text = await extract_page(page_id)
        return text

    await _run_ingest(job_id, _extract, source_name=page_id, source_type="confluence")


async def ingest_teams_chat(job_id: str, json_bytes: bytes, export_name: str):
    """Background task: parse Teams chat export → chunk → embed."""
    from zeta_ima.ingest.extractors.teams_chat import extract_teams_chat

    async def _extract(**kw):
        return extract_teams_chat(json_bytes)

    await _run_ingest(job_id, _extract, source_name=export_name, source_type="teams_chat")


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
                current_step="pending",
                progress_pct=0,
                chunks_created=0,
                total_chunks=0,
                embedded_chunks=0,
                estimated_seconds_remaining=0,
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
