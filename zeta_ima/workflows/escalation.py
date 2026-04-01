"""
Auto-escalation engine — monitors stuck stages and escalates.

Escalation ladder:
  1. Stage stuck > THRESHOLD_HOURS → create Jira ticket
  2. After 1st ping → Teams notification to stage owner
  3. After 3 unanswered pings → escalate to manager
  4. Continuous monitoring via background loop

Usage:
    from zeta_ima.workflows.escalation import escalation_engine

    # Start the background monitor (call once at app startup)
    await escalation_engine.start()

    # Stop gracefully
    await escalation_engine.stop()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from zeta_ima.workflows.models import (
    _Session,
    get_workflow,
    list_workflows,
    update_stage,
    workflow_escalations,
    workflow_stages,
)

log = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────

STUCK_THRESHOLD_HOURS = 4       # Stage must be stuck this long before first escalation
PING_INTERVAL_HOURS = 2         # Time between re-pings
MAX_PINGS_BEFORE_MANAGER = 3   # After this many pings, escalate to manager
CHECK_INTERVAL_SECONDS = 300    # How often the background loop runs (5 minutes)


class EscalationEngine:
    """Monitors workflows for stuck stages and auto-escalates."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the background escalation monitor."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        log.info("Escalation engine started (check every %ds)", CHECK_INTERVAL_SECONDS)

    async def stop(self):
        """Stop the background monitor gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Escalation engine stopped")

    async def _monitor_loop(self):
        """Main loop — runs every CHECK_INTERVAL_SECONDS."""
        while self._running:
            try:
                await self._check_all_workflows()
            except Exception as e:
                log.error(f"Escalation check failed: {e}", exc_info=True)

            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def _check_all_workflows(self):
        """Scan all active workflows for stuck stages."""
        active_wfs = await list_workflows(status="active", limit=500)
        now = datetime.now(timezone.utc)
        stuck_threshold = now - timedelta(hours=STUCK_THRESHOLD_HOURS)

        for wf in active_wfs:
            for stage in wf.get("stages", []):
                await self._check_stage(wf, stage, now, stuck_threshold)

    async def _check_stage(
        self,
        wf: dict,
        stage: dict,
        now: datetime,
        stuck_threshold: datetime,
    ):
        """Check if a single stage needs escalation."""
        stage_id = stage["id"]
        status = stage["status"]

        # Only escalate stages that are stuck
        is_stuck = False
        if status == "in_progress":
            started = stage.get("started_at")
            if started and isinstance(started, datetime) and started < stuck_threshold:
                is_stuck = True
        elif status == "awaiting_review":
            completed = stage.get("completed_at")
            if completed and isinstance(completed, datetime) and completed < stuck_threshold:
                is_stuck = True
        elif status == "needs_retry":
            is_stuck = True  # Failed stages always need attention

        if not is_stuck:
            return

        # Check existing escalation
        escalation = await self._get_escalation(stage_id)

        if escalation is None:
            # First escalation — create Jira ticket + first ping
            await self._create_escalation(wf, stage, now)
        elif not escalation["resolved"]:
            # Existing escalation — check if we need to re-ping or escalate to manager
            await self._update_escalation(wf, stage, escalation, now)

    async def _get_escalation(self, stage_id: str) -> Optional[dict]:
        """Fetch existing escalation for a stage."""
        async with _Session() as session:
            result = await session.execute(
                select(workflow_escalations)
                .where(workflow_escalations.c.stage_id == stage_id)
                .where(workflow_escalations.c.resolved == False)  # noqa: E712
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def _create_escalation(self, wf: dict, stage: dict, now: datetime):
        """Create initial escalation: Jira ticket + Teams ping."""
        escalation_id = str(uuid.uuid4())

        # Create Jira ticket (if Jira is configured)
        jira_ticket_id = None
        jira_url = None
        try:
            jira_result = await self._create_jira_ticket(wf, stage)
            jira_ticket_id = jira_result.get("ticket_id")
            jira_url = jira_result.get("url")
        except Exception as e:
            log.warning(f"Failed to create Jira ticket for escalation: {e}")

        # Store escalation
        async with _Session() as session:
            await session.execute(
                workflow_escalations.insert().values(
                    id=escalation_id,
                    workflow_id=wf["id"],
                    stage_id=stage["id"],
                    jira_ticket_id=jira_ticket_id,
                    jira_url=jira_url,
                    pings_sent=1,
                    last_ping_at=now,
                    escalated_to_manager=False,
                    resolved=False,
                    created_at=now,
                )
            )
            await session.commit()

        # Send Teams notification
        await self._send_teams_ping(
            wf=wf,
            stage=stage,
            message=f"⚠️ Stage **{stage['name']}** in workflow **{wf['name']}** is stuck "
                    f"(status: {stage['status']}). "
                    + (f"Jira ticket created: {jira_url}" if jira_url else "Please investigate."),
            target="owner",
        )

        log.info(
            f"Escalation created: workflow={wf['name']}, stage={stage['name']}, "
            f"jira={jira_ticket_id}"
        )

    async def _update_escalation(
        self,
        wf: dict,
        stage: dict,
        escalation: dict,
        now: datetime,
    ):
        """Re-ping or escalate to manager."""
        last_ping = escalation.get("last_ping_at")
        ping_threshold = now - timedelta(hours=PING_INTERVAL_HOURS)

        # Check if enough time has passed since last ping
        if last_ping and isinstance(last_ping, datetime) and last_ping > ping_threshold:
            return  # Too soon to re-ping

        pings_sent = escalation.get("pings_sent", 0) + 1
        escalate_to_manager = pings_sent >= MAX_PINGS_BEFORE_MANAGER

        # Update escalation record
        async with _Session() as session:
            await session.execute(
                workflow_escalations.update()
                .where(workflow_escalations.c.id == escalation["id"])
                .values(
                    pings_sent=pings_sent,
                    last_ping_at=now,
                    escalated_to_manager=escalate_to_manager,
                )
            )
            await session.commit()

        if escalate_to_manager and not escalation.get("escalated_to_manager"):
            # Escalate to manager
            await self._send_teams_ping(
                wf=wf,
                stage=stage,
                message=f"🚨 **MANAGER ESCALATION**: Stage **{stage['name']}** in workflow "
                        f"**{wf['name']}** has been stuck for {pings_sent} check cycles. "
                        f"Previous pings went unanswered. Immediate attention required."
                        + (f"\nJira: {escalation.get('jira_url')}" if escalation.get("jira_url") else ""),
                target="manager",
            )
            log.warning(
                f"Manager escalation: workflow={wf['name']}, stage={stage['name']}, "
                f"pings={pings_sent}"
            )
        else:
            # Regular re-ping
            await self._send_teams_ping(
                wf=wf,
                stage=stage,
                message=f"🔔 Reminder ({pings_sent}): Stage **{stage['name']}** in workflow "
                        f"**{wf['name']}** still needs attention (status: {stage['status']}).",
                target="owner",
            )

    async def resolve_escalation(self, stage_id: str):
        """Mark an escalation as resolved (called when stage completes or is approved)."""
        async with _Session() as session:
            await session.execute(
                workflow_escalations.update()
                .where(workflow_escalations.c.stage_id == stage_id)
                .where(workflow_escalations.c.resolved == False)  # noqa: E712
                .values(resolved=True)
            )
            await session.commit()

    # ─── External integrations (stub implementations) ───────────────

    async def _create_jira_ticket(self, wf: dict, stage: dict) -> dict:
        """
        Create a Jira ticket for a stuck stage.

        Returns {"ticket_id": "...", "url": "..."} or raises if Jira not configured.
        """
        from zeta_ima.integrations.vault import vault

        jira_keys = await vault.get_all("jira")
        if not jira_keys:
            log.info("Jira not configured — skipping ticket creation")
            return {}

        try:
            import httpx

            base_url = jira_keys.get("base_url", "").rstrip("/")
            email = jira_keys.get("email", "")
            token = jira_keys.get("api_token", "")

            if not all([base_url, email, token]):
                return {}

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{base_url}/rest/api/3/issue",
                    auth=(email, token),
                    json={
                        "fields": {
                            "project": {"key": jira_keys.get("project_key", "MKT")},
                            "summary": f"[Auto] Stuck: {stage['name']} in {wf['name']}",
                            "description": {
                                "type": "doc",
                                "version": 1,
                                "content": [{
                                    "type": "paragraph",
                                    "content": [{
                                        "type": "text",
                                        "text": (
                                            f"Workflow: {wf['name']} ({wf['id']})\n"
                                            f"Stage: {stage['name']} (index {stage.get('stage_index', '?')})\n"
                                            f"Status: {stage['status']}\n"
                                            f"Agent: {stage.get('agent_name', 'unknown')}\n"
                                            f"Error: {stage.get('error', 'N/A')}\n\n"
                                            f"Auto-created by Zeta IMA escalation engine."
                                        ),
                                    }],
                                }],
                            },
                            "issuetype": {"name": "Task"},
                            "priority": {"name": "High"},
                        }
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                ticket_key = data.get("key", "")
                return {
                    "ticket_id": ticket_key,
                    "url": f"{base_url}/browse/{ticket_key}",
                }
        except Exception as e:
            log.error(f"Jira ticket creation failed: {e}")
            return {}

    async def _send_teams_ping(
        self,
        wf: dict,
        stage: dict,
        message: str,
        target: str = "owner",
    ):
        """
        Send a Teams notification about a stuck stage.

        target: "owner" (stage owner) or "manager" (workflow creator's manager)
        """
        try:
            from zeta_ima.integrations.teams import send_proactive_message

            # Determine recipient
            if target == "owner" and stage.get("owner"):
                recipient_id = stage["owner"]
            else:
                recipient_id = wf.get("created_by", "")

            if not recipient_id:
                log.warning("No recipient for Teams ping — skipping")
                return

            await send_proactive_message(
                user_id=recipient_id,
                message=message,
            )
        except ImportError:
            log.debug("Teams integration not available — logging ping instead")
            log.info(f"[Teams Ping] {target}: {message}")
        except Exception as e:
            log.warning(f"Failed to send Teams ping: {e}")


# Module-level singleton
escalation_engine = EscalationEngine()
