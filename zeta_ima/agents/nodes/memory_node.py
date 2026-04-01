"""
Memory node — called only when the human clicks Approve.

Saves the approved output to:
  1. Qdrant brand_voice — for future brand context retrieval
  2. PostgreSQL audit trail — who approved what, for which campaign
  3. Learning signals — extract directional + tactical knowledge from the session
"""

import uuid

from zeta_ima.agents.state import AgentState
from zeta_ima.memory.brand import save_approved_output
from zeta_ima.memory.campaign import log_approved_output


async def memory_node(state: AgentState) -> dict:
    """Persist approved output and extract learning signals."""
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

    # Extract + store learning signals from the conversation (Genesis v2)
    try:
        from zeta_ima.memory.learning import classify_signal, record_directional_signal
        messages = state.get("messages", [])
        # Collect the last 10 user messages to extract signals from
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
                "category": "tactical",
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
                "content": "Output saved to brand memory and team brain. It will inform future work.",
            }
        ],
    }
