"""
Agent Role Registry — loads the agency org chart from YAML and provides
role lookups for nodes to inject persona into their system prompts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

log = logging.getLogger(__name__)

_MANIFEST_PATH = Path(__file__).parent / "agency_manifest.yaml"


@dataclass(frozen=True)
class AgentRole:
    """Immutable definition of an agent's identity within the marketing agency."""

    id: str                             # e.g. "senior_copywriter"
    title: str                          # e.g. "Senior Copywriter"
    department: str                     # "content" | "design" | "strategy" | "operations"
    node_name: str                      # Maps to graph node: "copy", "review", etc.
    responsibilities: List[str] = field(default_factory=list)
    expertise: List[str] = field(default_factory=list)
    reports_to: str = ""                # Role ID of manager
    interacts_with: List[str] = field(default_factory=list)
    persona_prompt: str = ""            # Injected into system prompt
    avatar_emoji: str = "🤖"

    def system_prompt_prefix(self) -> str:
        """Build the persona prefix to prepend to any system prompt."""
        lines = [
            f"You are **{self.title}** at Zeta Marketing Agency.",
            f"Department: {self.department.title()}.",
        ]
        if self.responsibilities:
            lines.append("Responsibilities: " + "; ".join(self.responsibilities) + ".")
        if self.persona_prompt:
            lines.append(self.persona_prompt)
        return "\n".join(lines)


class RoleRegistry:
    """Singleton registry of all agent roles, loaded from YAML."""

    def __init__(self) -> None:
        self._roles: Dict[str, AgentRole] = {}
        self._by_node: Dict[str, AgentRole] = {}
        self._loaded = False

    def load(self, path: Path | None = None) -> None:
        """Load roles from the YAML manifest."""
        manifest_path = path or _MANIFEST_PATH
        if not manifest_path.exists():
            log.warning("Agency manifest not found at %s", manifest_path)
            return

        with open(manifest_path) as f:
            data = yaml.safe_load(f) or {}

        for dept_key, dept_data in data.get("departments", {}).items():
            for role_data in dept_data.get("roles", []):
                role = AgentRole(
                    id=role_data["id"],
                    title=role_data["title"],
                    department=dept_key,
                    node_name=role_data.get("node_name", role_data["id"]),
                    responsibilities=role_data.get("responsibilities", []),
                    expertise=role_data.get("expertise", []),
                    reports_to=role_data.get("reports_to", ""),
                    interacts_with=role_data.get("interacts_with", []),
                    persona_prompt=role_data.get("persona_prompt", ""),
                    avatar_emoji=role_data.get("avatar_emoji", "🤖"),
                )
                self._roles[role.id] = role
                self._by_node[role.node_name] = role

        self._loaded = True
        log.info("Loaded %d agent roles from %s", len(self._roles), manifest_path)

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def get(self, role_id: str) -> Optional[AgentRole]:
        """Look up a role by its ID (e.g. 'senior_copywriter')."""
        self.ensure_loaded()
        return self._roles.get(role_id)

    def get_by_node(self, node_name: str) -> Optional[AgentRole]:
        """Look up a role by graph node name (e.g. 'copy' → Senior Copywriter)."""
        self.ensure_loaded()
        return self._by_node.get(node_name)

    def list_roles(self) -> List[AgentRole]:
        """Return all roles sorted by department then title."""
        self.ensure_loaded()
        return sorted(self._roles.values(), key=lambda r: (r.department, r.title))

    def list_by_department(self, department: str) -> List[AgentRole]:
        """Return all roles in a department."""
        self.ensure_loaded()
        return [r for r in self._roles.values() if r.department == department]

    def get_meeting_participants(self, pipeline: List[str]) -> List[AgentRole]:
        """Given a pipeline of node names, return the roles that participate."""
        self.ensure_loaded()
        participants = []
        seen = set()
        for node_name in pipeline:
            role = self._by_node.get(node_name)
            if role and role.id not in seen:
                participants.append(role)
                seen.add(role.id)
        # Always include CMO as meeting chair
        cmo = self._roles.get("cmo")
        if cmo and cmo.id not in seen:
            participants.insert(0, cmo)
        return participants

    def to_org_chart(self) -> Dict:
        """Return a JSON-serializable org chart for the frontend."""
        self.ensure_loaded()
        departments = {}
        for role in self._roles.values():
            dept = departments.setdefault(role.department, [])
            dept.append({
                "id": role.id,
                "title": role.title,
                "avatar": role.avatar_emoji,
                "reports_to": role.reports_to,
                "node_name": role.node_name,
            })
        return departments


# Module-level singleton
role_registry = RoleRegistry()
