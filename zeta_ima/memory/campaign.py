"""
PostgreSQL-backed campaign and audit log management.

Campaigns sit above sessions — one campaign can span multiple Teams conversations
(sessions) across multiple days. When a new session starts, we load the active
campaign so the bot can greet the user with context: "Picking up from last time —
you were working on the Series A campaign."

Schema:
  campaigns          — one row per campaign (user_id, name, status)
  approved_outputs   — audit trail of every approved copy output
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

# Build async DB URL (swap psycopg2 → asyncpg for async support)
_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
engine: AsyncEngine = create_async_engine(_async_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

metadata = MetaData()

campaigns = Table(
    "campaigns",
    metadata,
    Column("id", String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("user_id", String, nullable=False),
    Column("name", String, nullable=False),
    Column("status", String, nullable=False, default="active"),  # active | paused | complete
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    Column("updated_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)

approved_outputs = Table(
    "approved_outputs",
    metadata,
    Column("id", String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("campaign_id", String, ForeignKey("campaigns.id"), nullable=True),
    Column("user_id", String, nullable=False),
    Column("brief", Text, nullable=False),
    Column("text", Text, nullable=False),
    Column("channel", String, nullable=True),       # e.g. "linkedin", "email"
    Column("iterations_needed", Integer, default=1),
    Column("qdrant_id", String, nullable=True),     # Link to Qdrant point ID
    Column("approved_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)


async def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def load_active_campaign(user_id: str) -> Optional[dict]:
    """Return the user's active campaign, or None if they don't have one."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(campaigns).where(
                campaigns.c.user_id == user_id,
                campaigns.c.status == "active",
            )
        )
        row = result.fetchone()
        if row is None:
            return None
        return dict(row._mapping)


async def create_campaign(user_id: str, name: str) -> dict:
    """Create a new campaign for this user and return it."""
    async with AsyncSessionLocal() as session:
        campaign_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        await session.execute(
            campaigns.insert().values(
                id=campaign_id,
                user_id=user_id,
                name=name,
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
        return {"id": campaign_id, "user_id": user_id, "name": name, "status": "active"}


async def log_approved_output(metadata: dict) -> str:
    """Insert a row into approved_outputs for audit trail."""
    async with AsyncSessionLocal() as session:
        output_id = metadata.get("output_id") or str(uuid.uuid4())
        await session.execute(
            approved_outputs.insert().values(
                id=output_id,
                campaign_id=metadata.get("campaign_id"),
                user_id=metadata["user_id"],
                brief=metadata["brief"],
                text=metadata["text"],
                channel=metadata.get("channel"),
                iterations_needed=metadata.get("iterations_needed", 1),
                qdrant_id=metadata.get("qdrant_id"),
                approved_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
        return output_id
