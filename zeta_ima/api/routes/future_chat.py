"""
Future Chat WebSocket — enhanced real-time chat with step-by-step execution visibility.

Protocol (extends base chat):
  Client → Server: {"type": "message", "brief": "...", "task_template_id": "...", "prior_job_id": "...", ...}
  Client → Server: {"type": "approve", "comment": "..."}
  Client → Server: {"type": "reject",  "comment": "..."}

  Server → Client: {"type": "pipeline_plan", "steps": [...], "template_id": "..."}
  Server → Client: {"type": "agent_step", "from": "copy", "step_name": "...", "step_index": 0, "total_steps": 5, "status": "started"}
  Server → Client: {"type": "agent_step", "from": "copy", "step_name": "...", "step_index": 0, "total_steps": 5, "status": "completed", "preview": "..."}
  Server → Client: {"type": "job_suggestions", "suggestions": [...]}
  Server → Client: {"type": "thinking", "text": "..."}
  Server → Client: {"type": "draft", "text": "...", "review": {...}}
  Server → Client: {"type": "awaiting_approval", "draft": "...", "review": {...}, "approver": "..."}
  Server → Client: {"type": "done", "text": "..."}
  Server → Client: {"type": "error", "text": "..."}
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langgraph.types import Command

from zeta_ima.agents.graph import graph
from zeta_ima.agents.state import AgentState
from zeta_ima.memory.campaign import load_active_campaign
from zeta_ima.memory.session import make_thread_config

log = logging.getLogger(__name__)

router = APIRouter(tags=["future-chat"])


@router.websocket("/ws/future/chat/{session_id}")
async def future_chat_ws(ws: WebSocket, session_id: str):
    """Enhanced chat WebSocket with step-by-step execution updates."""
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
                await _handle_message(ws, msg, config)
            elif msg_type in ("approve", "reject"):
                await _handle_decision(ws, msg, config)
            else:
                await ws.send_json({"type": "error", "text": f"Unknown type: {msg_type}"})

    except WebSocketDisconnect:
        pass


async def _handle_message(ws: WebSocket, msg: dict, config: dict):
    """Handle a new user message — optionally with template and job suggestions."""
    brief = msg.get("brief", "").strip()
    task_template_id = msg.get("task_template_id")
    prior_job_id = msg.get("prior_job_id")
    campaign_id = msg.get("campaign_id")
    user_id = msg.get("user_id", "web-user")

    if not brief:
        await ws.send_json({"type": "error", "text": "Brief cannot be empty"})
        return

    # 1. If template specified, send pipeline plan
    if task_template_id:
        try:
            from zeta_ima.skills.task_templates import template_registry
            tmpl = template_registry.get(task_template_id)
            if tmpl:
                await ws.send_json({
                    "type": "pipeline_plan",
                    "template_id": task_template_id,
                    "template_name": tmpl.name,
                    "steps": [
                        {
                            "name": s.name,
                            "agent": s.agent,
                            "description": s.description,
                            "is_human_gate": s.is_human_gate,
                        }
                        for s in tmpl.steps
                    ],
                })
        except Exception as e:
            log.debug("Failed to send pipeline plan: %s", e)

    # 2. Send job suggestions if agent has history
    if task_template_id:
        try:
            from zeta_ima.memory.job_history import job_history
            suggestions = await job_history.get_suggestions(
                template_id=task_template_id,
                user_id=user_id,
                limit=2,
            )
            if suggestions:
                await ws.send_json({
                    "type": "job_suggestions",
                    "suggestions": suggestions,
                })
        except Exception as e:
            log.debug("Failed to load suggestions: %s", e)

    # 3. Send thinking indicator
    await ws.send_json({"type": "thinking", "text": "Analysing brief and pulling brand context..."})

    # 4. Build initial state
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
        "task_template_id": task_template_id,
    }

    # If reusing a prior job, inject its output as a starting point
    if prior_job_id:
        try:
            from zeta_ima.memory.job_history import job_history
            job = await job_history.get_job(prior_job_id)
            if job:
                initial_state["messages"].append(
                    {"role": "system", "content": f"Prior approved output to refine:\n{job.get('output_text', '')}"}
                )
        except Exception:
            pass

    # 5. Stream graph execution with step events
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event")

        # Forward A2A agent_messages (step events)
        if kind == "on_chain_end":
            output = event.get("data", {}).get("output", {})
            if isinstance(output, dict):
                agent_msgs = output.get("agent_messages", [])
                for am in agent_msgs:
                    if hasattr(am, "payload") and am.payload.get("_type") in ("step_started", "step_completed"):
                        await ws.send_json({
                            "type": "agent_step",
                            "from": am.from_agent,
                            "step_name": am.payload.get("step_name", ""),
                            "step_index": am.payload.get("step_index", 0),
                            "total_steps": am.payload.get("total_steps", 1),
                            "status": am.payload.get("status", "started"),
                            "preview": am.payload.get("preview", ""),
                        })

    # 6. Get final state and send result
    final_state = await graph.aget_state(config)
    if final_state and final_state.values:
        await _send_result(ws, final_state.values)


async def _handle_decision(ws: WebSocket, msg: dict, config: dict):
    """Handle approve/reject from the user."""
    decision = msg.get("type")
    comment = msg.get("comment", "")

    result = await graph.ainvoke(
        Command(resume={"decision": decision, "comment": comment}),
        config=config,
    )
    await _send_result(ws, result)


async def _send_result(ws: WebSocket, result: dict):
    """Send the appropriate message based on graph stage."""
    stage = result.get("stage")

    if stage == "awaiting_approval":
        payload = {
            "type": "awaiting_approval",
            "draft": result.get("current_draft", {}).get("text", ""),
            "review": result.get("review_result", {}),
            "iteration": result.get("iteration_count", 1),
            "brief": result.get("current_brief", ""),
        }
        # Include approver info if available
        agent_msgs = result.get("agent_messages", [])
        for am in agent_msgs:
            if hasattr(am, "payload") and "approver_name" in am.payload:
                payload["approver"] = am.payload["approver_name"]
                break
        await ws.send_json(payload)

    elif stage == "done":
        await ws.send_json({
            "type": "done",
            "text": result.get("current_draft", {}).get("text", ""),
            "tool_results": result.get("tool_results", {}),
        })
    else:
        last = result.get("messages", [{}])[-1]
        content = last.get("content", "") if isinstance(last, dict) else str(last)
        await ws.send_json({"type": "status", "text": content})
