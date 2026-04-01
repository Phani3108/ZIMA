"""
Redis-backed LangGraph checkpointer for session state.

Teams conversation ID is used as the LangGraph thread_id — it's already unique
per DM / channel thread, so no separate session ID generation is needed.

Session state (AgentState) survives server restarts and lives for SESSION_TTL_HOURS
(default 48h). Users can pick up exactly where they left off.

Also provides shared database helpers used by Genesis v2 modules (brain, executor):
  _pg_pool()       → asyncpg connection pool (for raw SQL—used by brain, executor)
  _get_qdrant()    → shared Qdrant client singleton
  _get_embedding() → async OpenAI embedding function
"""

import asyncpg
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from langgraph.checkpoint.redis import RedisSaver

from zeta_ima.config import settings

# ── LangGraph checkpointer ───────────────────────────────────────────────────

def get_checkpointer() -> RedisSaver:
    """Returns the Redis-backed LangGraph checkpointer."""
    return RedisSaver(
        redis_url=settings.redis_url,
        ttl={"default_ttl": settings.session_ttl_hours * 60},  # TTL in minutes
    )


def make_thread_config(teams_conversation_id: str) -> dict:
    """
    Maps a Teams conversation ID to a LangGraph thread config dict.

    Usage:
        config = make_thread_config(turn_context.activity.conversation.id)
        result = await graph.ainvoke(state, config=config)
    """
    return {"configurable": {"thread_id": teams_conversation_id}}


# ── Shared DB helpers (Genesis v2) ────────────────────────────────────────────

_pool: asyncpg.Pool | None = None
_qdrant_client: QdrantClient | None = None
_openai_client: AsyncOpenAI | None = None

EMBEDDING_MODEL = "text-embedding-3-small"


async def _pg_pool() -> asyncpg.Pool:
    """Lazy-init asyncpg connection pool. Shared across brain, executor, etc."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=2, max_size=10)
    return _pool


def _get_qdrant() -> QdrantClient:
    """Shared Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=settings.qdrant_url)
    return _qdrant_client


async def _get_embedding(text: str) -> list[float]:
    """Generate an embedding vector using OpenAI text-embedding-3-small."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await _openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text[:8000],  # Truncate to avoid token limit
    )
    return resp.data[0].embedding
