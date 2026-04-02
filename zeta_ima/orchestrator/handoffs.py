"""
Cross-Team Handoffs — publish/subscribe triggers between teams.

When a workflow stage is approved in one team, a handoff rule can automatically
trigger a new workflow in another team, pass context, and notify the receiving team.

Usage:
    from zeta_ima.orchestrator.handoffs import handoff_engine, init_handoffs_db

    await init_handoffs_db()
    rule_id = await handoff_engine.create_rule(
        source_team_id="t1",
        trigger_skill_id="seo_brief",
        trigger_event="stage_approved",
        target_team_id="t2",
        target_template_id="blog_post",
        variable_mapping={"brief": "{{output}}"},
    )
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    select,
    update,
    delete,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

log = logging.getLogger(__name__)

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

# ── Tables ────────────────────────────────────────────────────────────────────

handoff_rules_table = Table(
    "handoff_rules",
    _metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("source_team_id", String, nullable=False),
    Column("trigger_skill_id", String, nullable=True),  # null = any skill
    Column("trigger_event", String, nullable=False),      # stage_approved, workflow_completed
    Column("target_team_id", String, nullable=False),
    Column("target_template_id", String, nullable=False),
    Column("variable_mapping", JSONB, default={}),  # {"brief": "{{output}}", "brand": "{{brand_name}}"}
    Column("auto_start", Boolean, default=True),
    Column("enabled", Boolean, default=True),
    Column("created_by", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

handoff_log_table = Table(
    "handoff_log",
    _metadata,
    Column("id", String, primary_key=True),
    Column("rule_id", String, nullable=False),
    Column("source_workflow_id", String, nullable=False),
    Column("source_stage_id", String, nullable=True),
    Column("target_workflow_id", String, nullable=True),
    Column("status", String, nullable=False),  # triggered, created, failed
    Column("error", Text, nullable=True),
    Column("context_snapshot", JSONB, default={}),
    Column("created_at", DateTime, nullable=False),
)


async def init_handoffs_db() -> None:
    """Create handoff tables. Idempotent."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("Handoffs DB initialized")


# ── Handoff Engine ────────────────────────────────────────────────────────────


class HandoffEngine:

    async def create_rule(
        self,
        name: str,
        source_team_id: str,
        trigger_event: str,
        target_team_id: str,
        target_template_id: str,
        created_by: str,
        trigger_skill_id: str | None = None,
        variable_mapping: dict | None = None,
        auto_start: bool = True,
    ) -> str:
        """Create a cross-team handoff rule. Returns rule ID."""
        rid = f"hnd-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        async with _Session() as s:
            await s.execute(handoff_rules_table.insert().values(
                id=rid,
                name=name,
                source_team_id=source_team_id,
                trigger_skill_id=trigger_skill_id,
                trigger_event=trigger_event,
                target_team_id=target_team_id,
                target_template_id=target_template_id,
                variable_mapping=variable_mapping or {},
                auto_start=auto_start,
                enabled=True,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            ))
            await s.commit()
        log.info("Created handoff rule %s: %s → %s", rid, source_team_id, target_team_id)
        return rid

    async def list_rules(
        self,
        team_id: str | None = None,
        enabled_only: bool = True,
    ) -> list[dict]:
        """List handoff rules, optionally filtered by source team."""
        q = select(handoff_rules_table)
        if team_id:
            q = q.where(
                (handoff_rules_table.c.source_team_id == team_id)
                | (handoff_rules_table.c.target_team_id == team_id)
            )
        if enabled_only:
            q = q.where(handoff_rules_table.c.enabled == True)
        q = q.order_by(handoff_rules_table.c.created_at.desc())
        async with _Session() as s:
            rows = (await s.execute(q)).mappings().all()
            return [dict(r) for r in rows]

    async def get_rule(self, rule_id: str) -> dict | None:
        async with _Session() as s:
            row = (await s.execute(
                select(handoff_rules_table).where(handoff_rules_table.c.id == rule_id)
            )).mappings().first()
            return dict(row) if row else None

    async def update_rule(self, rule_id: str, **kwargs) -> dict | None:
        kwargs["updated_at"] = datetime.now(timezone.utc)
        async with _Session() as s:
            await s.execute(
                update(handoff_rules_table)
                .where(handoff_rules_table.c.id == rule_id)
                .values(**kwargs)
            )
            await s.commit()
        return await self.get_rule(rule_id)

    async def delete_rule(self, rule_id: str) -> bool:
        async with _Session() as s:
            result = await s.execute(
                delete(handoff_rules_table).where(handoff_rules_table.c.id == rule_id)
            )
            await s.commit()
            return result.rowcount > 0

    async def toggle_rule(self, rule_id: str, enabled: bool) -> dict | None:
        return await self.update_rule(rule_id, enabled=enabled)

    # ── Trigger Evaluation ────────────────────────────────────────────

    async def find_matching_rules(
        self,
        source_team_id: str,
        event: str,
        skill_id: str | None = None,
    ) -> list[dict]:
        """Find all enabled rules matching a trigger event."""
        q = (
            select(handoff_rules_table)
            .where(handoff_rules_table.c.source_team_id == source_team_id)
            .where(handoff_rules_table.c.trigger_event == event)
            .where(handoff_rules_table.c.enabled == True)
        )
        async with _Session() as s:
            rows = (await s.execute(q)).mappings().all()
            results = []
            for r in rows:
                rule = dict(r)
                # If rule has a specific skill filter, check it
                if rule["trigger_skill_id"] and skill_id and rule["trigger_skill_id"] != skill_id:
                    continue
                results.append(rule)
            return results

    async def execute_handoff(
        self,
        rule: dict,
        source_workflow_id: str,
        source_stage_id: str | None,
        context: dict,
    ) -> str:
        """Execute a handoff: create target workflow + log entry. Returns log entry ID."""
        log_id = f"hlog-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        try:
            # Resolve variable mapping
            variables = {}
            for key, template in rule.get("variable_mapping", {}).items():
                if isinstance(template, str) and template.startswith("{{") and template.endswith("}}"):
                    var_name = template[2:-2].strip()
                    variables[key] = context.get(var_name, "")
                else:
                    variables[key] = template

            # Create workflow in target team
            from zeta_ima.workflows.models import create_workflow
            target_wf = await create_workflow(
                name=f"Handoff: {rule['name']}",
                skill_id="handoff",
                template_id=rule["target_template_id"],
                variables=variables,
            )
            target_wf_id = target_wf["id"] if isinstance(target_wf, dict) else str(target_wf)

            # Auto-advance if configured
            if rule.get("auto_start"):
                try:
                    from zeta_ima.workflows.engine import engine
                    await engine.advance(target_wf_id)
                except Exception as e:
                    log.warning("Auto-advance failed for handoff %s: %s", target_wf_id, e)

            # Log success
            async with _Session() as s:
                await s.execute(handoff_log_table.insert().values(
                    id=log_id,
                    rule_id=rule["id"],
                    source_workflow_id=source_workflow_id,
                    source_stage_id=source_stage_id,
                    target_workflow_id=target_wf_id,
                    status="created",
                    context_snapshot=context,
                    created_at=now,
                ))
                await s.commit()

            # Notify target team
            try:
                from zeta_ima.notify.service import notifications
                await notifications.send(
                    user_id=f"team:{rule['target_team_id']}",
                    title=f"Handoff received: {rule['name']}",
                    body=f"A cross-team handoff created workflow from {rule['source_team_id']}",
                    action_url=f"/workflows/{target_wf_id}",
                    channel="web",
                )
            except Exception:
                pass

            return log_id

        except Exception as e:
            # Log failure
            async with _Session() as s:
                await s.execute(handoff_log_table.insert().values(
                    id=log_id,
                    rule_id=rule["id"],
                    source_workflow_id=source_workflow_id,
                    source_stage_id=source_stage_id,
                    target_workflow_id=None,
                    status="failed",
                    error=str(e)[:500],
                    context_snapshot=context,
                    created_at=now,
                ))
                await s.commit()
            log.error("Handoff failed for rule %s: %s", rule["id"], e)
            return log_id

    async def get_log(self, rule_id: str | None = None, limit: int = 50) -> list[dict]:
        """Get handoff execution log."""
        q = select(handoff_log_table)
        if rule_id:
            q = q.where(handoff_log_table.c.rule_id == rule_id)
        q = q.order_by(handoff_log_table.c.created_at.desc()).limit(limit)
        async with _Session() as s:
            rows = (await s.execute(q)).mappings().all()
            return [dict(r) for r in rows]


handoff_engine = HandoffEngine()
