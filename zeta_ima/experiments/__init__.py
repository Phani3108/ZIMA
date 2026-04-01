"""
A/B Testing — run variant experiments on workflow outputs.

Allows creating experiments that produce multiple variants of copy/design,
then tracking which variant gets approved or scores higher.

Storage: PostgreSQL tables `experiments` and `experiment_variants`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from zeta_ima.config import settings

log = logging.getLogger(__name__)

_async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
_engine = create_async_engine(_async_url, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_metadata = MetaData()

experiments = Table(
    "experiments",
    _metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("brief", Text, nullable=False),
    Column("skill_id", String, default=""),
    Column("template_id", String, default=""),
    Column("campaign_id", String, default=""),
    Column("created_by", String, nullable=False),
    Column("status", String, nullable=False, default="running"),
    # Status: running | concluded
    Column("winner_variant_id", String, default=""),
    Column("variables", JSONB, default={}),
    Column("created_at", DateTime),
    Column("concluded_at", DateTime),
)

experiment_variants = Table(
    "experiment_variants",
    _metadata,
    Column("id", String, primary_key=True),
    Column("experiment_id", String, ForeignKey("experiments.id"), nullable=False),
    Column("variant_label", String, nullable=False),  # e.g. "A", "B", "C"
    Column("llm_used", String, default=""),
    Column("prompt_variation", Text, default=""),  # any prompt tweak
    Column("output_text", Text, default=""),
    Column("workflow_id", String, default=""),
    Column("score", Float, default=0.0),           # manual or auto score (0–10)
    Column("feedback", Text, default=""),
    Column("is_winner", Boolean, default=False),
    Column("created_at", DateTime),
)


async def init_ab_db() -> None:
    """Create experiment tables."""
    async with _engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    log.info("A/B testing DB initialized")


class ABTestEngine:
    """Manages variant experiments."""

    async def create_experiment(
        self,
        name: str,
        brief: str,
        created_by: str,
        variant_configs: list[dict[str, Any]],
        skill_id: str = "",
        template_id: str = "",
        campaign_id: str = "",
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create an experiment with multiple variants.

        Each variant_config dict may contain:
          - variant_label: str (required, e.g. "A", "B")
          - llm_used: str (optional, override LLM for this variant)
          - prompt_variation: str (optional, tweak for this variant)

        Returns the experiment with its variant IDs.
        """
        now = datetime.now(timezone.utc)
        exp_id = str(uuid.uuid4())

        async with _Session() as session:
            await session.execute(
                experiments.insert().values(
                    id=exp_id,
                    name=name,
                    brief=brief,
                    skill_id=skill_id,
                    template_id=template_id,
                    campaign_id=campaign_id,
                    created_by=created_by,
                    status="running",
                    variables=variables or {},
                    created_at=now,
                )
            )

            variant_ids = []
            for vc in variant_configs:
                vid = str(uuid.uuid4())
                variant_ids.append(vid)
                await session.execute(
                    experiment_variants.insert().values(
                        id=vid,
                        experiment_id=exp_id,
                        variant_label=vc.get("variant_label", ""),
                        llm_used=vc.get("llm_used", ""),
                        prompt_variation=vc.get("prompt_variation", ""),
                        created_at=now,
                    )
                )
            await session.commit()

        log.info("Experiment %s created with %d variants", exp_id, len(variant_ids))
        return {"id": exp_id, "name": name, "variant_ids": variant_ids, "status": "running"}

    async def run_experiment(self, experiment_id: str) -> list[dict[str, Any]]:
        """
        Execute all variants: for each variant, run the workflow with its
        specific LLM/prompt and store the output.
        """
        from zeta_ima.agents.llm_router import call_llm
        from zeta_ima.memory.brand import search_brand_examples

        exp = await self.get_experiment(experiment_id)
        if not exp:
            raise ValueError("Experiment not found")

        brief = exp["brief"]
        brand_context = await search_brand_examples(brief)
        brand_text = "\n".join(f"- {ex['text']}" for ex in brand_context) if brand_context else ""

        variants = await self._get_variants(experiment_id)
        results = []

        for v in variants:
            prompt = f"Brief: {brief}"
            if v.get("prompt_variation"):
                prompt += f"\n\nVariation instructions: {v['prompt_variation']}"
            if brand_text:
                prompt += f"\n\nBrand context:\n{brand_text}"

            llm_chain = None
            if v.get("llm_used"):
                llm_chain = [v["llm_used"]]

            try:
                result = await call_llm(
                    prompt=prompt,
                    system="You are an expert marketing copywriter. Write compelling copy for the given brief.",
                    llm_chain=llm_chain,
                )
                output = result.text
                llm_used = result.provider_used
            except Exception as e:
                output = f"[Error: {e}]"
                llm_used = v.get("llm_used", "unknown")

            async with _Session() as session:
                await session.execute(
                    update(experiment_variants)
                    .where(experiment_variants.c.id == v["id"])
                    .values(output_text=output, llm_used=llm_used)
                )
                await session.commit()

            results.append({
                "variant_id": v["id"],
                "label": v["variant_label"],
                "llm_used": llm_used,
                "output_preview": output[:300],
            })

        return results

    async def score_variant(
        self,
        variant_id: str,
        score: float,
        feedback: str = "",
    ) -> None:
        """Score a variant (0–10 scale)."""
        if not 0 <= score <= 10:
            raise ValueError("Score must be 0–10")
        async with _Session() as session:
            await session.execute(
                update(experiment_variants)
                .where(experiment_variants.c.id == variant_id)
                .values(score=score, feedback=feedback)
            )
            await session.commit()

    async def conclude_experiment(self, experiment_id: str) -> dict[str, Any]:
        """
        Conclude an experiment: pick the highest-scored variant as winner.
        If scores are tied, the first variant wins.
        """
        variants = await self._get_variants(experiment_id)
        if not variants:
            raise ValueError("No variants found")

        # Find winner (highest score)
        winner = max(variants, key=lambda v: v.get("score", 0))
        now = datetime.now(timezone.utc)

        async with _Session() as session:
            await session.execute(
                update(experiment_variants)
                .where(experiment_variants.c.id == winner["id"])
                .values(is_winner=True)
            )
            await session.execute(
                update(experiments)
                .where(experiments.c.id == experiment_id)
                .values(
                    status="concluded",
                    winner_variant_id=winner["id"],
                    concluded_at=now,
                )
            )
            await session.commit()

        log.info("Experiment %s concluded, winner: %s", experiment_id, winner["variant_label"])
        return {
            "experiment_id": experiment_id,
            "winner_variant_id": winner["id"],
            "winner_label": winner["variant_label"],
            "winner_score": winner.get("score", 0),
        }

    async def get_experiment(self, experiment_id: str) -> dict | None:
        async with _Session() as session:
            result = await session.execute(
                select(experiments).where(experiments.c.id == experiment_id)
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def list_experiments(
        self,
        status: str | None = None,
        campaign_id: str | None = None,
    ) -> list[dict]:
        stmt = select(experiments).order_by(experiments.c.created_at.desc())
        if status:
            stmt = stmt.where(experiments.c.status == status)
        if campaign_id:
            stmt = stmt.where(experiments.c.campaign_id == campaign_id)
        async with _Session() as session:
            result = await session.execute(stmt)
            return [dict(r._mapping) for r in result.fetchall()]

    async def _get_variants(self, experiment_id: str) -> list[dict]:
        async with _Session() as session:
            result = await session.execute(
                select(experiment_variants)
                .where(experiment_variants.c.experiment_id == experiment_id)
                .order_by(experiment_variants.c.variant_label)
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def get_variants(self, experiment_id: str) -> list[dict]:
        """Public accessor for variant list."""
        return await self._get_variants(experiment_id)


ab_engine = ABTestEngine()
