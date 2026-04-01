"""
DALL·E integration — image generation via OpenAI Images API.
Reuses the OpenAI API key from vault.
"""

import httpx

from zeta_ima.integrations.vault import vault


async def _token() -> str:
    # DALL-E uses OpenAI API key; check dalle first, fall back to openai
    key = await vault.get("dalle", "api_key")
    if not key:
        key = await vault.get("openai", "api_key")
    return key or ""


async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    style: str = "vivid",
    model: str = "dall-e-3",
) -> dict:
    """
    Generate an image with DALL-E 3.

    Args:
        prompt: Image description
        size: "1024x1024" | "1792x1024" | "1024x1792"
        quality: "standard" | "hd"
        style: "vivid" | "natural"

    Returns:
        {"ok": bool, "url": str, "revised_prompt": str}
    """
    token = await _token()
    if not token:
        return {"ok": False, "error": "OpenAI/DALL-E not configured — add API key in Settings."}

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=120,
    ) as client:
        r = await client.post(
            "https://api.openai.com/v1/images/generations",
            json={
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": quality,
                "style": style,
                "response_format": "url",
            },
        )

    if not r.is_success:
        return {"ok": False, "error": f"DALL-E API error {r.status_code}: {r.text[:300]}"}

    data = r.json().get("data", [{}])[0]
    return {
        "ok": True,
        "url": data.get("url", ""),
        "revised_prompt": data.get("revised_prompt", prompt),
    }


async def generate_variations(
    image_url: str,
    n: int = 2,
    size: str = "1024x1024",
) -> dict:
    """
    Generate variations of an existing image (DALL-E 2 only).

    Returns:
        {"ok": bool, "urls": [str, ...]}
    """
    token = await _token()
    if not token:
        return {"ok": False, "error": "OpenAI/DALL-E not configured."}

    # Download the image first
    async with httpx.AsyncClient(timeout=30) as client:
        img_resp = await client.get(image_url)
        if not img_resp.is_success:
            return {"ok": False, "error": "Failed to download source image"}

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    ) as client:
        r = await client.post(
            "https://api.openai.com/v1/images/variations",
            files={"image": ("image.png", img_resp.content, "image/png")},
            data={"n": str(n), "size": size, "model": "dall-e-2"},
        )

    if not r.is_success:
        return {"ok": False, "error": f"DALL-E API error {r.status_code}: {r.text[:300]}"}

    urls = [d.get("url", "") for d in r.json().get("data", [])]
    return {"ok": True, "urls": urls}
