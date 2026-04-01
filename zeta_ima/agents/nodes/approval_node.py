"""
Approval node — async human-in-the-loop gate via LangGraph interrupt().

When the graph reaches this node it pauses and stores its full state in Redis.
The Teams bot sends an Adaptive Card with Approve / Reject buttons.
When the user clicks, the Teams webhook resumes the graph via:

    graph.ainvoke(Command(resume={"decision": "approve"|"reject", "comment": "..."}), config=...)

LangGraph restart semantics: interrupt() is synchronous (not async). The graph
thread is suspended at this node in Redis; no CPU is held. The graph resumes
from exactly this point when Command(resume=...) is sent.
"""

from langgraph.types import interrupt

from zeta_ima.agents.state import AgentState


def approval_node(state: AgentState) -> dict:
    """
    Pause graph and wait for human Approve/Reject in Teams.
    NOT async — interrupt() is a synchronous LangGraph primitive.
    """
    # This call suspends the graph. Execution resumes after the Teams webhook
    # calls graph.ainvoke(Command(resume={...}), config=thread_config).
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

    return {
        "approval_decision": decision,
        "approval_comment": comment,
        "stage": "done" if decision == "approve" else "drafting",
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
