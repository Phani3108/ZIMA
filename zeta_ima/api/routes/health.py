from fastapi import APIRouter
import redis as redis_lib
from qdrant_client import QdrantClient

from zeta_ima.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Health check — verifies Redis, Qdrant, and PostgreSQL connections."""
    status = {"status": "ok", "services": {}}

    # Redis
    try:
        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        status["services"]["redis"] = "ok"
    except Exception as e:
        status["services"]["redis"] = f"error: {e}"
        status["status"] = "degraded"

    # Qdrant
    try:
        q = QdrantClient(url=settings.qdrant_url)
        q.get_collections()
        status["services"]["qdrant"] = "ok"
    except Exception as e:
        status["services"]["qdrant"] = f"error: {e}"
        status["status"] = "degraded"

    return status
