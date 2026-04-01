"""
WebSocket endpoints for real-time workflow streaming and notifications.

WS /ws/workflows/{workflow_id}  → stream stage updates for a workflow
WS /ws/notifications            → stream notifications for the current user
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from zeta_ima.notify.service import notifications
from zeta_ima.workflows.events import workflow_events

log = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/workflows/{workflow_id}")
async def workflow_stream(websocket: WebSocket, workflow_id: str):
    """
    Stream real-time stage updates for a workflow.

    Client connects and receives events as stages complete:
    {"type": "stage_started", "stage_id": "...", "stage_name": "..."}
    {"type": "stage_completed", "stage_id": "...", "output": "..."}
    {"type": "workflow_completed", "workflow_id": "..."}
    """
    await websocket.accept()
    log.info(f"WS connected: workflow {workflow_id}")

    try:
        async for event in workflow_events.subscribe(workflow_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        log.info(f"WS disconnected: workflow {workflow_id}")
    except Exception as e:
        log.error(f"WS error for workflow {workflow_id}: {e}")


@router.websocket("/ws/notifications")
async def notification_stream(websocket: WebSocket):
    """
    Stream real-time notifications for the connected user.

    The user_id is sent as the first message after connection.
    """
    await websocket.accept()

    # Wait for user identification
    try:
        msg = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        user_id = msg.get("user_id", "dev-user")
    except Exception:
        user_id = "dev-user"

    # Register WebSocket
    queue = notifications.register_ws(user_id)
    log.info(f"Notification WS connected: user {user_id}")

    try:
        while True:
            notif = await queue.get()
            if notif is None:
                break
            await websocket.send_json(notif)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error(f"Notification WS error for {user_id}: {e}")
    finally:
        notifications.unregister_ws(user_id, queue)
        log.info(f"Notification WS disconnected: user {user_id}")
