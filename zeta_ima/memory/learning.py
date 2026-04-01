"""
Learning Memory — two-track learning system (Genesis v2).

Track 1 — Tactical: LLM performance, edit patterns, skill execution optimization.
  Uses Qdrant collection "learning_memory" + PostgreSQL "workflow_outcomes".

Track 2 — Directional: brand direction, strategy, positioning knowledge.
  Uses Qdrant collection "directional_memory" + PostgreSQL "learning_signals".
  Tagged by level: zeta | client | product.

Auto-classification: LLM call extracts directional vs tactical signals from
conversation text at conversation end or on demand.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

log = logging.getLogger(__name__)

COLLECTION_NAME = "learning_memory"
DIRECTIONAL_COLLECTION = "directional_memory"
EMBEDDING_DIMS = 1536

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

# Structured outcome records (tactical)
workflow_outcomes = Table(
    "workflow_outcomes",
    _metadata,
    Column("id", String, primary_key=True),
    Column("workflow_id", String, nullable=False),
    Column("stage_id", String, nullable=False),
    Column("skill_id", String, nullable=False),
    Column("prompt_id", String),
    Column("llm_used", String),
    Column("approved_first_try", Boolean, default=False),
    Column("iterations_needed", Integer, default=1),
    Column("user_feedback", Text),
    Column("scores", JSONB),
    Column("edit_instructions", JSONB),  # List of edit instructions applied
    Column("final_output_length", Integer),
    Column("execution_time_ms", Integer),
    Column("created_at", DateTime),
)

# Learning signals table (directional + tactical, Genesis v2)
learning_signals = Table(
    "learning_signals",
    _metadata,
    Column("id", String, primary_key=True),
    Column("signal_type", String, nullable=False),  # "directional" | "tactical"
    Column("level", String, default="zeta"),         # "zeta" | "client" | "product"
    Column("signal_text", Text, nullable=False),
    Column("source_user_id", String, nullable=False),
    Column("source_interaction_id", String, default=""),
    Column("role_weight", Float, default=1.0),       # Higher = more authoritative role
    Column("supersedes", String, default=""),         # ID of signal this overrides
    Column("confidence", Float, default=0.8),
    Column("tags", JSONB, default=[]),
    Column("created_at", DateTime),
)


async def init_learning_db() -> None:
    """Create learning tables and Qdrant collections."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)

    # Qdrant collections
    try:
        qdrant = QdrantClient(url=settings.qdrant_url)
        existing = {c.name for c in qdrant.get_collections().collections}

        for coll_name in (COLLECTION_NAME, DIRECTIONAL_COLLECTION):
            if coll_name not in existing:
                qdrant.create_collection(
                    collection_name=coll_name,
                    vectors_config=VectorParams(size=EMBEDDING_DIMS, distance=Distance.COSINE),
                )
                log.info(f"Created Qdrant collection: {coll_name}")
    except Exception as e:
        log.warning(f"Failed to create learning memory collections: {e}")


async def record_outcome(
    workflow_id: str,
    stage_id: str,
    skill_id: str,
    prompt_id: str = "",
    llm_used: str = "",
    approved_first_try: bool = False,
    iterations_needed: int = 1,
    user_feedback: str = "",
    scores: dict | None = None,
    edit_instructions: list[str] | None = None,
    final_output: str = "",
    execution_time_ms: int = 0,
) -> str:
    """
    Record a workflow stage outcome for learning.

    Called when a stage reaches "approved" status.
    """
    outcome_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    async with _Session() as session:
        await session.execute(
            workflow_outcomes.insert().values(
                id=outcome_id,
                workflow_id=workflow_id,
                stage_id=stage_id,
                skill_id=skill_id,
                prompt_id=prompt_id,
                llm_used=llm_used,
                approved_first_try=approved_first_try,
                iterations_needed=iterations_needed,
                user_feedback=user_feedback,
                scores=scores or {},
                edit_instructions=edit_instructions or [],
                final_output_length=len(final_output),
                execution_time_ms=execution_time_ms,
                created_at=now,
            )
        )
        await session.commit()

    # Also store in Qdrant for semantic retrieval (if output exists)
    if final_output:
        try:
            from zeta_ima.memory.brand import _embed
            vector = await _embed(final_output[:2000])
            qdrant = QdrantClient(url=settings.qdrant_url)
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=outcome_id,
                        vector=vector,
                        payload={
                            "type": "approved_output",
                            "skill_id": skill_id,
                            "prompt_id": prompt_id,
                            "llm_used": llm_used,
                            "approved_first_try": approved_first_try,
                            "output_preview": final_output[:500],
                            "workflow_id": workflow_id,
                            "created_at": now.isoformat(),
                        },
                    )
                ],
            )
        except Exception as e:
            log.warning(f"Failed to store learning vector: {e}")

    # ── Close the loop: record tactical signal from outcome ──
    try:
        feedback_parts = []
        if edit_instructions:
            feedback_parts.append(f"Edit instructions applied: {'; '.join(edit_instructions[:5])}")
        if user_feedback:
            feedback_parts.append(f"User feedback: {user_feedback}")
        if not approved_first_try:
            feedback_parts.append(f"Required {iterations_needed} iterations to approve")
        if feedback_parts:
            await record_tactical_signal(
                skill_id=skill_id,
                feedback=". ".join(feedback_parts),
                source_user_id="system",
                outcome={
                    "workflow_id": workflow_id,
                    "approved_first_try": approved_first_try,
                    "iterations_needed": iterations_needed,
                    "llm_used": llm_used,
                },
            )
    except Exception as e:
        log.warning(f"Failed to record tactical signal from outcome: {e}")

    return outcome_id


async def get_best_llm_for_skill(skill_id: str) -> Optional[str]:
    """
    Analyze past outcomes to find the LLM with the highest
    first-pass approval rate for a given skill.

    Returns the LLM name or None if no data.
    """
    async with _Session() as session:
        result = await session.execute(
            select(
                workflow_outcomes.c.llm_used,
                workflow_outcomes.c.approved_first_try,
            ).where(
                workflow_outcomes.c.skill_id == skill_id,
                workflow_outcomes.c.llm_used.isnot(None),
            )
        )
        rows = result.fetchall()

    if not rows:
        return None

    # Calculate approval rate per LLM
    stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "approved": 0})
    for row in rows:
        llm = row.llm_used
        stats[llm]["total"] += 1
        if row.approved_first_try:
            stats[llm]["approved"] += 1

    # Need at least 3 samples
    eligible = {
        llm: s["approved"] / s["total"]
        for llm, s in stats.items()
        if s["total"] >= 3
    }

    if not eligible:
        return None

    best = max(eligible, key=eligible.get)  # type: ignore
    log.info(
        f"Best LLM for '{skill_id}': {best} "
        f"({eligible[best]*100:.0f}% first-pass approval, "
        f"n={stats[best]['total']})"
    )
    return best


async def get_common_edits(skill_id: str, prompt_id: str = "", limit: int = 5) -> list[str]:
    """
    Return common edit instructions for a skill/prompt.

    These can be preemptively applied to future prompts.
    """
    async with _Session() as session:
        q = select(workflow_outcomes.c.edit_instructions).where(
            workflow_outcomes.c.skill_id == skill_id,
            workflow_outcomes.c.edit_instructions != "[]",
        )
        if prompt_id:
            q = q.where(workflow_outcomes.c.prompt_id == prompt_id)

        result = await session.execute(q.limit(100))
        rows = result.fetchall()

    # Flatten and count
    all_edits: list[str] = []
    for row in rows:
        instructions = row.edit_instructions
        if isinstance(instructions, list):
            all_edits.extend(instructions)

    counter = Counter(all_edits)
    return [edit for edit, _ in counter.most_common(limit)]


async def get_past_successes(
    skill_id: str,
    query: str = "",
    top_k: int = 3,
) -> list[dict]:
    """
    Find past successful outputs similar to the given query.

    Uses Qdrant semantic search on the learning_memory collection.
    """
    if not query:
        return []

    try:
        from zeta_ima.memory.brand import _embed
        vector = await _embed(query)
        qdrant = QdrantClient(url=settings.qdrant_url)
        results = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            query_filter=Filter(
                must=[FieldCondition(key="skill_id", match=MatchValue(value=skill_id))]
            ),
            limit=top_k,
        )
        return [
            {
                "output_preview": r.payload.get("output_preview", ""),
                "llm_used": r.payload.get("llm_used", ""),
                "approved_first_try": r.payload.get("approved_first_try", False),
                "score": r.score,
            }
            for r in results
        ]
    except Exception as e:
        log.warning(f"Learning memory search failed: {e}")
        return []


async def get_skill_stats(skill_id: str) -> dict:
    """Get aggregate stats for a skill."""
    async with _Session() as session:
        result = await session.execute(
            select(workflow_outcomes).where(
                workflow_outcomes.c.skill_id == skill_id
            )
        )
        rows = result.fetchall()

    if not rows:
        return {"total_executions": 0}

    total = len(rows)
    approved_first = sum(1 for r in rows if r.approved_first_try)
    avg_iterations = sum(r.iterations_needed for r in rows) / total

    llm_counts = Counter(r.llm_used for r in rows if r.llm_used)

    return {
        "total_executions": total,
        "first_pass_rate": round(approved_first / total * 100, 1),
        "avg_iterations": round(avg_iterations, 1),
        "top_llms": dict(llm_counts.most_common(3)),
    }


# ── Directional Learning (Genesis v2) ─────────────────────────────────────────

_CLASSIFY_SYSTEM = """You are a learning signal classifier for a marketing agency AI.

Given conversation text, extract learning signals and classify each as:
- "directional": about brand direction, positioning, strategy, tone, client goals ("We want to position as premium", "Our clients care about ROI", "Avoid sounding corporate")
- "tactical": about execution quality, specific skills, format preferences ("Make headlines shorter", "LinkedIn posts perform better with 3 bullet points", "This LLM writes better emails")

Each signal also has a level:
- "zeta": about Zeta as a company/agency
- "client": about a specific client or client type  
- "product": about a specific product or campaign

Return a JSON array. Each item: {"type": "directional"|"tactical", "level": "zeta"|"client"|"product", "text": "extracted signal", "confidence": 0.0-1.0, "tags": ["tag1"]}
Return [] if no meaningful signals found. Return ONLY the JSON array."""


async def classify_signal(
    message_text: str,
    source_user_id: str = "",
    source_interaction_id: str = "",
    role_weight: float = 1.0,
) -> list[dict]:
    """
    Extract and classify learning signals from conversation text using LLM.

    Returns list of classified signals ready to store.
    """
    if not message_text or len(message_text.strip()) < 20:
        return []

    import json
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        resp = await client.chat.completions.create(
            model=settings.signal_extraction_model,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": message_text[:3000]},
            ],
            max_tokens=800,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            signals = json.loads(raw[start:end])
            if isinstance(signals, list):
                return [
                    {
                        **s,
                        "source_user_id": source_user_id,
                        "source_interaction_id": source_interaction_id,
                        "role_weight": role_weight,
                    }
                    for s in signals
                    if isinstance(s, dict) and s.get("text")
                ]
    except Exception as e:
        log.warning(f"Signal classification failed: {e}")

    return []


async def record_directional_signal(
    signal_text: str,
    level: str,
    source_user_id: str,
    role_weight: float = 1.0,
    source_interaction_id: str = "",
    confidence: float = 0.8,
    tags: list[str] | None = None,
) -> str:
    """
    Store a directional learning signal (brand direction, strategy, positioning).

    Before storing, checks for semantic conflicts with existing signals.
    Conflicting signals are stored with a supersedes relationship.
    """
    from zeta_ima.memory.brand import _embed

    signal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    vector = await _embed(signal_text[:2000])
    qdrant = QdrantClient(url=settings.qdrant_url)

    # Check for near-duplicate or conflicting signals
    existing = qdrant.search(
        collection_name=DIRECTIONAL_COLLECTION,
        query_vector=vector,
        limit=3,
        score_threshold=0.85,
    )

    supersedes_id = ""
    if existing:
        top = existing[0]
        if top.score > 0.92:
            # Near-duplicate: merge (update existing, don't create new)
            qdrant.set_payload(
                collection_name=DIRECTIONAL_COLLECTION,
                payload={
                    "last_updated": now.isoformat(),
                    "access_count": (top.payload.get("access_count", 0) + 1),
                    "role_weight": max(top.payload.get("role_weight", 1.0), role_weight),
                },
                points=[top.id],
            )
            log.debug(f"Merged directional signal into existing {top.id}")
            return str(top.id)
        elif top.score > 0.85:
            # Potentially contradictory — store new but mark supersedes
            supersedes_id = str(top.id)
            log.info(f"New directional signal supersedes {supersedes_id} (score={top.score:.2f})")

    # Store in Qdrant
    qdrant.upsert(
        collection_name=DIRECTIONAL_COLLECTION,
        points=[
            PointStruct(
                id=signal_id,
                vector=vector,
                payload={
                    "text": signal_text,
                    "level": level,
                    "source_user_id": source_user_id,
                    "confidence": confidence,
                    "role_weight": role_weight,
                    "tags": tags or [],
                    "supersedes": supersedes_id,
                    "created_at": now.isoformat(),
                    "last_updated": now.isoformat(),
                    "access_count": 0,
                },
            )
        ],
    )

    # Store in PostgreSQL
    async with _Session() as session:
        await session.execute(
            learning_signals.insert().values(
                id=signal_id,
                signal_type="directional",
                level=level,
                signal_text=signal_text,
                source_user_id=source_user_id,
                source_interaction_id=source_interaction_id,
                role_weight=role_weight,
                supersedes=supersedes_id,
                confidence=confidence,
                tags=tags or [],
                created_at=now,
            )
        )
        await session.commit()

    return signal_id


async def record_tactical_signal(
    skill_id: str,
    feedback: str,
    source_user_id: str,
    outcome: dict | None = None,
) -> str:
    """Store a tactical learning signal (execution quality, skill performance)."""
    from zeta_ima.memory.brand import _embed

    signal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    async with _Session() as session:
        await session.execute(
            learning_signals.insert().values(
                id=signal_id,
                signal_type="tactical",
                level="zeta",
                signal_text=feedback,
                source_user_id=source_user_id,
                source_interaction_id=outcome.get("workflow_id", "") if outcome else "",
                role_weight=1.0,
                supersedes="",
                confidence=0.9,
                tags=[skill_id],
                created_at=now,
            )
        )
        await session.commit()

    return signal_id


async def get_directional_signals(
    level: str | None = None,
    top_k: int = 20,
) -> list[dict]:
    """Retrieve recent directional signals, optionally filtered by level."""
    q = select(learning_signals).where(
        learning_signals.c.signal_type == "directional"
    ).order_by(
        learning_signals.c.role_weight.desc(),
        learning_signals.c.created_at.desc(),
    ).limit(top_k)

    if level:
        q = q.where(learning_signals.c.level == level)

    async with _Session() as session:
        result = await session.execute(q)
        return [dict(row) for row in result.mappings().fetchall()]


async def record_rejection(
    skill_id: str,
    draft_text: str,
    rejection_comment: str,
    edit_instructions: list[str] | None = None,
    user_id: str = "",
    workflow_id: str = "",
    iteration: int = 1,
) -> str:
    """
    Record a rejection as a negative learning signal.

    This closes the feedback loop: rejections create tactical signals so
    future prompts can preemptively avoid the same mistakes.
    """
    feedback_parts = [f"REJECTED (iteration {iteration})"]
    if rejection_comment:
        feedback_parts.append(f"User said: {rejection_comment}")
    if edit_instructions:
        feedback_parts.append(f"Required fixes: {'; '.join(edit_instructions[:5])}")

    signal_id = await record_tactical_signal(
        skill_id=skill_id,
        feedback=". ".join(feedback_parts),
        source_user_id=user_id,
        outcome={
            "workflow_id": workflow_id,
            "approved_first_try": False,
            "iterations_needed": iteration,
            "rejection": True,
        },
    )
    log.info(
        "Recorded rejection signal %s for skill=%s user=%s",
        signal_id, skill_id, user_id,
    )
    return signal_id


async def persist_reflection_insights(
    skill_id: str,
    reflection_steps: list[dict],
    brief: str = "",
    user_id: str = "system",
) -> int:
    """
    Persist critique patterns from actor-critic reflection into learning memory.

    Each step's improvements become tactical signals so future copies
    avoid the same mistakes.
    """
    persisted = 0
    for step in reflection_steps:
        improvements = step.get("improvements", [])
        critique = step.get("critique", "")
        score = step.get("score", 0)
        if not improvements and not critique:
            continue

        feedback = f"Reflection (score {score:.1f}): {critique}"
        if improvements:
            feedback += f" | Improvements needed: {'; '.join(improvements[:5])}"

        await record_tactical_signal(
            skill_id=skill_id,
            feedback=feedback,
            source_user_id=user_id,
            outcome={"reflection_score": score, "iteration": step.get("iteration", 0)},
        )
        persisted += 1

    if persisted:
        log.info("Persisted %d reflection insights for skill=%s", persisted, skill_id)
    return persisted


async def get_learning_guidance(skill_id: str, brief: str = "", limit: int = 5) -> str:
    """
    Build a learning guidance block for injection into copy prompts.

    Combines common edit patterns + past rejection signals + directional signals
    into a concise instruction block.
    """
    parts: list[str] = []

    # 1. Common edit patterns (tactical)
    edits = await get_common_edits(skill_id, limit=limit)
    if edits:
        parts.append("COMMON CORRECTIONS (apply proactively):")
        for i, edit in enumerate(edits, 1):
            parts.append(f"  {i}. {edit}")

    # 2. Recent tactical rejection patterns
    async with _Session() as session:
        result = await session.execute(
            select(learning_signals.c.signal_text).where(
                learning_signals.c.signal_type == "tactical",
                learning_signals.c.tags.contains([skill_id]),
            ).order_by(
                learning_signals.c.created_at.desc(),
            ).limit(limit)
        )
        rejections = [row.signal_text for row in result.fetchall()]
    if rejections:
        parts.append("\nRECENT FEEDBACK PATTERNS (avoid these issues):")
        for i, rej in enumerate(rejections, 1):
            parts.append(f"  {i}. {rej}")

    # 3. Directional signals at zeta level
    signals = await get_directional_signals(level="zeta", top_k=3)
    if signals:
        parts.append("\nAGENCY DIRECTION:")
        for sig in signals:
            parts.append(f"  - {sig.get('signal_text', '')}")

    return "\n".join(parts) if parts else ""
