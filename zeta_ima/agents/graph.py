"""
LangGraph StateGraph — dynamic multi-agent graph builder.

Two construction modes:
  1. build_graph() — original hardcoded topology (backward compatible)
  2. build_pipeline_graph(pipeline) — dynamic topology from orchestrator routing

Original topology:
  START → research → route_intent
                         ├─ copy  → review → await_approval → save_memory → END
                         │              ↑ (reject loops back)
                         ├─ jira  → tool_done → END  (or → copy if multi-intent)
                         ├─ confluence → tool_done → END
                         ├─ canva → tool_done → END
                         └─ research-only → tool_done → END

Dynamic pipeline topology:
  START → agent[0] → agent[1] → ... → agent[n] → END
  With conditional edges for review/approval loops.

- Redis checkpointer persists full state across server restarts (48h TTL)
- interrupt_before=["await_approval"] pauses graph for human review
"""

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from zeta_ima.agents.nodes.approval_node import approval_node
from zeta_ima.agents.nodes.canva_node import canva_node
from zeta_ima.agents.nodes.confluence_node import confluence_node
from zeta_ima.agents.nodes.copy_node import copy_node
from zeta_ima.agents.nodes.jira_node import jira_node
from zeta_ima.agents.nodes.memory_node import memory_node
from zeta_ima.agents.nodes.research_node import research_node
from zeta_ima.agents.nodes.review_node import review_node
from zeta_ima.agents.nodes.recall_node import recall_node, await_recall_node
from zeta_ima.agents.meeting import run_meeting, should_skip_meeting
from zeta_ima.agents.router import classify_intent
from zeta_ima.agents.state import AgentState
from zeta_ima.memory.session import get_checkpointer


# ── Dynamic pipeline node imports (Genesis v2) ──
def _get_pm_node():
    from zeta_ima.agents.nodes.pm_node import pm_node
    return pm_node


def _get_design_node():
    from zeta_ima.agents.nodes.design_node import design_node
    return design_node


def _get_seo_node():
    from zeta_ima.agents.nodes.seo_node import seo_node
    return seo_node


def _get_competitive_intel_node():
    from zeta_ima.agents.nodes.competitive_intel_node import competitive_intel_node
    return competitive_intel_node


def _get_product_marketing_node():
    from zeta_ima.agents.nodes.product_marketing_node import product_marketing_node
    return product_marketing_node


# Node registry: maps pipeline agent names to node functions
def _get_node_registry() -> dict:
    return {
        "research": research_node,
        "copy": copy_node,
        "review": review_node,
        "approval": approval_node,
        "await_approval": approval_node,
        "save_memory": memory_node,
        "jira": jira_node,
        "confluence": confluence_node,
        "canva": canva_node,
        "pm": _get_pm_node(),
        "design": _get_design_node(),
        "seo": _get_seo_node(),
        "competitive_intel": _get_competitive_intel_node(),
        "product_marketing": _get_product_marketing_node(),
    }


# ── Meeting nodes (Phase 4 — agent scrum before execution) ──

async def meeting_node(state: AgentState) -> dict:
    """Run a scrum meeting where agents discuss the brief and produce a plan."""
    brief = state.get("current_brief", "")
    pipeline = state.get("pipeline", [])

    if should_skip_meeting(brief):
        return {
            "plan_status": "skipped",
            "meeting_transcript": [],
            "meeting_plan": {"summary": "Brief is simple — skipping planning meeting."},
        }

    plan = await run_meeting(
        brief=brief,
        pipeline=pipeline,
        kb_context=state.get("kb_context"),
        brain_context=state.get("brain_context"),
        modifications=state.get("user_plan_modifications", ""),
    )

    return {
        "meeting_transcript": [m.to_dict() for m in plan.transcript],
        "meeting_plan": plan.to_dict(),
        "plan_status": "awaiting_user",
        "stage": "planning",
    }


def await_plan_approval_node(state: AgentState) -> dict:
    """Pause graph for user to approve/modify/cancel the meeting plan."""
    plan_status = state.get("plan_status", "")

    # Skip interrupt if meeting was skipped
    if plan_status == "skipped":
        return {"plan_status": "approved"}

    decision_payload = interrupt({
        "meeting_transcript": state.get("meeting_transcript", []),
        "meeting_plan": state.get("meeting_plan", {}),
    })

    decision = decision_payload.get("decision", "approve")  # approve | modify | cancel
    modifications = decision_payload.get("modifications", "")

    if decision == "cancel":
        return {
            "plan_status": "cancelled",
            "stage": "done",
            "messages": [{"role": "assistant", "content": "Task cancelled by user."}],
        }
    elif decision == "modify":
        return {
            "plan_status": "modified",
            "user_plan_modifications": modifications,
        }
    else:
        return {"plan_status": "approved"}


# ── Original hardcoded graph (backward compatible) ──

async def route_intent_node(state: AgentState) -> dict:
    intents = await classify_intent(state["current_brief"])
    return {"intent": intents[0] if intents else "copy", "route_to": intents}


async def tool_done_node(state: AgentState) -> dict:
    results = state.get("tool_results", {})
    parts = []
    for key, val in results.items():
        if isinstance(val, dict) and val.get("url"):
            parts.append(f"{key}: {val['url']}")
        elif isinstance(val, list):
            parts.append(f"{key}: {len(val)} result(s)")
    return {
        "stage": "done",
        "messages": [{"role": "assistant", "content": "Done. " + " | ".join(parts) if parts else "Done."}],
    }


def _after_route(state: AgentState) -> str:
    intent = state.get("intent", "copy")
    return {"jira": "jira", "confluence": "confluence", "canva": "canva", "research": "tool_done"}.get(intent, "copy")


def _after_review(state: AgentState) -> str:
    return "await_approval" if state["stage"] == "awaiting_approval" else "copy"


def _after_approval(state: AgentState) -> str:
    if state.get("approval_decision") == "approve":
        # Run secondary tool agents if multi-intent
        remaining = [r for r in state.get("route_to", []) if r not in ("copy", "research")]
        if remaining:
            return remaining[0]
        return "save_memory"
    return "copy"


def _after_tool(state: AgentState) -> str:
    return "copy" if "copy" in state.get("route_to", []) else "tool_done"


def build_graph():
    """Original hardcoded graph topology (backward compatible)."""
    builder = StateGraph(AgentState)

    builder.add_node("research", research_node)
    builder.add_node("route_intent", route_intent_node)
    builder.add_node("copy", copy_node)
    builder.add_node("review", review_node)
    builder.add_node("await_approval", approval_node)
    builder.add_node("save_memory", memory_node)
    builder.add_node("jira", jira_node)
    builder.add_node("confluence", confluence_node)
    builder.add_node("canva", canva_node)
    builder.add_node("tool_done", tool_done_node)

    builder.set_entry_point("research")
    builder.add_edge("research", "route_intent")
    builder.add_conditional_edges("route_intent", _after_route, {
        "copy": "copy", "jira": "jira", "confluence": "confluence",
        "canva": "canva", "tool_done": "tool_done",
    })
    builder.add_edge("copy", "review")
    builder.add_conditional_edges("review", _after_review, {
        "await_approval": "await_approval", "copy": "copy",
    })
    builder.add_conditional_edges("await_approval", _after_approval, {
        "save_memory": "save_memory", "copy": "copy",
        "jira": "jira", "confluence": "confluence", "canva": "canva",
    })
    builder.add_edge("save_memory", END)
    builder.add_conditional_edges("jira", _after_tool, {"copy": "copy", "tool_done": "tool_done"})
    builder.add_conditional_edges("confluence", _after_tool, {"copy": "copy", "tool_done": "tool_done"})
    builder.add_conditional_edges("canva", _after_tool, {"copy": "copy", "tool_done": "tool_done"})
    builder.add_edge("tool_done", END)

    checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer, interrupt_before=["await_approval"])


# ── Dynamic pipeline graph (Genesis v2) ──

def _after_plan_approval(state: AgentState) -> str:
    """Route after plan approval: approved → execute, modified → re-meet, cancelled → end."""
    status = state.get("plan_status", "approved")
    if status == "cancelled":
        return "tool_done"
    if status == "modified":
        return "meeting"
    return "pipeline_start"  # placeholder resolved at build time


def build_pipeline_graph(pipeline: list[str]):
    """
    Build a LangGraph from an ordered pipeline of agent names.

    The pipeline comes from the orchestrator router. Examples:
      ["research", "pm", "copy", "design", "review", "approval"]
      ["research", "copy", "review", "approval"]
      ["research", "jira", "tool_done"]

    Special handling:
      - Meeting + plan approval are prepended (skipped for simple briefs)
      - "review" → "approval" edge has a conditional loop-back to the agent before review
      - "approval" interrupts for human input and has conditional routing
      - "tool_done" is the terminal node for tool-only pipelines
      - save_memory is auto-appended after approval
    """
    node_registry = _get_node_registry()
    builder = StateGraph(AgentState)

    # Normalize: ensure tool_done exists for simple pipelines
    if pipeline and pipeline[-1] not in ("approval", "tool_done"):
        pipeline = list(pipeline) + ["tool_done"]

    # Add save_memory after approval if not present
    normalized = []
    for i, name in enumerate(pipeline):
        normalized.append(name)
        if name == "approval" and (i + 1 >= len(pipeline) or pipeline[i + 1] != "save_memory"):
            normalized.append("save_memory")
    pipeline = normalized

    # Always need tool_done and save_memory nodes available
    builder.add_node("tool_done", tool_done_node)
    builder.add_node("save_memory", memory_node)

    # ── Meeting phase (prepended before execution pipeline) ──
    builder.add_node("recall", recall_node)
    builder.add_node("await_recall", await_recall_node)
    builder.add_node("meeting", meeting_node)
    builder.add_node("await_plan_approval", await_plan_approval_node)

    # Add all pipeline nodes
    added = {"tool_done", "save_memory", "recall", "await_recall", "meeting", "await_plan_approval"}
    for name in pipeline:
        if name not in added:
            node_fn = node_registry.get(name)
            if node_fn is None:
                continue  # Skip unknown nodes
            builder.add_node(name, node_fn)
            added.add(name)

    # ── Entry: recall → await_recall → meeting → await_plan_approval → first pipeline agent ──
    builder.set_entry_point("recall")
    builder.add_edge("recall", "await_recall")
    builder.add_edge("await_recall", "meeting")
    builder.add_edge("meeting", "await_plan_approval")

    first_agent = pipeline[0] if pipeline else "tool_done"

    # Plan approval routing: approve → execute, modify → re-meet, cancel → end
    def _plan_router(state: AgentState) -> str:
        status = state.get("plan_status", "approved")
        if status == "cancelled":
            return "tool_done"
        if status == "modified":
            return "meeting"
        return first_agent

    builder.add_conditional_edges("await_plan_approval", _plan_router, {
        "tool_done": "tool_done",
        "meeting": "meeting",
        first_agent: first_agent,
    })

    # Build edges
    interrupt_nodes = []
    for i, name in enumerate(pipeline):
        next_name = pipeline[i + 1] if i + 1 < len(pipeline) else None

        if name == "review" and next_name:
            # Review has conditional edge: PASS → next, FAIL → loop back to pre-review agent
            pre_review = pipeline[i - 1] if i > 0 else "copy"
            builder.add_conditional_edges(name, _after_review, {
                "await_approval": next_name if next_name == "approval" else "await_approval",
                "copy": pre_review,  # Loop back
            })

        elif name == "approval":
            interrupt_nodes.append(name)
            # Approval conditional: approve → save_memory, reject → loop back
            pre_review_idx = max(0, i - 2)  # Agent before review
            loop_target = pipeline[pre_review_idx] if pre_review_idx < len(pipeline) else "copy"
            targets = {"save_memory": "save_memory", "copy": loop_target}
            builder.add_conditional_edges(name, _after_approval, targets)

        elif name == "save_memory":
            builder.add_edge(name, END)

        elif name == "tool_done":
            builder.add_edge(name, END)

        elif next_name:
            builder.add_edge(name, next_name)

    checkpointer = get_checkpointer()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=list(set(interrupt_nodes + ["await_plan_approval", "await_recall"])),
    )


# Default graph instance (backward compatible)
graph = build_graph()

