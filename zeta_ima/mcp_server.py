"""
Zeta IMA — MCP Server

Exposes agency brain, skills, task queue, and ingest as MCP tools
for LLMs and external agents to consume.

Run:  python -m zeta_ima.mcp_server         (stdio)
      python -m zeta_ima.mcp_server --http   (streamable-http on :9100/mcp)
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

# ── Lifespan — initialise shared services ────────────────────────────────────

@asynccontextmanager
async def lifespan(server):
    """Start Redis, PostgreSQL, Qdrant connections before serving tools."""
    from zeta_ima.memory.session import init_session_store
    from zeta_ima.memory.brain import init_brain_db
    from zeta_ima.memory.learning import init_learning_db
    from zeta_ima.ingest.pipeline import init_ingest_db

    await init_session_store()
    await init_brain_db()
    await init_learning_db()
    await init_ingest_db()
    yield

mcp = FastMCP(
    "Zeta IMA",
    stateless_http=True,
    json_response=True,
    lifespan=lifespan,
)


# ── Brain tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def query_brain(
    query: str,
    category: str | None = None,
    level: str | None = None,
    top_k: int = 8,
) -> list[dict]:
    """Search the Zeta IMA agency brain for relevant knowledge — brand voice, copy patterns, strategy insights, audience data."""
    from zeta_ima.memory.brain import AgencyBrain
    brain = AgencyBrain()
    return await brain.query(query, category=category, level=level, top_k=top_k)


@mcp.tool()
async def contribute_brain(
    text: str,
    category: str = "general",
    level: str = "zeta",
    tags: list[str] | None = None,
    confidence: float = 0.8,
) -> dict:
    """Add a knowledge item to the agency brain. Categories: brand_voice, copy_pattern, strategy, audience, campaign, tactical, design, research, general."""
    from zeta_ima.memory.brain import AgencyBrain
    brain = AgencyBrain()
    return await brain.contribute(
        {"text": text, "category": category, "level": level, "tags": tags or [], "confidence": confidence},
    )


# ── Skills tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def list_skills(query: str | None = None) -> list[dict]:
    """List all available marketing skills, optionally filtered by search query."""
    from zeta_ima.skills.registry import skill_registry
    all_skills = skill_registry.list_skills()
    if query:
        q = query.lower()
        all_skills = [
            s for s in all_skills
            if q in s.get("name", "").lower() or q in s.get("description", "").lower()
        ]
    return all_skills


@mcp.tool()
async def execute_skill(
    skill_id: str,
    prompt_id: str,
    variables: dict[str, str],
    name: str | None = None,
) -> dict:
    """Execute a marketing skill with the given variables. Returns the generated output and workflow metadata."""
    from zeta_ima.skills.executor import run_skill
    return await run_skill(
        skill_id=skill_id,
        prompt_id=prompt_id,
        variables=variables,
        user_id="mcp",
        name=name,
    )


# ── Task queue tools ─────────────────────────────────────────────────────────

@mcp.tool()
async def list_tasks(
    status: str | None = None,
    pipeline: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List tasks from the orchestrator queue, optionally filtered by status (queued, running, completed, failed) or pipeline."""
    from zeta_ima.orchestrator.queue import list_tasks as _list
    return await _list(status=status, pipeline_name=pipeline, limit=limit)


@mcp.tool()
async def create_task(
    title: str,
    description: str,
    priority: int = 2,
) -> dict:
    """Create and enqueue a new task. Priority: 1=high, 2=normal, 3=low. The orchestrator auto-routes to the best pipeline."""
    from zeta_ima.orchestrator.queue import create_task as _create
    from zeta_ima.orchestrator.router import route_task

    routing = await route_task(f"{title}. {description}")
    task_id = await _create(
        title=title,
        description=description,
        requester_id="mcp",
        priority=priority,
        pipeline_name=routing.pipeline_name if routing else None,
        pipeline=routing.pipeline if routing else None,
        routing_rationale=routing.rationale if routing else None,
    )
    return {"id": task_id, "status": "queued", "pipeline": routing.pipeline_name if routing else None}


# ── Ingest tool ──────────────────────────────────────────────────────────────

@mcp.tool()
async def ingest_url(url: str) -> dict:
    """Ingest a URL into the knowledge base. Extracts text, chunks, embeds, and stores for RAG retrieval."""
    from zeta_ima.ingest.pipeline import ingest_url as _ingest_url
    import uuid
    job_id = str(uuid.uuid4())
    asyncio.create_task(_ingest_url(job_id, url))
    return {"job_id": job_id, "status": "processing", "url": url}


# ── Search knowledge base ───────────────────────────────────────────────────

@mcp.tool()
async def search_knowledge(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Search the ingested knowledge base (documents, URLs, Confluence pages) for relevant content."""
    from zeta_ima.memory.brand import _qdrant, _embed
    from zeta_ima.config import settings

    embedding = await _embed(query)
    hits = _qdrant.search(
        collection_name=settings.qdrant_kb_collection,
        query_vector=embedding,
        limit=top_k,
        with_payload=True,
    )
    return [
        {**h.payload, "score": round(h.score, 4)}
        for h in hits
        if h.score >= 0.35
    ]


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = "streamable-http" if "--http" in sys.argv else "stdio"
    port = 9100 if transport == "streamable-http" else None
    kwargs: dict[str, Any] = {"transport": transport}
    if port:
        kwargs["port"] = port
    mcp.run(**kwargs)
