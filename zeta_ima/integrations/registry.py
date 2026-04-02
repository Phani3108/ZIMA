"""
Integration registry — defines all supported external tools and their required keys.

Used by the settings UI to show which integrations are configured and which need setup.
Each integration includes provisioning URL and setup steps for non-technical users.
"""

INTEGRATIONS: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "category": "llm",
        "description": "Used for copy generation and review agents.",
        "required": False,
        "setup_url": "https://platform.openai.com/api-keys",
        "setup_steps": [
            "Go to platform.openai.com and sign in (or create an account).",
            "Navigate to API Keys in the left sidebar.",
            "Click 'Create new secret key', give it a name, and copy the key.",
            "Paste the key below and click Save.",
        ],
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "category": "llm",
        "description": "Claude models for strategy, brand voice, and long-form content.",
        "required": False,
        "setup_url": "https://console.anthropic.com/settings/keys",
        "setup_steps": [
            "Go to console.anthropic.com and sign in.",
            "Navigate to Settings → API Keys.",
            "Click 'Create Key', name it, and copy the value.",
            "Paste the key below and click Save.",
        ],
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "google": {
        "label": "Google AI (Gemini)",
        "category": "llm",
        "description": "Gemini models for research, analysis, and content generation.",
        "required": False,
        "setup_url": "https://aistudio.google.com/apikey",
        "setup_steps": [
            "Go to aistudio.google.com and sign in with your Google account.",
            "Click 'Get API Key' → 'Create API Key'.",
            "Select or create a Google Cloud project.",
            "Copy the generated key and paste it below.",
        ],
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "jira": {
        "label": "Jira",
        "category": "devops",
        "description": "Create tickets, search issues, auto-escalate stuck workflows.",
        "required": False,
        "setup_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
        "setup_steps": [
            "Go to id.atlassian.com → Security → API tokens.",
            "Click 'Create API token', give it a label.",
            "Copy the token. Your Base URL is https://yourcompany.atlassian.net.",
            "Enter all three fields below (URL, email, token) and click Save.",
        ],
        "keys": [
            {"name": "base_url", "label": "Jira Base URL (e.g. https://yourco.atlassian.net)", "secret": False},
            {"name": "email", "label": "Account Email", "secret": False},
            {"name": "api_token", "label": "API Token", "secret": True},
        ],
    },
    "confluence": {
        "label": "Confluence",
        "category": "devops",
        "description": "Read and publish Confluence pages.",
        "required": False,
        "setup_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
        "setup_steps": [
            "Uses the same Atlassian API token as Jira.",
            "Go to id.atlassian.com → Security → API tokens (or reuse the Jira token).",
            "Your Space Key is in the Confluence URL: /wiki/spaces/SPACEKEY/...",
            "Enter all four fields below and click Save.",
        ],
        "keys": [
            {"name": "base_url", "label": "Confluence Base URL", "secret": False},
            {"name": "email", "label": "Account Email", "secret": False},
            {"name": "api_token", "label": "API Token", "secret": True},
            {"name": "space_key", "label": "Default Space Key", "secret": False},
        ],
    },
    "github": {
        "label": "GitHub",
        "category": "devops",
        "description": "Create PRs, read files, set commit statuses.",
        "required": False,
        "setup_url": "https://github.com/settings/apps",
        "setup_steps": [
            "Go to github.com → Settings → Developer settings → GitHub Apps.",
            "Click 'New GitHub App', fill in the name and permissions.",
            "After creation, note the App ID on the app page.",
            "Generate a private key (PEM file) — open it in a text editor and copy the contents.",
            "Install the app on your repository and note the Installation ID from the URL.",
        ],
        "keys": [
            {"name": "app_id", "label": "GitHub App ID", "secret": False},
            {"name": "installation_id", "label": "Installation ID", "secret": False},
            {"name": "private_key_pem", "label": "Private Key (PEM)", "secret": True},
        ],
    },
    "canva": {
        "label": "Canva",
        "category": "creative",
        "description": "Create designs from briefs using Canva Connect API.",
        "required": False,
        "setup_url": "https://www.canva.com/developers/",
        "setup_steps": [
            "Go to canva.com/developers and sign in.",
            "Create an Integration (app) to get your Client ID and Secret.",
            "Generate an Access Token via the OAuth flow or the developer portal.",
            "Paste all three values below.",
        ],
        "keys": [
            {"name": "client_id", "label": "Client ID", "secret": False},
            {"name": "client_secret", "label": "Client Secret", "secret": True},
            {"name": "access_token", "label": "Access Token", "secret": True},
        ],
    },
    "linkedin": {
        "label": "LinkedIn",
        "category": "publishing",
        "description": "Post approved content directly to LinkedIn.",
        "required": False,
        "setup_url": "https://www.linkedin.com/developers/apps",
        "setup_steps": [
            "Go to linkedin.com/developers/apps and create an app.",
            "Under Auth, request the 'w_member_social' and 'r_liteprofile' scopes.",
            "Generate an OAuth2 access token (valid 60 days, refresh as needed).",
            "Optionally, find your Organization URN in the LinkedIn admin.",
        ],
        "keys": [
            {"name": "access_token", "label": "OAuth Access Token", "secret": True},
            {"name": "org_id", "label": "Organization URN (optional)", "secret": False},
        ],
    },
    "figma": {
        "label": "Figma",
        "category": "creative",
        "description": "Extract design tokens, export assets, and inspect layouts.",
        "required": False,
        "setup_url": "https://www.figma.com/developers/api#access-tokens",
        "setup_steps": [
            "Go to figma.com → Account Settings → Personal Access Tokens.",
            "Click 'Create a new personal access token'.",
            "Copy the token and paste it below.",
            "Team ID is optional — find it in the URL: figma.com/files/team/TEAM_ID.",
        ],
        "keys": [
            {"name": "access_token", "label": "Personal Access Token", "secret": True},
            {"name": "team_id", "label": "Team ID (optional)", "secret": False},
        ],
    },
    "dalle": {
        "label": "DALL·E (OpenAI Images)",
        "category": "creative",
        "description": "Generate marketing images and ad visuals via DALL·E 3.",
        "required": False,
        "setup_url": "https://platform.openai.com/api-keys",
        "setup_steps": [
            "Uses the same OpenAI API Key.",
            "If you've already configured OpenAI above, this will work automatically.",
            "Otherwise, get a key from platform.openai.com → API Keys.",
        ],
        "keys": [
            {"name": "api_key", "label": "OpenAI API Key (shared with OpenAI integration)", "secret": True},
        ],
    },
    "gemini_image": {
        "label": "Gemini Image (Nano Banana 2)",
        "category": "creative",
        "description": "Generate and edit images via Google Gemini Nano Banana 2.",
        "required": False,
        "setup_url": "https://aistudio.google.com/apikey",
        "setup_steps": [
            "Uses the same Google AI API Key.",
            "If you've already configured Google AI above, this will work automatically.",
            "Otherwise, get a key from aistudio.google.com.",
        ],
        "keys": [
            {"name": "api_key", "label": "Google API Key (shared with Google AI integration)", "secret": True},
        ],
    },
    "semrush": {
        "label": "SEMrush",
        "category": "seo",
        "description": "Keyword research, SERP analysis, and competitive intelligence.",
        "required": False,
        "setup_url": "https://www.semrush.com/user/settings/apikey",
        "setup_steps": [
            "Go to semrush.com and sign in.",
            "Navigate to Account Settings → API Key.",
            "Copy your API key and paste it below.",
            "Note: SEMrush API requires a paid plan.",
        ],
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "mailchimp": {
        "label": "Mailchimp",
        "category": "email",
        "description": "Create and schedule email campaigns, manage audiences.",
        "required": False,
        "setup_url": "https://mailchimp.com/account/api/",
        "setup_steps": [
            "Go to mailchimp.com → Account → Extras → API Keys.",
            "Click 'Create A Key' and copy it.",
            "Your server prefix is the part after the dash in your API key (e.g., 'us21').",
            "Enter both values below.",
        ],
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
            {"name": "server_prefix", "label": "Server Prefix (e.g. us21)", "secret": False},
        ],
    },
    "sendgrid": {
        "label": "SendGrid",
        "category": "email",
        "description": "Send transactional and marketing emails at scale.",
        "required": False,
        "setup_url": "https://app.sendgrid.com/settings/api_keys",
        "setup_steps": [
            "Go to app.sendgrid.com → Settings → API Keys.",
            "Click 'Create API Key' and choose 'Full Access' or custom permissions.",
            "Copy the key (it's only shown once) and paste it below.",
        ],
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
        ],
    },
    "buffer": {
        "label": "Buffer",
        "category": "publishing",
        "description": "Schedule and publish social media posts across platforms.",
        "required": False,
        "setup_url": "https://buffer.com/developers/api",
        "setup_steps": [
            "Go to buffer.com → Settings → Apps & Extras.",
            "Create an app or use a personal access token.",
            "Copy the access token and paste it below.",
        ],
        "keys": [
            {"name": "access_token", "label": "Access Token", "secret": True},
        ],
    },
    "twitter": {
        "label": "Twitter / X",
        "category": "publishing",
        "description": "Post tweets and threads to Twitter/X.",
        "required": False,
        "setup_url": "https://developer.twitter.com/en/portal/dashboard",
        "setup_steps": [
            "Go to developer.twitter.com and sign in.",
            "Create a project and app under the Developer Portal.",
            "Under Keys and Tokens, generate all four values below.",
            "Ensure the app has 'Read and Write' permissions.",
        ],
        "keys": [
            {"name": "api_key", "label": "API Key", "secret": True},
            {"name": "api_secret", "label": "API Secret", "secret": True},
            {"name": "access_token", "label": "Access Token", "secret": True},
            {"name": "access_secret", "label": "Access Token Secret", "secret": True},
        ],
    },
    "hubspot": {
        "label": "HubSpot",
        "category": "crm",
        "description": "CRM integration — sync leads, create contacts, trigger workflows.",
        "required": False,
        "setup_url": "https://app.hubspot.com/private-apps",
        "setup_steps": [
            "Go to HubSpot → Settings → Integrations → Private Apps.",
            "Click 'Create a private app'.",
            "Set the required scopes (contacts, deals, etc.).",
            "Copy the access token and paste it below.",
        ],
        "keys": [
            {"name": "access_token", "label": "Private App Access Token", "secret": True},
        ],
    },
    "google_analytics": {
        "label": "Google Analytics",
        "category": "analytics",
        "description": "Pull traffic and conversion data for content performance tracking.",
        "required": False,
        "setup_url": "https://console.cloud.google.com/apis/credentials",
        "setup_steps": [
            "Go to Google Cloud Console → IAM → Service Accounts.",
            "Create a service account and download the JSON key file.",
            "In GA4, go to Admin → Property → Property Access Management and add the service account email.",
            "Paste the entire JSON key contents below, and enter your GA4 Property ID.",
        ],
        "keys": [
            {"name": "service_account_json", "label": "Service Account JSON", "secret": True},
            {"name": "property_id", "label": "GA4 Property ID", "secret": False},
        ],
    },
}


# ── Category metadata for frontend grouping ──────────────────────────

CATEGORIES = {
    "llm":        {"label": "AI Models", "icon": "brain", "order": 0},
    "creative":   {"label": "Creative Tools", "icon": "palette", "order": 1},
    "publishing": {"label": "Publishing & Social", "icon": "share2", "order": 2},
    "email":      {"label": "Email Marketing", "icon": "mail", "order": 3},
    "seo":        {"label": "SEO & Research", "icon": "search", "order": 4},
    "devops":     {"label": "DevOps & Collaboration", "icon": "gitBranch", "order": 5},
    "crm":        {"label": "CRM", "icon": "users", "order": 6},
    "analytics":  {"label": "Analytics", "icon": "barChart", "order": 7},
}


# ── Infrastructure services (env-var-based, not vault) ───────────────

INFRA_SERVICES = {
    "azure_openai": {
        "label": "Azure OpenAI",
        "category": "azure",
        "description": "Production LLM endpoint (preferred over vanilla OpenAI).",
        "env_vars": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"],
        "setup_url": "https://portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI",
        "setup_steps": [
            "Go to Azure Portal → Create Resource → Azure OpenAI.",
            "Create a resource and deploy models (gpt-4o, gpt-4o-mini, text-embedding-3-small).",
            "Go to Keys and Endpoint under your resource.",
            "Copy the endpoint and one of the keys.",
        ],
    },
    "teams_bot": {
        "label": "Microsoft Teams Bot",
        "category": "microsoft",
        "description": "Teams integration for chat, approvals, and proactive messaging.",
        "env_vars": ["MICROSOFT_APP_ID", "MICROSOFT_APP_PASSWORD"],
        "setup_url": "https://dev.teams.microsoft.com/apps",
        "setup_steps": [
            "Go to Azure Portal → Create Resource → Azure Bot.",
            "Set pricing tier to F0 (free) for dev.",
            "After creation, go to Configuration → copy Microsoft App ID.",
            "Click 'Manage Password' → New client secret → copy value.",
            "Set Messaging endpoint to https://yourdomain.com/api/messages.",
            "Go to Channels → Add Microsoft Teams channel.",
        ],
    },
    "postgresql": {
        "label": "PostgreSQL",
        "category": "infrastructure",
        "description": "Primary database for workflows, campaigns, audit logs, and vault.",
        "env_vars": ["DATABASE_URL"],
        "setup_url": "",
        "setup_steps": [
            "For local dev: docker compose up -d (port 5433).",
            "For production: Use Azure Database for PostgreSQL or any managed PostgreSQL.",
            "Set DATABASE_URL to postgresql://user:pass@host:5432/zeta_ima.",
        ],
    },
    "redis": {
        "label": "Redis",
        "category": "infrastructure",
        "description": "Session state, rate limiting, notifications, and task queues.",
        "env_vars": ["REDIS_URL"],
        "setup_url": "",
        "setup_steps": [
            "For local dev: docker compose up -d (port 6379).",
            "For production: Use Azure Cache for Redis or any managed Redis.",
            "Set REDIS_URL to redis://host:6379.",
        ],
    },
    "qdrant": {
        "label": "Qdrant (Vector DB)",
        "category": "infrastructure",
        "description": "Vector database for brand voice, knowledge base, and learning memory.",
        "env_vars": ["QDRANT_URL"],
        "setup_url": "https://cloud.qdrant.io/",
        "setup_steps": [
            "For local dev: docker compose up -d (port 6333).",
            "For production: Use Qdrant Cloud or self-hosted.",
            "Set QDRANT_URL to http://host:6333.",
            "Or switch to Azure AI Search by setting VECTOR_BACKEND=azure_ai_search.",
        ],
    },
    "azure_blob": {
        "label": "Azure Blob Storage",
        "category": "azure",
        "description": "File storage for conversation archives and document ingestion.",
        "env_vars": ["AZURE_STORAGE_CONNECTION_STRING"],
        "setup_url": "https://portal.azure.com/#create/Microsoft.StorageAccount",
        "setup_steps": [
            "Go to Azure Portal → Create Resource → Storage Account.",
            "After creation, go to Access keys → copy the Connection string.",
            "Paste it as AZURE_STORAGE_CONNECTION_STRING in your environment.",
            "Optional: not required for local dev (falls back to local filesystem).",
        ],
    },
    "azure_ai_search": {
        "label": "Azure AI Search",
        "category": "azure",
        "description": "Production vector search backend (alternative to Qdrant).",
        "env_vars": ["AZURE_AI_SEARCH_ENDPOINT", "AZURE_AI_SEARCH_KEY"],
        "setup_url": "https://portal.azure.com/#create/Microsoft.Search",
        "setup_steps": [
            "Go to Azure Portal → Create Resource → Azure AI Search.",
            "After creation, go to Keys → copy the admin key and endpoint.",
            "Set VECTOR_BACKEND=azure_ai_search to activate.",
        ],
    },
    "azure_cosmos": {
        "label": "Azure Cosmos DB",
        "category": "azure",
        "description": "Production learning document store (alternative to PostgreSQL learning tables).",
        "env_vars": ["AZURE_COSMOS_ENDPOINT", "AZURE_COSMOS_KEY"],
        "setup_url": "https://portal.azure.com/#create/Microsoft.DocumentDB",
        "setup_steps": [
            "Go to Azure Portal → Create Resource → Azure Cosmos DB (NoSQL).",
            "After creation, go to Keys → copy the URI and Primary Key.",
            "Set LEARNING_STORE=cosmos to activate.",
        ],
    },
    "azure_keyvault": {
        "label": "Azure Key Vault",
        "category": "azure",
        "description": "Stores the encryption key for the credential vault.",
        "env_vars": ["AZ_KEY_VAULT_URL", "AZ_TENANT_ID", "AZ_CLIENT_ID", "AZ_CLIENT_SECRET"],
        "setup_url": "https://portal.azure.com/#create/Microsoft.KeyVault",
        "setup_steps": [
            "Go to Azure Portal → Create Resource → Key Vault.",
            "After creation, go to Secrets → Generate/Import → create a secret with a Fernet key.",
            "Register an App in Azure AD → create a client secret.",
            "Grant the app 'Key Vault Secrets User' role on the vault.",
            "Set AZ_KEY_VAULT_URL, AZ_TENANT_ID, AZ_CLIENT_ID, AZ_CLIENT_SECRET.",
            "Optional: for local dev, set VAULT_KEY to a local Fernet key instead.",
        ],
    },
}


def get_integration(name: str) -> dict:
    """Returns integration definition or raises KeyError."""
    return INTEGRATIONS[name]


def all_integrations() -> list[str]:
    return list(INTEGRATIONS.keys())
