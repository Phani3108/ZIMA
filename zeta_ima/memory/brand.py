"""
Brand voice memory — backed by the vector store abstraction.

Two operations:
  - search_brand_examples(brief) → top-K approved outputs similar to this brief
  - save_approved_output(text, metadata) → called after human clicks Approve

The embedding model is text-embedding-3-small (1536 dims). Cheap and fast.
Each vector point payload stores: text, user_id, campaign_id, brief, channel, approved_at.
"""

import uuid
from typing import List

from openai import AsyncOpenAI

from zeta_ima.config import settings, get_embedding_client
from zeta_ima.infra.vector_store import get_vector_store

# Lazy-loaded embedding client to respect Azure vs vanilla toggle at runtime
_openai: AsyncOpenAI | None = None

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536


def _get_openai():
    global _openai
    if _openai is None:
        _openai = get_embedding_client()
    return _openai


def ensure_collection() -> None:
    """Create the brand_voice collection/index if it doesn't exist. Call once at startup."""
    vs = get_vector_store()
    vs.ensure_collection(settings.qdrant_collection, vector_size=EMBEDDING_DIMS)


async def _embed(text: str) -> List[float]:
    resp = await _get_openai().embeddings.create(model=settings.embedding_model, input=text)
    return resp.data[0].embedding


async def search_brand_examples(brief: str, top_k: int | None = None) -> List[str]:
    """
    Pull the top-K semantically similar approved outputs from vector store.
    These are injected as brand context into the copy agent prompt.
    Returns empty list if the collection has no points yet (cold start).
    """
    k = top_k or settings.brand_context_top_k
    vector = await _embed(brief)
    vs = get_vector_store()
    results = vs.search(
        collection=settings.qdrant_collection,
        query_vector=vector,
        top_k=k,
    )
    return [r["payload"]["text"] for r in results if "text" in r.get("payload", {})]


async def save_approved_output(text: str, metadata: dict) -> str:
    """
    Save an approved copy output to vector store for future brand context retrieval.

    metadata should include: user_id, campaign_id, brief, channel, iterations_needed.
    Returns the point ID.
    """
    output_id = metadata.get("output_id") or str(uuid.uuid4())
    vector = await _embed(text)
    vs = get_vector_store()
    vs.upsert(
        collection=settings.qdrant_collection,
        point_id=output_id,
        vector=vector,
        payload={"text": text, **metadata},
    )
    return output_id
