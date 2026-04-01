"""
Teams bot — ActivityHandler for the Zeta IMA multi-agent system.

Handles:
  1. on_message_activity  — user sends text or attaches a file
  2. on_invoke_activity   — user clicks Approve/Reject on an Adaptive Card
  3. on_members_added_activity — welcome message

Special commands (parsed from message text):
  "share with @Alice ..."  → proactive DM to Alice's stored conversation ref
  Attachment (PDF/DOCX/txt) → trigger ingestion pipeline

The Teams conversation ID is used as the LangGraph thread_id.
ConversationReference is saved on every message for proactive messaging.
"""

import re

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import Activity, ActivityTypes
from langgraph.types import Command

from zeta_ima.agents.graph import graph
from zeta_ima.agents.state import AgentState
from zeta_ima.bot.cards import (
    approved_confirmation_card,
    draft_approval_card,
    thinking_card,
)
from zeta_ima.memory.campaign import load_active_campaign
from zeta_ima.memory.session import make_thread_config
from zeta_ima.notify.graph import save_conversation_ref, send_proactive_card

_ADAPTIVE_CARD_CONTENT_TYPE = "application/vnd.microsoft.card.adaptive"


def _card_attachment(card: dict) -> dict:
    return {"contentType": _ADAPTIVE_CARD_CONTENT_TYPE, "content": card}


class ZetaMarketingBot(ActivityHandler):

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        activity = turn_context.activity
        user_message = (activity.text or "").strip()
        conversation_id = activity.conversation.id
        user_id = activity.from_property.id

        # Save conversation reference for proactive messaging
        try:
            from botbuilder.core import TurnContext as TC
            ref = TC.get_conversation_reference(activity)
            await save_conversation_ref(user_id, user_id, ref.serialize())
        except Exception:
            pass

        # Handle file attachments — ingest them
        if activity.attachments:
            await self._handle_attachments(turn_context, activity.attachments, user_id)
            return

        if not user_message:
            await turn_context.send_activity(
                MessageFactory.text("Please send me a brief and I'll draft copy for you.")
            )
            return

        # "share with @Alice ..." command
        share_match = re.search(r"share\s+(?:this\s+)?with\s+@?(\w+)", user_message, re.IGNORECASE)
        if share_match:
            await self._handle_share(turn_context, share_match.group(1), conversation_id)
            return

        config = make_thread_config(conversation_id)
        await turn_context.send_activity(
            MessageFactory.attachment(_card_attachment(thinking_card(user_message)))
        )

        campaign = await load_active_campaign(user_id)
        campaign_id = campaign["id"] if campaign else None

        initial_state: AgentState = {
            "messages": [{"role": "user", "content": user_message}],
            "current_brief": user_message,
            "drafts": [],
            "current_draft": {},
            "review_result": {},
            "iteration_count": 0,
            "user_id": user_id,
            "user_teams_id": user_id,
            "active_campaign_id": campaign_id,
            "stage": "drafting",
            "approval_decision": None,
            "approval_comment": None,
            "brand_examples": [],
            "intent": "",
            "route_to": [],
            "tool_results": {},
            "kb_context": [],
        }

        result = await graph.ainvoke(initial_state, config=config)
        await self._send_result(turn_context, result)

    async def _handle_attachments(self, turn_context: TurnContext, attachments, user_id: str):
        """Ingest file attachments from Teams."""
        import httpx
        from zeta_ima.ingest.pipeline import create_job, ingest_file_bytes
        import asyncio

        for att in attachments:
            if not att.content_url:
                continue
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    r = await client.get(att.content_url)
                    r.raise_for_status()
                job_id = await create_job("file", att.name or "teams_attachment")
                # Run ingestion in background
                asyncio.create_task(ingest_file_bytes(job_id, r.content, att.name or "attachment"))
                await turn_context.send_activity(
                    MessageFactory.text(f"Ingesting '{att.name}' (job: {job_id[:8]}...). I'll have it in my knowledge base shortly.")
                )
            except Exception as e:
                await turn_context.send_activity(MessageFactory.text(f"Failed to ingest '{att.name}': {e}"))

    async def _handle_share(self, turn_context: TurnContext, target_name: str, source_conversation_id: str):
        """Share the current draft with another Teams user by name."""
        # Get the current state from Redis to find the last draft
        config = make_thread_config(source_conversation_id)
        try:
            state = await graph.aget_state(config)
            draft = state.values.get("current_draft", {}).get("text", "")
            if not draft:
                await turn_context.send_activity(MessageFactory.text("No draft to share. Generate one first."))
                return

            # Find the target user's conversation ref by display name (simplified lookup)
            from sqlalchemy import select
            from zeta_ima.notify.graph import conversation_refs, _Session
            async with _Session() as session:
                result = await session.execute(
                    select(conversation_refs).where(
                        conversation_refs.c.teams_user_id.ilike(f"%{target_name}%")
                    )
                )
                row = result.fetchone()

            if not row:
                await turn_context.send_activity(
                    MessageFactory.text(f"@{target_name} hasn't used Zeta yet — they need to DM me first.")
                )
                return

            from zeta_ima.bot.cards import draft_approval_card
            card = draft_approval_card(draft=draft, review={}, iteration=1, brief="Shared draft")
            sent = await send_proactive_card(row.user_id, card)
            msg = f"Shared with @{target_name}." if sent else f"Failed to reach @{target_name}."
            await turn_context.send_activity(MessageFactory.text(msg))
        except Exception as e:
            await turn_context.send_activity(MessageFactory.text(f"Share failed: {e}"))

    async def on_invoke_activity(self, turn_context: TurnContext) -> None:
        """Handle Adaptive Card Approve/Reject button clicks."""
        activity = turn_context.activity
        value = activity.value or {}

        action = value.get("action")
        comment = value.get("comment", "")

        if action not in ("approve", "reject"):
            await turn_context.send_activity(
                MessageFactory.text("Unknown action. Please use the Approve or Reject buttons.")
            )
            return

        conversation_id = activity.conversation.id
        config = make_thread_config(conversation_id)

        # Resume the paused LangGraph graph from the interrupt point
        result = await graph.ainvoke(
            Command(resume={"decision": action, "comment": comment}),
            config=config,
        )
        await self._send_result(turn_context, result)

    async def _send_result(self, turn_context: TurnContext, result: dict) -> None:
        """Route the graph result to the right Teams message."""
        stage = result.get("stage")

        if stage == "awaiting_approval":
            card = draft_approval_card(
                draft=result["current_draft"]["text"],
                review=result["review_result"],
                iteration=result.get("iteration_count", 1),
                brief=result.get("current_brief", ""),
            )
            await turn_context.send_activity(
                MessageFactory.attachment(_card_attachment(card))
            )

        elif stage == "done":
            card = approved_confirmation_card(result["current_draft"]["text"])
            await turn_context.send_activity(
                MessageFactory.attachment(_card_attachment(card))
            )

        else:
            # Fallback: shouldn't normally be reached in production
            last_msg = result.get("messages", [{}])[-1].get("content", "")
            await turn_context.send_activity(MessageFactory.text(last_msg or "Processing..."))

    async def on_members_added_activity(self, members_added, turn_context: TurnContext) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(
                        "Hi, I'm Zeta — your AI marketing assistant. "
                        "Send me a brief and I'll draft copy for you."
                    )
                )
