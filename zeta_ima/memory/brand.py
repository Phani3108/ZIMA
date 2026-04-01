"""
Qdrant-backed brand voice memory.

Two operations:
  - search_brand_examples(brief) → top-K approved outputs similar to this brief
  - save_approved_output(text, metadata) → called after human clicks Approve

The embedding model is text-embedding-3-small (1536 dims). Cheap and fast.
Each Qdrant point payload stores: text, user_id, campaign_id, brief, channel, approved_at.
"""

import uuid
from typing import List

from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from zeta_ima.config import settings

_qdrant = QdrantClient(url=settings.qdrant_url)
_openai = AsyncOpenAI(api_key=settings.openai_api_key)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536


def ensure_collection() -> None:
    """Create the Qdrant collection if it doesn't exist. Call once at startup."""
    existing = {c.name for c in _qdrant.get_collections().collections}
    if settings.qdrant_collection not in existing:
        _qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=EMBEDDING_DIMS, distance=Distance.COSINE),
        )


async def _embed(text: str) -> List[float]:
    resp = await _openai.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


async def search_brand_examples(brief: str, top_k: int | None = None) -> List[str]:
    """
    Pull the top-K semantically similar approved outputs from Qdrant.
    These are injected as brand context into the copy agent prompt.
    Returns empty list if the collection has no points yet (cold start).
    """
    k = top_k or settings.brand_context_top_k
    vector = await _embed(brief)
    results = _qdrant.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        limit=k,
    )
    return [r.payload["text"] for r in results]


async def save_approved_output(text: str, metadata: dict) -> str:
    """
    Save an approved copy output to Qdrant for future brand context retrieval.

    metadata should include: user_id, campaign_id, brief, channel, iterations_needed.
    Returns the Qdrant point ID.
    """
    output_id = metadata.get("output_id") or str(uuid.uuid4())
    vector = await _embed(text)
    _qdrant.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=output_id,
                vector=vector,
                payload={"text": text, **metadata},
            )
        ],
    )
    return output_id
