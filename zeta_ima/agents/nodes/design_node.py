"""
Design Agent Node — generates images and visuals using the tool chain
configured by the Manager in the engine (Gemini / DALL-E / Canva / etc.).

Reads A2A handoff messages for design instructions from the PM agent.
Config-driven: tool routing and platform presets come from design_config DB.
"""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path

from zeta_ima.agents.state import AgentState
from zeta_ima.config import settings
from zeta_ima.orchestrator.a2a import AgentMessage, emit_step, get_latest_handoff

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "design_agent.md"


async def design_node(state: AgentState) -> dict:
    """Generate images/visuals based on brief and PM instructions."""
    brief = state.get("current_brief", "")
    tool_results = dict(state.get("tool_results", {}))
    agent_messages = list(state.get("agent_messages", []))

    # Step 1/3: Preparing design brief
    agent_messages.append(emit_step("design", "Preparing design brief", 0, 3, "started").to_dict())

    # Check for PM handoff instructions
    handoff = get_latest_handoff(agent_messages, "design")
    if handoff and handoff.handoff_instructions:
        design_prompt = handoff.handoff_instructions
    else:
        design_prompt = brief

    # Check for copy draft text to incorporate
    draft_text = state.get("current_draft", {}).get("text", "")
    if draft_text:
        design_prompt = f"{design_prompt}\n\nCopy text to incorporate: {draft_text[:500]}"

    # Detect if this is a Canva template request
    canva_match = re.search(r"\bDAF\w+\b", brief, re.IGNORECASE)
    if canva_match or any(kw in brief.lower() for kw in ["canva template", "use template"]):
        from zeta_ima.agents.nodes.canva_node import canva_node
        return await canva_node(state)

    # ── Load config-driven tool chain and presets ─────────────────
    from zeta_ima.agents.design_config import design_config

    # Determine skill_id from state (set by execution endpoint or default)
    skill_id = state.get("tool_results", {}).get("_skill_id", "social_visual")
    platform = state.get("tool_results", {}).get("_platform", "")

    tool_cfg = await design_config.get_tool_config(skill_id)
    provider_chain = [tool_cfg.primary_tool, tool_cfg.backup_tool]
    # Map tool names to provider names used by call_image_llm
    TOOL_TO_PROVIDER = {"gemini": "gemini", "dalle": "openai", "canva": "canva", "figma": "figma", "midjourney": "midjourney"}
    provider_chain = [TOOL_TO_PROVIDER.get(t, t) for t in provider_chain]

    # Load preset for platform (dimensions, resolution)
    preset = await design_config.get_preset_for_platform(skill_id, platform) if platform else None
    if preset:
        aspect_ratio = preset.aspect_ratio
        resolution = preset.resolution
    else:
        aspect_ratio = settings.image_default_aspect_ratio
        resolution = settings.image_default_resolution
        # Infer aspect ratio from brief keywords as fallback
        lower_brief = brief.lower()
        if any(kw in lower_brief for kw in ["linkedin", "instagram post", "square"]):
            aspect_ratio = "1:1"
        elif any(kw in lower_brief for kw in ["story", "reel", "portrait", "poster"]):
            aspect_ratio = "9:16"
        elif any(kw in lower_brief for kw in ["banner", "landscape", "header", "cover"]):
            aspect_ratio = "16:9"
        elif any(kw in lower_brief for kw in ["wide", "panoramic"]):
            aspect_ratio = "21:9"

    # Prepend style prompt prefix from rules
    rules = await design_config.get_rules()
    if rules.style_prompt_prefix:
        design_prompt = f"{rules.style_prompt_prefix}\n\n{design_prompt}"

    agent_messages.append(
        emit_step("design", "Preparing design brief", 0, 3, "completed", f"Aspect: {aspect_ratio}").to_dict()
    )

    # Step 2/3: Generating visuals
    agent_messages.append(emit_step("design", "Generating visuals", 1, 3, "started").to_dict())

    from zeta_ima.agents.llm_router import call_image_llm, LLMError

    try:
        result = await call_image_llm(
            prompt=design_prompt,
            provider_chain=provider_chain,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

        # Upload image to blob storage for download/sharing
        image_url = ""
        download_url = ""
        if result.image_b64:
            try:
                from zeta_ima.infra.blob_store import get_blob_store
                import uuid

                bs = get_blob_store()
                ext = "png" if "png" in (result.mime_type or "png") else "jpg"
                blob_path = f"design-outputs/{uuid.uuid4().hex}.{ext}"
                image_bytes = base64.b64decode(result.image_b64)
                image_url = await bs.upload(blob_path, image_bytes, content_type=result.mime_type or "image/png")
                download_url = image_url  # Same URL — blob storage serves directly
            except Exception as e:
                log.warning("Failed to upload image to blob storage: %s", e)

        tool_results["design"] = {
            "ok": True,
            "provider": result.provider_used,
            "model": result.model_used,
            "mime_type": result.mime_type,
            "revised_prompt": result.revised_prompt,
            "image_b64_preview": result.image_b64[:100] + "..." if result.image_b64 else "",
            "image_b64": result.image_b64,  # Full b64 for Teams card inline
            "image_url": image_url,
            "download_url": download_url,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "skill_id": skill_id,
            "platform": platform,
        }

        # A2A: send response to review agent
        agent_messages.append(AgentMessage(
            from_agent="design",
            to_agent="review",
            message_type="response",
            payload={
                "output_type": "image",
                "provider": result.provider_used,
                "revised_prompt": result.revised_prompt,
                "image_url": image_url,
            },
            context_summary=f"Generated {aspect_ratio} image via {result.provider_used}/{result.model_used}",
        ).to_dict())

        msg = (
            f"[Design] Image generated via {result.provider_used} ({result.model_used}). "
            f"Aspect: {aspect_ratio}, Resolution: {resolution}"
        )
        agent_messages.append(emit_step("design", "Generating visuals", 1, 3, "completed", f"Via {result.provider_used}").to_dict())
        agent_messages.append(emit_step("design", "Design complete", 2, 3, "completed").to_dict())

    except LLMError as e:
        tool_results["design"] = {"ok": False, "error": str(e)}
        msg = f"[Design] Image generation failed: {e}"
        agent_messages.append(emit_step("design", "Generating visuals", 1, 3, "completed", f"Failed: {e}").to_dict())
        agent_messages.append(emit_step("design", "Design complete", 2, 3, "completed", "Failed").to_dict())

    return {
        "tool_results": tool_results,
        "agent_messages": agent_messages,
        "messages": [{"role": "assistant", "content": msg}],
    }
