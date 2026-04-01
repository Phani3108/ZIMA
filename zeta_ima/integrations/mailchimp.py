"""
Mailchimp integration — email campaign management.
Uses Mailchimp Marketing API v3.
"""

import httpx

from zeta_ima.integrations.vault import vault


async def _creds() -> tuple[str, str]:
    """Return (api_key, server_prefix) or empty strings."""
    keys = await vault.get_all("mailchimp")
    return keys.get("api_key", ""), keys.get("server_prefix", "")


def _base_url(server: str) -> str:
    return f"https://{server}.api.mailchimp.com/3.0"


async def _request(method: str, path: str, json: dict | None = None) -> dict:
    key, server = await _creds()
    if not key or not server:
        return {"ok": False, "error": "Mailchimp not configured — add API key and server prefix in Settings."}

    async with httpx.AsyncClient(
        auth=("anystring", key),
        timeout=30,
    ) as client:
        r = await client.request(method, f"{_base_url(server)}{path}", json=json)

    if not r.is_success:
        return {"ok": False, "error": f"Mailchimp API error {r.status_code}: {r.text[:300]}"}

    return {"ok": True, "data": r.json()}


async def ping() -> dict:
    """Test API key validity."""
    return await _request("GET", "/ping")


async def list_audiences(limit: int = 10) -> dict:
    """List audiences (lists)."""
    result = await _request("GET", f"/lists?count={limit}")
    if not result["ok"]:
        return result
    lists = result["data"].get("lists", [])
    return {
        "ok": True,
        "audiences": [
            {
                "id": l["id"],
                "name": l["name"],
                "member_count": l["stats"]["member_count"],
            }
            for l in lists
        ],
    }


async def create_campaign(
    list_id: str,
    subject: str,
    from_name: str,
    from_email: str = "",
    html_content: str = "",
    preview_text: str = "",
) -> dict:
    """
    Create a regular email campaign.

    Returns:
        {"ok": bool, "campaign_id": str, "web_id": int, "archive_url": str}
    """
    # Step 1: Create campaign
    result = await _request("POST", "/campaigns", json={
        "type": "regular",
        "recipients": {"list_id": list_id},
        "settings": {
            "subject_line": subject,
            "from_name": from_name,
            **({"reply_to": from_email} if from_email else {}),
            **({"preview_text": preview_text} if preview_text else {}),
        },
    })

    if not result["ok"]:
        return result

    campaign = result["data"]
    campaign_id = campaign["id"]

    # Step 2: Set content
    if html_content:
        content_result = await _request(
            "PUT",
            f"/campaigns/{campaign_id}/content",
            json={"html": html_content},
        )
        if not content_result["ok"]:
            return content_result

    return {
        "ok": True,
        "campaign_id": campaign_id,
        "web_id": campaign.get("web_id"),
        "archive_url": campaign.get("archive_url", ""),
    }


async def send_campaign(campaign_id: str) -> dict:
    """Send a campaign. This is IRREVERSIBLE."""
    return await _request("POST", f"/campaigns/{campaign_id}/actions/send")


async def get_campaign_report(campaign_id: str) -> dict:
    """Get campaign performance report."""
    result = await _request("GET", f"/reports/{campaign_id}")
    if not result["ok"]:
        return result

    report = result["data"]
    return {
        "ok": True,
        "sends": report.get("emails_sent", 0),
        "opens": report.get("opens", {}).get("opens_total", 0),
        "open_rate": report.get("opens", {}).get("open_rate", 0),
        "clicks": report.get("clicks", {}).get("clicks_total", 0),
        "click_rate": report.get("clicks", {}).get("click_rate", 0),
        "unsubscribes": report.get("unsubscribed", 0),
    }
