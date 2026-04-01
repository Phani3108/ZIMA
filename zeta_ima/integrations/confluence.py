"""
Confluence integration — adapted from AAH/services/integrations/confluence.py.
Credentials loaded from vault.
"""

import httpx

from zeta_ima.integrations.vault import vault


async def _creds() -> tuple[str, str, str, str]:
    base_url = await vault.get("confluence", "base_url") or ""
    email = await vault.get("confluence", "email") or ""
    token = await vault.get("confluence", "api_token") or ""
    space_key = await vault.get("confluence", "space_key") or ""
    return base_url.rstrip("/"), email, token, space_key


async def publish_page(title: str, body_html: str, parent_page_id: str = None) -> dict:
    """Publish a new Confluence page. Returns {"ok": bool, "url": "..."}"""
    base_url, email, token, space_key = await _creds()
    if not all([base_url, email, token, space_key]):
        return {"ok": False, "error": "Confluence not configured — add credentials in Settings."}

    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": body_html, "representation": "storage"}},
    }
    if parent_page_id:
        payload["ancestors"] = [{"id": parent_page_id}]

    async with httpx.AsyncClient(auth=(email, token), timeout=15) as client:
        r = await client.post(f"{base_url}/wiki/rest/api/content", json=payload)

    if not r.is_success:
        return {"ok": False, "error": f"Confluence error {r.status_code}: {r.text[:200]}"}

    data = r.json()
    page_id = data.get("id", "")
    url = f"{base_url}/wiki{data.get('_links', {}).get('webui', '')}"
    return {"ok": True, "page_id": page_id, "url": url}


async def get_page(page_id: str) -> dict:
    """Fetch a Confluence page body. Returns {"ok": bool, "title": str, "body": str}"""
    base_url, email, token, _ = await _creds()
    if not all([base_url, email, token]):
        return {"ok": False, "error": "Confluence not configured."}

    async with httpx.AsyncClient(auth=(email, token), timeout=10) as client:
        r = await client.get(
            f"{base_url}/wiki/rest/api/content/{page_id}",
            params={"expand": "body.storage"},
        )

    if not r.is_success:
        return {"ok": False, "error": f"Confluence error {r.status_code}"}

    data = r.json()
    return {
        "ok": True,
        "title": data.get("title", ""),
        "body": data.get("body", {}).get("storage", {}).get("value", ""),
    }


async def search_pages(query: str, limit: int = 5) -> list[dict]:
    """Full-text search Confluence. Returns list of {title, url, space}."""
    base_url, email, token, _ = await _creds()
    if not all([base_url, email, token]):
        return []

    async with httpx.AsyncClient(auth=(email, token), timeout=10) as client:
        r = await client.get(
            f"{base_url}/wiki/rest/api/content/search",
            params={"cql": f'type=page AND text~"{query}"', "limit": limit},
        )

    if not r.is_success:
        return []

    results = r.json().get("results", [])
    return [
        {
            "title": p["title"],
            "url": f"{base_url}/wiki{p.get('_links', {}).get('webui', '')}",
            "space": p.get("space", {}).get("key", ""),
        }
        for p in results
    ]
