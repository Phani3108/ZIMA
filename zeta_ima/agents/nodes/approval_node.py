"""
Approval node — async human-in-the-loop gate via LangGraph interrupt().

When the graph reaches this node it pauses and stores its full state in Redis.
The Teams bot sends an Adaptive Card with Approve / Reject buttons.
When the user clicks, the Teams webhook resumes the graph via:

    graph.ainvoke(Command(resume={"decision": "approve"|"reject", "comment": "..."}), config=...)

LangGraph restart semantics: interrupt() is synchronous (not async). The graph
thread is suspended at this node in Redis; no CPU is held. The graph resumes
from exactly this point when Command(resume=...) is sent.

On rejection: records a negative learning signal so the copy agent avoids
the same mistakes next time (closes the feedback loop).
"""

import logging

from langgraph.types import interrupt

from zeta_ima.agents.state import AgentState
from zeta_ima.orchestrator.a2a import emit_step

log = logging.getLogger(__name__)


def approval_node(state: AgentState) -> dict:
    """
    Pause graph and wait for human Approve/Reject in Teams.
    NOT async — interrupt() is a synchronous LangGraph primitive.
    """
    agent_messages = list(state.get("agent_messages", []))

    # Step 1/2: Resolve approver and send notification
    agent_messages.append(emit_step("approval", "Resolving approver", 0, 2, "started").to_dict())

    # Try to resolve named approver from team approval routing
    approver_name = "the reviewer"
    try:
        import asyncio
        from zeta_ima.teams_collab import teams_service
        team_id = state.get("team_id", "")
        # Determine which agent type just produced work
        pipeline = state.get("pipeline", [])
        pipeline_idx = state.get("pipeline_index", 0)
        agent_type = pipeline[pipeline_idx - 1] if pipeline and pipeline_idx > 0 else "copy"
        if team_id:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    approver = pool.submit(
                        asyncio.run,
                        teams_service.get_approver(team_id, agent_type)
                    ).result()
                if approver:
                    approver_name = approver.get("approver_display_name") or approver.get("approver_user_id", "the reviewer")
                    # Send notification to the named approver
                    try:
                        asyncio.ensure_future(
                            _notify_approver(
                                approver["approver_user_id"],
                                approver.get("approver_email", ""),
                                state,
                            )
                        )
                    except Exception:
                        pass
    except Exception as e:
        log.debug("Approver resolution failed (non-fatal): %s", e)

    agent_messages.append(emit_step("approval", "Resolving approver", 0, 2, "completed", f"Routed to {approver_name}").to_dict())
    agent_messages.append(emit_step("approval", f"Waiting for {approver_name}'s approval", 1, 2, "started").to_dict())

    decision_payload = interrupt(
        {
            "draft": state["current_draft"]["text"],
            "review": state["review_result"],
            "iteration": state.get("iteration_count", 1),
            "brief": state["current_brief"],
        }
    )

    # ── Execution resumes here after the human clicks Approve or Reject ──
    decision = decision_payload.get("decision", "reject")
    comment = decision_payload.get("comment", "")

    # ── Record rejection as negative learning signal ──
    if decision == "reject" and comment:
        try:
            import asyncio
            from zeta_ima.memory.learning import record_rejection
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Fire-and-forget in LangGraph sync context
                asyncio.ensure_future(record_rejection(
                    skill_id=state.get("intent", "copy"),
                    draft_text=state["current_draft"]["text"][:500],
                    rejection_comment=comment,
                    user_id=state.get("user_id", ""),
                    workflow_id=state.get("current_draft", {}).get("iteration", ""),
                    iteration=state.get("iteration_count", 1),
                ))
            log.info("Rejection learning signal queued for skill=%s", state.get("intent", "copy"))
        except Exception as e:
            log.debug("Rejection learning failed (non-fatal): %s", e)

    # ── Archive rejected session ──
    if decision == "reject":
        try:
            import asyncio
            from zeta_ima.memory.conversation_archive import archive_session
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(archive_session(
                    team_id=state.get("team_id", "__default__"),
                    user_id=state.get("user_id", ""),
                    brief=state.get("current_brief", ""),
                    pipeline_id=state.get("intent", ""),
                    messages=state.get("messages", []),
                    outcome="rejected",
                    tags=[state.get("intent", "copy")],
                ))
        except Exception:
            pass

    return {
        "approval_decision": decision,
        "approval_comment": comment,
        "stage": "done" if decision == "approve" else "drafting",
        "agent_messages": agent_messages,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"Decision: {decision.upper()}."
                    + (f" Feedback: {comment}" if comment else "")
                ),
            }
        ],
    }


async def _notify_approver(user_id: str, email: str, state: dict) -> None:
    """Send approval notification to the named approver on all channels."""
    try:
        from zeta_ima.notify.service import notifications
        brief = state.get("current_brief", "")[:200]
        draft_preview = state.get("current_draft", {}).get("text", "")[:300]
        scores = state.get("review_result", {}).get("scores", {})
        await notifications.send(
            user_id=user_id,
            title="Approval Needed",
            body=(
                f"A draft for \"{brief}\" is ready for your review.\n"
                f"Scores: {scores}\n"
                f"Preview: {draft_preview}..."
            ),
            action_url=f"/future/approvals",
            channel="all",
            metadata={"type": "approval_request", "approver_email": email},
        )
    except Exception as e:
        logging.getLogger(__name__).debug("Approver notification failed: %s", e)
