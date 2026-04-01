"""
Workflow event emitter — pub/sub for real-time stage updates.

The workflow engine emits events when stages change status.
WebSocket connections and the notification service subscribe to events.

Usage:
    from zeta_ima.workflows.events import workflow_events

    # Subscribe
    async for event in workflow_events.subscribe("workflow-123"):
        print(event)

    # Emit
    await workflow_events.emit("workflow-123", {
        "type": "stage_completed",
        "stage_id": "...",
        "output": "...",
    })
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

log = logging.getLogger(__name__)


class WorkflowEventBus:
    """In-memory pub/sub for workflow events."""

    def __init__(self):
        # workflow_id -> set of asyncio.Queue
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        # Global subscribers (receive ALL events)
        self._global_subscribers: set[asyncio.Queue] = set()

    async def emit(self, workflow_id: str, event: dict) -> None:
        """Broadcast an event to all subscribers of a workflow."""
        event = {"workflow_id": workflow_id, **event}

        # Workflow-specific subscribers
        for q in self._subscribers.get(workflow_id, set()).copy():
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                log.warning(f"Event queue full for workflow {workflow_id}, dropping event")

        # Global subscribers
        for q in self._global_subscribers.copy():
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, workflow_id: str) -> AsyncIterator[dict]:
        """Yield events for a specific workflow as they arrive."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        if workflow_id not in self._subscribers:
            self._subscribers[workflow_id] = set()
        self._subscribers[workflow_id].add(q)

        try:
            while True:
                event = await q.get()
                if event is None:  # Shutdown signal
                    break
                yield event
        finally:
            self._subscribers.get(workflow_id, set()).discard(q)
            if not self._subscribers.get(workflow_id):
                self._subscribers.pop(workflow_id, None)

    async def subscribe_all(self) -> AsyncIterator[dict]:
        """Yield ALL workflow events (for notification service)."""
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._global_subscribers.add(q)

        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield event
        finally:
            self._global_subscribers.discard(q)

    def close_workflow(self, workflow_id: str) -> None:
        """Send shutdown signal to all subscribers of a workflow."""
        for q in self._subscribers.get(workflow_id, set()):
            q.put_nowait(None)
        self._subscribers.pop(workflow_id, None)


# Module-level singleton
workflow_events = WorkflowEventBus()
