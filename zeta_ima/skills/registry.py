"""
Skill Registry — auto-discovers all skill definitions and provides lookup.

Usage:
    from zeta_ima.skills.registry import get_skill, list_skills, get_all_skills

    all_skills = list_skills()                    # List of SkillDefinition
    skill = get_skill("seo_content")              # Single skill by ID
    prompt = skill.get_prompt("seo_blog_post")    # Prompt within skill
"""

from __future__ import annotations

import importlib
import pkgutil
from functools import lru_cache
from typing import Optional

from zeta_ima.skills.base import SkillDefinition


@lru_cache(maxsize=1)
def _load_all() -> dict[str, SkillDefinition]:
    """Import every module in skills/definitions/ and collect their `skill` attribute."""
    import zeta_ima.skills.definitions as pkg

    skills: dict[str, SkillDefinition] = {}
    for finder, name, is_pkg in pkgutil.iter_modules(pkg.__path__):
        mod = importlib.import_module(f"zeta_ima.skills.definitions.{name}")
        defn = getattr(mod, "skill", None)
        if isinstance(defn, SkillDefinition):
            skills[defn.id] = defn
    return skills


def list_skills() -> list[SkillDefinition]:
    """Return all registered skills, sorted by category then name."""
    category_order = {"foundation": 0, "strategy": 1, "execution": 2, "distribution": 3}
    return sorted(
        _load_all().values(),
        key=lambda s: (category_order.get(s.category, 99), s.name),
    )


def get_skill(skill_id: str) -> Optional[SkillDefinition]:
    """Look up a skill by ID. Returns None if not found."""
    return _load_all().get(skill_id)


def get_all_skills() -> dict[str, SkillDefinition]:
    """Return the full skill registry as {id: SkillDefinition}."""
    return dict(_load_all())


def list_skills_api() -> list[dict]:
    """Return serialized skill list for the REST API."""
    return [s.to_api_dict() for s in list_skills()]
