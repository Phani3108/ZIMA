"""
Scores API — campaign score ingestion and retrieval.

POST /scores/upload           → Excel upload
POST /scores/manual           → Manual form entry
POST /scores/sync/{source}    → API pull (mailchimp, ga4, linkedin)
GET  /scores/campaign/{id}    → Get scores for a campaign
GET  /scores/trend             → Score trend data
"""

from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel

from zeta_ima.memory.scores import (
    get_campaign_score,
    get_score_trend,
    ingest_scores_api,
    ingest_scores_excel,
    ingest_scores_manual,
)

router = APIRouter(prefix="/scores", tags=["scores"])


class ManualScoreInput(BaseModel):
    team_id: str
    campaign_id: str
    workflow_id: str = ""
    metrics: dict = {}
    composite_score: float = 0.0
    ingested_by: str = ""
    notes: str = ""


class ApiSyncInput(BaseModel):
    team_id: str
    campaign_id: str = ""
    credentials: dict = {}


@router.post("/upload")
async def upload_scores(
    team_id: str = Query(...),
    ingested_by: str = Query(""),
    file: UploadFile = File(...),
):
    """Upload an Excel file with campaign scores."""
    data = await file.read()
    ids = await ingest_scores_excel(team_id=team_id, file_bytes=data, ingested_by=ingested_by)
    return {"ingested": len(ids), "entry_ids": ids}


@router.post("/manual")
async def manual_score(body: ManualScoreInput):
    """Submit scores manually via form."""
    entry_id = await ingest_scores_manual(
        team_id=body.team_id,
        campaign_id=body.campaign_id,
        workflow_id=body.workflow_id,
        metrics=body.metrics,
        composite_score=body.composite_score,
        ingested_by=body.ingested_by,
        notes=body.notes,
    )
    return {"entry_id": entry_id}


@router.post("/sync/{source}")
async def sync_scores(source: str, body: ApiSyncInput):
    """Pull scores from an analytics API (mailchimp, ga4, linkedin)."""
    ids = await ingest_scores_api(
        team_id=body.team_id,
        source=source,
        campaign_id=body.campaign_id,
        credentials=body.credentials,
    )
    return {"source": source, "ingested": len(ids), "entry_ids": ids}


@router.get("/campaign/{campaign_id}")
async def campaign_score(
    campaign_id: str,
    team_id: str = Query(...),
):
    """Get the latest score for a campaign."""
    score = await get_campaign_score(team_id=team_id, campaign_id=campaign_id)
    if not score:
        return {"score": None}
    return {"score": score}


@router.get("/trend")
async def score_trend(
    team_id: str = Query(...),
    campaign_id: str = Query(""),
    limit: int = Query(20, ge=1, le=100),
):
    """Get score trend data."""
    trend = await get_score_trend(team_id=team_id, campaign_id=campaign_id, limit=limit)
    return {"trend": trend, "count": len(trend)}
