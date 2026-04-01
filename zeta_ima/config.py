from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Runtime mode
    mode: str = "dev"               # "dev" | "prod"

    # LLM
    openai_api_key: str = ""
    llm_copy: str = "gpt-4o"
    llm_review: str = "gpt-4o-mini"
    llm_router: str = "gpt-4o-mini"

    # Image generation
    gemini_image_model: str = "gemini-3.1-flash-image-preview"
    image_default_aspect_ratio: str = "1:1"
    image_default_resolution: str = "1K"
    image_provider_chain: str = "gemini,openai"  # comma-separated fallback chain

    # Learning & distillation
    signal_extraction_model: str = "gpt-4o-mini"
    distill_timeout_minutes: int = 30  # auto-distill after this inactivity
    brain_compact_hour: int = 2  # UTC hour for daily brain compaction

    # Orchestrator
    task_dispatch_interval_seconds: int = 5

    # Redis (session checkpointer)
    redis_url: str = "redis://localhost:6379"
    session_ttl_hours: int = 48

    # Qdrant (brand memory + knowledge base)
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "brand_voice"
    qdrant_kb_collection: str = "knowledge_base"
    brand_context_top_k: int = 5
    kb_context_top_k: int = 5

    # PostgreSQL (campaigns, audit)
    database_url: str = "postgresql://zeta:zeta_dev@localhost:5432/zeta_ima"

    # Teams Bot
    microsoft_app_id: str = ""
    microsoft_app_password: str = ""

    # Microsoft Azure (Graph API proactive messaging + Azure Key Vault)
    az_tenant_id: str = ""
    az_client_id: str = ""
    az_client_secret: str = ""
    az_key_vault_url: str = ""          # e.g. https://zeta-ima-kv.vault.azure.net/
    az_key_vault_secret_name: str = "zeta-vault-key"

    # Teams broadcast channel (auto-post approved outputs)
    teams_broadcast_channel_id: str = ""   # 19:abc@thread.tacv2
    teams_team_id: str = ""

    # Auth
    jwt_secret: str = "dev-secret-change-me-in-prod"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Local dev vault key — used when az_key_vault_url is empty.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    vault_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
