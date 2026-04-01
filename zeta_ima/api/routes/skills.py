"""
Skills routes — browse the skill catalog, get skill details, execute a prompt.

GET  /skills                          → list all skills (grouped by category)
GET  /skills/{skill_id}               → full skill detail with prompts
POST /skills/{skill_id}/execute       → execute a single prompt (creates a 1-stage workflow)
GET  /skills/categories               → list unique categories
GET  /skills/search?q=...             → search skills by keyword
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from zeta_ima.api.auth import get_current_user
from zeta_ima.skills.registry import get_skill, list_skills, list_skills_api
from zeta_ima.workflows.engine import workflow_engine

router = APIRouter(prefix="/skills", tags=["skills"])


class ExecutePayload(BaseModel):
    """Payload for executing a single skill prompt."""
    prompt_id: str
    variables: dict[str, str]
    name: Optional[str] = None
    campaign_id: Optional[str] = None
    llm_override: Optional[str] = None


# ─── Catalog ────────────────────────────────────────────────────────

@router.get("")
async def get_skills(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return all skills, sorted by category → name."""
    return list_skills_api()


@router.get("/categories")
async def get_categories(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return unique categories with skill counts."""
    skills = list_skills()
    category_map: dict[str, int] = {}
    for s in skills:
        category_map[s.category] = category_map.get(s.category, 0) + 1

    order = {"foundation": 0, "strategy": 1, "execution": 2, "distribution": 3}
    return sorted(
        [{"id": cat, "name": cat.title(), "skill_count": count} for cat, count in category_map.items()],
        key=lambda c: order.get(c["id"], 99),
    )


@router.get("/search")
async def search_skills(
    q: str = Query(..., min_length=1),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """Search skills by keyword in name, description, or prompt names."""
    query = q.lower()
    results = []
    for skill in list_skills():
        # Match against skill name, description, category
        text_blob = f"{skill.name} {skill.description} {skill.category}".lower()
        # Also match against prompt names and descriptions
        for p in skill.prompts:
            text_blob += f" {p.name} {p.description}".lower()

        if query in text_blob:
            results.append(skill.to_api_dict())

    return results


# ─── Skill Detail ───────────────────────────────────────────────────

@router.get("/{skill_id}")
async def get_skill_detail(
    skill_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Return full skill detail including all prompts."""
    skill = get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    return skill.to_api_dict()


@router.get("/{skill_id}/prompts/{prompt_id}")
async def get_prompt_detail(
    skill_id: str,
    prompt_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Return a single prompt with its template and variables."""
    skill = get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    prompt = skill.get_prompt(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found in skill '{skill_id}'")

    return {
        "id": prompt.id,
        "name": prompt.name,
        "description": prompt.description,
        "prompt_text": prompt.prompt_text,
        "variables": prompt.variables,
        "platform": prompt.platform,
        "output_type": prompt.output_type,
        "example_output": prompt.example_output,
        "agent": prompt.agent,
        "skill_id": skill_id,
        "skill_name": skill.name,
        "default_llm": skill.default_llm,
        "fallback_llms": skill.fallback_llms,
    }


# ─── Execute ────────────────────────────────────────────────────────

@router.post("/{skill_id}/execute")
async def execute_skill_prompt(
    skill_id: str,
    payload: ExecutePayload,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Execute a skill prompt by creating a single-stage workflow and advancing it.

    Returns the workflow with its execution result.
    """
    skill = get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    prompt = skill.get_prompt(payload.prompt_id)
    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{payload.prompt_id}' not found in skill '{skill_id}'",
        )

    # Validate required variables
    missing = [v for v in prompt.variables if v not in payload.variables]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required variables: {missing}",
        )

    # Create a single-stage workflow
    wf = await workflow_engine.create_from_skill(
        skill_id=skill_id,
        prompt_id=payload.prompt_id,
        variables=payload.variables,
        user_id=user["user_id"],
        name=payload.name,
        campaign_id=payload.campaign_id,
    )

    # Execute immediately in background
    async def _run():
        try:
            await workflow_engine.advance(wf["id"])
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Skill execution failed: {e}")

    background.add_task(_run)

    return {
        "workflow_id": wf["id"],
        "status": "started",
        "skill_id": skill_id,
        "prompt_id": payload.prompt_id,
        "message": f"Executing '{prompt.name}' — check workflow status for results.",
    }
