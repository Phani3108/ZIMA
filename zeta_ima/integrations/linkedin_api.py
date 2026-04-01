"""
LinkedIn integration — post content via LinkedIn Community Management API.
Credentials loaded from vault.
"""

import httpx

from zeta_ima.integrations.vault import vault

LINKEDIN_API = "https://api.linkedin.com"


async def _creds() -> dict[str, str]:
    return await vault.get_all("linkedin")


async def get_user_profile() -> dict:
    """Get the authenticated user's profile (test connection)."""
    creds = await _creds()
    token = creds.get("access_token", "")
    if not token:
        return {"ok": False, "error": "LinkedIn not configured — add access token in Settings."}

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401",
        },
        timeout=15,
    ) as client:
        r = await client.get(f"{LINKEDIN_API}/v2/userinfo")

    if not r.is_success:
        return {"ok": False, "error": f"LinkedIn API error {r.status_code}: {r.text[:300]}"}

    data = r.json()
    return {"ok": True, "name": data.get("name", ""), "sub": data.get("sub", "")}


async def create_post(
    text: str,
    org_id: str | None = None,
    visibility: str = "PUBLIC",
) -> dict:
    """
    Create a text post on LinkedIn.

    Args:
        text: Post content (up to 3000 chars)
        org_id: Organization URN (e.g. "urn:li:organization:12345"). If None, posts as user.
        visibility: "PUBLIC" | "CONNECTIONS"

    Returns:
        {"ok": bool, "post_urn": str, "url": str}
    """
    creds = await _creds()
    token = creds.get("access_token", "")
    if not token:
        return {"ok": False, "error": "LinkedIn not configured — add access token in Settings."}

    # Determine author
    author = org_id or creds.get("org_id", "")
    if not author:
        # Need to get user URN
        profile = await get_user_profile()
        if not profile["ok"]:
            return profile
        author = f"urn:li:person:{profile['sub']}"

    if not author.startswith("urn:"):
        author = f"urn:li:organization:{author}"

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401",
        },
        timeout=30,
    ) as client:
        r = await client.post(
            f"{LINKEDIN_API}/rest/posts",
            json={
                "author": author,
                "commentary": text,
                "visibility": visibility,
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )

    if not r.is_success:
        return {"ok": False, "error": f"LinkedIn API error {r.status_code}: {r.text[:300]}"}

    # The post URN is in the x-restli-id header
    post_urn = r.headers.get("x-restli-id", "")
    return {
        "ok": True,
        "post_urn": post_urn,
        "url": f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else "",
    }


async def create_image_post(
    text: str,
    image_url: str,
    org_id: str | None = None,
) -> dict:
    """
    Create a post with an image on LinkedIn.

    This is a multi-step process:
    1. Initialize image upload
    2. Upload the image binary
    3. Create the post referencing the image

    Returns:
        {"ok": bool, "post_urn": str, "url": str}
    """
    creds = await _creds()
    token = creds.get("access_token", "")
    if not token:
        return {"ok": False, "error": "LinkedIn not configured."}

    author = org_id or creds.get("org_id", "")
    if not author:
        profile = await get_user_profile()
        if not profile["ok"]:
            return profile
        author = f"urn:li:person:{profile['sub']}"
    if not author.startswith("urn:"):
        author = f"urn:li:organization:{author}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }

    async with httpx.AsyncClient(headers=headers, timeout=60) as client:
        # Step 1: Initialize upload
        init = await client.post(
            f"{LINKEDIN_API}/rest/images?action=initializeUpload",
            json={"initializeUploadRequest": {"owner": author}},
        )
        if not init.is_success:
            return {"ok": False, "error": f"Image upload init failed: {init.text[:200]}"}

        upload_data = init.json().get("value", {})
        upload_url = upload_data.get("uploadUrl", "")
        image_urn = upload_data.get("image", "")

        # Step 2: Download and upload image
        img_resp = await client.get(image_url)
        if not img_resp.is_success:
            return {"ok": False, "error": "Failed to download source image"}

        upload_resp = await client.put(
            upload_url,
            content=img_resp.content,
            headers={"Content-Type": "application/octet-stream", "Authorization": f"Bearer {token}"},
        )
        if not upload_resp.is_success:
            return {"ok": False, "error": f"Image upload failed: {upload_resp.status_code}"}

        # Step 3: Create post with image
        r = await client.post(
            f"{LINKEDIN_API}/rest/posts",
            json={
                "author": author,
                "commentary": text,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "content": {
                    "media": {
                        "title": "Marketing Visual",
                        "id": image_urn,
                    }
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            },
        )

    if not r.is_success:
        return {"ok": False, "error": f"Post creation failed: {r.text[:300]}"}

    post_urn = r.headers.get("x-restli-id", "")
    return {
        "ok": True,
        "post_urn": post_urn,
        "url": f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else "",
    }
