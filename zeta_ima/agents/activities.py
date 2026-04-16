"""
Agent activity definitions — narrowly scoped tasks each agent can perform.

Activities are loaded from activities.yaml and expose:
  - ActivityDefinition (dataclass): id, title, description, input_schema, workflow, tools, output_type
  - ActivityRegistry (singleton): list_for_agent(), get(), all()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_YAML_PATH = Path(__file__).parent / "activities.yaml"


@dataclass(frozen=True)
class InputField:
    id: str
    label: str
    type: str = "text"  # text | select | multiselect
    options: list[str] = field(default_factory=list)
    required: bool = False
    hint: str = ""


@dataclass(frozen=True)
class ActivityDefinition:
    id: str
    agent: str  # agent slug (e.g. "design")
    title: str
    description: str
    input_schema: list[InputField]
    workflow: list[str]  # ordered step labels
    tools: list[str]
    output_type: str


    # ── Skill-slug → activity ID mapping ──────────────────────────
    # Used by Teams bot so designers can type "/socialmedia" instead
    # of remembering the internal activity ID "social_visual".

SKILL_SLUG_MAP: dict[str, str] = {
    # Design agent
    "socialmedia": "social_visual",
    "social": "social_visual",
    "emailheader": "email_header",
    "email": "email_header",
    "brand": "brand_asset",
    "brandpack": "brand_asset",
    "ad": "ad_creative",
    "adcreative": "ad_creative",
    "slide": "presentation_slide",
    "presentation": "presentation_slide",
    # Copy agent
    "linkedin": "linkedin_post",
    "emailsequence": "email_sequence",
    "blog": "blog_article",
    "adcopy": "ad_copy",
}


class ActivityRegistry:
    _instance: ActivityRegistry | None = None

    def __init__(self) -> None:
        self._activities: dict[str, ActivityDefinition] = {}
        self._by_agent: dict[str, list[ActivityDefinition]] = {}
        self._load()

    @classmethod
    def get_instance(cls) -> ActivityRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── public API ──────────────────────────────────────────────

    def list_for_agent(self, agent_name: str) -> list[ActivityDefinition]:
        return self._by_agent.get(agent_name, [])

    def get(self, activity_id: str) -> ActivityDefinition | None:
        return self._activities.get(activity_id)

    def get_by_slug(self, slug: str) -> ActivityDefinition | None:
        """Resolve a Teams slash-command slug to an activity definition."""
        activity_id = SKILL_SLUG_MAP.get(slug.lower().strip("/"))
        if activity_id:
            return self._activities.get(activity_id)
        # Fallback: try using slug directly as activity ID
        return self._activities.get(slug)

    def all(self) -> list[ActivityDefinition]:
        return list(self._activities.values())

    def agents(self) -> list[str]:
        return list(self._by_agent.keys())

    # ── loader ──────────────────────────────────────────────────

    def _load(self) -> None:
        if not _YAML_PATH.exists():
            logger.warning("activities.yaml not found at %s", _YAML_PATH)
            return
        try:
            data = yaml.safe_load(_YAML_PATH.read_text()) or {}
        except Exception:
            logger.exception("Failed to parse activities.yaml")
            return

        agents_data: dict[str, Any] = data.get("agents", {})
        for agent_slug, agent_block in agents_data.items():
            activities_raw = agent_block.get("activities", [])
            for act in activities_raw:
                fields = [
                    InputField(
                        id=f["id"],
                        label=f.get("label", f["id"]),
                        type=f.get("type", "text"),
                        options=f.get("options", []),
                        required=f.get("required", False),
                        hint=f.get("hint", ""),
                    )
                    for f in act.get("input_schema", [])
                ]
                defn = ActivityDefinition(
                    id=act["id"],
                    agent=agent_slug,
                    title=act["title"],
                    description=act.get("description", ""),
                    input_schema=fields,
                    workflow=act.get("workflow", []),
                    tools=act.get("tools", []),
                    output_type=act.get("output_type", "text"),
                )
                self._activities[defn.id] = defn
                self._by_agent.setdefault(agent_slug, []).append(defn)

        logger.info(
            "Loaded %d activities for %d agents from activities.yaml",
            len(self._activities),
            len(self._by_agent),
        )
