"""
Team Collaboration — multi-user teams with roles and shared workspaces.

Teams group users with assigned roles. Resources (workflows, campaigns,
experiments) can be scoped to a team, enabling shared visibility.

Roles: admin, manager, strategist, copywriter, designer, member
  - admin: full access, can manage team membership
  - manager: can manage workflows and approve
  - strategist/copywriter/designer: specific skill domains
  - member: basic access
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    select,
    update,
    delete,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

log = logging.getLogger(__name__)

VALID_ROLES = {"admin", "manager", "strategist", "copywriter", "designer", "member"}

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

teams = Table(
    "teams",
    _metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("description", Text, default=""),
    Column("created_by", String, nullable=False),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)

team_members = Table(
    "team_members",
    _metadata,
    Column("id", String, primary_key=True),
    Column("team_id", String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", String, nullable=False),
    Column("role", String, nullable=False, default="member"),
    Column("display_name", String, default=""),
    Column("email", String, default=""),
    Column("joined_at", DateTime),
    UniqueConstraint("team_id", "user_id", name="uq_team_user"),
)

team_approval_routing = Table(
    "team_approval_routing",
    _metadata,
    Column("id", String, primary_key=True),
    Column("team_id", String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
    Column("agent_type", String, nullable=False),
    Column("approver_user_id", String, nullable=False),
    Column("approver_display_name", String, default=""),
    Column("approver_email", String, default=""),
    Column("fallback_approver_user_id", String, default=""),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
    UniqueConstraint("team_id", "agent_type", name="uq_team_agent_approval"),
)


async def init_teams_db() -> None:
    """Create team tables."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("Teams DB initialized")


class TeamsService:
    """Manages teams and membership."""

    # ── Team CRUD ─────────────────────────────────────────────────────────

    async def create_team(
        self,
        name: str,
        created_by: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new team. Creator is auto-added as admin."""
        now = datetime.now(timezone.utc)
        team_id = str(uuid.uuid4())

        async with _Session() as session:
            await session.execute(
                teams.insert().values(
                    id=team_id,
                    name=name,
                    description=description,
                    created_by=created_by,
                    created_at=now,
                    updated_at=now,
                )
            )
            # Add creator as admin
            await session.execute(
                team_members.insert().values(
                    id=str(uuid.uuid4()),
                    team_id=team_id,
                    user_id=created_by,
                    role="admin",
                    joined_at=now,
                )
            )
            await session.commit()

        log.info("Team %s created by %s", name, created_by)
        return {"id": team_id, "name": name, "description": description}

    async def list_teams(self, user_id: str | None = None) -> list[dict]:
        """List teams. If user_id given, only teams the user belongs to."""
        if user_id:
            stmt = (
                select(teams)
                .join(team_members, teams.c.id == team_members.c.team_id)
                .where(team_members.c.user_id == user_id)
                .order_by(teams.c.name)
            )
        else:
            stmt = select(teams).order_by(teams.c.name)
        async with _Session() as session:
            result = await session.execute(stmt)
            return [dict(r._mapping) for r in result.fetchall()]

    async def get_team(self, team_id: str) -> dict | None:
        async with _Session() as session:
            result = await session.execute(
                select(teams).where(teams.c.id == team_id)
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def update_team(self, team_id: str, **kwargs: Any) -> dict | None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        async with _Session() as session:
            await session.execute(
                update(teams).where(teams.c.id == team_id).values(**kwargs)
            )
            await session.commit()
        return await self.get_team(team_id)

    async def delete_team(self, team_id: str) -> bool:
        async with _Session() as session:
            result = await session.execute(
                delete(teams).where(teams.c.id == team_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ── Membership ────────────────────────────────────────────────────────

    async def add_member(
        self,
        team_id: str,
        user_id: str,
        role: str = "member",
        display_name: str = "",
        email: str = "",
    ) -> dict[str, Any]:
        """Add a user to a team with a specified role."""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

        member_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        async with _Session() as session:
            await session.execute(
                team_members.insert().values(
                    id=member_id,
                    team_id=team_id,
                    user_id=user_id,
                    role=role,
                    display_name=display_name,
                    email=email,
                    joined_at=now,
                )
            )
            await session.commit()

        log.info("User %s added to team %s as %s", user_id, team_id, role)
        return {"id": member_id, "team_id": team_id, "user_id": user_id, "role": role}

    async def remove_member(self, team_id: str, user_id: str) -> bool:
        async with _Session() as session:
            result = await session.execute(
                delete(team_members).where(
                    team_members.c.team_id == team_id,
                    team_members.c.user_id == user_id,
                )
            )
            await session.commit()
            return result.rowcount > 0

    async def update_member_role(
        self,
        team_id: str,
        user_id: str,
        new_role: str,
    ) -> bool:
        if new_role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {new_role}")
        async with _Session() as session:
            result = await session.execute(
                update(team_members)
                .where(
                    team_members.c.team_id == team_id,
                    team_members.c.user_id == user_id,
                )
                .values(role=new_role)
            )
            await session.commit()
            return result.rowcount > 0

    async def list_members(self, team_id: str) -> list[dict]:
        async with _Session() as session:
            result = await session.execute(
                select(team_members)
                .where(team_members.c.team_id == team_id)
                .order_by(team_members.c.role, team_members.c.display_name)
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def get_user_membership(self, user_id: str) -> dict | None:
        """Get the user's primary team membership (first team found)."""
        async with _Session() as session:
            result = await session.execute(
                select(team_members)
                .where(team_members.c.user_id == user_id)
                .limit(1)
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def get_user_teams(self, user_id: str) -> list[dict]:
        """Get all team memberships for a user."""
        async with _Session() as session:
            result = await session.execute(
                select(team_members, teams.c.name.label("team_name"))
                .join(teams, teams.c.id == team_members.c.team_id)
                .where(team_members.c.user_id == user_id)
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def is_team_admin(self, team_id: str, user_id: str) -> bool:
        """Check if user is admin of the given team."""
        async with _Session() as session:
            result = await session.execute(
                select(team_members.c.role)
                .where(
                    team_members.c.team_id == team_id,
                    team_members.c.user_id == user_id,
                )
            )
            row = result.fetchone()
            return row is not None and row.role in ("admin", "manager")

    # ── Approval Routing (Future) ─────────────────────────────────────

    async def set_approval_routing(
        self,
        team_id: str,
        agent_type: str,
        approver_user_id: str,
        approver_display_name: str = "",
        approver_email: str = "",
        fallback_approver_user_id: str | None = None,
    ) -> dict:
        """Set or update the approval routing for a team + agent type."""
        now = datetime.now(timezone.utc)
        async with _Session() as session:
            # Upsert: delete existing, then insert
            await session.execute(
                delete(team_approval_routing).where(
                    team_approval_routing.c.team_id == team_id,
                    team_approval_routing.c.agent_type == agent_type,
                )
            )
            row_id = str(uuid.uuid4())
            await session.execute(
                team_approval_routing.insert().values(
                    id=row_id,
                    team_id=team_id,
                    agent_type=agent_type,
                    approver_user_id=approver_user_id,
                    approver_display_name=approver_display_name,
                    approver_email=approver_email,
                    fallback_approver_user_id=fallback_approver_user_id or "",
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()
        return {
            "team_id": team_id,
            "agent_type": agent_type,
            "approver_user_id": approver_user_id,
            "approver_display_name": approver_display_name,
        }

    async def get_approver(self, team_id: str, agent_type: str) -> dict | None:
        """Get the configured approver for a team + agent type."""
        async with _Session() as session:
            result = await session.execute(
                select(team_approval_routing).where(
                    team_approval_routing.c.team_id == team_id,
                    team_approval_routing.c.agent_type == agent_type,
                )
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def list_approval_routing(self, team_id: str) -> list[dict]:
        """List all approval routing rules for a team."""
        async with _Session() as session:
            result = await session.execute(
                select(team_approval_routing)
                .where(team_approval_routing.c.team_id == team_id)
                .order_by(team_approval_routing.c.agent_type)
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def delete_approval_routing(self, team_id: str, agent_type: str) -> bool:
        """Remove approval routing for a team + agent type."""
        async with _Session() as session:
            result = await session.execute(
                delete(team_approval_routing).where(
                    team_approval_routing.c.team_id == team_id,
                    team_approval_routing.c.agent_type == agent_type,
                )
            )
            await session.commit()
            return result.rowcount > 0


teams_service = TeamsService()
