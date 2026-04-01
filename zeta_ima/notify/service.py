"""
Unified Notification Service — web push, Teams, email.

Notifications are stored in Redis for quick retrieval and
optionally forwarded to Teams/email depending on channel config.

Usage:
    from zeta_ima.notify.service import notifications

    await notifications.send(
        user_id="dev-user",
        title="Stage Complete",
        body="Your SEO blog post draft is ready for review.",
        action_url="/workflows/abc123",
        channel="web",
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)


class NotificationService:
    """Manages notifications across web, Teams, and email channels."""

    def __init__(self):
        self._redis = None
        # In-memory fallback for when Redis is unavailable
        self._memory_store: dict[str, list[dict]] = {}
        # WebSocket connections per user
        self._ws_connections: dict[str, set[asyncio.Queue]] = {}

    async def init(self, redis_url: str = ""):
        """Initialize Redis connection for notification storage."""
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                log.info("Notification service connected to Redis")
            except Exception as e:
                log.warning(f"Redis not available for notifications, using memory: {e}")
                self._redis = None

    async def send(
        self,
        user_id: str,
        title: str,
        body: str,
        action_url: str = "",
        channel: str = "web",
        metadata: dict | None = None,
    ) -> str:
        """
        Send a notification.

        Args:
            user_id: Target user
            title: Notification title
            body: Notification body
            action_url: URL to navigate to when clicked
            channel: "web" | "teams" | "email" | "all"
            metadata: Extra data (workflow_id, stage_id, etc.)

        Returns:
            notification_id
        """
        notif_id = str(uuid.uuid4())
        notif = {
            "id": notif_id,
            "user_id": user_id,
            "title": title,
            "body": body,
            "action_url": action_url,
            "channel": channel,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        # Store notification
        await self._store(user_id, notif)

        # Push to connected WebSocket clients
        await self._push_ws(user_id, notif)

        # Forward to Teams if requested
        if channel in ("teams", "all"):
            await self._send_teams(user_id, title, body, action_url)

        # Forward to email if requested
        if channel in ("email", "all"):
            await self._send_email(user_id, title, body, action_url)

        return notif_id

    async def get_unread(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get unread notifications for a user."""
        all_notifs = await self._get_all(user_id)
        unread = [n for n in all_notifs if not n.get("read")]
        return unread[:limit]

    async def get_all_notifications(self, user_id: str, limit: int = 100) -> list[dict]:
        """Get all notifications for a user."""
        return (await self._get_all(user_id))[:limit]

    async def mark_read(self, user_id: str, notif_id: str) -> bool:
        """Mark a notification as read."""
        all_notifs = await self._get_all(user_id)
        for n in all_notifs:
            if n["id"] == notif_id:
                n["read"] = True
                await self._save_all(user_id, all_notifs)
                return True
        return False

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read. Returns count marked."""
        all_notifs = await self._get_all(user_id)
        count = 0
        for n in all_notifs:
            if not n.get("read"):
                n["read"] = True
                count += 1
        await self._save_all(user_id, all_notifs)
        return count

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        return len(await self.get_unread(user_id))

    # ─── WebSocket push ─────────────────────────────────────────

    def register_ws(self, user_id: str) -> asyncio.Queue:
        """Register a WebSocket connection for a user."""
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        if user_id not in self._ws_connections:
            self._ws_connections[user_id] = set()
        self._ws_connections[user_id].add(q)
        return q

    def unregister_ws(self, user_id: str, q: asyncio.Queue) -> None:
        """Unregister a WebSocket connection."""
        self._ws_connections.get(user_id, set()).discard(q)

    async def _push_ws(self, user_id: str, notif: dict) -> None:
        """Push notification to all connected WebSocket clients for this user."""
        for q in self._ws_connections.get(user_id, set()).copy():
            try:
                q.put_nowait(notif)
            except asyncio.QueueFull:
                pass

    # ─── Storage ─────────────────────────────────────────────────

    async def _store(self, user_id: str, notif: dict) -> None:
        key = f"notifications:{user_id}"
        if self._redis:
            await self._redis.lpush(key, json.dumps(notif))
            await self._redis.ltrim(key, 0, 199)  # Keep last 200
        else:
            if user_id not in self._memory_store:
                self._memory_store[user_id] = []
            self._memory_store[user_id].insert(0, notif)
            self._memory_store[user_id] = self._memory_store[user_id][:200]

    async def _get_all(self, user_id: str) -> list[dict]:
        key = f"notifications:{user_id}"
        if self._redis:
            items = await self._redis.lrange(key, 0, -1)
            return [json.loads(item) for item in items]
        return list(self._memory_store.get(user_id, []))

    async def _save_all(self, user_id: str, notifs: list[dict]) -> None:
        key = f"notifications:{user_id}"
        if self._redis:
            pipe = self._redis.pipeline()
            pipe.delete(key)
            for n in notifs:
                pipe.rpush(key, json.dumps(n))
            await pipe.execute()
        else:
            self._memory_store[user_id] = notifs

    # ─── External channels ──────────────────────────────────────

    async def _send_teams(self, user_id: str, title: str, body: str, url: str) -> None:
        try:
            from zeta_ima.integrations.teams import send_proactive_message
            await send_proactive_message(
                user_id=user_id,
                message=f"**{title}**\n\n{body}" + (f"\n\n[View →]({url})" if url else ""),
            )
        except Exception as e:
            log.debug(f"Teams notification skipped: {e}")

    async def _send_email(self, user_id: str, title: str, body: str, url: str) -> None:
        try:
            from zeta_ima.integrations.sendgrid import send_email
            # In a real setup, user_id would map to an email address
            # For now, this is a stub
            log.debug(f"Email notification for {user_id}: {title}")
        except Exception as e:
            log.debug(f"Email notification skipped: {e}")


# Module-level singleton
notifications = NotificationService()
