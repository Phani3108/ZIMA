"""
Task Dispatcher — background loop that pops tasks from the queue, routes them,
and creates workflows.

The dispatcher runs as an asyncio background task started at app startup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from zeta_ima.config import settings
from zeta_ima.orchestrator.queue import pop_next_task, update_task
from zeta_ima.orchestrator.router import route_task

log = logging.getLogger(__name__)

_running = False


async def _dispatch_one(task: dict) -> None:
    """Route a single task and create the corresponding workflow."""
    task_id = task["id"]
    brief = task.get("description") or task.get("title", "")

    try:
        # Mark task as assigned while we route
        await update_task(task_id, status="assigned")

        # Route the task
        decision = await route_task(brief)

        # Update task with routing decision
        await update_task(
            task_id,
            pipeline=decision.pipeline,
            pipeline_name=decision.pipeline_name,
            priority=decision.priority,
            routing_rationale=decision.rationale,
            status="in_progress",
        )

        # Create a workflow from the task
        from zeta_ima.workflows.engine import WorkflowEngine
        engine = WorkflowEngine()

        # Build stage definitions from the pipeline
        stages = []
        for i, agent_name in enumerate(decision.pipeline):
            # Determine if this stage needs approval
            needs_approval = agent_name in ("approval", "review")
            stages.append({
                "name": agent_name.replace("_", " ").title(),
                "agent": agent_name,
                "requires_approval": needs_approval,
            })

        from zeta_ima.workflows.models import create_workflow
        wf = await create_workflow(
            name=task.get("title", f"Task {task_id[:8]}"),
            skill_id="orchestrated",
            template_id=decision.pipeline_name,
            created_by=task["requester_id"],
            variables={"brief": brief, **(task.get("metadata") or {})},
            stages=stages,
            campaign_id=task.get("metadata", {}).get("campaign_id"),
        )

        await update_task(task_id, workflow_id=wf["id"])

        # Auto-advance the workflow
        try:
            await engine.advance(wf["id"])
        except Exception as e:
            log.warning(f"Auto-advance for task {task_id} failed: {e}")

        log.info(
            f"Task {task_id[:8]} dispatched → pipeline={decision.pipeline_name}, "
            f"workflow={wf['id'][:8]}, source={decision.source}"
        )

    except Exception as e:
        log.error(f"Failed to dispatch task {task_id}: {e}", exc_info=True)
        await update_task(task_id, status="escalated",
                          metadata={**(task.get("metadata") or {}), "dispatch_error": str(e)})


async def dispatch_loop() -> None:
    """Background loop: pop tasks from queue and dispatch them."""
    global _running
    _running = True
    interval = settings.task_dispatch_interval_seconds

    log.info(f"Task dispatcher started (interval={interval}s)")

    while _running:
        try:
            task = await pop_next_task()
            if task and task["status"] == "queued":
                await _dispatch_one(task)
            else:
                await asyncio.sleep(interval)
        except Exception as e:
            log.error(f"Dispatcher loop error: {e}", exc_info=True)
            await asyncio.sleep(interval)


async def start_dispatcher() -> asyncio.Task:
    """Start the dispatch loop as a background task."""
    return asyncio.create_task(dispatch_loop())


def stop_dispatcher() -> None:
    """Signal the dispatch loop to stop."""
    global _running
    _running = False
