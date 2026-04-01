"""
Research node — searches knowledge_base, agency brain, and injects results as context.
Runs before all other agents to provide grounding context.
"""

from openai import AsyncOpenAI

from zeta_ima.agents.state import AgentState
from zeta_ima.config import settings
from zeta_ima.memory.brand import _qdrant, _openai


async def research_node(state: AgentState) -> dict:
    """Search knowledge_base + agency brain for relevant context."""
    brief = state.get("current_brief", "")
    if not brief:
        return {"kb_context": [], "brain_context": []}

    # Embed the brief
    resp = await _openai.embeddings.create(model="text-embedding-3-small", input=brief)
    vector = resp.data[0].embedding

    # Search knowledge_base collection
    results = _qdrant.search(
        collection_name=settings.qdrant_kb_collection,
        query_vector=vector,
        limit=settings.kb_context_top_k,
    )

    kb_context = [r.payload.get("text", "") for r in results if r.payload.get("text")]

    # Search agency brain (Genesis v2)
    brain_context = []
    try:
        from zeta_ima.memory.brain import agency_brain
        brain_results = await agency_brain.query(brief, top_k=5)
        brain_context = [r["text"] for r in brain_results if r.get("text")]
    except Exception:
        pass  # Brain may not be initialized yet

    msg_parts = []
    if kb_context:
        msg_parts.append(f"{len(kb_context)} KB chunks")
    if brain_context:
        msg_parts.append(f"{len(brain_context)} brain insights")

    return {
        "kb_context": kb_context,
        "brain_context": brain_context,
        "messages": [
            {
                "role": "assistant",
                "content": f"[Research] Found {', '.join(msg_parts) if msg_parts else 'no context'}.",
            }
        ] if msg_parts else [],
    }
