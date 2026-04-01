"""
Skill & Prompt data models.

Skills are pure data — no execution logic. The workflow engine and agent pool
handle running prompts against LLMs and tools. Adding a new skill means adding
one file under skills/definitions/ with zero logic changes elsewhere.

Genesis v2 adds UserSkill — user-authored Python skills with sandboxed execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class PromptTemplate:
    """A single executable prompt within a skill."""

    id: str
    name: str                              # "LinkedIn Product Launch Post"
    description: str                       # One-liner shown in the UI picker
    prompt_text: str                       # Jinja2-style template with {{var}} placeholders
    variables: list[str] = field(default_factory=list)  # Required user inputs
    platform: str = "any"                  # "openai" | "claude" | "gemini" | "any"
    output_type: str = "text"              # "text" | "image" | "design" | "html" | "json"
    example_output: str = ""               # Sample output for preview in UI
    agent: str = "copy"                    # Which agent runs this prompt


@dataclass(frozen=True)
class SkillDefinition:
    """A marketing skill — a collection of related prompts with shared context."""

    id: str                                # "seo_content"
    name: str                              # "SEO Content"
    description: str                       # Paragraph shown on skill detail page
    icon: str                              # Lucide icon name ("search", "pen-tool", etc.)
    category: str                          # "foundation" | "strategy" | "execution" | "distribution"
    prompts: list[PromptTemplate]          # 3-8 prompts per skill
    platforms: list[str] = field(default_factory=lambda: ["openai", "claude", "gemini"])
    tools_used: list[str] = field(default_factory=list)
    workflow_stages: list[str] = field(default_factory=list)
    default_llm: str = "openai"
    fallback_llms: list[str] = field(default_factory=lambda: ["claude", "gemini"])

    def get_prompt(self, prompt_id: str) -> Optional[PromptTemplate]:
        """Look up a prompt by ID."""
        return next((p for p in self.prompts if p.id == prompt_id), None)

    def to_api_dict(self) -> dict:
        """Serialize for the /skills API response."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "platforms": self.platforms,
            "tools_used": self.tools_used,
            "workflow_stages": self.workflow_stages,
            "default_llm": self.default_llm,
            "fallback_llms": self.fallback_llms,
            "prompts": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "variables": p.variables,
                    "platform": p.platform,
                    "output_type": p.output_type,
                    "example_output": p.example_output,
                    "agent": p.agent,
                }
                for p in self.prompts
            ],
        }


# ── User-authored codable skills (Genesis v2) ─────────────────────────────────

@dataclass
class UserSkill:
    """
    A user-written Python skill stored in the database and executed in a
    RestrictedPython sandbox.

    The code must define a function:
        def run(inputs: dict, gateway) -> dict:
            ...
    where `gateway` is a restricted API gateway object.
    """

    id: str
    name: str
    description: str
    code: str                               # Python source
    created_by: str                         # user_id
    version: int = 1
    is_shared: bool = False                 # visible to whole team?
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_api_dict(self, include_code: bool = False) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "version": self.version,
            "is_shared": self.is_shared,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_code:
            d["code"] = self.code
        return d
