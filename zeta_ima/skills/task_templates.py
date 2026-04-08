"""
Task Template Registry — loads declarative task templates from YAML.

Each template defines:
  - A unique agent pipeline (chain of agents that execute in order)
  - Human-readable steps with descriptions (shown in execution UI)
  - The owning agent, skill, and prompt to use

Usage:
    from zeta_ima.skills.task_templates import template_registry

    tmpl = template_registry.get("linkedin_post")
    all_templates = template_registry.list_all()
    copy_templates = template_registry.list_for_agent("copy")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

_YAML_PATH = Path(__file__).parent.parent / "orchestrator" / "task_templates.yaml"


@dataclass(frozen=True)
class TaskStep:
    """A single human-readable step in a task template."""
    name: str
    agent: str
    description: str = ""
    is_human_gate: bool = False


@dataclass(frozen=True)
class TaskTemplate:
    """Declarative definition of a content task type."""
    id: str
    name: str
    description: str
    icon: str
    owner_agent: str
    skill_id: str
    prompt_id: str
    pipeline: list[str]
    steps: list[TaskStep]
    default_priority: int = 2

    def to_api_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "owner_agent": self.owner_agent,
            "skill_id": self.skill_id,
            "prompt_id": self.prompt_id,
            "pipeline": self.pipeline,
            "steps": [
                {
                    "name": s.name,
                    "agent": s.agent,
                    "description": s.description,
                    "is_human_gate": s.is_human_gate,
                }
                for s in self.steps
            ],
            "default_priority": self.default_priority,
        }


class TaskTemplateRegistry:
    """Loads and caches task templates from the YAML file."""

    def __init__(self) -> None:
        self._templates: dict[str, TaskTemplate] = {}
        self._load()

    def _load(self) -> None:
        if not _YAML_PATH.exists():
            log.warning("task_templates.yaml not found at %s", _YAML_PATH)
            return

        with open(_YAML_PATH) as f:
            data = yaml.safe_load(f)

        raw = data.get("templates", {})
        for tid, tdata in raw.items():
            steps = [
                TaskStep(
                    name=s["name"],
                    agent=s["agent"],
                    description=s.get("description", ""),
                    is_human_gate=s.get("is_human_gate", False),
                )
                for s in tdata.get("steps", [])
            ]
            self._templates[tid] = TaskTemplate(
                id=tid,
                name=tdata["name"],
                description=tdata.get("description", ""),
                icon=tdata.get("icon", "file"),
                owner_agent=tdata.get("owner_agent", "copy"),
                skill_id=tdata.get("skill_id", ""),
                prompt_id=tdata.get("prompt_id", ""),
                pipeline=tdata.get("pipeline", []),
                steps=steps,
                default_priority=tdata.get("default_priority", 2),
            )

        log.info("Loaded %d task templates", len(self._templates))

    def get(self, template_id: str) -> Optional[TaskTemplate]:
        return self._templates.get(template_id)

    def list_all(self) -> list[TaskTemplate]:
        return list(self._templates.values())

    def list_for_agent(self, agent_name: str) -> list[TaskTemplate]:
        return [t for t in self._templates.values() if t.owner_agent == agent_name]


# Module-level singleton
template_registry = TaskTemplateRegistry()
