"""
Multi-LLM Dispatcher — routes prompts to OpenAI, Claude, or Gemini.

Each skill defines a preferred LLM chain (e.g., claude → openai → gemini).
The dispatcher tries each in order, falling back transparently on failure.

Usage:
    from zeta_ima.agents.llm_router import call_llm

    result = await call_llm(
        prompt="Write a LinkedIn post...",
        system="You are a copywriter...",
        llm_chain=["claude", "openai", "gemini"],
    )
    print(result.text, result.provider_used, result.model_used)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from zeta_ima.config import settings
from zeta_ima.integrations.vault import vault

log = logging.getLogger(__name__)


@dataclass
class LLMResult:
    text: str
    provider_used: str       # "openai" | "claude" | "gemini"
    model_used: str          # "gpt-4o" | "claude-sonnet-4-20250514" | etc.
    input_tokens: int = 0
    output_tokens: int = 0


class LLMError(Exception):
    """Raised when an LLM call fails (API error, auth error, timeout)."""


# ---------------------------------------------------------------------------
# Provider-specific callers
# ---------------------------------------------------------------------------

async def _call_openai(prompt: str, system: str, model: str = "gpt-4o",
                       temperature: float = 0.7, max_tokens: int = 4096) -> LLMResult:
    from openai import AsyncOpenAI

    api_key = settings.openai_api_key
    if not api_key:
        # Try vault
        api_key = await vault.get("openai", "api_key")
    if not api_key:
        raise LLMError("OpenAI API key not configured")

    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return LLMResult(
        text=resp.choices[0].message.content or "",
        provider_used="openai",
        model_used=model,
        input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
        output_tokens=resp.usage.completion_tokens if resp.usage else 0,
    )


async def _call_claude(prompt: str, system: str, model: str = "claude-sonnet-4-20250514",
                        temperature: float = 0.7, max_tokens: int = 4096) -> LLMResult:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        raise LLMError("anthropic package not installed")

    api_key = await vault.get("anthropic", "api_key")
    if not api_key:
        raise LLMError("Anthropic API key not configured")

    client = AsyncAnthropic(api_key=api_key)
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text if resp.content else ""
    return LLMResult(
        text=text,
        provider_used="claude",
        model_used=model,
        input_tokens=resp.usage.input_tokens if resp.usage else 0,
        output_tokens=resp.usage.output_tokens if resp.usage else 0,
    )


async def _call_gemini(prompt: str, system: str, model: str = "gemini-2.5-flash",
                        temperature: float = 0.7, max_tokens: int = 4096) -> LLMResult:
    try:
        from google import genai
    except ImportError:
        raise LLMError("google-genai package not installed")

    api_key = await vault.get("google", "api_key")
    if not api_key:
        raise LLMError("Google API key not configured")

    client = genai.Client(api_key=api_key)
    resp = await client.aio.models.generate_content(
        model=model,
        contents=f"{system}\n\n{prompt}",
        config=genai.types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    return LLMResult(
        text=resp.text or "",
        provider_used="gemini",
        model_used=model,
    )


# Provider dispatch table
_PROVIDERS = {
    "openai": _call_openai,
    "claude": _call_claude,
    "gemini": _call_gemini,
}

# Default models per provider
_DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "claude": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.5-flash",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def call_llm(
    prompt: str,
    system: str = "You are a helpful marketing assistant.",
    llm_chain: Optional[list[str]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model_override: Optional[str] = None,
    user_id: str = "system",
    skill_id: str = "",
    workflow_id: str = "",
) -> LLMResult:
    """
    Call an LLM with automatic fallback chain.

    Args:
        prompt: The user prompt.
        system: System message.
        llm_chain: Ordered list of providers to try, e.g. ["claude", "openai", "gemini"].
                   Defaults to ["openai", "claude", "gemini"].
        temperature: Sampling temperature.
        max_tokens: Max response tokens.
        model_override: Force a specific model (e.g., "gpt-4o-mini").
        user_id: For cost tracking and rate limiting.
        skill_id: For cost attribution.
        workflow_id: For cost attribution.

    Returns:
        LLMResult with the text and which provider/model was used.

    Raises:
        LLMError if ALL providers in the chain fail.
    """
    # Rate limit check
    try:
        from zeta_ima.agents.cost_tracker import cost_tracker
        limit_check = await cost_tracker.check_rate_limit(user_id)
        if not limit_check["allowed"]:
            raise LLMError(f"Rate limit exceeded: {limit_check['reason']}")
    except ImportError:
        pass  # cost_tracker not initialized yet
    except LLMError:
        raise
    except Exception:
        pass  # non-fatal

    chain = llm_chain or ["openai", "claude", "gemini"]
    errors: list[str] = []

    for provider in chain:
        caller = _PROVIDERS.get(provider)
        if caller is None:
            errors.append(f"{provider}: unknown provider")
            continue

        model = model_override or _DEFAULT_MODELS.get(provider, "")
        try:
            result = await caller(prompt, system, model=model,
                                  temperature=temperature, max_tokens=max_tokens)
            if provider != chain[0]:
                log.info(f"LLM fallback: used {provider} (primary {chain[0]} failed)")

            # Track cost
            try:
                from zeta_ima.agents.cost_tracker import cost_tracker
                await cost_tracker.record(
                    user_id=user_id,
                    provider=result.provider_used,
                    model=result.model_used,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    skill_id=skill_id,
                    workflow_id=workflow_id,
                )
            except Exception:
                pass  # non-fatal

            return result
        except LLMError:
            raise  # re-raise rate limit errors
        except Exception as e:
            msg = f"{provider}/{model}: {type(e).__name__}: {e}"
            log.warning(f"LLM call failed — {msg}")
            errors.append(msg)

    raise LLMError(f"All LLM providers failed: {'; '.join(errors)}")


# ---------------------------------------------------------------------------
# Image generation — Nano Banana 2 (Gemini) with DALL-E fallback
# ---------------------------------------------------------------------------

@dataclass
class ImageResult:
    image_b64: str           # Base64-encoded image data
    mime_type: str           # "image/png" | "image/jpeg"
    revised_prompt: str      # Prompt as interpreted by the model
    provider_used: str       # "gemini" | "openai"
    model_used: str          # "gemini-3.1-flash-image-preview" | "dall-e-3"


async def _call_gemini_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    resolution: str = "1K",
) -> ImageResult:
    from zeta_ima.integrations.gemini_image import generate_image

    result = await generate_image(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )
    if not result["ok"]:
        raise LLMError(f"Gemini image: {result.get('error', 'unknown')}")

    return ImageResult(
        image_b64=result["image_b64"],
        mime_type=result["mime_type"],
        revised_prompt=result["revised_prompt"],
        provider_used="gemini",
        model_used="gemini-3.1-flash-image-preview",
    )


async def _call_dalle_image(prompt: str, **kwargs) -> ImageResult:
    from zeta_ima.integrations.dalle import generate_image
    import base64
    import httpx

    result = await generate_image(prompt=prompt)
    if not result["ok"]:
        raise LLMError(f"DALL-E image: {result.get('error', 'unknown')}")

    # DALL-E returns a URL — download and encode as base64
    image_b64 = ""
    if result.get("url"):
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(result["url"])
            if resp.is_success:
                image_b64 = base64.b64encode(resp.content).decode("utf-8")

    return ImageResult(
        image_b64=image_b64,
        mime_type="image/png",
        revised_prompt=result.get("revised_prompt", prompt),
        provider_used="openai",
        model_used="dall-e-3",
    )


_IMAGE_PROVIDERS = {
    "gemini": _call_gemini_image,
    "openai": _call_dalle_image,
}


async def call_image_llm(
    prompt: str,
    provider_chain: Optional[list[str]] = None,
    aspect_ratio: str = "1:1",
    resolution: str = "1K",
) -> ImageResult:
    """
    Generate an image with automatic fallback chain.

    Default chain: Gemini Nano Banana 2 → DALL-E 3.

    Args:
        prompt: Image description.
        provider_chain: Ordered list of providers to try.
        aspect_ratio: Aspect ratio (Gemini only).
        resolution: Resolution (Gemini only).

    Returns:
        ImageResult with base64 image data.

    Raises:
        LLMError if ALL providers fail.
    """
    chain = provider_chain or ["gemini", "openai"]
    errors: list[str] = []

    for provider in chain:
        caller = _IMAGE_PROVIDERS.get(provider)
        if caller is None:
            errors.append(f"{provider}: unknown image provider")
            continue
        try:
            result = await caller(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )
            if provider != chain[0]:
                log.info(f"Image fallback: used {provider} (primary {chain[0]} failed)")
            return result
        except Exception as e:
            msg = f"{provider}: {type(e).__name__}: {e}"
            log.warning(f"Image generation failed — {msg}")
            errors.append(msg)

    raise LLMError(f"All image providers failed: {'; '.join(errors)}")


async def check_available_providers() -> dict[str, bool]:
    """Check which LLM providers have valid API keys configured."""
    available = {}

    # OpenAI
    has_openai = bool(settings.openai_api_key)
    if not has_openai:
        has_openai = bool(await vault.get("openai", "api_key"))
    available["openai"] = has_openai

    # Claude
    available["claude"] = bool(await vault.get("anthropic", "api_key"))

    # Gemini
    available["gemini"] = bool(await vault.get("google", "api_key"))

    return available
