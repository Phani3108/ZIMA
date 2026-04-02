"""
Artifact Library API — CRUD, versioning, comments, sharing.

Internal endpoints (team-authenticated):
  GET    /artifacts                   → list team artifacts
  POST   /artifacts                   → create artifact
  GET    /artifacts/:id               → get artifact detail
  PUT    /artifacts/:id               → create new version
  DELETE /artifacts/:id               → delete artifact
  GET    /artifacts/:id/versions      → version history
  GET    /artifacts/:id/comments      → list comments
  POST   /artifacts/:id/comments      → add comment
  POST   /artifacts/:id/share         → create share link
  GET    /artifacts/:id/shares        → list share links
  DELETE /artifacts/shares/:token     → revoke share link

Public (no auth):
  GET    /artifacts/shared/:token     → view artifact via share link
  POST   /artifacts/shared/:token/comments → add comment via share link
  POST   /artifacts/shared/:token/approve  → approve via share link
  POST   /artifacts/shared/:token/reject   → reject via share link
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from zeta_ima.memory.artifacts import artifact_store

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


# ── Request Models ────────────────────────────────────────────────────────────

class CreateArtifactRequest(BaseModel):
    team_id: str
    title: str
    content: str
    content_type: str = "markdown"
    created_by: str = "user"
    source_workflow_id: str | None = None
    source_stage_id: str | None = None
    skill_id: str | None = None
    tags: list[str] = []


class UpdateArtifactRequest(BaseModel):
    content: str
    updated_by: str = "user"
    title: str | None = None
    tags: list[str] | None = None


class AddCommentRequest(BaseModel):
    author: str
    body: str


class CreateShareRequest(BaseModel):
    created_by: str = "user"
    expires_hours: int | None = 72
    allow_comments: bool = True
    allow_approve: bool = False


class ExternalCommentRequest(BaseModel):
    author: str  # reviewer name
    body: str


class ExternalDecisionRequest(BaseModel):
    reviewer: str
    comment: str = ""


# ── Team Endpoints (Authenticated) ───────────────────────────────────────────

@router.get("")
async def list_artifacts(
    team_id: str = Query(...),
    tags: str = Query(""),
    search: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List artifacts for a team with optional filtering."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    items = await artifact_store.list_artifacts(
        team_id=team_id,
        tags=tag_list,
        search=search or None,
        limit=limit,
        offset=offset,
    )
    return {"artifacts": items, "count": len(items)}


@router.post("")
async def create_artifact(req: CreateArtifactRequest):
    """Create a new artifact."""
    aid = await artifact_store.create(
        team_id=req.team_id,
        title=req.title,
        content=req.content,
        content_type=req.content_type,
        created_by=req.created_by,
        source_workflow_id=req.source_workflow_id,
        source_stage_id=req.source_stage_id,
        skill_id=req.skill_id,
        tags=req.tags,
    )
    return {"id": aid, "status": "created"}


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Get full artifact detail including content."""
    artifact = await artifact_store.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.put("/{artifact_id}")
async def update_artifact(artifact_id: str, req: UpdateArtifactRequest):
    """Create a new version of an artifact."""
    try:
        new_id = await artifact_store.create_version(
            artifact_id=artifact_id,
            content=req.content,
            updated_by=req.updated_by,
            title=req.title,
            tags=req.tags,
        )
        return {"id": new_id, "status": "version_created"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str):
    """Delete an artifact."""
    ok = await artifact_store.delete_artifact(artifact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"status": "deleted"}


@router.get("/{artifact_id}/versions")
async def version_history(artifact_id: str):
    """Get the full version chain for an artifact."""
    versions = await artifact_store.get_version_history(artifact_id)
    return {"versions": versions, "count": len(versions)}


# ── Comments ──────────────────────────────────────────────────────────────────

@router.get("/{artifact_id}/comments")
async def list_comments(artifact_id: str, limit: int = Query(100, ge=1, le=500)):
    comments = await artifact_store.list_comments(artifact_id, limit=limit)
    return {"comments": comments, "count": len(comments)}


@router.post("/{artifact_id}/comments")
async def add_comment(artifact_id: str, req: AddCommentRequest):
    cid = await artifact_store.add_comment(
        artifact_id=artifact_id,
        author=req.author,
        body=req.body,
    )
    return {"id": cid, "status": "created"}


# ── Share Links ───────────────────────────────────────────────────────────────

@router.post("/{artifact_id}/share")
async def create_share_link(artifact_id: str, req: CreateShareRequest):
    """Create a share link for external review."""
    artifact = await artifact_store.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    token = await artifact_store.create_share_link(
        artifact_id=artifact_id,
        created_by=req.created_by,
        expires_hours=req.expires_hours,
        allow_comments=req.allow_comments,
        allow_approve=req.allow_approve,
    )
    return {"token": token, "url": f"/review/{token}"}


@router.get("/{artifact_id}/shares")
async def list_share_links(artifact_id: str):
    links = await artifact_store.list_share_links(artifact_id)
    return {"links": links, "count": len(links)}


@router.delete("/shares/{token}")
async def revoke_share_link(token: str):
    ok = await artifact_store.revoke_share_link(token)
    if not ok:
        raise HTTPException(status_code=404, detail="Share link not found")
    return {"status": "revoked"}


# ── Public / External Review Endpoints ────────────────────────────────────────

@router.get("/shared/{token}")
async def get_shared_artifact(token: str):
    """View an artifact via a share token. No auth required."""
    artifact = await artifact_store.get_by_token(token)
    if not artifact:
        raise HTTPException(status_code=404, detail="Link expired or not found")
    permissions = artifact.pop("_share_permissions", {})
    # Strip sensitive fields
    safe = {
        "id": artifact["id"],
        "title": artifact["title"],
        "content": artifact["content"],
        "content_type": artifact["content_type"],
        "version": artifact["version"],
        "tags": artifact.get("tags", []),
        "created_at": artifact.get("created_at"),
        "updated_at": artifact.get("updated_at"),
        "permissions": permissions,
    }
    # Include comments if allowed
    if permissions.get("allow_comments"):
        safe["comments"] = await artifact_store.list_comments(artifact["id"])
    return safe


@router.post("/shared/{token}/comments")
async def add_external_comment(token: str, req: ExternalCommentRequest):
    """Add a comment via share link. No auth required."""
    artifact = await artifact_store.get_by_token(token)
    if not artifact:
        raise HTTPException(status_code=404, detail="Link expired or not found")
    permissions = artifact.get("_share_permissions", {})
    if not permissions.get("allow_comments"):
        raise HTTPException(status_code=403, detail="Comments not allowed on this link")
    cid = await artifact_store.add_comment(
        artifact_id=artifact["id"],
        author=f"[External] {req.author}",
        body=req.body,
        is_external=True,
    )
    # Notify team
    try:
        from zeta_ima.notify.service import notifications
        await notifications.send(
            user_id=f"team:{artifact['team_id']}",
            title=f"External comment on \"{artifact['title']}\"",
            body=f"{req.author}: {req.body[:100]}",
            action_url=f"/artifacts/{artifact['id']}",
            channel="web",
        )
    except Exception:
        pass
    return {"id": cid, "status": "created"}


@router.post("/shared/{token}/approve")
async def approve_shared_artifact(token: str, req: ExternalDecisionRequest):
    """Approve an artifact via share link."""
    artifact = await artifact_store.get_by_token(token)
    if not artifact:
        raise HTTPException(status_code=404, detail="Link expired or not found")
    permissions = artifact.get("_share_permissions", {})
    if not permissions.get("allow_approve"):
        raise HTTPException(status_code=403, detail="Approval not allowed on this link")
    # Record as comment + audit
    await artifact_store.add_comment(
        artifact_id=artifact["id"],
        author=f"[External] {req.reviewer}",
        body=f"✅ APPROVED{': ' + req.comment if req.comment else ''}",
        is_external=True,
    )
    try:
        from zeta_ima.memory.audit import audit_log
        await audit_log.record(
            actor=f"external:{req.reviewer}",
            action="approved",
            resource_type="artifact",
            resource_id=artifact["id"],
            details={"comment": req.comment, "via": "share_link"},
        )
        from zeta_ima.notify.service import notifications
        await notifications.send(
            user_id=f"team:{artifact['team_id']}",
            title=f"Artifact approved: \"{artifact['title']}\"",
            body=f"External reviewer {req.reviewer} approved this artifact",
            action_url=f"/artifacts/{artifact['id']}",
            channel="web",
        )
    except Exception:
        pass
    return {"status": "approved"}


@router.post("/shared/{token}/reject")
async def reject_shared_artifact(token: str, req: ExternalDecisionRequest):
    """Reject an artifact via share link."""
    artifact = await artifact_store.get_by_token(token)
    if not artifact:
        raise HTTPException(status_code=404, detail="Link expired or not found")
    permissions = artifact.get("_share_permissions", {})
    if not permissions.get("allow_approve"):
        raise HTTPException(status_code=403, detail="Review not allowed on this link")
    await artifact_store.add_comment(
        artifact_id=artifact["id"],
        author=f"[External] {req.reviewer}",
        body=f"❌ REJECTED{': ' + req.comment if req.comment else ''}",
        is_external=True,
    )
    try:
        from zeta_ima.memory.audit import audit_log
        await audit_log.record(
            actor=f"external:{req.reviewer}",
            action="rejected",
            resource_type="artifact",
            resource_id=artifact["id"],
            details={"comment": req.comment, "via": "share_link"},
        )
        from zeta_ima.notify.service import notifications
        await notifications.send(
            user_id=f"team:{artifact['team_id']}",
            title=f"Artifact rejected: \"{artifact['title']}\"",
            body=f"External reviewer {req.reviewer} rejected: {req.comment[:100]}",
            action_url=f"/artifacts/{artifact['id']}",
            channel="web",
        )
    except Exception:
        pass
    return {"status": "rejected"}
