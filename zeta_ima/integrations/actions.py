"""
Tool Action Registry — maps agent actions to integration functions.

When a workflow stage has a `tool_action` field, the agent pool looks up
the action here and invokes the corresponding integration function.

Each action declares:
  - integration: which vault credential set to check
  - module: Python module path for dynamic import
  - fn: function name to call
  - requires_approval: whether to gate execution behind user approval
  - description: human-readable description for the UI
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Optional

from zeta_ima.integrations.vault import vault

log = logging.getLogger(__name__)


ACTIONS: dict[str, dict] = {
    # ─── Image Generation ───────────────────────────────────────
    "generate_image": {
        "integration": "gemini_image",
        "module": "zeta_ima.integrations.gemini_image",
        "fn": "generate_image",
        "requires_approval": False,
        "description": "Generate a marketing image with Nano Banana 2 (Gemini)",
        "output_type": "image",
    },
    "generate_image_dalle": {
        "integration": "dalle",
        "module": "zeta_ima.integrations.dalle",
        "fn": "generate_image",
        "requires_approval": False,
        "description": "Generate a marketing image with DALL-E 3 (fallback)",
        "output_type": "image",
    },
    "edit_image": {
        "integration": "gemini_image",
        "module": "zeta_ima.integrations.gemini_image",
        "fn": "edit_image",
        "requires_approval": False,
        "description": "Edit an image with Nano Banana 2 (Gemini)",
        "output_type": "image",
    },
    "generate_image_variations": {
        "integration": "dalle",
        "module": "zeta_ima.integrations.dalle",
        "fn": "generate_variations",
        "requires_approval": False,
        "description": "Generate variations of an existing image",
        "output_type": "image",
    },

    # ─── Design ─────────────────────────────────────────────────
    "create_design": {
        "integration": "canva",
        "module": "zeta_ima.integrations.canva",
        "fn": "create_design_from_template",
        "requires_approval": False,
        "description": "Create a Canva design from template",
        "output_type": "design",
    },
    "list_design_templates": {
        "integration": "canva",
        "module": "zeta_ima.integrations.canva",
        "fn": "list_templates",
        "requires_approval": False,
        "description": "Browse available Canva templates",
        "output_type": "json",
    },

    # ─── Social Media Publishing ────────────────────────────────
    "post_linkedin": {
        "integration": "linkedin",
        "module": "zeta_ima.integrations.linkedin_api",
        "fn": "create_post",
        "requires_approval": True,
        "description": "Publish a post to LinkedIn",
        "output_type": "url",
    },
    "post_linkedin_image": {
        "integration": "linkedin",
        "module": "zeta_ima.integrations.linkedin_api",
        "fn": "create_image_post",
        "requires_approval": True,
        "description": "Publish a LinkedIn post with image",
        "output_type": "url",
    },
    "schedule_social": {
        "integration": "buffer",
        "module": "zeta_ima.integrations.buffer",
        "fn": "create_post",
        "requires_approval": True,
        "description": "Schedule social media post via Buffer",
        "output_type": "json",
    },

    # ─── Email ──────────────────────────────────────────────────
    "create_email_campaign": {
        "integration": "mailchimp",
        "module": "zeta_ima.integrations.mailchimp",
        "fn": "create_campaign",
        "requires_approval": True,
        "description": "Create an email campaign in Mailchimp",
        "output_type": "json",
    },
    "send_email_campaign": {
        "integration": "mailchimp",
        "module": "zeta_ima.integrations.mailchimp",
        "fn": "send_campaign",
        "requires_approval": True,
        "description": "Send a Mailchimp campaign (irreversible)",
        "output_type": "json",
    },
    "send_email": {
        "integration": "sendgrid",
        "module": "zeta_ima.integrations.sendgrid",
        "fn": "send_email",
        "requires_approval": True,
        "description": "Send email via SendGrid",
        "output_type": "json",
    },

    # ─── SEO / Research ─────────────────────────────────────────
    "keyword_research": {
        "integration": "semrush",
        "module": "zeta_ima.integrations.semrush",
        "fn": "keyword_overview",
        "requires_approval": False,
        "description": "Get keyword volume and competition data",
        "output_type": "json",
    },
    "related_keywords": {
        "integration": "semrush",
        "module": "zeta_ima.integrations.semrush",
        "fn": "related_keywords",
        "requires_approval": False,
        "description": "Find related keywords for content planning",
        "output_type": "json",
    },
    "competitor_keywords": {
        "integration": "semrush",
        "module": "zeta_ima.integrations.semrush",
        "fn": "domain_organic_keywords",
        "requires_approval": False,
        "description": "Analyze competitor's top organic keywords",
        "output_type": "json",
    },
    "domain_overview": {
        "integration": "semrush",
        "module": "zeta_ima.integrations.semrush",
        "fn": "domain_overview",
        "requires_approval": False,
        "description": "Get domain traffic and keyword overview",
        "output_type": "json",
    },

    # ─── Project Management ─────────────────────────────────────
    "create_ticket": {
        "integration": "jira",
        "module": "zeta_ima.integrations.jira",
        "fn": "create_ticket",
        "requires_approval": False,
        "description": "Create a Jira ticket for task tracking",
        "output_type": "url",
    },

    # ─── Knowledge Base ─────────────────────────────────────────
    "publish_confluence": {
        "integration": "confluence",
        "module": "zeta_ima.integrations.confluence",
        "fn": "create_page",
        "requires_approval": True,
        "description": "Publish content to Confluence",
        "output_type": "url",
    },
}


async def execute_action(action_name: str, **kwargs: Any) -> dict:
    """
    Execute a tool action by name with the given arguments.

    Returns the integration function's result dict, or an error dict
    if the action is unknown or the integration is not configured.
    """
    action = ACTIONS.get(action_name)
    if action is None:
        return {"ok": False, "error": f"Unknown action: {action_name}"}

    # Check if the integration is configured
    integration = action["integration"]
    configured = await vault.list_configured()
    if integration not in configured:
        return {
            "ok": False,
            "error": f"{integration.title()} not configured. Add credentials in Settings → Integrations.",
        }

    # Dynamically import and call the function
    try:
        mod = importlib.import_module(action["module"])
        fn = getattr(mod, action["fn"])
        result = await fn(**kwargs)
        return result
    except Exception as e:
        log.error(f"Action '{action_name}' failed: {e}", exc_info=True)
        return {"ok": False, "error": f"Action failed: {str(e)}"}


def list_actions() -> list[dict]:
    """Return all actions for the API."""
    return [
        {
            "name": name,
            "integration": a["integration"],
            "description": a["description"],
            "requires_approval": a["requires_approval"],
            "output_type": a["output_type"],
        }
        for name, a in ACTIONS.items()
    ]


def get_actions_for_integration(integration: str) -> list[dict]:
    """Return all actions that use a specific integration."""
    return [
        {"name": name, **{k: v for k, v in a.items() if k != "module"}}
        for name, a in ACTIONS.items()
        if a["integration"] == integration
    ]
