"""
WebSocket chat route — real-time bidirectional chat for the web app.

Protocol:
  Client → Server: {"type": "message", "brief": "...", "campaign_id": "...", "session_id": "..."}
  Client → Server: {"type": "approve", "comment": "..."}
  Client → Server: {"type": "reject", "comment": "..."}

  Server → Client: {"type": "thinking", "text": "Drafting..."}
  Server → Client: {"type": "draft", "text": "...", "review": {...}, "iteration": n}
  Server → Client: {"type": "awaiting_approval", "draft": "...", "review": {...}}
  Server → Client: {"type": "done", "text": "Approved and saved."}
  Server → Client: {"type": "tool_result", "tool": "jira", "result": {...}}
  Server → Client: {"type": "error", "text": "..."}
"""

import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langgraph.types import Command

from zeta_ima.agents.graph import graph
from zeta_ima.agents.state import AgentState
from zeta_ima.memory.campaign import load_active_campaign
from zeta_ima.memory.session import make_thread_config

router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat/{session_id}")
async def chat_ws(ws: WebSocket, session_id: str):
    """
    WebSocket endpoint for web app chat.
    session_id is the client-generated session ID (maps to LangGraph thread_id).
    """
    await ws.accept()
    config = make_thread_config(session_id)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "text": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "message")

            if msg_type == "message":
                brief = msg.get("brief", "").strip()
                campaign_id = msg.get("campaign_id")
                user_id = msg.get("user_id", "web-user")

                if not brief:
                    await ws.send_json({"type": "error", "text": "Brief cannot be empty"})
                    continue

                # Send immediate acknowledgement
                await ws.send_json({"type": "thinking", "text": "Analysing brief and pulling brand context..."})

                campaign = await load_active_campaign(user_id)
                effective_campaign_id = campaign_id or (campaign["id"] if campaign else None)

                initial_state: AgentState = {
                    "messages": [{"role": "user", "content": brief}],
                    "current_brief": brief,
                    "drafts": [],
                    "current_draft": {},
                    "review_result": {},
                    "iteration_count": 0,
                    "user_id": user_id,
                    "user_teams_id": user_id,
                    "active_campaign_id": effective_campaign_id,
                    "stage": "drafting",
                    "approval_decision": None,
                    "approval_comment": None,
                    "brand_examples": [],
                    "intent": "",
                    "route_to": [],
                    "tool_results": {},
                    "kb_context": [],
                }

                result = await graph.ainvoke(initial_state, config=config)
                await _send_result(ws, result)

            elif msg_type in ("approve", "reject"):
                comment = msg.get("comment", "")
                result = await graph.ainvoke(
                    Command(resume={"decision": msg_type, "comment": comment}),
                    config=config,
                )
                await _send_result(ws, result)

            else:
                await ws.send_json({"type": "error", "text": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        pass


async def _send_result(ws: WebSocket, result: dict):
    stage = result.get("stage")

    if stage == "awaiting_approval":
        await ws.send_json({
            "type": "awaiting_approval",
            "draft": result.get("current_draft", {}).get("text", ""),
            "review": result.get("review_result", {}),
            "iteration": result.get("iteration_count", 1),
            "brief": result.get("current_brief", ""),
        })
    elif stage == "done":
        tool_results = result.get("tool_results", {})
        await ws.send_json({
            "type": "done",
            "text": result.get("current_draft", {}).get("text", ""),
            "tool_results": tool_results,
        })
    else:
        last = result.get("messages", [{}])[-1].get("content", "")
        await ws.send_json({"type": "status", "text": last})
