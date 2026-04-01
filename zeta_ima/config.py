from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Runtime mode
    mode: str = "dev"               # "dev" | "prod"

    # ── Azure OpenAI (primary) ──────────────────────────────────────────────
    azure_openai_endpoint: str = ""       # e.g. https://my-resource.openai.azure.com/
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    # Deployment names (mapped from model names in Azure OpenAI Studio)
    azure_openai_deploy_gpt4o: str = "gpt-4o"
    azure_openai_deploy_gpt4o_mini: str = "gpt-4o-mini"
    azure_openai_deploy_embedding: str = "text-embedding-3-small"

    # ── Fallback: vanilla OpenAI (used when azure_openai_endpoint is empty) ─
    openai_api_key: str = ""

    # Model aliases (used throughout the codebase)
    llm_copy: str = "gpt-4o"
    llm_review: str = "gpt-4o-mini"
    llm_router: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

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

    # Meeting settings
    meeting_skip_word_threshold: int = 20  # Skip scrum meeting for briefs under this word count

    # Redis (session checkpointer)
    redis_url: str = "redis://localhost:6379"
    session_ttl_hours: int = 48

    # Qdrant (brand memory + knowledge base)
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "brand_voice"
    qdrant_kb_collection: str = "knowledge_base"
    brand_context_top_k: int = 5
    kb_context_top_k: int = 5

    # ── Azure Blob Storage ──────────────────────────────────────────────────
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "zeta-ima-files"

    # ── Azure AI Search (vector backend alternative to Qdrant) ──────────────
    azure_ai_search_endpoint: str = ""       # e.g. https://my-search.search.windows.net
    azure_ai_search_key: str = ""
    azure_ai_search_index_prefix: str = "zeta"  # indexes: zeta-brand_voice, zeta-knowledge_base, etc.

    # ── Azure Cosmos DB (learning store alternative to PostgreSQL) ───────────
    azure_cosmos_endpoint: str = ""          # e.g. https://my-cosmos.documents.azure.com:443/
    azure_cosmos_key: str = ""
    azure_cosmos_database: str = "zeta_ima_learning"

    # ── Backend toggles ─────────────────────────────────────────────────────
    vector_backend: str = "qdrant"           # "qdrant" | "azure_ai_search"
    learning_store: str = "postgres"         # "postgres" | "cosmos"

    # PostgreSQL (campaigns, audit)
    database_url: str = "postgresql://zeta:zeta_dev@localhost:5433/zeta_ima"

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

    # Confidence-gated auto-approval thresholds
    auto_approve_min_score: int = 8       # All rubric scores must be >= this
    auto_approve_brand_fit: int = 9       # brand_fit specifically must be >= this
    auto_approve_enabled: bool = False    # Off by default; enable per campaign

    # Local dev vault key — used when az_key_vault_url is empty.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    vault_key: str = ""

    @property
    def use_azure_openai(self) -> bool:
        """True when Azure OpenAI is configured (has endpoint + key)."""
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


# ── LLM client factories ───────────────────────────────────────────────────
# Centralised helpers so every node uses the correct client (Azure or vanilla).

def get_openai_client():
    """Return an AsyncOpenAI or AsyncAzureOpenAI client based on config."""
    if settings.use_azure_openai:
        from openai import AsyncAzureOpenAI
        return AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=settings.openai_api_key)


def get_embedding_client():
    """Return an AsyncOpenAI or AsyncAzureOpenAI client for embeddings."""
    # Same client, but callers may want a separate reference
    return get_openai_client()
