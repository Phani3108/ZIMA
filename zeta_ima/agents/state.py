from typing import Annotated, List, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── Conversation history (short-term, stored in Redis via LangGraph checkpointer) ──
    # add_messages reducer merges new messages rather than overwriting, so parallel
    # nodes can never clobber conversation history.
    messages: Annotated[List[dict], add_messages]

    # Active work state
    current_brief: str          # Brief the user submitted this session
    drafts: List[dict]          # All drafts generated this session: [{"text": ..., "iteration": n}]
    current_draft: dict         # Draft currently under review
    review_result: dict         # Output of review_node: {"raw": ..., "passed": bool, "scores": {...}}
    iteration_count: int        # How many drafts generated this session

    # User context (loaded from PostgreSQL at session start)
    user_id: str
    user_teams_id: str          # Teams user object ID (from activity.from_property.id)
    active_campaign_id: Optional[str]  # Links session to a long-lived campaign

    # Workflow control
    stage: str                  # "drafting" | "reviewing" | "awaiting_approval" | "done"
    approval_decision: Optional[str]   # "approve" | "reject"
    approval_comment: Optional[str]    # Optional human feedback on approval/reject

    # Brand context (injected from Qdrant, refreshed per copy request)
    brand_examples: List[str]   # Top-K approved outputs semantically similar to this brief

    # Multi-agent orchestration (Phase 2)
    intent: str                 # Primary intent: "copy" | "jira" | "confluence" | "github" | "canva" | "research"
    route_to: List[str]         # All intents for this request (multi-intent)
    tool_results: dict          # Accumulated tool agent results: {jira_create: {...}, canva: {...}}
    kb_context: List[str]       # Knowledge base chunks from research_node

    # ── A2A Pipeline (Genesis v2) ──
    pipeline: List[str]         # Ordered agent chain: ["research", "pm", "copy", "design", "review", "approval"]
    pipeline_index: int         # Current position in the pipeline
    agent_messages: List[dict]  # A2A messages exchanged between agents (AgentMessage dicts)

    # ── Agency Brain context (Genesis v2) ──
    brain_context: List[str]    # Knowledge from the aggregated agency brain
