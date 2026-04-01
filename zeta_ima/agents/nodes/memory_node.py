"""
Memory node — called only when the human clicks Approve.

Saves the approved output to:
  1. Qdrant brand_voice — for future brand context retrieval
  2. PostgreSQL audit trail — who approved what, for which campaign
  3. Learning outcome — record success/failure metrics + tactical signals
  4. Reflection insights — persist critique patterns from actor-critic
  5. Directional signals — extract brand/strategy knowledge from conversation
  6. Agency brain — contribute approved output to shared knowledge
"""

import logging
import uuid

from zeta_ima.agents.state import AgentState
from zeta_ima.memory.brand import save_approved_output
from zeta_ima.memory.campaign import log_approved_output

log = logging.getLogger(__name__)


async def memory_node(state: AgentState) -> dict:
    """Persist approved output, record learning outcome, and extract signals."""
    output_id = str(uuid.uuid4())

    meta = {
        "output_id": output_id,
        "user_id": state["user_id"],
        "campaign_id": state.get("active_campaign_id"),
        "brief": state["current_brief"],
        "text": state["current_draft"]["text"],
        "iterations_needed": state.get("iteration_count", 1),
    }

    # Save to Qdrant (brand memory)
    qdrant_id = await save_approved_output(state["current_draft"]["text"], meta)

    # Save to PostgreSQL (audit log)
    meta["qdrant_id"] = qdrant_id
    await log_approved_output(meta)

    # ── Record learning outcome (closes the feedback loop) ──
    try:
        from zeta_ima.memory.learning import record_outcome
        await record_outcome(
            workflow_id=output_id,
            stage_id=output_id,
            skill_id=state.get("intent", "copy"),
            llm_used=getattr(state.get("current_draft", {}), "get", lambda k, d=None: d)("llm_used", "gpt-4o") if isinstance(state.get("current_draft"), dict) else "gpt-4o",
            approved_first_try=state.get("iteration_count", 1) == 1,
            iterations_needed=state.get("iteration_count", 1),
            user_feedback=state.get("approval_comment", ""),
            scores=state.get("review_result", {}).get("scores"),
            edit_instructions=[state["approval_comment"]] if state.get("approval_comment") else [],
            final_output=state["current_draft"]["text"],
        )
    except Exception as e:
        log.warning("Failed to record learning outcome: %s", e)

    # ── Persist reflection insights (actor-critic patterns → tactical memory) ──
    try:
        review_result = state.get("review_result", {})
        reflection_data = review_result.get("reflection")
        if reflection_data and review_result.get("_reflection_steps"):
            from zeta_ima.memory.learning import persist_reflection_insights
            await persist_reflection_insights(
                skill_id=state.get("intent", "copy"),
                reflection_steps=review_result["_reflection_steps"],
                brief=state["current_brief"],
                user_id=state.get("user_id", "system"),
            )
    except Exception as e:
        log.debug("Reflection persistence skipped: %s", e)

    # Extract + store learning signals from the conversation (Genesis v2)
    try:
        from zeta_ima.memory.learning import classify_signal, record_directional_signal
        messages = state.get("messages", [])
        user_texts = [
            m.get("content", "") for m in messages[-10:]
            if isinstance(m, dict) and m.get("role") == "user"
        ]
        combined_text = "\n".join(user_texts)
        if combined_text.strip():
            signals = await classify_signal(
                message_text=combined_text,
                source_user_id=state.get("user_id", ""),
                source_interaction_id=output_id,
            )
            for sig in signals:
                if sig.get("type") == "directional":
                    await record_directional_signal(
                        signal_text=sig["text"],
                        level=sig.get("level", "zeta"),
                        source_user_id=state.get("user_id", ""),
                        confidence=sig.get("confidence", 0.8),
                        tags=sig.get("tags", []),
                        source_interaction_id=output_id,
                    )
    except Exception:
        pass  # Non-fatal

    # Also push to agency brain
    try:
        from zeta_ima.memory.brain import agency_brain
        await agency_brain.contribute(
            {
                "text": state["current_draft"]["text"],
                "category": "copy_pattern",
                "level": "zeta",
                "confidence": 0.85,
                "tags": [state.get("intent", "copy")],
            },
            user_id=state.get("user_id", ""),
        )
    except Exception:
        pass  # Non-fatal

    # Auto-broadcast to Teams channel (fire-and-forget)
    try:
        from zeta_ima.notify.graph import post_to_channel
        from zeta_ima.bot.cards import approved_confirmation_card
        await post_to_channel(approved_confirmation_card(state["current_draft"]["text"]))
    except Exception:
        pass

    return {
        "stage": "done",
        "messages": [
            {
                "role": "assistant",
                "content": "Output saved to brand memory and team brain. Learning signals recorded.",
            }
        ],
    }
