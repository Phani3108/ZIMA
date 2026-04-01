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

from zeta_ima.agents.nodes.approval_node import approval_node
from zeta_ima.agents.nodes.canva_node import canva_node
from zeta_ima.agents.nodes.confluence_node import confluence_node
from zeta_ima.agents.nodes.copy_node import copy_node
from zeta_ima.agents.nodes.jira_node import jira_node
from zeta_ima.agents.nodes.memory_node import memory_node
from zeta_ima.agents.nodes.research_node import research_node
from zeta_ima.agents.nodes.review_node import review_node
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
    }


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

def build_pipeline_graph(pipeline: list[str]):
    """
    Build a LangGraph from an ordered pipeline of agent names.

    The pipeline comes from the orchestrator router. Examples:
      ["research", "pm", "copy", "design", "review", "approval"]
      ["research", "copy", "review", "approval"]
      ["research", "jira", "tool_done"]

    Special handling:
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

    # Always need tool_done node available
    builder.add_node("tool_done", tool_done_node)
    builder.add_node("save_memory", memory_node)

    # Add all pipeline nodes
    added = {"tool_done", "save_memory"}
    for name in pipeline:
        if name not in added:
            node_fn = node_registry.get(name)
            if node_fn is None:
                continue  # Skip unknown nodes
            builder.add_node(name, node_fn)
            added.add(name)

    # Set entry point
    builder.set_entry_point(pipeline[0])

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
        interrupt_before=interrupt_nodes or ["await_approval"],
    )


# Default graph instance (backward compatible)
graph = build_graph()

