"""
Authentication — Teams SSO token verification.
Adapted from RDT 6/orchestrator/auth.py.

Teams SSO flow:
  1. Frontend (Teams tab) calls microsoftTeams.authentication.getAuthToken()
  2. Passes token in Authorization: Bearer <token> header
  3. Backend verifies JWT against Microsoft JWKS endpoint
  4. Returns user info dict

Dev mode: accepts any token, returns a dev user. Set MODE=dev in .env.
"""

import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from zeta_ima.config import settings

security = HTTPBearer(auto_error=False)


async def verify_teams_token(token: str) -> Optional[dict]:
    """Verify a Teams SSO JWT. Returns user info or None."""
    try:
        if settings.mode == "prod":
            from jwt import PyJWKClient
            jwks = PyJWKClient("https://login.microsoftonline.com/common/discovery/v2.0/keys")
            key = jwks.get_signing_key_from_jwt(token)
            decoded = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=os.getenv("MICROSOFT_APP_ID", ""),
            )
        else:
            decoded = jwt.decode(token, options={"verify_signature": False})

        return {
            "user_id": decoded.get("oid") or decoded.get("sub", "unknown"),
            "email": decoded.get("upn") or decoded.get("preferred_username", ""),
            "name": decoded.get("name", "Unknown"),
            "teams_user_id": decoded.get("oid", ""),
        }
    except Exception:
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency — returns authenticated user or raises 401."""
    if settings.mode == "dev":
        return {
            "sub": "dev-user",
            "user_id": "dev-user",
            "email": "dev@example.com",
            "name": "Dev User",
            "teams_user_id": "dev-user",
            "role": "admin",
            "team_id": "",
        }

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user = await verify_teams_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Enrich with team/role from DB
    user["sub"] = user.get("user_id", user.get("teams_user_id", "unknown"))
    try:
        from zeta_ima.teams_collab import teams_service
        membership = await teams_service.get_user_membership(user["sub"])
        if membership:
            user["role"] = membership.get("role", "member")
            user["team_id"] = membership.get("team_id", "")
        else:
            user["role"] = "member"
            user["team_id"] = ""
    except Exception:
        user["role"] = "member"
        user["team_id"] = ""

    return user
