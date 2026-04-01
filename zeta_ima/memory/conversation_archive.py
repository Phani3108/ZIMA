"""
Conversation Archive — records full session history for recall and learning.

Each archived session stores:
  - Brief, pipeline, outcome, messages (summary)
  - Full message JSON uploaded to blob storage for long-term retention
  - Vector embedding of the brief for semantic search (finding similar past work)

Usage::

    from zeta_ima.memory.conversation_archive import (
        archive_session, get_recent_sessions, get_similar_sessions,
    )
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

ARCHIVE_CONTAINER = "conversation_archive"
ARCHIVE_VECTOR_COLLECTION = "conversation_vectors"
EMBEDDING_DIMS = 1536


async def _init_vector_collection() -> None:
    """Ensure the conversation vectors collection exists."""
    from zeta_ima.infra.vector_store import get_vector_store
    vs = get_vector_store()
    if not vs.collection_exists(ARCHIVE_VECTOR_COLLECTION):
        vs.ensure_collection(ARCHIVE_VECTOR_COLLECTION, vector_size=EMBEDDING_DIMS)


async def archive_session(
    team_id: str,
    user_id: str,
    brief: str,
    pipeline_id: str = "",
    messages: list[dict[str, Any]] | None = None,
    outcome: str = "approved",
    tags: list[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    """
    Archive a completed session.

    1. Store summary row in document store (conversation_archive table).
    2. Upload full messages JSON to blob storage.
    3. Embed the brief for semantic search.

    Returns the archive entry ID.
    """
    from zeta_ima.infra.document_store import get_document_store
    from zeta_ima.infra.blob_store import get_blob_store
    from zeta_ima.infra.vector_store import get_vector_store
    from zeta_ima.memory.brand import _embed

    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    messages = messages or []

    # 1. Upload full messages to blob
    blob_url = ""
    if messages:
        bs = get_blob_store()
        blob_path = f"conversations/{team_id}/{entry_id}.json"
        data = json.dumps(messages, default=str).encode("utf-8")
        blob_url = await bs.upload(blob_path, data)

    # 2. Store summary in document store
    ds = get_document_store()
    doc = {
        "id": entry_id,
        "team_id": team_id,
        "user_id": user_id,
        "brief": brief,
        "pipeline_id": pipeline_id,
        "messages_json": json.dumps(messages[:5]) if messages else "[]",  # First 5 messages as preview
        "outcome": outcome,
        "blob_url": blob_url,
        "tags": tags or [],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if extra_metadata:
        doc.update(extra_metadata)
    await ds.upsert(ARCHIVE_CONTAINER, doc)

    # 3. Embed brief for semantic search
    if brief.strip():
        try:
            vector = await _embed(brief[:2000])
            vs = get_vector_store()
            await _init_vector_collection()
            vs.upsert(
                collection=ARCHIVE_VECTOR_COLLECTION,
                point_id=entry_id,
                vector=vector,
                payload={
                    "team_id": team_id,
                    "user_id": user_id,
                    "brief": brief[:500],
                    "pipeline_id": pipeline_id,
                    "outcome": outcome,
                    "created_at": now.isoformat(),
                },
            )
        except Exception as e:
            log.warning("Failed to embed archived brief: %s", e)

    log.info(
        "Archived session %s for team=%s user=%s outcome=%s",
        entry_id, team_id, user_id, outcome,
    )
    return entry_id


async def get_recent_sessions(
    team_id: str,
    user_id: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Get the most recent archived sessions for a team (optionally filtered by user).
    """
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    filters: dict[str, Any] = {"team_id": team_id}
    if user_id:
        filters["user_id"] = user_id

    return await ds.query(
        ARCHIVE_CONTAINER,
        filters=filters,
        order_by="created_at DESC",
        limit=limit,
    )


async def get_similar_sessions(
    team_id: str,
    brief: str,
    limit: int = 3,
    min_score: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Find past sessions with similar briefs using semantic search.

    Returns list of dicts: {id, brief, pipeline_id, outcome, score, created_at}.
    """
    if not brief.strip():
        return []

    from zeta_ima.memory.brand import _embed
    from zeta_ima.infra.vector_store import get_vector_store

    try:
        vector = await _embed(brief[:2000])
        vs = get_vector_store()
        results = vs.search(
            collection=ARCHIVE_VECTOR_COLLECTION,
            query_vector=vector,
            top_k=limit * 2,  # over-fetch to allow post-filter
            filters={"team_id": team_id},
            score_threshold=min_score,
        )
        return [
            {
                "id": r["id"],
                "brief": r["payload"].get("brief", ""),
                "pipeline_id": r["payload"].get("pipeline_id", ""),
                "outcome": r["payload"].get("outcome", ""),
                "score": r["score"],
                "created_at": r["payload"].get("created_at", ""),
            }
            for r in results[:limit]
        ]
    except Exception as e:
        log.warning("Similar session search failed: %s", e)
        return []


async def get_session_detail(session_id: str, team_id: str = "") -> dict[str, Any] | None:
    """
    Fetch full session details including messages from blob storage.
    """
    from zeta_ima.infra.document_store import get_document_store
    from zeta_ima.infra.blob_store import get_blob_store

    ds = get_document_store()
    doc = await ds.get(ARCHIVE_CONTAINER, session_id, partition_key=team_id)
    if not doc:
        return None

    # If blob_url exists, fetch full messages
    blob_url = doc.get("blob_url", "")
    if blob_url:
        bs = get_blob_store()
        blob_path = f"conversations/{doc.get('team_id', '')}/{session_id}.json"
        data = await bs.download(blob_path)
        if data:
            try:
                doc["full_messages"] = json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                doc["full_messages"] = []

    return doc
