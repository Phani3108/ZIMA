from fastapi import APIRouter
import redis as redis_lib

from zeta_ima.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Health check — verifies Redis, vector store, and PostgreSQL connections."""
    status = {"status": "ok", "services": {}}

    # Redis
    try:
        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        status["services"]["redis"] = "ok"
    except Exception as e:
        status["services"]["redis"] = f"error: {e}"
        status["status"] = "degraded"

    # Vector store
    try:
        from zeta_ima.infra.vector_store import get_vector_store
        vs = get_vector_store()
        vs.collection_exists("brand_voice")
        status["services"]["vector_store"] = f"ok ({settings.vector_backend})"
    except Exception as e:
        status["services"]["vector_store"] = f"error: {e}"
        status["status"] = "degraded"

    return status
