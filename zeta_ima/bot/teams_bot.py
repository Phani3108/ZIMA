"""
Teams bot — ActivityHandler for the Zeta IMA multi-agent system.

Handles:
  1. on_message_activity  — user sends text or attaches a file
  2. on_invoke_activity   — user clicks Approve/Reject/Plan/Design actions on Adaptive Cards
  3. on_members_added_activity — welcome message

Slash commands (design agent — parsed from message text):
  "@Zima /socialmedia /prompt ..."  → design skill execution
  "/skills" or "/help"             → list available skills
  "share with @Alice ..."          → proactive DM to Alice's stored conversation ref
  "what's pending"                 → list items awaiting action
  "status" / "digest"              → daily digest card

Everything else → treated as a general brief → LangGraph agent.

The Teams conversation ID is used as the LangGraph thread_id.
ConversationReference is saved on every message for proactive messaging.
"""

import re

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import Activity, ActivityTypes
from langgraph.types import Command

from zeta_ima.agents.activities import ActivityRegistry, SKILL_SLUG_MAP
from zeta_ima.agents.graph import graph
from zeta_ima.agents.state import AgentState
from zeta_ima.bot.cards import (
    approved_confirmation_card,
    design_approved_card,
    design_thinking_card,
    draft_approval_card,
    execution_status_card,
    image_result_card,
    meeting_plan_card,
    questions_card,
    skills_list_card,
    status_summary_card,
    thinking_card,
)
from zeta_ima.memory.campaign import load_active_campaign
from zeta_ima.memory.session import make_thread_config
from zeta_ima.notify.graph import save_conversation_ref, send_proactive_card

_ADAPTIVE_CARD_CONTENT_TYPE = "application/vnd.microsoft.card.adaptive"

# ── Slash-command regex ─────────────────────────────────────────────────────
# Matches: @Zima /socialmedia /prompt <text>
# Also:    /socialmedia /prompt <text>  (without @mention)
_SKILL_CMD_RE = re.compile(
    r"(?:@\w+\s+)?/(\w+)\s+/prompt\s+(.+)",
    re.IGNORECASE | re.DOTALL,
)
# Match: /skills or /help (with optional @mention)
_SKILLS_LIST_RE = re.compile(r"(?:@\w+\s+)?/(skills|help)\s*$", re.IGNORECASE)


def _card_attachment(card: dict) -> dict:
    return {"contentType": _ADAPTIVE_CARD_CONTENT_TYPE, "content": card}


def _build_skills_list() -> list[dict]:
    """Build skills list for the skills_list_card from activities.yaml."""
    registry = ActivityRegistry.get_instance()
    activities = registry.list_for_agent("design")
    # Reverse map: activity_id → first slug
    id_to_slug: dict[str, str] = {}
    for slug, act_id in SKILL_SLUG_MAP.items():
        if act_id not in id_to_slug:
            id_to_slug[act_id] = slug

    skills = []
    for act in activities:
        slug = id_to_slug.get(act.id, act.id)
        skills.append({
            "slug": slug,
            "title": act.title,
            "description": act.description,
            "example": f"Create a {act.title.lower()} for our product launch",
        })
    return skills


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

        # ── /skills or /help command ─────────────────────────────────
        if _SKILLS_LIST_RE.match(user_message):
            skills = _build_skills_list()
            card = skills_list_card("Design Agent", skills)
            await turn_context.send_activity(
                MessageFactory.attachment(_card_attachment(card))
            )
            return

        # ── /skill /prompt command (design execution) ────────────────
        skill_match = _SKILL_CMD_RE.match(user_message)
        if skill_match:
            skill_slug = skill_match.group(1).lower()
            prompt_text = skill_match.group(2).strip()
            await self._handle_design_command(
                turn_context, skill_slug, prompt_text, user_id, conversation_id
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

        # ── Default: treat as general brief → LangGraph ──────────────
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

    # ── Design slash-command handler ─────────────────────────────────────────

    async def _handle_design_command(
        self,
        turn_context: TurnContext,
        skill_slug: str,
        prompt_text: str,
        user_id: str,
        conversation_id: str,
    ) -> None:
        """Handle /skill /prompt commands for the Design Agent."""
        from dataclasses import asdict

        registry = ActivityRegistry.get_instance()
        activity_def = registry.get_by_slug(skill_slug)

        if activity_def is None:
            await turn_context.send_activity(
                MessageFactory.text(
                    f"Unknown skill `/{skill_slug}`. Type `/skills` to see available commands."
                )
            )
            return

        if activity_def.agent != "design":
            await turn_context.send_activity(
                MessageFactory.text(
                    f"`/{skill_slug}` belongs to the {activity_def.agent} agent. "
                    f"Design skills: type `/skills` to see the list."
                )
            )
            return

        # Check for required fields not provided in the prompt
        required_fields = [f for f in activity_def.input_schema if f.required]
        if required_fields:
            # Send questions card for the designer to fill in
            q_data = [
                {
                    "id": f.id,
                    "label": f.label,
                    "type": f.type,
                    "options": f.options,
                    "required": f.required,
                    "hint": f.hint,
                }
                for f in activity_def.input_schema
            ]
            card = questions_card(
                skill_title=activity_def.title,
                questions=q_data,
                skill_id=activity_def.id,
                prompt=prompt_text,
            )
            await turn_context.send_activity(
                MessageFactory.attachment(_card_attachment(card))
            )
            return

        # No required fields — execute directly
        await self._execute_design(
            turn_context, activity_def, prompt_text, "", user_id
        )

    async def _execute_design(
        self,
        turn_context: TurnContext,
        activity_def,
        prompt_text: str,
        platform: str,
        user_id: str,
    ) -> None:
        """Run design_node and send the result card."""
        # Send thinking card
        card = design_thinking_card(activity_def.title, prompt_text)
        await turn_context.send_activity(
            MessageFactory.attachment(_card_attachment(card))
        )

        from zeta_ima.agents.nodes.design_node import design_node

        initial_state: AgentState = {
            "messages": [{"role": "user", "content": prompt_text}],
            "current_brief": prompt_text,
            "drafts": [],
            "current_draft": {},
            "review_result": {},
            "iteration_count": 0,
            "user_id": user_id,
            "user_teams_id": user_id,
            "active_campaign_id": None,
            "stage": "executing",
            "approval_decision": None,
            "approval_comment": None,
            "brand_examples": [],
            "intent": "design",
            "route_to": ["design"],
            "tool_results": {
                "_skill_id": activity_def.id,
                "_platform": platform,
            },
            "kb_context": [],
            "pipeline": ["design"],
            "pipeline_index": 0,
            "agent_messages": [],
            "meeting_transcript": [],
            "meeting_plan": {},
            "plan_status": "",
            "user_plan_modifications": None,
            "brain_context": [],
        }

        result = await design_node(initial_state)
        design_result = result.get("tool_results", {}).get("design", {})

        if design_result.get("ok"):
            card = image_result_card(
                image_url=design_result.get("image_url", ""),
                download_url=design_result.get("download_url", ""),
                prompt=design_result.get("revised_prompt", prompt_text),
                provider=design_result.get("provider", ""),
                aspect_ratio=design_result.get("aspect_ratio", ""),
                skill_title=activity_def.title,
                platform=platform,
            )
            # Store result in conversation state for iteration
            try:
                config = make_thread_config(turn_context.activity.conversation.id)
                from zeta_ima.memory.session import save_design_state
                await save_design_state(config["configurable"]["thread_id"], {
                    "skill_id": activity_def.id,
                    "prompt": prompt_text,
                    "platform": platform,
                    "result": design_result,
                })
            except Exception:
                pass
        else:
            error = design_result.get("error", "Unknown error")
            card = {
                "type": "AdaptiveCard",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.5",
                "body": [{
                    "type": "TextBlock",
                    "text": f"❌ Design generation failed: {error}",
                    "weight": "Bolder",
                    "color": "Attention",
                    "wrap": True,
                }],
            }

        await turn_context.send_activity(
            MessageFactory.attachment(_card_attachment(card))
        )

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
        """Handle Adaptive Card button clicks — draft approval + plan approval + design actions."""
        activity = turn_context.activity
        value = activity.value or {}

        action = value.get("action")
        comment = value.get("comment", "")
        modifications = value.get("modifications", "")
        conversation_id = activity.conversation.id
        config = make_thread_config(conversation_id)
        user_id = activity.from_property.id

        # ── Design actions ────────────────────────────────────────────────────

        if action == "design_execute":
            # Questions card submitted — extract answers and execute
            skill_id = value.get("skill_id", "")
            prompt = value.get("prompt", "")
            registry = ActivityRegistry.get_instance()
            activity_def = registry.get(skill_id)
            if not activity_def:
                await turn_context.send_activity(
                    MessageFactory.text("Skill not found. Type `/skills` for available commands.")
                )
                return

            # Extract platform from answers (q_platform field)
            platform = value.get("q_platform", "")
            # Map friendly platform names to preset keys
            PLATFORM_MAP = {
                "LinkedIn": "linkedin_post", "Instagram": "instagram_post",
                "Twitter": "twitter_post", "Facebook": "facebook_post",
                "Facebook Ads": "facebook_ad", "Google Display": "google_display",
                "LinkedIn Ads": "linkedin_ad", "Instagram Ads": "instagram_ad",
            }
            platform = PLATFORM_MAP.get(platform, platform.lower().replace(" ", "_") if platform else "")

            # Append any extra context from form fields to prompt
            extras = []
            for key, val in value.items():
                if key.startswith("q_") and key != "q_platform" and val:
                    field_name = key[2:]  # strip q_ prefix
                    extras.append(f"{field_name}: {val}")
            if extras:
                prompt = f"{prompt}\n\n{chr(10).join(extras)}"

            await self._execute_design(
                turn_context, activity_def, prompt, platform, user_id
            )
            return

        if action == "design_cancel":
            await turn_context.send_activity(
                MessageFactory.text("Design request cancelled. Send a new `/skill /prompt` when ready.")
            )
            return

        if action == "design_approve":
            # Approve design — save to brand memory
            try:
                from zeta_ima.memory.session import load_design_state
                ds = await load_design_state(conversation_id)
                image_url = ds.get("result", {}).get("image_url", "") if ds else ""
                download_url = ds.get("result", {}).get("download_url", "") if ds else ""
            except Exception:
                image_url = ""
                download_url = ""

            card = design_approved_card(image_url, download_url)
            await turn_context.send_activity(
                MessageFactory.attachment(_card_attachment(card))
            )
            return

        if action == "design_retry":
            # Re-run with same parameters
            try:
                from zeta_ima.memory.session import load_design_state
                ds = await load_design_state(conversation_id)
                if ds:
                    registry = ActivityRegistry.get_instance()
                    activity_def = registry.get(ds["skill_id"])
                    if activity_def:
                        await self._execute_design(
                            turn_context, activity_def, ds["prompt"], ds.get("platform", ""), user_id
                        )
                        return
            except Exception:
                pass
            await turn_context.send_activity(
                MessageFactory.text("Couldn't retry — please send the command again.")
            )
            return

        if action == "design_adjust":
            # Re-run with adjusted prompt
            feedback = value.get("adjust_feedback", "")
            if not feedback:
                await turn_context.send_activity(
                    MessageFactory.text("Please type your adjustments in the text box and click Adjust again.")
                )
                return
            try:
                from zeta_ima.memory.session import load_design_state
                ds = await load_design_state(conversation_id)
                if ds:
                    registry = ActivityRegistry.get_instance()
                    activity_def = registry.get(ds["skill_id"])
                    if activity_def:
                        adjusted_prompt = f"{ds['prompt']}\n\nAdjustments: {feedback}"
                        await self._execute_design(
                            turn_context, activity_def, adjusted_prompt, ds.get("platform", ""), user_id
                        )
                        return
            except Exception:
                pass
            await turn_context.send_activity(
                MessageFactory.text("Couldn't apply adjustments — please send the command again.")
            )
            return

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
