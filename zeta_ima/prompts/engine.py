"""
Prompt Engine — versioned prompt management + team-scoped overrides.

Prompts follow a fallback chain: team version → global version → file on disk.

Usage::

    from zeta_ima.prompts.engine import get_active_prompt, create_version
    prompt = await get_active_prompt("copy", team_id="t1")
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zeta_ima.config import settings

log = logging.getLogger(__name__)

PROMPT_VERSIONS_CONTAINER = "prompt_versions"
_PROMPTS_DIR = Path(__file__).parent


async def get_active_prompt(skill_id: str, team_id: str = "__global__") -> str:
    """
    Get the active prompt for a skill, following the fallback chain:
    1. Team-specific version (if team_id provided)
    2. Global active version
    3. File on disk (original prompt)
    """
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    # 1. Try team-specific version
    if team_id and team_id != "__global__":
        team_versions = await ds.query(
            PROMPT_VERSIONS_CONTAINER,
            filters={"skill_id": skill_id, "team_id": team_id, "is_active": True},
            limit=1,
        )
        if team_versions:
            log.debug("Using team prompt for %s/%s (v%d)", skill_id, team_id, team_versions[0].get("version", 0))
            return team_versions[0]["content"]

    # 2. Try global active version
    global_versions = await ds.query(
        PROMPT_VERSIONS_CONTAINER,
        filters={"skill_id": skill_id, "team_id": "__global__", "is_active": True},
        limit=1,
    )
    if global_versions:
        return global_versions[0]["content"]

    # 3. Fallback to file on disk
    prompt_file = _PROMPTS_DIR / f"{skill_id}.md"
    if prompt_file.exists():
        return prompt_file.read_text()

    log.warning("No prompt found for skill=%s team=%s", skill_id, team_id)
    return ""


async def create_version(
    skill_id: str,
    content: str,
    team_id: str = "__global__",
    change_type: str = "manual",
    change_reason: str = "",
    created_by: str = "system",
    activate: bool = True,
) -> dict[str, Any]:
    """
    Create a new prompt version.

    If activate=True, deactivate previous active version and set this one active.
    """
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    # Get latest version number
    existing = await ds.query(
        PROMPT_VERSIONS_CONTAINER,
        filters={"skill_id": skill_id, "team_id": team_id},
        order_by="created_at DESC",
        limit=1,
    )
    current_version = existing[0].get("version", 0) if existing else 0
    new_version = current_version + 1
    parent_id = existing[0].get("id", "") if existing else ""

    version_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Deactivate previous active
    if activate and existing:
        for v in existing:
            if v.get("is_active"):
                v["is_active"] = False
                await ds.upsert(PROMPT_VERSIONS_CONTAINER, v)

    doc = {
        "id": version_id,
        "skill_id": skill_id,
        "team_id": team_id,
        "version": new_version,
        "content": content,
        "change_type": change_type,
        "change_reason": change_reason,
        "parent_id": parent_id,
        "is_active": activate,
        "performance": {},
        "created_by": created_by,
        "created_at": now.isoformat(),
    }
    await ds.upsert(PROMPT_VERSIONS_CONTAINER, doc)

    log.info(
        "Created prompt version %s v%d for %s/%s (%s)",
        version_id, new_version, skill_id, team_id, change_type,
    )
    return doc


async def rollback(skill_id: str, team_id: str = "__global__", to_version: int = 0) -> dict[str, Any] | None:
    """
    Rollback to a specific version (or the previous one if to_version=0).
    """
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    versions = await ds.query(
        PROMPT_VERSIONS_CONTAINER,
        filters={"skill_id": skill_id, "team_id": team_id},
        order_by="created_at DESC",
        limit=50,
    )

    if not versions:
        return None

    # Deactivate all
    for v in versions:
        if v.get("is_active"):
            v["is_active"] = False
            await ds.upsert(PROMPT_VERSIONS_CONTAINER, v)

    # Find target
    target = None
    if to_version > 0:
        for v in versions:
            if v.get("version") == to_version:
                target = v
                break
    else:
        # Previous version (second item if sorted DESC)
        target = versions[1] if len(versions) > 1 else versions[0]

    if target:
        target["is_active"] = True
        await ds.upsert(PROMPT_VERSIONS_CONTAINER, target)
        log.info("Rolled back %s/%s to v%d", skill_id, team_id, target.get("version", 0))

    return target


async def get_version_history(
    skill_id: str,
    team_id: str = "__global__",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get version history for a skill/team."""
    from zeta_ima.infra.document_store import get_document_store
    ds = get_document_store()

    return await ds.query(
        PROMPT_VERSIONS_CONTAINER,
        filters={"skill_id": skill_id, "team_id": team_id},
        order_by="created_at DESC",
        limit=limit,
    )
