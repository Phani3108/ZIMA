"""
Resilient Agent Pool — runs agents independently with LLM fallback chains.

Key design: each agent is an independent asyncio task. If the copy agent fails
because OpenAI is down, the design agent's Canva work is unaffected. Results
merge at the workflow level, not the agent level.

Usage:
    pool = AgentPool()
    result = await pool.execute("copy", state, skill_context)
    # or parallel:
    results = await pool.execute_parallel([("copy", ctx1), ("design", ctx2)], state)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from zeta_ima.agents.llm_router import LLMError, LLMResult, call_llm
from zeta_ima.skills.base import PromptTemplate, SkillDefinition
from zeta_ima.skills.registry import get_skill

log = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from a single agent execution."""

    status: str                    # "success" | "failed" | "needs_retry"
    output: Optional[str] = None  # Generated text / JSON / HTML
    preview_type: Optional[str] = None   # "text" | "image" | "design" | "html" | "social_mock"
    preview_url: Optional[str] = None    # Embed URL for Canva/Figma
    llm_used: Optional[str] = None       # "openai/gpt-4o"
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    completed_at: Optional[datetime] = None


def _render_prompt(template: PromptTemplate, variables: dict, context: dict) -> str:
    """Render a prompt template by substituting {{var}} placeholders."""
    text = template.prompt_text

    # Merge user variables + auto-injected context
    all_vars = {**variables, **context}

    for key, value in all_vars.items():
        placeholder = "{{" + key + "}}"
        text = text.replace(placeholder, str(value) if value else "")

    return text


class AgentPool:
    """
    Manages independent agent execution with LLM fallback chains.

    Each agent:
    1. Resolves its prompt from the skill + prompt ID
    2. Renders the prompt with user variables + KB/brand context
    3. Calls the LLM with the skill's preferred fallback chain
    4. Returns an AgentResult (success or failed, never crashes the workflow)
    """

    async def execute(
        self,
        agent_name: str,
        skill_id: str,
        prompt_id: str,
        variables: dict,
        context: dict,
        llm_override: Optional[str] = None,
    ) -> AgentResult:
        """
        Execute a single agent task.

        Args:
            agent_name: Agent type ("copy", "seo", "design", "research", etc.)
            skill_id: Skill to use for prompt lookup.
            prompt_id: Specific prompt template ID.
            variables: User-provided template variables.
            context: Auto-injected context (brand_voice, kb_context, brand_examples).
            llm_override: Force a specific provider (bypasses fallback chain).
        """
        try:
            skill = get_skill(skill_id)
            if skill is None:
                return AgentResult(status="failed", error=f"Skill '{skill_id}' not found")

            prompt_tmpl = skill.get_prompt(prompt_id)
            if prompt_tmpl is None:
                return AgentResult(
                    status="failed",
                    error=f"Prompt '{prompt_id}' not found in skill '{skill_id}'",
                )

            # Render the prompt
            rendered = _render_prompt(prompt_tmpl, variables, context)

            # Build system message from brand voice context
            system = (
                f"You are an expert {agent_name} agent for a marketing agency. "
                f"Skill: {skill.name}. "
                f"Follow the instructions precisely and produce high-quality output."
            )

            # Determine LLM chain
            if llm_override:
                chain = [llm_override]
            else:
                chain = [skill.default_llm] + [
                    f for f in skill.fallback_llms if f != skill.default_llm
                ]

            # Call LLM with fallback
            result: LLMResult = await call_llm(
                prompt=rendered,
                system=system,
                llm_chain=chain,
            )

            return AgentResult(
                status="success",
                output=result.text,
                preview_type=prompt_tmpl.output_type,
                llm_used=f"{result.provider_used}/{result.model_used}",
                metadata={
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "agent": agent_name,
                    "skill": skill_id,
                    "prompt": prompt_id,
                },
                completed_at=datetime.now(timezone.utc),
            )

        except LLMError as e:
            log.error(f"Agent '{agent_name}' LLM chain exhausted: {e}")
            return AgentResult(
                status="failed",
                error=str(e),
                metadata={"agent": agent_name, "skill": skill_id, "prompt": prompt_id},
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            log.exception(f"Agent '{agent_name}' unexpected error: {e}")
            return AgentResult(
                status="failed",
                error=f"Unexpected error: {type(e).__name__}: {e}",
                metadata={"agent": agent_name, "skill": skill_id, "prompt": prompt_id},
                completed_at=datetime.now(timezone.utc),
            )

    async def execute_parallel(
        self,
        tasks: list[dict],
        context: dict,
    ) -> dict[str, AgentResult]:
        """
        Run multiple agents in parallel. Each succeeds or fails independently.

        Args:
            tasks: List of dicts with keys: agent, skill_id, prompt_id, variables
            context: Shared context (brand voice, KB, etc.)

        Returns:
            Dict mapping task index/name to AgentResult.
        """
        async def _run(task: dict) -> tuple[str, AgentResult]:
            name = task.get("name", task.get("agent", "unknown"))
            result = await self.execute(
                agent_name=task["agent"],
                skill_id=task["skill_id"],
                prompt_id=task["prompt_id"],
                variables=task.get("variables", {}),
                context=context,
                llm_override=task.get("llm_override"),
            )
            return name, result

        pairs = await asyncio.gather(
            *[_run(t) for t in tasks],
            return_exceptions=True,
        )

        results: dict[str, AgentResult] = {}
        for item in pairs:
            if isinstance(item, Exception):
                log.error(f"Parallel agent task raised: {item}")
                results[str(item)] = AgentResult(
                    status="failed", error=str(item),
                    completed_at=datetime.now(timezone.utc),
                )
            else:
                name, result = item
                results[name] = result

        return results


# Module-level singleton
agent_pool = AgentPool()
