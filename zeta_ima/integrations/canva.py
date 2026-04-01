"""
Canva integration — Canva Connect API.
Creates designs from briefs using Canva's autofill API.
Credentials loaded from vault.
"""

import httpx

from zeta_ima.integrations.vault import vault

CANVA_API_BASE = "https://api.canva.com/rest/v1"


async def _token() -> str:
    return await vault.get("canva", "access_token") or ""


async def create_design_from_template(
    template_id: str,
    title: str,
    text_fields: dict[str, str],
) -> dict:
    """
    Create a Canva design by autofilling a template.

    Args:
        template_id: Canva template ID (e.g. "DAFXxxxxxx")
        title: Design title
        text_fields: Dict of field_name → text_value for template autofill

    Returns:
        {"ok": bool, "design_id": str, "edit_url": str, "view_url": str}
    """
    token = await _token()
    if not token:
        return {"ok": False, "error": "Canva not configured — add credentials in Settings."}

    # Build autofill data
    data_items = [
        {"type": "text", "name": name, "text": {"text": value}}
        for name, value in text_fields.items()
    ]

    payload = {
        "brand_template_id": template_id,
        "title": title,
        "data": {"type": "autofill", "data": data_items},
    }

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    ) as client:
        r = await client.post(f"{CANVA_API_BASE}/autofills", json=payload)

    if not r.is_success:
        return {"ok": False, "error": f"Canva API error {r.status_code}: {r.text[:200]}"}

    job = r.json().get("job", {})
    design_id = job.get("design", {}).get("id", "")
    edit_url = job.get("design", {}).get("urls", {}).get("edit_url", "")
    view_url = job.get("design", {}).get("urls", {}).get("view_url", "")

    return {"ok": True, "design_id": design_id, "edit_url": edit_url, "view_url": view_url}


async def list_templates(keyword: str = "", limit: int = 10) -> list[dict]:
    """Search Canva brand templates. Returns [{id, title, thumbnail_url}]"""
    token = await _token()
    if not token:
        return []

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    ) as client:
        r = await client.get(
            f"{CANVA_API_BASE}/brand-templates",
            params={"limit": limit, **({"query": keyword} if keyword else {})},
        )

    if not r.is_success:
        return []

    items = r.json().get("items", [])
    return [
        {
            "id": t["id"],
            "title": t.get("title", ""),
            "thumbnail_url": t.get("thumbnail", {}).get("url", ""),
        }
        for t in items
    ]
