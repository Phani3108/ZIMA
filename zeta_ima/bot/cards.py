"""
Adaptive Card templates for the Zeta IMA Teams bot.

Structure reused from RDT 6/scripts/nightly_metrics.py's create_teams_card().
All cards use Adaptive Cards v1.4 schema (compatible with Teams).
"""

from typing import Optional


def draft_approval_card(
    draft: str,
    review: dict,
    iteration: int,
    brief: str,
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

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": f"Draft #{iteration} — Ready for Your Review",
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
                "text": draft,
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
        ],
        "actions": [
            {
                "type": "Action.Execute",
                "title": "Approve",
                "verb": "approve",
                "data": {"action": "approve"},
                "style": "positive",
            },
            {
                "type": "Action.Execute",
                "title": "Reject & Revise",
                "verb": "reject",
                "data": {"action": "reject"},
                "style": "destructive",
            },
        ],
    }


def thinking_card(brief: str) -> dict:
    """Ephemeral 'Thinking...' card sent immediately on receipt of brief."""
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Drafting copy...",
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
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": "Approved and saved to brand memory.",
                "weight": "Bolder",
                "color": "Good",
            },
            {
                "type": "TextBlock",
                "text": text,
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
