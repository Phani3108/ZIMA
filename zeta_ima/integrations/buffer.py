"""
Buffer integration — social media scheduling.
Uses Buffer Publish API v1.
"""

import httpx

from zeta_ima.integrations.vault import vault

BUFFER_API = "https://api.bufferapp.com/1"


async def _token() -> str:
    return await vault.get("buffer", "access_token") or ""


async def _request(method: str, path: str, data: dict | None = None) -> dict:
    token = await _token()
    if not token:
        return {"ok": False, "error": "Buffer not configured — add access token in Settings."}

    params = {"access_token": token}

    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            r = await client.get(f"{BUFFER_API}{path}", params=params)
        else:
            r = await client.post(f"{BUFFER_API}{path}", params=params, data=data)

    if not r.is_success:
        return {"ok": False, "error": f"Buffer API error {r.status_code}: {r.text[:300]}"}

    return {"ok": True, "data": r.json()}


async def get_user() -> dict:
    """Test connection by fetching user info."""
    return await _request("GET", "/user.json")


async def list_profiles() -> dict:
    """
    List connected social profiles.

    Returns:
        {"ok": bool, "profiles": [{"id", "service", "formatted_username"}]}
    """
    result = await _request("GET", "/profiles.json")
    if not result["ok"]:
        return result

    profiles = result["data"]
    if not isinstance(profiles, list):
        profiles = []

    return {
        "ok": True,
        "profiles": [
            {
                "id": p.get("id", ""),
                "service": p.get("service", ""),
                "formatted_username": p.get("formatted_username", ""),
                "avatar": p.get("avatar_https", ""),
            }
            for p in profiles
        ],
    }


async def create_post(
    profile_ids: list[str],
    text: str,
    media_links: list[str] | None = None,
    scheduled_at: str | None = None,
    shorten: bool = True,
) -> dict:
    """
    Create a social post via Buffer.

    Args:
        profile_ids: List of Buffer profile IDs to post to
        text: Post text content
        media_links: Optional image/video URLs
        scheduled_at: ISO timestamp for scheduled post. If None, adds to queue.
        shorten: Whether Buffer should shorten links

    Returns:
        {"ok": bool, "updates": [{id, status, due_at}]}
    """
    data: dict = {
        "text": text,
        "profile_ids[]": profile_ids,
        "shorten": str(shorten).lower(),
    }

    if media_links:
        for i, link in enumerate(media_links):
            data[f"media[link]"] = link
            if i == 0:
                data["media[photo]"] = link

    if scheduled_at:
        data["scheduled_at"] = scheduled_at
    else:
        data["now"] = "false"  # Add to queue, don't post immediately

    result = await _request("POST", "/updates/create.json", data=data)
    if not result["ok"]:
        return result

    update = result["data"]
    return {
        "ok": update.get("success", False),
        "update_id": update.get("updates", [{}])[0].get("id", "") if update.get("updates") else "",
        "message": update.get("message", ""),
    }


async def get_pending_updates(profile_id: str, limit: int = 10) -> dict:
    """Get pending (queued) updates for a profile."""
    result = await _request("GET", f"/profiles/{profile_id}/updates/pending.json?count={limit}")
    if not result["ok"]:
        return result

    updates = result["data"].get("updates", [])
    return {
        "ok": True,
        "updates": [
            {
                "id": u.get("id", ""),
                "text": u.get("text", ""),
                "due_at": u.get("due_at", 0),
                "status": u.get("status", ""),
            }
            for u in updates
        ],
    }
