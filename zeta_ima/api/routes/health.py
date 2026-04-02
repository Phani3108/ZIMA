import logging
import os

from fastapi import APIRouter
import redis as redis_lib

from zeta_ima.config import settings
from zeta_ima.integrations.registry import INFRA_SERVICES

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Health check — verifies Redis, vector store, and PostgreSQL connections."""
    status = {"status": "ok", "services": {}}

    # Redis
    try:
        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        status["services"]["redis"] = {"status": "connected"}
    except Exception as e:
        status["services"]["redis"] = {"status": "error", "error": str(e)}
        status["status"] = "degraded"

    # Vector store
    try:
        from zeta_ima.infra.vector_store import get_vector_store
        vs = get_vector_store()
        vs.collection_exists("brand_voice")
        status["services"]["vector_store"] = {"status": "connected", "backend": settings.vector_backend}
    except Exception as e:
        status["services"]["vector_store"] = {"status": "error", "error": str(e)}
        status["status"] = "degraded"

    # PostgreSQL
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        _url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        status["services"]["postgresql"] = {"status": "connected"}
    except Exception as e:
        status["services"]["postgresql"] = {"status": "error", "error": str(e)}
        status["status"] = "degraded"

    # Azure Blob (if configured)
    if settings.azure_storage_connection_string:
        try:
            from zeta_ima.infra.blob_store import get_blob_store
            bs = get_blob_store()
            # Try listing (limit 1) to verify connection
            blobs = await bs.list_blobs(prefix="__health__", limit=1)
            status["services"]["azure_blob"] = {"status": "connected"}
        except Exception as e:
            status["services"]["azure_blob"] = {"status": "error", "error": str(e)}
            status["status"] = "degraded"

    # Azure AI Search (if active)
    if settings.vector_backend == "azure_ai_search":
        try:
            from zeta_ima.infra.vector_store import get_vector_store
            vs = get_vector_store()
            status["services"]["azure_ai_search"] = {"status": "connected"}
        except Exception as e:
            status["services"]["azure_ai_search"] = {"status": "error", "error": str(e)}
            status["status"] = "degraded"

    # Azure Cosmos DB (if active)
    if settings.learning_store == "cosmos":
        try:
            from zeta_ima.infra.document_store import get_document_store
            ds = get_document_store()
            status["services"]["azure_cosmos"] = {"status": "connected"}
        except Exception as e:
            status["services"]["azure_cosmos"] = {"status": "error", "error": str(e)}
            status["status"] = "degraded"

    return status


@router.get("/health/system")
async def system_status() -> dict:
    """
    Full system status for the setup/integrations dashboard.

    Returns infrastructure service configs (which env vars are set/missing),
    and integration credentials status (configured/unconfigured + test results).
    """
    # Infrastructure: check which env vars are set
    infra = {}
    for svc_id, svc in INFRA_SERVICES.items():
        env_status = {}
        all_set = True
        for var in svc["env_vars"]:
            # Check both uppercase and the pydantic field name (lowercase)
            val = os.environ.get(var, "") or getattr(settings, var.lower(), "")
            is_set = bool(val)
            if not is_set:
                all_set = False
            env_status[var] = is_set
        infra[svc_id] = {
            **svc,
            "env_status": env_status,
            "configured": all_set,
        }

    # Integration credentials
    from zeta_ima.integrations.vault import vault
    from zeta_ima.integrations.registry import INTEGRATIONS, CATEGORIES
    configured_set = set(await vault.list_configured())

    integrations = {}
    for name, meta in INTEGRATIONS.items():
        integrations[name] = {
            **meta,
            "configured": name in configured_set,
        }

    return {
        "infra": infra,
        "integrations": integrations,
        "categories": CATEGORIES,
    }
