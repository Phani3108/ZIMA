"""
Notification routes — real-time notifications + REST endpoints.

GET    /notifications              → list notifications for current user
GET    /notifications/unread-count → get unread count
POST   /notifications/{id}/read   → mark as read
POST   /notifications/read-all    → mark all as read
GET    /ws/notifications           → WebSocket for real-time notifications
"""

import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query

from zeta_ima.api.auth import get_current_user
from zeta_ima.notify.service import notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """List notifications for the current user."""
    if unread_only:
        return await notifications.get_unread(user["user_id"], limit)
    return await notifications.get_all_notifications(user["user_id"], limit)


@router.get("/unread-count")
async def unread_count(user: dict = Depends(get_current_user)) -> dict:
    """Get the count of unread notifications."""
    count = await notifications.get_unread_count(user["user_id"])
    return {"count": count}


@router.post("/{notif_id}/read")
async def mark_read(
    notif_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Mark a notification as read."""
    ok = await notifications.mark_read(user["user_id"], notif_id)
    return {"ok": ok}


@router.post("/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)) -> dict:
    """Mark all notifications as read."""
    count = await notifications.mark_all_read(user["user_id"])
    return {"ok": True, "count": count}
