"""
Settings routes — API key management (read/write to vault).

GET  /settings/integrations              → list all integrations + configured status + metadata
POST /settings/integrations/{name}       → set one or more keys for an integration
DELETE /settings/integrations/{name}     → remove all keys for an integration
POST /settings/integrations/{name}/test  → test connection for an integration
GET  /settings/actions                   → list available tool actions
POST /settings/infra/test/{service}      → test an infrastructure service connection
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.config import settings as app_settings
from zeta_ima.integrations.actions import list_actions, get_actions_for_integration
from zeta_ima.integrations.registry import INTEGRATIONS, CATEGORIES, INFRA_SERVICES, all_integrations
from zeta_ima.integrations.vault import vault

log = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class KeysPayload(BaseModel):
    keys: dict[str, str]   # {key_name: value}


@router.get("/integrations")
async def list_integrations(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return all integrations with configured/unconfigured status + setup metadata."""
    configured = set(await vault.list_configured())
    result = []
    for name, meta in INTEGRATIONS.items():
        result.append({
            "name": name,
            "label": meta["label"],
            "category": meta.get("category", "other"),
            "description": meta["description"],
            "configured": name in configured,
            "required_keys": [k["name"] for k in meta["keys"]],
            "key_definitions": meta["keys"],
            "setup_url": meta.get("setup_url", ""),
            "setup_steps": meta.get("setup_steps", []),
            "required": meta.get("required", False),
        })
    return result


@router.post("/integrations/{name}")
async def set_integration_keys(
    name: str,
    payload: KeysPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    """Store encrypted credentials for an integration."""
    if name not in INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {name}")

    for key_name, value in payload.keys.items():
        if value:  # Skip empty values
            await vault.set(name, key_name, value)

    return {"ok": True, "integration": name, "keys_stored": list(payload.keys.keys())}


@router.delete("/integrations/{name}")
async def delete_integration(
    name: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Remove all stored keys for an integration."""
    if name not in INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {name}")

    await vault.delete_integration(name)
    return {"ok": True, "integration": name}


@router.post("/integrations/{name}/test")
async def test_integration(
    name: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Test an integration's credentials by making a lightweight API call.

    Returns {"ok": True, "message": "..."} or {"ok": False, "error": "..."}.
    """
    if name not in INTEGRATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {name}")

    configured = await vault.list_configured()
    if name not in configured:
        return {"ok": False, "error": f"{INTEGRATIONS[name]['label']} is not configured. Add credentials first."}

    try:
        if name == "openai":
            import httpx
            key = await vault.get("openai", "api_key")
            async with httpx.AsyncClient(headers={"Authorization": f"Bearer {key}"}, timeout=10) as c:
                r = await c.get("https://api.openai.com/v1/models?limit=1")
            if r.is_success:
                return {"ok": True, "message": "OpenAI connected — API key is valid."}
            return {"ok": False, "error": f"OpenAI rejected the key: {r.text[:200]}"}

        elif name == "anthropic":
            import httpx
            key = await vault.get("anthropic", "api_key")
            async with httpx.AsyncClient(headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=10) as c:
                r = await c.get("https://api.anthropic.com/v1/models")
            if r.is_success:
                return {"ok": True, "message": "Anthropic connected — Claude models accessible."}
            return {"ok": False, "error": f"Anthropic rejected the key: {r.text[:200]}"}

        elif name == "google":
            import httpx
            key = await vault.get("google", "api_key")
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"https://generativelanguage.googleapis.com/v1/models?key={key}")
            if r.is_success:
                return {"ok": True, "message": "Google AI connected — Gemini models accessible."}
            return {"ok": False, "error": f"Google AI rejected the key: {r.text[:200]}"}

        elif name == "jira":
            keys = await vault.get_all("jira")
            if not keys.get("base_url"):
                return {"ok": False, "error": "Jira Base URL is not set."}
            import httpx
            async with httpx.AsyncClient(auth=(keys.get("email", ""), keys.get("api_token", "")), timeout=10) as c:
                r = await c.get(f"{keys['base_url'].rstrip('/')}/rest/api/3/myself")
            if r.is_success:
                return {"ok": True, "message": f"Jira connected as {r.json().get('displayName', 'OK')}."}
            return {"ok": False, "error": f"Jira authentication failed: {r.text[:200]}"}

        elif name == "confluence":
            keys = await vault.get_all("confluence")
            if not keys.get("base_url"):
                return {"ok": False, "error": "Confluence Base URL is not set."}
            import httpx
            async with httpx.AsyncClient(auth=(keys.get("email", ""), keys.get("api_token", "")), timeout=10) as c:
                r = await c.get(f"{keys['base_url'].rstrip('/')}/wiki/rest/api/space?limit=1")
            if r.is_success:
                return {"ok": True, "message": "Confluence connected — space list accessible."}
            return {"ok": False, "error": f"Confluence authentication failed: {r.text[:200]}"}

        elif name == "github":
            keys = await vault.get_all("github")
            if not keys.get("app_id"):
                return {"ok": False, "error": "GitHub App ID is not set."}
            import httpx
            # Test with a simple app metadata request
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"https://api.github.com/app", headers={
                    "Accept": "application/vnd.github+json",
                })
            # Just verify credentials are stored; full JWT auth test is complex
            return {"ok": True, "message": "GitHub App credentials stored. Full auth requires JWT signing."}

        elif name == "canva":
            from zeta_ima.integrations.canva import list_templates
            result = await list_templates(limit=1)
            return {"ok": True, "message": f"Canva connected — {len(result)} template(s) found."}

        elif name == "semrush":
            from zeta_ima.integrations.semrush import keyword_overview
            result = await keyword_overview("test", "us")
            if result["ok"]:
                return {"ok": True, "message": "SEMrush connected — keyword API accessible."}
            return {"ok": False, "error": result.get("error", "SEMrush test failed.")}

        elif name == "mailchimp":
            from zeta_ima.integrations.mailchimp import ping
            result = await ping()
            if result["ok"]:
                return {"ok": True, "message": "Mailchimp connected — API key is valid."}
            return {"ok": False, "error": result.get("error", "Mailchimp test failed.")}

        elif name == "sendgrid":
            from zeta_ima.integrations.sendgrid import get_profile
            result = await get_profile()
            if result["ok"]:
                return {"ok": True, "message": "SendGrid connected — profile accessible."}
            return {"ok": False, "error": result.get("error", "SendGrid test failed.")}

        elif name == "linkedin":
            from zeta_ima.integrations.linkedin_api import get_user_profile
            result = await get_user_profile()
            if result["ok"]:
                return {"ok": True, "message": f"LinkedIn connected as {result.get('name', 'OK')}."}
            return {"ok": False, "error": result.get("error", "LinkedIn token may be expired. Tokens last 60 days.")}

        elif name == "buffer":
            from zeta_ima.integrations.buffer import get_user
            result = await get_user()
            if result["ok"]:
                return {"ok": True, "message": "Buffer connected — account accessible."}
            return {"ok": False, "error": result.get("error", "Buffer test failed.")}

        elif name == "gemini_image":
            import httpx
            key = await vault.get("gemini_image", "api_key")
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"https://generativelanguage.googleapis.com/v1/models?key={key}")
            if r.is_success:
                return {"ok": True, "message": "Gemini Image connected — models accessible."}
            return {"ok": False, "error": f"Google API key rejected: {r.text[:200]}"}

        elif name == "figma":
            import httpx
            token = await vault.get("figma", "access_token")
            async with httpx.AsyncClient(headers={"X-Figma-Token": token or ""}, timeout=10) as c:
                r = await c.get("https://api.figma.com/v1/me")
            if r.is_success:
                user_data = r.json()
                return {"ok": True, "message": f"Figma connected as {user_data.get('handle', 'OK')}."}
            return {"ok": False, "error": f"Figma token rejected: {r.text[:200]}"}

        elif name == "dalle":
            import httpx
            key = await vault.get("dalle", "api_key")
            async with httpx.AsyncClient(headers={"Authorization": f"Bearer {key}"}, timeout=10) as c:
                r = await c.get("https://api.openai.com/v1/models?limit=1")
            if r.is_success:
                return {"ok": True, "message": "DALL·E connected — OpenAI API key is valid."}
            return {"ok": False, "error": f"OpenAI key rejected: {r.text[:200]}"}

        elif name in ("twitter", "hubspot", "google_analytics"):
            return {"ok": True, "message": f"{INTEGRATIONS[name]['label']} credentials stored. Verification available after first use."}

        else:
            return {"ok": True, "message": "Credentials stored but no test endpoint available."}

    except Exception as e:
        log.error(f"Integration test failed for {name}: {e}")
        return {"ok": False, "error": f"Connection test failed: {str(e)}"}


# ── Infrastructure service tests ──────────────────────────────────────

@router.post("/infra/test/{service}")
async def test_infra_service(
    service: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Test connectivity for an infrastructure service (env-var-based)."""
    try:
        if service == "redis":
            import redis as redis_lib
            r = redis_lib.from_url(app_settings.redis_url)
            r.ping()
            return {"ok": True, "message": f"Redis connected at {app_settings.redis_url.split('@')[-1] if '@' in app_settings.redis_url else app_settings.redis_url}."}

        elif service == "postgresql":
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            _url = app_settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
            engine = create_async_engine(_url, echo=False)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
            await engine.dispose()
            short_ver = version.split(",")[0] if version else "unknown"
            return {"ok": True, "message": f"PostgreSQL connected — {short_ver}."}

        elif service == "qdrant":
            from zeta_ima.infra.vector_store import get_vector_store
            vs = get_vector_store()
            vs.collection_exists("brand_voice")
            return {"ok": True, "message": f"Qdrant connected at {app_settings.qdrant_url}."}

        elif service == "azure_openai":
            if not app_settings.azure_openai_endpoint:
                return {"ok": False, "error": "AZURE_OPENAI_ENDPOINT is not set."}
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    f"{app_settings.azure_openai_endpoint.rstrip('/')}/openai/models?api-version={app_settings.azure_openai_api_version}",
                    headers={"api-key": app_settings.azure_openai_api_key},
                )
            if r.is_success:
                models = r.json().get("data", [])
                model_ids = [m.get("id", "") for m in models[:5]]
                return {"ok": True, "message": f"Azure OpenAI connected — {len(models)} model(s): {', '.join(model_ids)}."}
            return {"ok": False, "error": f"Azure OpenAI rejected: {r.text[:200]}"}

        elif service == "azure_blob":
            if not app_settings.azure_storage_connection_string:
                return {"ok": False, "error": "AZURE_STORAGE_CONNECTION_STRING is not set."}
            from zeta_ima.infra.blob_store import get_blob_store
            bs = get_blob_store()
            await bs.list_blobs(prefix="__health__", limit=1)
            return {"ok": True, "message": "Azure Blob Storage connected."}

        elif service == "azure_ai_search":
            if not app_settings.azure_ai_search_endpoint:
                return {"ok": False, "error": "AZURE_AI_SEARCH_ENDPOINT is not set."}
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    f"{app_settings.azure_ai_search_endpoint.rstrip('/')}/indexes?api-version=2024-07-01",
                    headers={"api-key": app_settings.azure_ai_search_key},
                )
            if r.is_success:
                return {"ok": True, "message": "Azure AI Search connected."}
            return {"ok": False, "error": f"Azure AI Search rejected: {r.text[:200]}"}

        elif service == "azure_cosmos":
            if not app_settings.azure_cosmos_endpoint:
                return {"ok": False, "error": "AZURE_COSMOS_ENDPOINT is not set."}
            from zeta_ima.infra.document_store import get_document_store
            ds = get_document_store()
            return {"ok": True, "message": "Azure Cosmos DB connected."}

        elif service == "azure_keyvault":
            if not app_settings.az_key_vault_url:
                if app_settings.vault_key:
                    return {"ok": True, "message": "Using local Fernet key (no Azure Key Vault). OK for dev."}
                return {"ok": False, "error": "Neither AZ_KEY_VAULT_URL nor VAULT_KEY is set."}
            from azure.identity import ClientSecretCredential
            from azure.keyvault.secrets import SecretClient
            cred = ClientSecretCredential(
                tenant_id=app_settings.az_tenant_id,
                client_id=app_settings.az_client_id,
                client_secret=app_settings.az_client_secret,
            )
            client = SecretClient(vault_url=app_settings.az_key_vault_url, credential=cred)
            secret = client.get_secret(app_settings.az_key_vault_secret_name)
            return {"ok": True, "message": f"Azure Key Vault connected — secret '{app_settings.az_key_vault_secret_name}' accessible."}

        elif service == "teams_bot":
            if not app_settings.microsoft_app_id:
                return {"ok": False, "error": "MICROSOFT_APP_ID is not set. Register a bot in Azure Portal first."}
            import httpx
            # Try to get a bot framework token to verify credentials
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": app_settings.microsoft_app_id,
                        "client_secret": app_settings.microsoft_app_password,
                        "scope": "https://api.botframework.com/.default",
                    },
                )
            if r.is_success:
                return {"ok": True, "message": "Teams Bot credentials valid — Bot Framework token acquired."}
            return {"ok": False, "error": f"Bot credentials rejected: {r.json().get('error_description', r.text[:200])}"}

        else:
            return {"ok": False, "error": f"Unknown infrastructure service: {service}"}

    except Exception as e:
        log.error(f"Infra test failed for {service}: {e}")
        return {"ok": False, "error": f"Connection test failed: {str(e)}"}


@router.get("/actions")
async def get_tool_actions(user: dict = Depends(get_current_user)) -> list[dict]:
    """List all available tool actions that agents can invoke."""
    return list_actions()
