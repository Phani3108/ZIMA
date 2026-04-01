"""
Teams chat extractor — parses exported Teams chat JSON.

Teams chat export format (from Teams → Export → JSON):
[
  {
    "id": "...",
    "messageType": "message",
    "createdDateTime": "2025-01-15T10:30:00Z",
    "from": {"user": {"displayName": "Phani M", "id": "..."}},
    "body": {"content": "Here is the updated brief...", "contentType": "text"}
  },
  ...
]
"""

import json
from datetime import datetime


def extract_teams_chat(json_bytes: bytes) -> str:
    """
    Parse a Teams chat JSON export into plain text (speaker-turn format).
    Returns a string ready for chunking.
    """
    try:
        messages = json.loads(json_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid Teams chat JSON: {e}")

    lines = []
    for msg in messages:
        msg_type = msg.get("messageType", "")
        if msg_type not in ("message", ""):
            continue

        body = msg.get("body", {})
        content = body.get("content", "").strip()
        if not content:
            continue

        # Strip HTML tags if content_type is html
        if body.get("contentType") == "html":
            from bs4 import BeautifulSoup
            content = BeautifulSoup(content, "lxml").get_text(separator=" ", strip=True)

        sender = (
            msg.get("from", {}).get("user", {}).get("displayName", "Unknown")
        )
        ts = msg.get("createdDateTime", "")
        if ts:
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass

        lines.append(f"[{ts}] {sender}: {content}")

    return "\n".join(lines)
