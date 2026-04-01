"""
Gemini Nano Banana 2 — image generation via Google Gemini API.

Model: gemini-3.1-flash-image-preview (Nano Banana 2)
Supports: text-to-image, image editing, up to 4K resolution, 14 reference images,
          Google Search grounding, thinking mode.

Fallback to DALL-E 3 is handled in llm_router.call_image_llm().
"""

from __future__ import annotations

import base64
import io
import logging
import uuid
from pathlib import Path
from typing import Optional

from zeta_ima.config import settings
from zeta_ima.integrations.vault import vault

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.1-flash-image-preview"

# Valid aspect ratios for Nano Banana 2
VALID_ASPECT_RATIOS = {
    "1:1", "1:4", "1:8", "2:3", "3:2", "3:4",
    "4:1", "4:3", "4:5", "5:4", "8:1",
    "9:16", "16:9", "21:9",
}

# Valid resolutions
VALID_RESOLUTIONS = {"512", "1K", "2K", "4K"}


async def _get_client():
    """Lazy-init a genai Client with API key from vault."""
    try:
        from google import genai
    except ImportError:
        raise RuntimeError("google-genai package not installed — run: pip install google-genai")

    api_key = await vault.get("google", "api_key")
    if not api_key:
        raise RuntimeError("Google API key not configured — add it in Settings → Integrations.")

    return genai.Client(api_key=api_key)


async def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    resolution: str = "1K",
    thinking_level: str = "minimal",
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Generate an image with Gemini Nano Banana 2 (text-to-image).

    Args:
        prompt: Descriptive scene prompt.
        aspect_ratio: One of VALID_ASPECT_RATIOS (default "1:1").
        resolution: One of "512", "1K", "2K", "4K" (default "1K").
        thinking_level: "minimal" or "high" (default "minimal").
        model: Gemini model name (default gemini-3.1-flash-image-preview).

    Returns:
        {"ok": bool, "image_b64": str, "mime_type": str, "revised_prompt": str}
        or {"ok": False, "error": str}
    """
    from google.genai import types

    if aspect_ratio not in VALID_ASPECT_RATIOS:
        aspect_ratio = "1:1"
    if resolution not in VALID_RESOLUTIONS:
        resolution = "1K"

    try:
        client = await _get_client()

        config = types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=resolution,
            ),
            thinking_config=types.ThinkingConfig(
                thinking_level=thinking_level.capitalize(),
            ),
        )

        response = await client.aio.models.generate_content(
            model=model,
            contents=[prompt],
            config=config,
        )

        # Extract image and text from response parts
        image_b64 = ""
        mime_type = "image/png"
        revised_prompt = ""

        for part in response.parts:
            if hasattr(part, "thought") and part.thought:
                continue  # skip thinking parts
            if part.text is not None:
                revised_prompt = part.text
            elif part.inline_data is not None:
                image_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                mime_type = part.inline_data.mime_type or "image/png"

        if not image_b64:
            return {"ok": False, "error": "No image generated — model returned text only."}

        return {
            "ok": True,
            "image_b64": image_b64,
            "mime_type": mime_type,
            "revised_prompt": revised_prompt or prompt,
        }

    except Exception as e:
        log.error(f"Gemini image generation failed: {e}", exc_info=True)
        return {"ok": False, "error": f"Gemini image error: {str(e)}"}


async def edit_image(
    prompt: str,
    source_image_b64: str,
    source_mime_type: str = "image/png",
    aspect_ratio: str = "1:1",
    resolution: str = "1K",
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Edit an existing image using Nano Banana 2 (text + image → image).

    Args:
        prompt: Edit instruction (e.g., "Change the background to a sunset").
        source_image_b64: Base64-encoded source image.
        source_mime_type: MIME type of the source image.
        aspect_ratio: Output aspect ratio.
        resolution: Output resolution.

    Returns:
        {"ok": bool, "image_b64": str, "mime_type": str, "revised_prompt": str}
    """
    from google.genai import types
    from PIL import Image

    if aspect_ratio not in VALID_ASPECT_RATIOS:
        aspect_ratio = "1:1"
    if resolution not in VALID_RESOLUTIONS:
        resolution = "1K"

    try:
        client = await _get_client()

        # Decode the source image
        image_bytes = base64.b64decode(source_image_b64)
        source_image = Image.open(io.BytesIO(image_bytes))

        config = types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=resolution,
            ),
        )

        response = await client.aio.models.generate_content(
            model=model,
            contents=[prompt, source_image],
            config=config,
        )

        image_b64 = ""
        mime_type = "image/png"
        revised_prompt = ""

        for part in response.parts:
            if hasattr(part, "thought") and part.thought:
                continue
            if part.text is not None:
                revised_prompt = part.text
            elif part.inline_data is not None:
                image_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                mime_type = part.inline_data.mime_type or "image/png"

        if not image_b64:
            return {"ok": False, "error": "No image generated during edit."}

        return {
            "ok": True,
            "image_b64": image_b64,
            "mime_type": mime_type,
            "revised_prompt": revised_prompt or prompt,
        }

    except Exception as e:
        log.error(f"Gemini image edit failed: {e}", exc_info=True)
        return {"ok": False, "error": f"Gemini image edit error: {str(e)}"}
