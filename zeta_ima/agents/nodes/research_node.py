"""
Research node — searches knowledge_base, agency brain, and injects results as context.
Runs before all other agents to provide grounding context.
"""

from zeta_ima.agents.state import AgentState
from zeta_ima.config import settings, get_openai_client
from zeta_ima.infra.vector_store import get_vector_store
from zeta_ima.orchestrator.a2a import emit_step


async def research_node(state: AgentState) -> dict:
    """Search knowledge_base + agency brain for relevant context."""
    brief = state.get("current_brief", "")
    if not brief:
        return {"kb_context": [], "brain_context": []}

    agent_messages = list(state.get("agent_messages", []))

    # Step 1/3: Searching knowledge base
    agent_messages.append(emit_step("research", "Searching knowledge base", 0, 3, "started").to_dict())

    # Embed the brief
    client = get_openai_client()
    resp = await client.embeddings.create(model=settings.embedding_model, input=brief)
    vector = resp.data[0].embedding

    # Search knowledge_base collection
    vs = get_vector_store()
    results = vs.search(
        collection_name=settings.qdrant_kb_collection,
        query_vector=vector,
        limit=settings.kb_context_top_k,
    )

    kb_context = [r.get("text", "") for r in results if r.get("text")]
    agent_messages.append(emit_step("research", "Searching knowledge base", 0, 3, "completed", f"Found {len(kb_context)} KB chunks").to_dict())

    # Step 2/3: Searching agency brain
    agent_messages.append(emit_step("research", "Searching agency brain", 1, 3, "started").to_dict())
    brain_context = []
    try:
        from zeta_ima.memory.brain import agency_brain
        brain_results = await agency_brain.query(brief, top_k=5)
        brain_context = [r["text"] for r in brain_results if r.get("text")]
    except Exception:
        pass  # Brain may not be initialized yet
    agent_messages.append(emit_step("research", "Searching agency brain", 1, 3, "completed", f"Found {len(brain_context)} brain insights").to_dict())

    # Step 3/3: Research complete
    msg_parts = []
    if kb_context:
        msg_parts.append(f"{len(kb_context)} KB chunks")
    if brain_context:
        msg_parts.append(f"{len(brain_context)} brain insights")
    agent_messages.append(emit_step("research", "Research complete", 2, 3, "completed", ", ".join(msg_parts) if msg_parts else "No context found").to_dict())

    return {
        "kb_context": kb_context,
        "brain_context": brain_context,
        "agent_messages": agent_messages,
        "messages": [
            {
                "role": "assistant",
                "content": f"[Research] Found {', '.join(msg_parts) if msg_parts else 'no context'}.",
            }
        ] if msg_parts else [],
    }
