"""
Agency Brain — Phase 2.3

The aggregated, always-on knowledge base for the full agency.
All agents can query it; approved outputs and distilled signals contribute to it.

Storage:
  - Qdrant collection  "agency_brain"  — vector search
  - PostgreSQL table   "brain_contributions" — provenance + conflict tracking

Conflict resolution:
  1. latest_wins     — same category + high similarity → newer wins
  2. role_weight     — higher role_weight contributions override lower
  3. manual          — items flagged "conflict" surfaced in UI for human resolution
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from zeta_ima.config import settings
from zeta_ima.integrations.vault import vault

log = logging.getLogger(__name__)

BRAIN_COLLECTION = "agency_brain"
SIMILARITY_OVERRIDE = 0.92   # ≥ this → latest_wins merge
SIMILARITY_CONFLICT = 0.82   # ≥ this (but < override) → flag_conflict

VALID_CATEGORIES = {
    "general", "brand_voice", "copy_pattern", "strategy",
    "audience", "campaign", "tactical", "design", "research",
}
VALID_LEVELS = {"zeta", "team", "personal"}

# Role weights for conflict resolution
ROLE_WEIGHTS: dict[str, float] = {
    "admin": 1.0,
    "manager": 0.85,
    "strategist": 0.75,
    "copywriter": 0.65,
    "designer": 0.65,
    "member": 0.5,
    "system": 0.9,
}


# ── DB helpers ───────────────────────────────────────────────────────────────

async def init_brain_db() -> None:
    """Create brain vector collection and PostgreSQL table on startup."""
    from zeta_ima.memory.session import _pg_pool
    from zeta_ima.infra.vector_store import get_vector_store

    vs = get_vector_store()
    vs.ensure_collection(BRAIN_COLLECTION, vector_size=1536)

    # PostgreSQL
    pool = await _pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_contributions (
                id              TEXT PRIMARY KEY,
                text            TEXT NOT NULL,
                category        TEXT NOT NULL DEFAULT 'general',
                level           TEXT NOT NULL DEFAULT 'zeta',
                confidence      FLOAT NOT NULL DEFAULT 0.8,
                role_weight     FLOAT NOT NULL DEFAULT 0.5,
                contributed_by  TEXT,
                tags            JSONB DEFAULT '[]',
                status          TEXT NOT NULL DEFAULT 'active',
                supersedes      TEXT,
                qdrant_id       TEXT,
                created_at      TIMESTAMPTZ DEFAULT now(),
                updated_at      TIMESTAMPTZ DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_bc_category ON brain_contributions(category);
            CREATE INDEX IF NOT EXISTS idx_bc_status   ON brain_contributions(status);
            """
        )


# ── AgencyBrain class ────────────────────────────────────────────────────────

class AgencyBrain:
    """Stateless service object — calls are async and safe to share."""

    # ── Query ────────────────────────────────────────────────────────────────

    async def query(
        self,
        query_text: str,
        category: str | None = None,
        level: str | None = None,
        tags: list[str] | None = None,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:
        """
        Semantic search across the agency brain.

        Args:
            query_text: Natural-language query to embed and search.
            category:   Filter by knowledge category (brand_voice, copy_pattern, etc.).
            level:      Filter by scope level (zeta, team, personal).
            tags:       Filter by one or more tags (ANY match).
            top_k:      Maximum results to return.

        Returns list of dicts with: id, text, category, level, confidence,
        role_weight, contributed_by, tags, score.
        """
        from zeta_ima.memory.session import _get_embedding
        from zeta_ima.infra.vector_store import get_vector_store

        if category and category not in VALID_CATEGORIES:
            log.warning("query: invalid category %r, ignoring filter", category)
            category = None
        if level and level not in VALID_LEVELS:
            log.warning("query: invalid level %r, ignoring filter", level)
            level = None

        embedding = await _get_embedding(query_text)
        vs = get_vector_store()

        # Build simple equality filters for the vector store
        filters: dict[str, Any] = {"status": "active"}
        if category:
            filters["category"] = category
        if level:
            filters["level"] = level

        hits = vs.search(
            collection=BRAIN_COLLECTION,
            query_vector=embedding,
            top_k=top_k,
            filters=filters,
            score_threshold=0.35,
        )

        results = []
        for h in hits:
            payload = h.get("payload", {})
            # Tag filtering: match if any requested tag is present (post-filter)
            if tags and not any(t in payload.get("tags", []) for t in tags):
                continue
            results.append({**payload, "score": h["score"], "id": h["id"]})

        log.debug("brain query: %d results for %r", len(results), query_text[:60])
        return results

    # ── Contribute ───────────────────────────────────────────────────────────

    async def contribute(
        self,
        item: dict[str, Any],
        user_id: str = "system",
        user_role: str = "member",
    ) -> dict[str, Any]:
        """
        Add or update a knowledge item in the brain.

        Conflict resolution:
          - similarity ≥ SIMILARITY_OVERRIDE  → latest_wins merge (replace existing)
          - SIMILARITY_CONFLICT ≤ sim < SIMILARITY_OVERRIDE → flag for manual review
          - similarity < SIMILARITY_CONFLICT   → add as new entry

        Returns: {"id": str, "action": "created"|"merged"|"conflict"}
        """
        from zeta_ima.memory.session import _pg_pool, _get_embedding
        from zeta_ima.infra.vector_store import get_vector_store

        text = item.get("text", "").strip()
        if not text:
            return {"id": "", "action": "skipped"}

        category = item.get("category", "general")
        level = item.get("level", "zeta")
        if category not in VALID_CATEGORIES:
            log.warning("contribute: invalid category %r, defaulting to 'general'", category)
            category = "general"
        if level not in VALID_LEVELS:
            log.warning("contribute: invalid level %r, defaulting to 'zeta'", level)
            level = "zeta"

        rw = ROLE_WEIGHTS.get(user_role, 0.5)
        embedding = await _get_embedding(text)
        vs = get_vector_store()
        pool = await _pg_pool()

        # Check for near-duplicates
        hits = vs.search(
            collection=BRAIN_COLLECTION,
            query_vector=embedding,
            top_k=3,
        )

        entry_id = str(uuid.uuid4())
        action = "created"
        supersedes_id = None

        for h in hits:
            payload = h.get("payload", {})
            existing_rw = payload.get("role_weight", 0.5)
            if h["score"] >= SIMILARITY_OVERRIDE:
                # latest_wins: only override if our role_weight ≥ existing
                if rw >= existing_rw:
                    # Soft-delete old entry
                    vs.set_payload(
                        collection=BRAIN_COLLECTION,
                        point_id=h["id"],
                        payload={"status": "superseded"},
                    )
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE brain_contributions SET status='superseded', updated_at=now() WHERE qdrant_id=$1",
                            str(h["id"]),
                        )
                    supersedes_id = str(h["id"])
                    action = "merged"
                    log.info("brain merge: %s supersedes %s", entry_id, supersedes_id)
                else:
                    # Incoming has lower authority — flag as conflict for human review
                    action = "conflict_skipped"
                    log.info("brain conflict_skipped: incoming rw=%.2f < existing rw=%.2f", rw, existing_rw)
                    return {"id": str(h["id"]), "action": action}
                break
            elif h["score"] >= SIMILARITY_CONFLICT:
                action = "conflict"
                log.info("brain conflict flagged: similarity %.4f for incoming text", h["score"])
                # Still store but mark as conflict
                break

        payload = {
            "text": text,
            "category": category,
            "level": level,
            "confidence": float(item.get("confidence", 0.75)),
            "role_weight": rw,
            "contributed_by": user_id,
            "tags": item.get("tags", []),
            "status": "conflict" if action == "conflict" else "active",
            "supersedes": supersedes_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        vs.upsert(
            collection=BRAIN_COLLECTION,
            point_id=entry_id,
            vector=embedding,
            payload=payload,
        )

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO brain_contributions
                  (id, text, category, level, confidence, role_weight,
                   contributed_by, tags, status, supersedes, qdrant_id)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                """,
                entry_id, text, category, level,
                payload["confidence"], rw, user_id,
                json.dumps(item.get("tags", [])),
                payload["status"], supersedes_id, entry_id,
            )

        # Audit trail
        await self._audit(user_id, action, entry_id, {"category": category, "level": level})
        return {"id": entry_id, "action": action}

    # ── Batch Contribute ─────────────────────────────────────────────────────

    async def batch_contribute(
        self,
        items: list[dict[str, Any]],
        user_id: str = "system",
        user_role: str = "member",
    ) -> list[dict[str, Any]]:
        """Contribute multiple knowledge items. Returns a result per item."""
        results = []
        for item in items:
            result = await self.contribute(item, user_id=user_id, user_role=user_role)
            results.append(result)
        log.info("batch_contribute: %d items processed for user %s", len(results), user_id)
        return results

    # ── List conflicts ───────────────────────────────────────────────────────

    async def list_conflicts(self) -> list[dict[str, Any]]:
        """Return all knowledge items currently flagged as conflicts."""
        from zeta_ima.memory.session import _pg_pool

        pool = await _pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, text, category, level, confidence, role_weight,
                       contributed_by, tags, created_at
                FROM brain_contributions
                WHERE status = 'conflict'
                ORDER BY created_at DESC
                LIMIT 100
                """
            )
        return [dict(r) for r in rows]

    # ── Resolve conflict ─────────────────────────────────────────────────────

    async def resolve_conflict(
        self,
        entry_id: str,
        resolution: str,   # "accept" | "reject"
        resolved_by: str,
    ) -> None:
        """
        Human resolution: accept keeps the entry active; reject soft-deletes it.
        Also updates the vector store payload status.
        """
        from zeta_ima.memory.session import _pg_pool
        from zeta_ima.infra.vector_store import get_vector_store

        new_status = "active" if resolution == "accept" else "rejected"
        pool = await _pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT qdrant_id FROM brain_contributions WHERE id=$1", entry_id
            )
            if not row:
                return
            qdrant_id = row["qdrant_id"]
            await conn.execute(
                "UPDATE brain_contributions SET status=$1, updated_at=now() WHERE id=$2",
                new_status, entry_id,
            )

        vs = get_vector_store()
        vs.set_payload(
            collection=BRAIN_COLLECTION,
            point_id=qdrant_id,
            payload={"status": new_status},
        )
        log.info("conflict resolved: %s → %s by %s", entry_id, new_status, resolved_by)
        await self._audit(resolved_by, f"conflict_{resolution}", entry_id, {"new_status": new_status})

    # ── Compact ──────────────────────────────────────────────────────────────

    async def compact(self) -> dict[str, int]:
        """Sprint compaction + cleanup of superseded/rejected entries from Qdrant."""
        from zeta_ima.memory.distiller import compact_sprint
        result = await compact_sprint()
        cleaned = await self.cleanup_stale()
        result["stale_cleaned"] = cleaned
        return result

    # ── Statistics ────────────────────────────────────────────────────────────

    async def statistics(self) -> dict[str, Any]:
        """Return health stats: total entries, per-category counts, conflict count."""
        from zeta_ima.memory.session import _pg_pool

        pool = await _pg_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT count(*) FROM brain_contributions WHERE status='active'"
            )
            by_category = await conn.fetch(
                "SELECT category, count(*) as cnt FROM brain_contributions WHERE status='active' GROUP BY category ORDER BY cnt DESC"
            )
            by_level = await conn.fetch(
                "SELECT level, count(*) as cnt FROM brain_contributions WHERE status='active' GROUP BY level ORDER BY cnt DESC"
            )
            conflicts = await conn.fetchval(
                "SELECT count(*) FROM brain_contributions WHERE status='conflict'"
            )
            superseded = await conn.fetchval(
                "SELECT count(*) FROM brain_contributions WHERE status='superseded'"
            )
        return {
            "total_active": total,
            "conflicts_pending": conflicts,
            "superseded": superseded,
            "by_category": {r["category"]: r["cnt"] for r in by_category},
            "by_level": {r["level"]: r["cnt"] for r in by_level},
        }

    # ── Cleanup stale entries ─────────────────────────────────────────────────

    async def cleanup_stale(self, days_old: int = 30) -> int:
        """Remove superseded/rejected entries older than `days_old` from vector store."""
        from zeta_ima.memory.session import _pg_pool
        from zeta_ima.infra.vector_store import get_vector_store

        pool = await _pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, qdrant_id FROM brain_contributions
                WHERE status IN ('superseded', 'rejected')
                  AND updated_at < now() - ($1 || ' days')::interval
                """,
                str(days_old),
            )
        if not rows:
            return 0

        vs = get_vector_store()
        qdrant_ids = [r["qdrant_id"] for r in rows if r["qdrant_id"]]
        pg_ids = [r["id"] for r in rows]

        if qdrant_ids:
            vs.delete_points(collection=BRAIN_COLLECTION, point_ids=qdrant_ids)

        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM brain_contributions WHERE id = ANY($1::text[])",
                pg_ids,
            )

        log.info("cleanup_stale: removed %d entries older than %d days", len(pg_ids), days_old)
        return len(pg_ids)

    # ── Audit helper ─────────────────────────────────────────────────────────

    @staticmethod
    async def _audit(actor: str, action: str, resource_id: str, details: dict[str, Any]) -> None:
        try:
            from zeta_ima.memory.audit import audit_log
            await audit_log.record(
                actor=actor,
                action=f"brain_{action}",
                resource_type="brain_contribution",
                resource_id=resource_id,
                details=details,
            )
        except Exception:
            log.debug("audit recording skipped", exc_info=True)


# ── Singleton ────────────────────────────────────────────────────────────────

agency_brain = AgencyBrain()
