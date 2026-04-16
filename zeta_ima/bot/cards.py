"""
Adaptive Card templates for the Zeta IMA Teams bot.

All cards use Adaptive Cards v1.5 schema (compatible with Teams).
Cards follow the split: Teams = quick action, Web = full detail.
Every card includes a "View details" Action.OpenUrl to the web dashboard.
"""

from typing import List, Optional

from zeta_ima.config import settings

_FRONTEND = settings.frontend_url


# ── Design Agent Cards ──────────────────────────────────────────────────────


def skills_list_card(agent_name: str, skills: list[dict]) -> dict:
    """
    Card listing available skills for an agent.
    Shown when designer types /skills or /help in Teams.
    Each skill shows: title, description, example usage.
    """
    body: list = [
        {
            "type": "TextBlock",
            "text": f"🎨 {agent_name} — Available Skills",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": "Use these slash commands to create designs:",
            "isSubtle": True,
            "wrap": True,
        },
        {"type": "Separator"},
    ]

    for skill in skills:
        slug = skill.get("slug", "")
        title = skill.get("title", "")
        desc = skill.get("description", "")
        example = skill.get("example", "")

        body.append({
            "type": "Container",
            "style": "emphasis",
            "spacing": "Small",
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"**/{slug}** — {title}",
                    "weight": "Bolder",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": desc,
                    "wrap": True,
                    "isSubtle": True,
                },
                {
                    "type": "TextBlock",
                    "text": f"💡 `@Zima /{slug} /prompt {example}`",
                    "wrap": True,
                    "size": "Small",
                    "color": "Accent",
                },
            ],
        })

    body.append({"type": "Separator"})
    body.append({
        "type": "TextBlock",
        "text": "_Tip: Add /prompt followed by your instructions_",
        "isSubtle": True,
        "wrap": True,
        "size": "Small",
    })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": [{
            "type": "Action.OpenUrl",
            "title": "View all skills →",
            "url": f"{_FRONTEND}/future/agent/design",
        }],
    }


def questions_card(
    skill_title: str,
    questions: list[dict],
    skill_id: str,
    prompt: str,
) -> dict:
    """
    Adaptive Card with input fields matching the activity's input_schema.
    Shown when designer invokes a skill with missing required fields.

    Each question → Input.Text or Input.ChoiceSet based on type.
    """
    body: list = [
        {
            "type": "TextBlock",
            "text": f"🖌️ Design Agent has a few questions",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": f"Skill: **{skill_title}**",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Your prompt: _{prompt[:200]}_",
            "isSubtle": True,
            "wrap": True,
        },
        {"type": "Separator"},
    ]

    for q in questions:
        field_id = q["id"]
        label = q["label"]
        field_type = q.get("type", "text")
        options = q.get("options", [])
        required = q.get("required", False)
        hint = q.get("hint", "")

        req_marker = " *" if required else ""

        if field_type in ("select", "multiselect") and options:
            choices = [{"title": opt, "value": opt} for opt in options]
            body.append({
                "type": "TextBlock",
                "text": f"{label}{req_marker}",
                "weight": "Bolder",
                "size": "Small",
            })
            body.append({
                "type": "Input.ChoiceSet",
                "id": f"q_{field_id}",
                "style": "compact",
                "isMultiSelect": field_type == "multiselect",
                "placeholder": f"Select{' one or more' if field_type == 'multiselect' else ''}...",
                "choices": choices,
            })
        else:
            placeholder = hint if hint else f"Enter {label.lower()}..."
            body.append({
                "type": "Input.Text",
                "id": f"q_{field_id}",
                "label": f"{label}{req_marker}",
                "placeholder": placeholder,
                "isMultiline": len(placeholder) > 50,
            })

    actions = [
        {
            "type": "Action.Execute",
            "title": "▶️ Generate",
            "verb": "design_execute",
            "data": {
                "action": "design_execute",
                "skill_id": skill_id,
                "prompt": prompt,
            },
            "style": "positive",
        },
        {
            "type": "Action.Execute",
            "title": "❌ Cancel",
            "verb": "design_cancel",
            "data": {"action": "design_cancel"},
            "style": "destructive",
        },
    ]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def image_result_card(
    image_url: str,
    download_url: str,
    prompt: str,
    provider: str,
    aspect_ratio: str,
    skill_title: str,
    platform: str = "",
) -> dict:
    """
    Card showing the generated image with download/share/iterate actions.
    Image displayed inline if URL is accessible; otherwise shows link.
    """
    platform_text = f" ({platform.replace('_', ' ').title()})" if platform else ""

    body: list = [
        {
            "type": "TextBlock",
            "text": f"🖼️ {skill_title}{platform_text} — Ready",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Good",
        },
    ]

    # Show image inline if URL is available
    if image_url and not image_url.startswith("file://"):
        body.append({
            "type": "Image",
            "url": image_url,
            "altText": "Generated design",
            "size": "Large",
        })
    elif image_url:
        body.append({
            "type": "TextBlock",
            "text": f"📎 [View Image]({image_url})",
            "wrap": True,
        })

    body.extend([
        {"type": "Separator"},
        {
            "type": "FactSet",
            "facts": [
                {"title": "Provider", "value": provider},
                {"title": "Aspect Ratio", "value": aspect_ratio},
                {"title": "Prompt", "value": prompt[:200]},
            ],
        },
        {
            "type": "Input.Text",
            "id": "adjust_feedback",
            "placeholder": "Any adjustments? (e.g., 'make it brighter', 'add more text')",
            "isMultiline": True,
        },
    ])

    actions = [
        {
            "type": "Action.Execute",
            "title": "✅ Looks Good",
            "verb": "design_approve",
            "data": {"action": "design_approve"},
            "style": "positive",
        },
        {
            "type": "Action.Execute",
            "title": "🔄 Try Another",
            "verb": "design_retry",
            "data": {"action": "design_retry"},
        },
        {
            "type": "Action.Execute",
            "title": "✏️ Adjust",
            "verb": "design_adjust",
            "data": {"action": "design_adjust"},
        },
    ]

    if download_url:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "⬇️ Download",
            "url": download_url,
        })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def design_approved_card(image_url: str, download_url: str) -> dict:
    """Confirmation card after designer approves a design."""
    body: list = [
        {
            "type": "TextBlock",
            "text": "✅ Design approved and saved to brand memory.",
            "weight": "Bolder",
            "color": "Good",
        },
    ]

    if image_url and not image_url.startswith("file://"):
        body.append({
            "type": "Image",
            "url": image_url,
            "altText": "Approved design",
            "size": "Medium",
        })

    actions = []
    if download_url:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "⬇️ Download",
            "url": download_url,
        })
    actions.append({
        "type": "Action.OpenUrl",
        "title": "View in dashboard →",
        "url": f"{_FRONTEND}/future/agent/design",
    })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def design_thinking_card(skill_title: str, prompt: str) -> dict:
    """Ephemeral 'Working...' card for design generation."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": f"🖌️ Working on your {skill_title}...",
                "weight": "Bolder",
                "color": "Accent",
            },
            {
                "type": "TextBlock",
                "text": f"Prompt: {prompt[:150]}",
                "isSubtle": True,
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": "⏳ Generating image — this usually takes 10-30 seconds.",
                "isSubtle": True,
                "wrap": True,
            },
        ],
    }


# ── Original Cards (copy/general workflows) ────────────────────────────────


def draft_approval_card(
    draft: str,
    review: dict,
    iteration: int,
    brief: str,
    workflow_id: str = "",
) -> dict:
    """
    Approval card shown to the user after a draft passes the review agent.
    Contains: draft text, review scores, optional feedback input, Approve/Reject buttons.
    """
    scores = review.get("scores", {})

    score_facts = []
    score_map = {"brand_fit": "Brand fit", "clarity": "Clarity", "cta_strength": "CTA strength"}
    for key, label in score_map.items():
        val = scores.get(key)
        score_facts.append({"title": label, "value": f"{val}/10" if val is not None else "—"})

    score_facts.append({"title": "Review verdict", "value": review.get("reason", "—")})
    score_facts.append({"title": "Iteration", "value": str(iteration)})

    actions = [
        {
            "type": "Action.Execute",
            "title": "✅ Approve",
            "verb": "approve",
            "data": {"action": "approve"},
            "style": "positive",
        },
        {
            "type": "Action.Execute",
            "title": "❌ Reject & Revise",
            "verb": "reject",
            "data": {"action": "reject"},
            "style": "destructive",
        },
    ]
    if workflow_id:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "View details →",
            "url": f"{_FRONTEND}/workflows/{workflow_id}",
        })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": f"📝 Draft #{iteration} — Ready for Your Review",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent",
            },
            {
                "type": "TextBlock",
                "text": f"Brief: {brief[:120]}{'...' if len(brief) > 120 else ''}",
                "isSubtle": True,
                "wrap": True,
            },
            {"type": "Separator"},
            {
                "type": "TextBlock",
                "text": draft[:2000],
                "wrap": True,
            },
            {"type": "Separator"},
            {
                "type": "FactSet",
                "facts": score_facts,
            },
            {
                "type": "Input.Text",
                "id": "comment",
                "placeholder": "Optional feedback (shown to agent if you Reject)...",
                "isMultiline": True,
            },
            {"type": "Separator"},
            {
                "type": "TextBlock",
                "text": "Rate this output (optional):",
                "isSubtle": True,
            },
            {
                "type": "Input.ChoiceSet",
                "id": "rating",
                "style": "compact",
                "placeholder": "1-5 stars",
                "choices": [
                    {"title": "⭐ 1 — Poor", "value": "1"},
                    {"title": "⭐⭐ 2 — Below average", "value": "2"},
                    {"title": "⭐⭐⭐ 3 — Average", "value": "3"},
                    {"title": "⭐⭐⭐⭐ 4 — Good", "value": "4"},
                    {"title": "⭐⭐⭐⭐⭐ 5 — Excellent", "value": "5"},
                ],
            },
            {
                "type": "Input.ChoiceSet",
                "id": "feedback_tags",
                "isMultiSelect": True,
                "style": "compact",
                "placeholder": "Select feedback tags...",
                "choices": [
                    {"title": "Tone perfect", "value": "Tone perfect"},
                    {"title": "Great CTA", "value": "Great CTA"},
                    {"title": "On-brand", "value": "On-brand"},
                    {"title": "Too formal", "value": "Too formal"},
                    {"title": "Too casual", "value": "Too casual"},
                    {"title": "Off-brand", "value": "Off-brand"},
                    {"title": "Too long", "value": "Too long"},
                    {"title": "Too short", "value": "Too short"},
                    {"title": "Great structure", "value": "Great structure"},
                    {"title": "Missing key info", "value": "Missing key info"},
                ],
            },
        ],
        "actions": actions,
    }


def meeting_plan_card(
    transcript: List[dict],
    plan: dict,
    brief: str,
    workflow_id: str = "",
) -> dict:
    """
    Scrum meeting card — shows agent discussion summary + plan.
    User can Continue, Modify, or Cancel.
    """
    # Build transcript text (max 5 messages in Teams, rest on web)
    body: list = [
        {
            "type": "TextBlock",
            "text": "📋 Agency Planning Meeting",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": f"Brief: {brief[:120]}{'...' if len(brief) > 120 else ''}",
            "isSubtle": True,
            "wrap": True,
        },
        {"type": "Separator"},
    ]

    # Show up to 5 meeting messages
    for msg in transcript[:5]:
        avatar = msg.get("avatar", "🤖")
        title = msg.get("agent_title", "Agent")
        content = msg.get("content", "")
        body.append({
            "type": "TextBlock",
            "text": f"{avatar} **{title}**: {content[:300]}",
            "wrap": True,
        })

    if len(transcript) > 5:
        body.append({
            "type": "TextBlock",
            "text": f"_...and {len(transcript) - 5} more messages. View full transcript in dashboard._",
            "isSubtle": True,
            "wrap": True,
        })

    body.append({"type": "Separator"})

    # Plan summary
    plan_facts = [
        {"title": "Agents involved", "value": str(len(plan.get("assigned_agents", {})))},
        {"title": "Est. time", "value": plan.get("estimated_duration", "~30s")},
    ]
    if plan.get("summary"):
        plan_facts.append({"title": "Plan", "value": plan["summary"][:200]})

    body.append({"type": "FactSet", "facts": plan_facts})

    # Modification input
    body.append({
        "type": "Input.Text",
        "id": "modifications",
        "placeholder": "Any changes? (e.g., 'Skip SEO', 'Make it more formal')...",
        "isMultiline": True,
    })

    actions = [
        {
            "type": "Action.Execute",
            "title": "✅ Continue",
            "verb": "plan_approve",
            "data": {"action": "plan_approve"},
            "style": "positive",
        },
        {
            "type": "Action.Execute",
            "title": "✏️ Modify",
            "verb": "plan_modify",
            "data": {"action": "plan_modify"},
        },
        {
            "type": "Action.Execute",
            "title": "❌ Cancel",
            "verb": "plan_cancel",
            "data": {"action": "plan_cancel"},
            "style": "destructive",
        },
    ]
    if workflow_id:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "View full plan →",
            "url": f"{_FRONTEND}/workflows/{workflow_id}",
        })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def execution_status_card(
    agent_title: str,
    agent_emoji: str,
    status_text: str,
    pipeline: List[str],
    current_step: int,
    workflow_id: str = "",
) -> dict:
    """Card showing which agent is currently active during execution."""
    total = len(pipeline)
    progress = f"Step {current_step}/{total}"

    body = [
        {
            "type": "TextBlock",
            "text": f"{agent_emoji} {agent_title} is working...",
            "weight": "Bolder",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": status_text,
            "wrap": True,
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "Progress", "value": progress},
                {"title": "Pipeline", "value": " → ".join(pipeline)},
            ],
        },
    ]

    actions = []
    if workflow_id:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "View live progress →",
            "url": f"{_FRONTEND}/workflows/{workflow_id}",
        })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def status_summary_card(pending_items: List[dict]) -> dict:
    """Response to 'what's pending?' — list of items awaiting action."""
    body: list = [
        {
            "type": "TextBlock",
            "text": "📋 Your Pending Items",
            "weight": "Bolder",
            "size": "Medium",
        },
    ]

    if not pending_items:
        body.append({
            "type": "TextBlock",
            "text": "Nothing pending — you're all caught up! 🎉",
            "wrap": True,
        })
    else:
        for item in pending_items[:10]:
            body.append({
                "type": "TextBlock",
                "text": f"• **{item.get('type', 'Task')}**: {item.get('brief', '')[:100]}",
                "wrap": True,
            })

    actions = [{
        "type": "Action.OpenUrl",
        "title": "Open dashboard →",
        "url": f"{_FRONTEND}/dashboard",
    }]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def ingest_status_card(
    source_name: str,
    status: str,
    chunks_created: int = 0,
    current_step: str = "",
    progress_pct: int = 0,
) -> dict:
    """Card for ingestion status — uses card refresh for pseudo-live updates."""
    if status == "done":
        emoji = "✅"
        text = f"**{source_name}** indexed — {chunks_created} chunks. Ask me about it now."
    elif status == "error":
        emoji = "❌"
        text = f"**{source_name}** failed to index."
    else:
        emoji = "⏳"
        text = f"**{source_name}** — {current_step} ({progress_pct}%)"

    body = [
        {
            "type": "TextBlock",
            "text": f"{emoji} Document Ingestion",
            "weight": "Bolder",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": text,
            "wrap": True,
        },
    ]

    actions = [{
        "type": "Action.OpenUrl",
        "title": "View ingestion details →",
        "url": f"{_FRONTEND}/ingest",
    }]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def daily_digest_card(
    pending_reviews: int,
    active_workflows: int,
    completed_today: int,
    top_items: List[dict] | None = None,
) -> dict:
    """Proactive morning digest card."""
    body: list = [
        {
            "type": "TextBlock",
            "text": "☀️ Good Morning — Your Daily Digest",
            "weight": "Bolder",
            "size": "Medium",
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "Awaiting your review", "value": str(pending_reviews)},
                {"title": "Active workflows", "value": str(active_workflows)},
                {"title": "Completed today", "value": str(completed_today)},
            ],
        },
    ]

    if top_items:
        body.append({"type": "Separator"})
        for item in top_items[:5]:
            body.append({
                "type": "TextBlock",
                "text": f"• {item.get('brief', '')[:100]}",
                "wrap": True,
                "isSubtle": True,
            })

    actions = [{
        "type": "Action.OpenUrl",
        "title": "Open dashboard →",
        "url": f"{_FRONTEND}/dashboard",
    }]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }


def thinking_card(brief: str) -> dict:
    """Ephemeral 'Thinking...' card sent immediately on receipt of brief."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": "🤔 Planning your request...",
                "weight": "Bolder",
                "color": "Accent",
            },
            {
                "type": "TextBlock",
                "text": f"Brief: {brief[:120]}",
                "isSubtle": True,
                "wrap": True,
            },
        ],
    }


def approved_confirmation_card(text: str) -> dict:
    """Confirmation card shown after user approves — output saved to brand memory."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": "✅ Approved and saved to brand memory.",
                "weight": "Bolder",
                "color": "Good",
            },
            {
                "type": "TextBlock",
                "text": text[:2000],
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": "This output will inform future copy generation.",
                "isSubtle": True,
                "wrap": True,
            },
        ],
    }


def prior_work_card(prior_work: list[dict], brief: str) -> dict:
    """
    Card showing similar past work — user can reuse, modify, or start fresh.
    Adaptive Card v1.5-compatible.
    """
    body: list[dict] = [
        {
            "type": "TextBlock",
            "text": "🔄 Similar Past Work Found",
            "weight": "Bolder",
            "size": "Medium",
        },
        {
            "type": "TextBlock",
            "text": f"Your brief: \"{brief[:200]}...\"" if len(brief) > 200 else f"Your brief: \"{brief}\"",
            "wrap": True,
            "isSubtle": True,
        },
    ]

    # Show up to 3 prior work items
    for i, item in enumerate(prior_work[:3]):
        score_text = f"Match: {item.get('similarity', 0):.0%}"
        if item.get("campaign_score", 0) > 0:
            score_text += f" | Campaign score: {item['campaign_score']:.0f}/100"

        body.append({
            "type": "Container",
            "style": "emphasis",
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"**#{i+1}** — {item.get('source', 'unknown').replace('_', ' ').title()}",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": item.get("brief", item.get("text_preview", ""))[:300],
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": score_text,
                    "isSubtle": True,
                },
            ],
        })

    # Action buttons
    actions = [
        {
            "type": "Action.Submit",
            "title": "✅ Use Similar Approach",
            "data": {
                "verb": "recall_reuse",
                "selected_id": prior_work[0]["id"] if prior_work else "",
            },
        },
        {
            "type": "Action.Submit",
            "title": "📝 Modify",
            "data": {
                "verb": "recall_modify",
                "selected_id": prior_work[0]["id"] if prior_work else "",
            },
        },
        {
            "type": "Action.Submit",
            "title": "🆕 Start Fresh",
            "data": {"verb": "recall_fresh"},
        },
    ]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }
