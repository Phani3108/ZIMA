"""
History API — conversation archive endpoints.

GET  /history?team_id=...&user_id=...&limit=10  → recent sessions
GET  /history/similar?team_id=...&brief=...      → semantically similar past sessions
GET  /history/{session_id}?team_id=...           → full session detail (incl. blob messages)
"""

from fastapi import APIRouter, Query

from zeta_ima.memory.conversation_archive import (
    get_recent_sessions,
    get_session_detail,
    get_similar_sessions,
)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def list_sessions(
    team_id: str = Query(...),
    user_id: str = Query(""),
    limit: int = Query(10, ge=1, le=100),
):
    """List recent archived sessions for a team."""
    sessions = await get_recent_sessions(team_id=team_id, user_id=user_id, limit=limit)
    return {"sessions": sessions, "count": len(sessions)}


@router.get("/similar")
async def similar_sessions(
    team_id: str = Query(...),
    brief: str = Query(...),
    limit: int = Query(3, ge=1, le=20),
):
    """Find past sessions with similar briefs."""
    results = await get_similar_sessions(team_id=team_id, brief=brief, limit=limit)
    return {"similar": results, "count": len(results)}


@router.get("/{session_id}")
async def session_detail(
    session_id: str,
    team_id: str = Query(""),
):
    """Fetch full session details including messages."""
    detail = await get_session_detail(session_id=session_id, team_id=team_id)
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    return detail
