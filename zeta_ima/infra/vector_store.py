"""
Vector Store Abstraction — unified interface over Qdrant and Azure AI Search.

Toggle via ``settings.vector_backend`` ("qdrant" | "azure_ai_search").

Usage::

    from zeta_ima.infra.vector_store import get_vector_store
    vs = get_vector_store()
    await vs.upsert("brand_voice", point_id, vector, payload)
    results = await vs.search("brand_voice", query_vector, top_k=5)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

# ── Public factory ────────────────────────────────────────────────────────────

_instance: "VectorStore | None" = None


def get_vector_store() -> "VectorStore":
    """Return the configured vector store singleton."""
    global _instance
    if _instance is None:
        backend = settings.vector_backend
        if backend == "azure_ai_search":
            _instance = AzureAISearchBackend()
        else:
            _instance = QdrantBackend()
        log.info("Vector store backend: %s", backend)
    return _instance


# ── Interface ─────────────────────────────────────────────────────────────────


class VectorStore(ABC):
    """Minimal vector-store contract used by brand, brain, learning modules."""

    @abstractmethod
    def ensure_collection(
        self,
        name: str,
        vector_size: int = 1536,
    ) -> None:
        """Create collection/index if it doesn't exist (idempotent)."""

    @abstractmethod
    def upsert(
        self,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Insert or update a single vector point."""

    @abstractmethod
    def upsert_batch(
        self,
        collection: str,
        points: list[dict],
    ) -> None:
        """Batch upsert. Each item: {"id": str, "vector": [...], "payload": {...}}."""

    @abstractmethod
    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """
        Semantic search. Returns list of dicts with keys:
        ``id``, ``score``, ``payload``.

        ``filters``: {"field_name": value} — exact match per field.
        """

    @abstractmethod
    def set_payload(
        self,
        collection: str,
        point_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Update payload fields on an existing point."""

    @abstractmethod
    def delete_points(
        self,
        collection: str,
        point_ids: list[str],
    ) -> None:
        """Delete points by ID."""

    @abstractmethod
    def collection_exists(self, name: str) -> bool:
        """Check if a collection/index already exists."""


# ── Qdrant Backend ────────────────────────────────────────────────────────────


class QdrantBackend(VectorStore):
    """Qdrant-backed implementation (local dev default)."""

    def __init__(self) -> None:
        from qdrant_client import QdrantClient
        self._client = QdrantClient(url=settings.qdrant_url)

    # -- helpers ---------------------------------------------------------------

    def _qdrant_filter(self, filters: dict[str, Any] | None):
        """Convert simple {field: value} dict to Qdrant Filter."""
        if not filters:
            return None
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        return Filter(
            must=[
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
        )

    # -- interface impl --------------------------------------------------------

    def ensure_collection(self, name: str, vector_size: int = 1536) -> None:
        from qdrant_client.models import VectorParams, Distance
        existing = {c.name for c in self._client.get_collections().collections}
        if name not in existing:
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            log.info("Created Qdrant collection: %s", name)

    def upsert(
        self,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        from qdrant_client.models import PointStruct
        self._client.upsert(
            collection_name=collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def upsert_batch(self, collection: str, points: list[dict]) -> None:
        from qdrant_client.models import PointStruct
        structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in points
        ]
        self._client.upsert(collection_name=collection, points=structs)

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        kwargs: dict[str, Any] = {
            "collection_name": collection,
            "query_vector": query_vector,
            "limit": top_k,
            "with_payload": True,
        }
        qf = self._qdrant_filter(filters)
        if qf:
            kwargs["query_filter"] = qf
        if score_threshold > 0:
            kwargs["score_threshold"] = score_threshold

        hits = self._client.search(**kwargs)
        return [
            {"id": str(h.id), "score": round(h.score, 4), "payload": h.payload or {}}
            for h in hits
        ]

    def set_payload(
        self,
        collection: str,
        point_id: str,
        payload: dict[str, Any],
    ) -> None:
        self._client.set_payload(
            collection_name=collection,
            payload=payload,
            points=[point_id],
        )

    def delete_points(self, collection: str, point_ids: list[str]) -> None:
        from qdrant_client.models import PointIdsList
        self._client.delete(
            collection_name=collection,
            points_selector=PointIdsList(points=point_ids),
        )

    def collection_exists(self, name: str) -> bool:
        existing = {c.name for c in self._client.get_collections().collections}
        return name in existing


# ── Azure AI Search Backend ───────────────────────────────────────────────────


class AzureAISearchBackend(VectorStore):
    """
    Azure AI Search-backed implementation.

    Each Qdrant "collection" maps to an Azure AI Search index named
    ``{settings.azure_ai_search_index_prefix}-{collection}``.
    """

    def __init__(self) -> None:
        from azure.search.documents.indexes import SearchIndexClient
        from azure.core.credentials import AzureKeyCredential

        self._endpoint = settings.azure_ai_search_endpoint
        self._credential = AzureKeyCredential(settings.azure_ai_search_key)
        self._prefix = settings.azure_ai_search_index_prefix
        self._index_client = SearchIndexClient(
            endpoint=self._endpoint,
            credential=self._credential,
        )

    def _index_name(self, collection: str) -> str:
        return f"{self._prefix}-{collection}"

    def _search_client(self, collection: str):
        from azure.search.documents import SearchClient
        return SearchClient(
            endpoint=self._endpoint,
            index_name=self._index_name(collection),
            credential=self._credential,
        )

    def ensure_collection(self, name: str, vector_size: int = 1536) -> None:
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SearchField,
            SearchFieldDataType,
            SearchableField,
            SimpleField,
            VectorSearch,
            HnswAlgorithmConfiguration,
            VectorSearchProfile,
            SearchFieldDataType as DT,
        )

        index_name = self._index_name(name)
        try:
            self._index_client.get_index(index_name)
            return  # already exists
        except Exception:
            pass

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchField(
                name="vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=vector_size,
                vector_search_profile_name="default-profile",
            ),
            SimpleField(name="payload", type=SearchFieldDataType.String, filterable=False),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="default-profile",
                    algorithm_configuration_name="default-hnsw",
                )
            ],
        )

        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
        )
        self._index_client.create_index(index)
        log.info("Created Azure AI Search index: %s", index_name)

    def upsert(
        self,
        collection: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        import json
        client = self._search_client(collection)
        doc = {
            "id": point_id,
            "vector": vector,
            "payload": json.dumps(payload),
        }
        client.upload_documents(documents=[doc])

    def upsert_batch(self, collection: str, points: list[dict]) -> None:
        import json
        client = self._search_client(collection)
        docs = [
            {"id": p["id"], "vector": p["vector"], "payload": json.dumps(p["payload"])}
            for p in points
        ]
        # Azure AI Search batch limit is 1000 docs
        for i in range(0, len(docs), 1000):
            client.upload_documents(documents=docs[i:i + 1000])

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        import json
        from azure.search.documents.models import VectorizedQuery

        client = self._search_client(collection)
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="vector",
        )

        # Build OData filter for exact-match fields
        filter_str = None
        if filters:
            # Payload is stored as JSON string; for filtered search we'd need
            # separate indexed fields.  For now, post-filter in Python.
            pass

        results = client.search(
            search_text=None,
            vector_queries=[vector_query],
            top=top_k,
            filter=filter_str,
        )

        out: list[dict] = []
        for r in results:
            score = r.get("@search.score", 0.0)
            if score < score_threshold:
                continue
            payload = {}
            raw = r.get("payload")
            if raw:
                try:
                    payload = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    payload = {}
            # Apply post-filter on payload fields
            if filters:
                if not all(payload.get(k) == v for k, v in filters.items()):
                    continue
            out.append({
                "id": r["id"],
                "score": round(score, 4),
                "payload": payload,
            })
        return out

    def set_payload(
        self,
        collection: str,
        point_id: str,
        payload: dict[str, Any],
    ) -> None:
        import json
        client = self._search_client(collection)
        # Fetch existing, merge, re-upload
        try:
            existing = client.get_document(key=point_id)
            old_payload = {}
            raw = existing.get("payload")
            if raw:
                try:
                    old_payload = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    pass
            merged = {**old_payload, **payload}
            doc = {
                "id": point_id,
                "vector": existing.get("vector", []),
                "payload": json.dumps(merged),
            }
            client.upload_documents(documents=[doc])
        except Exception:
            log.warning("set_payload: point %s not found in %s", point_id, collection)

    def delete_points(self, collection: str, point_ids: list[str]) -> None:
        client = self._search_client(collection)
        docs = [{"id": pid} for pid in point_ids]
        client.delete_documents(documents=docs)

    def collection_exists(self, name: str) -> bool:
        try:
            self._index_client.get_index(self._index_name(name))
            return True
        except Exception:
            return False
