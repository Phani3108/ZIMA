"""
Integration registry — defines all supported external tools and their required keys.

Used by the settings UI to show which integrations are configured and which need setup.
"""

INTEGRATIONS: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "description": "Used for copy generation and review agents.",
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "jira": {
        "label": "Jira",
        "description": "Create tickets, search issues, update status.",
        "keys": [
            {"name": "base_url", "label": "Jira Base URL (e.g. https://yourco.atlassian.net)", "secret": False},
            {"name": "email", "label": "Account Email", "secret": False},
            {"name": "api_token", "label": "API Token", "secret": True},
        ],
    },
    "confluence": {
        "label": "Confluence",
        "description": "Read and publish Confluence pages.",
        "keys": [
            {"name": "base_url", "label": "Confluence Base URL", "secret": False},
            {"name": "email", "label": "Account Email", "secret": False},
            {"name": "api_token", "label": "API Token", "secret": True},
            {"name": "space_key", "label": "Default Space Key", "secret": False},
        ],
    },
    "github": {
        "label": "GitHub",
        "description": "Create PRs, read files, set commit statuses.",
        "keys": [
            {"name": "app_id", "label": "GitHub App ID", "secret": False},
            {"name": "installation_id", "label": "Installation ID", "secret": False},
            {"name": "private_key_pem", "label": "Private Key (PEM)", "secret": True},
        ],
    },
    "canva": {
        "label": "Canva",
        "description": "Create designs from briefs using Canva Connect API.",
        "keys": [
            {"name": "client_id", "label": "Client ID", "secret": False},
            {"name": "client_secret", "label": "Client Secret", "secret": True},
            {"name": "access_token", "label": "Access Token", "secret": True},
        ],
    },
    "linkedin": {
        "label": "LinkedIn",
        "description": "Post approved content directly to LinkedIn.",
        "keys": [
            {"name": "access_token", "label": "OAuth Access Token", "secret": True},
            {"name": "org_id", "label": "Organization URN (optional)", "secret": False},
        ],
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "description": "Claude models for strategy, brand voice, and long-form content.",
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "google": {
        "label": "Google AI (Gemini)",
        "description": "Gemini models for research, analysis, and content generation.",
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "figma": {
        "label": "Figma",
        "description": "Extract design tokens, export assets, and inspect layouts.",
        "keys": [
            {"name": "access_token", "label": "Personal Access Token", "secret": True},
            {"name": "team_id", "label": "Team ID (optional)", "secret": False},
        ],
    },
    "dalle": {
        "label": "DALL·E (OpenAI Images)",
        "description": "Generate marketing images and ad visuals via DALL·E 3.",
        "keys": [
            {"name": "api_key", "label": "OpenAI API Key (shared with OpenAI integration)", "secret": True},
        ],
    },
    "semrush": {
        "label": "SEMrush",
        "description": "Keyword research, SERP analysis, and competitive intelligence.",
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "mailchimp": {
        "label": "Mailchimp",
        "description": "Create and schedule email campaigns, manage audiences.",
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
            {"name": "server_prefix", "label": "Server Prefix (e.g. us21)", "secret": False},
        ],
    },
    "sendgrid": {
        "label": "SendGrid",
        "description": "Send transactional and marketing emails at scale.",
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "buffer": {
        "label": "Buffer",
        "description": "Schedule and publish social media posts across platforms.",
        "keys": [
            {"name": "access_token", "label": "Access Token", "secret": True},
        ],
    },
    "twitter": {
        "label": "Twitter / X",
        "description": "Post tweets and threads to Twitter/X.",
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
            {"name": "api_secret", "label": "API Secret", "secret": True},
            {"name": "access_token", "label": "Access Token", "secret": True},
            {"name": "access_secret", "label": "Access Token Secret", "secret": True},
        ],
    },
    "hubspot": {
        "label": "HubSpot",
        "description": "CRM integration — sync leads, create contacts, trigger workflows.",
        "keys": [
            {"name": "access_token", "label": "Private App Access Token", "secret": True},
        ],
    },
    "google_analytics": {
        "label": "Google Analytics",
        "description": "Pull traffic and conversion data for content performance tracking.",
        "keys": [
            {"name": "service_account_json", "label": "Service Account JSON", "secret": True},
            {"name": "property_id", "label": "GA4 Property ID", "secret": False},
        ],
    },
    "gemini_image": {
        "label": "Gemini Nano Banana 2 (Image Generation)",
        "description": "Generate and edit images via Google Gemini Nano Banana 2. Uses the same Google API key.",
        "keys": [
            {"name": "api_key", "label": "Google API Key (shared with Google AI integration)", "secret": True},
        ],
    },
}


def get_integration(name: str) -> dict:
    """Returns integration definition or raises KeyError."""
    return INTEGRATIONS[name]


def all_integrations() -> list[str]:
    return list(INTEGRATIONS.keys())
