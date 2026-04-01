"""
API Key Vault — encrypted credential storage.

Architecture:
  - Keys encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
  - The Fernet key itself lives in Azure Key Vault (fetched once at startup)
  - Encrypted values stored in PostgreSQL table `integration_keys`

Usage:
    from zeta_ima.integrations.vault import vault
    await vault.set("jira", "api_token", "my-secret-token")
    token = await vault.get("jira", "api_token")
"""

import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from cryptography.fernet import Fernet
from sqlalchemy import (
    Column,
    DateTime,
    LargeBinary,
    MetaData,
    String,
    Table,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()
integration_keys = Table(
    "integration_keys",
    _metadata,
    Column("id", String, primary_key=True),
    Column("integration", String, nullable=False),
    Column("key_name", String, nullable=False),
    Column("encrypted_value", LargeBinary, nullable=False),
    Column("updated_at", DateTime),
)


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """
    Return a Fernet instance.

    Production: fetches the Fernet key from Azure Key Vault (requires
    az_key_vault_url + Azure AD creds in config).

    Local dev: falls back to config.vault_key. If that is also empty,
    generates an ephemeral key (keys won't survive process restart).
    """
    if settings.az_key_vault_url:
        cred = ClientSecretCredential(
            tenant_id=settings.az_tenant_id,
            client_id=settings.az_client_id,
            client_secret=settings.az_client_secret,
        )
        client = SecretClient(vault_url=settings.az_key_vault_url, credential=cred)
        secret = client.get_secret(settings.az_key_vault_secret_name)
        return Fernet(secret.value.encode())

    # Local dev fallback
    if settings.vault_key:
        return Fernet(settings.vault_key.encode())

    # Generate ephemeral key — works for dev, but keys won't persist across restarts
    import warnings
    warnings.warn(
        "No vault_key or az_key_vault_url configured — using ephemeral Fernet key. "
        "Encrypted values will NOT survive a restart.",
        stacklevel=2,
    )
    return Fernet(Fernet.generate_key())


class _Vault:
    async def init(self) -> None:
        """Create integration_keys table if it doesn't exist."""
        async with _engine.begin() as conn:
            await conn.run_sync(_metadata.create_all)

    async def set(self, integration: str, key_name: str, value: str) -> None:
        """Encrypt and upsert a credential."""
        f = _get_fernet()
        encrypted = f.encrypt(value.encode())

        async with _Session() as session:
            stmt = pg_insert(integration_keys).values(
                id=f"{integration}:{key_name}",
                integration=integration,
                key_name=key_name,
                encrypted_value=encrypted,
                updated_at=datetime.now(timezone.utc),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={"encrypted_value": encrypted, "updated_at": datetime.now(timezone.utc)},
            )
            await session.execute(stmt)
            await session.commit()

    async def get(self, integration: str, key_name: str) -> Optional[str]:
        """Retrieve and decrypt a credential. Returns None if not found."""
        async with _Session() as session:
            result = await session.execute(
                select(integration_keys).where(
                    integration_keys.c.integration == integration,
                    integration_keys.c.key_name == key_name,
                )
            )
            row = result.fetchone()
            if row is None:
                return None
            f = _get_fernet()
            return f.decrypt(row.encrypted_value).decode()

    async def get_all(self, integration: str) -> dict[str, str]:
        """Return all decrypted keys for an integration."""
        async with _Session() as session:
            result = await session.execute(
                select(integration_keys).where(
                    integration_keys.c.integration == integration
                )
            )
            rows = result.fetchall()
            f = _get_fernet()
            return {r.key_name: f.decrypt(r.encrypted_value).decode() for r in rows}

    async def delete_integration(self, integration: str) -> None:
        """Remove all keys for an integration."""
        async with _Session() as session:
            await session.execute(
                integration_keys.delete().where(
                    integration_keys.c.integration == integration
                )
            )
            await session.commit()

    async def list_configured(self) -> list[str]:
        """Return list of integrations that have at least one key stored."""
        async with _Session() as session:
            result = await session.execute(
                select(integration_keys.c.integration).distinct()
            )
            return [r[0] for r in result.fetchall()]


vault = _Vault()
