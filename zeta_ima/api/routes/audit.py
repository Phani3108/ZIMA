"""
Audit trail routes — view action history.

GET /audit                             → recent audit entries
GET /audit/resource/{type}/{id}        → audit trail for a specific resource
GET /audit/workflow/{workflow_id}      → full audit trail for a workflow
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from zeta_ima.api.auth import get_current_user
from zeta_ima.memory.audit import audit_log

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def get_recent_audit(
    limit: int = Query(50, ge=1, le=500),
    action: Optional[str] = Query(None, description="Filter by action type"),
    actor: Optional[str] = Query(None, description="Filter by actor"),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Get recent audit entries."""
    return await audit_log.get_recent(limit=limit, action=action, actor=actor)


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_audit(
    resource_type: str,
    resource_id: str,
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Get audit trail for a specific resource."""
    return await audit_log.get_for_resource(resource_type, resource_id, limit)


@router.get("/workflow/{workflow_id}")
async def get_workflow_audit(
    workflow_id: str,
    limit: int = Query(200, ge=1, le=500),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Get complete audit trail for a workflow (includes all stage events)."""
    return await audit_log.get_for_workflow(workflow_id, limit)
