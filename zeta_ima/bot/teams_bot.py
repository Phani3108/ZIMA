"""
Teams bot — ActivityHandler for the Zeta IMA multi-agent system.

Handles:
  1. on_message_activity  — user sends text or attaches a file
  2. on_invoke_activity   — user clicks Approve/Reject/Plan actions on Adaptive Cards
  3. on_members_added_activity — welcome message

Special commands (parsed from message text):
  "share with @Alice ..."  → proactive DM to Alice's stored conversation ref
  "what's pending"         → list items awaiting action
  "status" / "digest"     → daily digest card
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
    execution_status_card,
    meeting_plan_card,
    status_summary_card,
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

        # "what's pending" command
        if re.search(r"what('?s|\s+is)\s+pending|pending\s+items?|show\s+pending", user_message, re.IGNORECASE):
            await self._handle_pending(turn_context, user_id)
            return

        # "status" / "digest" command
        if re.search(r"\b(status|digest|summary|overview)\b", user_message, re.IGNORECASE) and len(user_message.split()) <= 3:
            await self._handle_digest(turn_context, user_id)
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
            "stage": "planning",
            "approval_decision": None,
            "approval_comment": None,
            "brand_examples": [],
            "intent": "",
            "route_to": [],
            "tool_results": {},
            "kb_context": [],
            "pipeline": [],
            "pipeline_index": 0,
            "agent_messages": [],
            "meeting_transcript": [],
            "meeting_plan": {},
            "plan_status": "",
            "user_plan_modifications": None,
            "brain_context": [],
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
        """Handle Adaptive Card button clicks — draft approval + plan approval."""
        activity = turn_context.activity
        value = activity.value or {}

        action = value.get("action")
        comment = value.get("comment", "")
        modifications = value.get("modifications", "")
        conversation_id = activity.conversation.id
        config = make_thread_config(conversation_id)

        # ── Recall verbs (prior work recognition) ─────────────────────────────
        if action in ("recall_reuse", "recall_modify", "recall_fresh"):
            decision = {"recall_reuse": "reuse", "recall_modify": "modify", "recall_fresh": "start_fresh"}[action]
            selected_id = value.get("selected_id", "")
            result = await graph.ainvoke(
                Command(resume={"decision": decision, "selected_id": selected_id}),
                config=config,
            )
            await self._send_result(turn_context, result)
            return

        # ── Plan approval verbs ──────────────────────────────────────────────
        if action == "plan_approve":
            result = await graph.ainvoke(
                Command(resume={"decision": "approve"}),
                config=config,
            )
            await self._send_result(turn_context, result)
            return

        if action == "plan_modify":
            if not modifications:
                await turn_context.send_activity(
                    MessageFactory.text("Please type your modifications in the text box and click Modify again.")
                )
                return
            result = await graph.ainvoke(
                Command(resume={"decision": "modify", "modifications": modifications}),
                config=config,
            )
            await self._send_result(turn_context, result)
            return

        if action == "plan_cancel":
            result = await graph.ainvoke(
                Command(resume={"decision": "cancel"}),
                config=config,
            )
            await self._send_result(turn_context, result)
            return

        # ── Draft approval verbs ─────────────────────────────────────────────
        if action not in ("approve", "reject"):
            await turn_context.send_activity(
                MessageFactory.text("Unknown action. Use the buttons on the card.")
            )
            return

        # Record structured feedback (fire-and-forget)
        try:
            rating = int(value.get("rating", 0) or 0)
            feedback_tags_raw = value.get("feedback_tags", "")
            feedback_tags = [t.strip() for t in feedback_tags_raw.split(",") if t.strip()] if feedback_tags_raw else []
            if rating > 0 or feedback_tags or comment:
                from zeta_ima.memory.feedback import record_feedback
                await record_feedback(
                    team_id=value.get("team_id", "__default__"),
                    user_id=activity.from_property.id,
                    workflow_id=value.get("workflow_id", ""),
                    skill_id=value.get("skill_id", "copy"),
                    rating=rating,
                    tags=feedback_tags,
                    free_text=comment,
                )
        except Exception:
            pass  # Non-fatal

        # Resume the paused LangGraph graph from the interrupt point
        result = await graph.ainvoke(
            Command(resume={"decision": action, "comment": comment}),
            config=config,
        )
        await self._send_result(turn_context, result)

    async def _send_result(self, turn_context: TurnContext, result: dict) -> None:
        """Route the graph result to the right Teams message."""
        stage = result.get("stage")
        plan_status = result.get("plan_status")

        # Planning meeting — show the meeting plan card
        if plan_status == "awaiting_user" or stage == "planning":
            card = meeting_plan_card(
                transcript=result.get("meeting_transcript", []),
                plan=result.get("meeting_plan", {}),
                brief=result.get("current_brief", ""),
            )
            await turn_context.send_activity(
                MessageFactory.attachment(_card_attachment(card))
            )

        elif plan_status == "cancelled":
            await turn_context.send_activity(
                MessageFactory.text("Task cancelled. Send me a new brief when you're ready.")
            )

        elif stage == "awaiting_approval":
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
            draft = result.get("current_draft", {}).get("text", "")
            if draft:
                card = approved_confirmation_card(draft)
                await turn_context.send_activity(
                    MessageFactory.attachment(_card_attachment(card))
                )
            else:
                # Tool-only pipeline (research, jira, etc.)
                last_msg = result.get("messages", [{}])[-1].get("content", "Done.")
                await turn_context.send_activity(MessageFactory.text(last_msg))

        else:
            # Fallback: shouldn't normally be reached in production
            last_msg = result.get("messages", [{}])[-1].get("content", "")
            await turn_context.send_activity(MessageFactory.text(last_msg or "Processing..."))

    async def _handle_pending(self, turn_context: TurnContext, user_id: str):
        """Show items awaiting the user's action."""
        try:
            from zeta_ima.api.routes.workflows import get_pending_items
            items = await get_pending_items(user_id)
        except Exception:
            items = []

        card = status_summary_card(items)
        await turn_context.send_activity(
            MessageFactory.attachment(_card_attachment(card))
        )

    async def _handle_digest(self, turn_context: TurnContext, user_id: str):
        """Show a daily digest / status overview."""
        from zeta_ima.bot.cards import daily_digest_card
        try:
            from zeta_ima.api.routes.workflows import get_digest_stats
            stats = await get_digest_stats(user_id)
        except Exception:
            stats = {"pending_reviews": 0, "active_workflows": 0, "completed_today": 0}

        card = daily_digest_card(
            pending_reviews=stats.get("pending_reviews", 0),
            active_workflows=stats.get("active_workflows", 0),
            completed_today=stats.get("completed_today", 0),
        )
        await turn_context.send_activity(
            MessageFactory.attachment(_card_attachment(card))
        )

    async def on_members_added_activity(self, members_added, turn_context: TurnContext) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(
                        "Hi, I'm Zeta — your AI marketing assistant. "
                        "Send me a brief and I'll draft copy for you."
                    )
                )
