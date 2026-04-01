"""
Microsoft Graph API — proactive Teams messaging.

Two capabilities:
  1. send_to_user(teams_user_id, card)    — DM a specific user (e.g. "share with @Alice")
  2. post_to_channel(card)                 — broadcast to the configured channel on approval

Uses Bot Framework Connector API for proactive bot messages (not Graph REST directly),
which requires storing ConversationReference when users first message the bot.

ConversationReferences are stored in PostgreSQL `conversation_refs` table.
"""

import json
from datetime import datetime, timezone
from typing import Optional

import httpx
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity
from sqlalchemy import Column, DateTime, JSON, MetaData, String, Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()
conversation_refs = Table(
    "conversation_refs",
    _metadata,
    Column("user_id", String, primary_key=True),
    Column("teams_user_id", String),
    Column("conversation_ref", JSON),
    Column("updated_at", DateTime),
)


async def init_notify_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)


async def save_conversation_ref(user_id: str, teams_user_id: str, ref: dict) -> None:
    """Store a user's ConversationReference for proactive messaging later."""
    async with _Session() as session:
        stmt = pg_insert(conversation_refs).values(
            user_id=user_id,
            teams_user_id=teams_user_id,
            conversation_ref=ref,
            updated_at=datetime.now(timezone.utc),
        ).on_conflict_do_update(
            index_elements=["user_id"],
            set_={"conversation_ref": ref, "updated_at": datetime.now(timezone.utc)},
        )
        await session.execute(stmt)
        await session.commit()


async def get_conversation_ref(user_id: str) -> Optional[dict]:
    """Retrieve stored ConversationReference for a user."""
    from sqlalchemy import select
    async with _Session() as session:
        result = await session.execute(
            select(conversation_refs).where(conversation_refs.c.user_id == user_id)
        )
        row = result.fetchone()
        return dict(row._mapping["conversation_ref"]) if row else None


async def send_proactive_card(user_id: str, card: dict) -> bool:
    """
    Send a proactive message (Adaptive Card) to a Teams user via their stored ConversationReference.
    Returns True on success.
    """
    ref = await get_conversation_ref(user_id)
    if not ref:
        return False

    adapter = BotFrameworkAdapter(
        BotFrameworkAdapterSettings(
            app_id=settings.microsoft_app_id,
            app_password=settings.microsoft_app_password,
        )
    )

    async def _send(turn_context):
        from botbuilder.core import MessageFactory
        attachment = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card,
        }
        await turn_context.send_activity(MessageFactory.attachment(attachment))

    try:
        from botbuilder.schema import ConversationReference
        conv_ref = ConversationReference().deserialize(ref)
        await adapter.continue_conversation(conv_ref, _send, settings.microsoft_app_id)
        return True
    except Exception as e:
        print(f"[notify] Proactive message failed: {e}")
        return False


async def post_to_channel(card: dict) -> bool:
    """
    Post an Adaptive Card to the configured broadcast channel via Microsoft Graph API.
    Requires az_tenant_id, az_client_id, az_client_secret, teams_team_id, teams_broadcast_channel_id.
    """
    if not all([settings.az_tenant_id, settings.az_client_id, settings.teams_team_id, settings.teams_broadcast_channel_id]):
        return False

    # Get Graph API token via client credentials
    token = await _get_graph_token()
    if not token:
        return False

    # Post message with Adaptive Card attachment
    payload = {
        "body": {"contentType": "html", "content": "<attachment id=\"1\"></attachment>"},
        "attachments": [{
            "id": "1",
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": json.dumps(card),
        }],
    }

    url = (
        f"https://graph.microsoft.com/v1.0/teams/{settings.teams_team_id}"
        f"/channels/{settings.teams_broadcast_channel_id}/messages"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
    return r.is_success


async def _get_graph_token() -> Optional[str]:
    """Fetch a client-credentials access token for Microsoft Graph."""
    url = f"https://login.microsoftonline.com/{settings.az_tenant_id}/oauth2/v2.0/token"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, data={
            "grant_type": "client_credentials",
            "client_id": settings.az_client_id,
            "client_secret": settings.az_client_secret,
            "scope": "https://graph.microsoft.com/.default",
        })
    if r.is_success:
        return r.json().get("access_token")
    return None
