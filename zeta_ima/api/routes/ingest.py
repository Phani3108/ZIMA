"""
Ingest routes — document ingestion via file upload, URL, Confluence, or Teams chat export.

POST /ingest/file          → multipart file upload
POST /ingest/url           → scrape a URL
POST /ingest/confluence    → pull a Confluence page by ID
POST /ingest/teams-chat    → upload a Teams chat JSON export
GET  /ingest/jobs          → list recent ingestion jobs
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from zeta_ima.api.auth import get_current_user
from zeta_ima.ingest.pipeline import (
    create_job,
    ingest_confluence_page,
    ingest_file_bytes,
    ingest_teams_chat,
    ingest_url,
    list_jobs,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_MB = 20


@router.post("/file")
async def upload_file(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict:
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {ALLOWED_EXTENSIONS}")

    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_MB}MB limit")

    job_id = await create_job("file", filename)
    background.add_task(ingest_file_bytes, job_id, content, filename)
    return {"job_id": job_id, "status": "pending", "source": filename}


class UrlPayload(BaseModel):
    url: str


@router.post("/url")
async def ingest_url_endpoint(
    payload: UrlPayload,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    job_id = await create_job("url", payload.url)
    background.add_task(ingest_url, job_id, payload.url)
    return {"job_id": job_id, "status": "pending", "source": payload.url}


class ConfluencePayload(BaseModel):
    page_id: str


@router.post("/confluence")
async def ingest_confluence_endpoint(
    payload: ConfluencePayload,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    job_id = await create_job("confluence", payload.page_id)
    background.add_task(ingest_confluence_page, job_id, payload.page_id)
    return {"job_id": job_id, "status": "pending", "source": payload.page_id}


@router.post("/teams-chat")
async def ingest_teams_chat_endpoint(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict:
    content = await file.read()
    job_id = await create_job("teams_chat", file.filename or "teams_export.json")
    background.add_task(ingest_teams_chat, job_id, content, file.filename or "teams_export.json")
    return {"job_id": job_id, "status": "pending", "source": file.filename}


@router.get("/jobs")
async def get_jobs(user: dict = Depends(get_current_user)) -> list[dict]:
    jobs = await list_jobs(limit=50)
    # Convert datetime to string for JSON
    for j in jobs:
        for k in ("created_at", "completed_at"):
            if j.get(k):
                j[k] = str(j[k])
    return jobs
