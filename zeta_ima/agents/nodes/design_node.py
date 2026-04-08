"""
Design Agent Node — generates images and visuals using Nano Banana 2 (Gemini)
with DALL-E 3 as fallback, and Canva for template-based designs.

Reads A2A handoff messages for design instructions from the PM agent.
"""

from __future__ import annotations

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
        # Route to Canva
        from zeta_ima.agents.nodes.canva_node import canva_node
        return await canva_node(state)

    # Use image LLM router (Nano Banana 2 → DALL-E fallback)
    from zeta_ima.agents.llm_router import call_image_llm, LLMError
    agent_messages.append(emit_step("design", "Preparing design brief", 0, 3, "completed", f"Aspect: {aspect_ratio}").to_dict())

    # Step 2/3: Generating visuals
    agent_messages.append(emit_step("design", "Generating visuals", 1, 3, "started").to_dict())

    # Determine aspect ratio from context
    aspect_ratio = settings.image_default_aspect_ratio
    resolution = settings.image_default_resolution

    # Try to infer aspect ratio from keywords
    lower_brief = brief.lower()
    if any(kw in lower_brief for kw in ["linkedin", "instagram post", "square"]):
        aspect_ratio = "1:1"
    elif any(kw in lower_brief for kw in ["story", "reel", "portrait", "poster"]):
        aspect_ratio = "9:16"
    elif any(kw in lower_brief for kw in ["banner", "landscape", "header", "cover"]):
        aspect_ratio = "16:9"
    elif any(kw in lower_brief for kw in ["wide", "panoramic"]):
        aspect_ratio = "21:9"

    try:
        provider_chain = settings.image_provider_chain.split(",")
        result = await call_image_llm(
            prompt=design_prompt,
            provider_chain=provider_chain,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )

        tool_results["design"] = {
            "ok": True,
            "provider": result.provider_used,
            "model": result.model_used,
            "mime_type": result.mime_type,
            "revised_prompt": result.revised_prompt,
            "image_b64_preview": result.image_b64[:100] + "..." if result.image_b64 else "",
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
