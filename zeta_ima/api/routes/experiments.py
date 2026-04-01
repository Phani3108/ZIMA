"""
A/B Experiment routes.

POST   /experiments              → create an experiment with variants
POST   /experiments/{id}/run     → generate outputs for all variants
GET    /experiments               → list experiments
GET    /experiments/{id}          → get experiment with variants
POST   /experiments/{id}/score    → score a variant
POST   /experiments/{id}/conclude → pick winner and conclude
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.experiments import ab_engine

router = APIRouter(prefix="/experiments", tags=["experiments"])


class VariantConfig(BaseModel):
    variant_label: str
    llm_used: Optional[str] = None
    prompt_variation: Optional[str] = None


class CreateExperimentPayload(BaseModel):
    name: str
    brief: str
    variants: list[VariantConfig]
    skill_id: Optional[str] = None
    template_id: Optional[str] = None
    campaign_id: Optional[str] = None
    variables: Optional[dict[str, Any]] = None


class ScorePayload(BaseModel):
    variant_id: str
    score: float
    feedback: str = ""


@router.post("", status_code=201)
async def create_experiment(
    payload: CreateExperimentPayload,
    user: dict = Depends(get_current_user),
) -> dict:
    if len(payload.variants) < 2:
        raise HTTPException(status_code=400, detail="At least 2 variants required")
    return await ab_engine.create_experiment(
        name=payload.name,
        brief=payload.brief,
        created_by=user["sub"],
        variant_configs=[v.model_dump() for v in payload.variants],
        skill_id=payload.skill_id or "",
        template_id=payload.template_id or "",
        campaign_id=payload.campaign_id or "",
        variables=payload.variables,
    )


@router.post("/{experiment_id}/run")
async def run_experiment(
    experiment_id: str,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    try:
        return await ab_engine.run_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("")
async def list_experiments(
    status: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    return await ab_engine.list_experiments(status=status, campaign_id=campaign_id)


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    exp = await ab_engine.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    variants = await ab_engine.get_variants(experiment_id)
    return {**exp, "variants": variants}


@router.post("/{experiment_id}/score")
async def score_variant(
    experiment_id: str,
    payload: ScorePayload,
    user: dict = Depends(get_current_user),
) -> dict:
    try:
        await ab_engine.score_variant(
            variant_id=payload.variant_id,
            score=payload.score,
            feedback=payload.feedback,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"variant_id": payload.variant_id, "score": payload.score}


@router.post("/{experiment_id}/conclude")
async def conclude_experiment(
    experiment_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    try:
        return await ab_engine.conclude_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
