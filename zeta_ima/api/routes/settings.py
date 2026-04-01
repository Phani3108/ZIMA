"""
Settings routes — API key management (read/write to vault).

GET  /settings/integrations              → list all integrations + configured status
POST /settings/integrations/{name}       → set one or more keys for an integration
DELETE /settings/integrations/{name}     → remove all keys for an integration
POST /settings/integrations/{name}/test  → test connection for an integration
GET  /settings/actions                   → list available tool actions
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.integrations.actions import list_actions, get_actions_for_integration
from zeta_ima.integrations.registry import INTEGRATIONS, all_integrations
from zeta_ima.integrations.vault import vault

log = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class KeysPayload(BaseModel):
    keys: dict[str, str]   # {key_name: value}


@router.get("/integrations")
async def list_integrations(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return all integrations with configured/unconfigured status."""
    configured = set(await vault.list_configured())
    result = []
    for name, meta in INTEGRATIONS.items():
        result.append({
            "name": name,
            "label": meta["label"],
            "description": meta["description"],
            "configured": name in configured,
            "required_keys": [k["name"] for k in meta["keys"]],
            "key_definitions": meta["keys"],
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
        return {"ok": False, "error": f"{name} is not configured. Add credentials first."}

    try:
        if name == "openai":
            import httpx
            key = await vault.get("openai", "api_key")
            async with httpx.AsyncClient(headers={"Authorization": f"Bearer {key}"}, timeout=10) as c:
                r = await c.get("https://api.openai.com/v1/models?limit=1")
            return {"ok": r.is_success, "message": "OpenAI connected" if r.is_success else r.text[:200]}

        elif name == "anthropic":
            import httpx
            key = await vault.get("anthropic", "api_key")
            async with httpx.AsyncClient(headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=10) as c:
                r = await c.get("https://api.anthropic.com/v1/models")
            return {"ok": r.is_success, "message": "Anthropic connected" if r.is_success else r.text[:200]}

        elif name == "google":
            import httpx
            key = await vault.get("google", "api_key")
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"https://generativelanguage.googleapis.com/v1/models?key={key}")
            return {"ok": r.is_success, "message": "Google AI connected" if r.is_success else r.text[:200]}

        elif name == "jira":
            keys = await vault.get_all("jira")
            import httpx
            async with httpx.AsyncClient(auth=(keys.get("email", ""), keys.get("api_token", "")), timeout=10) as c:
                r = await c.get(f"{keys.get('base_url', '').rstrip('/')}/rest/api/3/myself")
            if r.is_success:
                return {"ok": True, "message": f"Jira connected as {r.json().get('displayName', 'OK')}"}
            return {"ok": False, "error": r.text[:200]}

        elif name == "canva":
            from zeta_ima.integrations.canva import list_templates
            result = await list_templates(limit=1)
            return {"ok": True, "message": f"Canva connected ({len(result)} templates found)"}

        elif name == "semrush":
            from zeta_ima.integrations.semrush import keyword_overview
            result = await keyword_overview("test", "us")
            return {"ok": result["ok"], "message": "SEMrush connected" if result["ok"] else result.get("error", "")}

        elif name == "mailchimp":
            from zeta_ima.integrations.mailchimp import ping
            result = await ping()
            return {"ok": result["ok"], "message": "Mailchimp connected" if result["ok"] else result.get("error", "")}

        elif name == "sendgrid":
            from zeta_ima.integrations.sendgrid import get_profile
            result = await get_profile()
            return {"ok": result["ok"], "message": "SendGrid connected" if result["ok"] else result.get("error", "")}

        elif name == "linkedin":
            from zeta_ima.integrations.linkedin_api import get_user_profile
            result = await get_user_profile()
            if result["ok"]:
                return {"ok": True, "message": f"LinkedIn connected as {result.get('name', 'OK')}"}
            return {"ok": False, "error": result.get("error", "")}

        elif name == "buffer":
            from zeta_ima.integrations.buffer import get_user
            result = await get_user()
            return {"ok": result["ok"], "message": "Buffer connected" if result["ok"] else result.get("error", "")}

        elif name in ("dalle", "figma", "twitter", "hubspot", "google_analytics", "confluence", "github"):
            return {"ok": True, "message": f"{name} credentials stored. Full test requires specific API call."}

        else:
            return {"ok": True, "message": "Credentials stored but no test endpoint available."}

    except Exception as e:
        log.error(f"Integration test failed for {name}: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/actions")
async def get_tool_actions(user: dict = Depends(get_current_user)) -> list[dict]:
    """List all available tool actions that agents can invoke."""
    return list_actions()
