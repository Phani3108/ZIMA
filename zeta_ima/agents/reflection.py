"""
Actor-Critic Reflection Loops — Phase 3.1

The ReflectionLoop runs an iterative improve-then-critique cycle on any draft text.
It supports three modes:
  - self:   one model writes, another persona critiques (single LLM, two roles)
  - peer:   two separate LLM calls — one actor, one separate critic system prompt
  - multi:  multiple critic passes from different lenses (brand, legal, audience)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from zeta_ima.integrations.vault import vault

# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ReflectionStep:
    iteration: int
    draft: str
    critique: str
    score: float        # 0–10 quality score from critic
    passed: bool        # True when score ≥ threshold
    improvements: list[str] = field(default_factory=list)


@dataclass
class ReflectionResult:
    final_draft: str
    steps: list[ReflectionStep]
    converged: bool     # True if threshold met, False if max_iterations hit
    final_score: float
    iterations_used: int


# ── System prompts ────────────────────────────────────────────────────────────

_ACTOR_SYSTEM = """\
You are an expert marketing copywriter. You write and revise copy based on:
1. The original creative brief
2. Brand voice guidelines provided
3. Specific critique feedback from a senior creative director

Always respond with ONLY the revised copy text — no preamble, no commentary."""

_CRITIC_SYSTEM = """\
You are a senior creative director at a top marketing agency.
Evaluate the following marketing copy against the brief and brand guide.

Respond with JSON:
{
  "score": <0–10, where 10 is publish-ready>,
  "passed": <true if score >= threshold>,
  "critique": "<concise critique in 1-3 sentences>",
  "improvements": ["specific improvement 1", "specific improvement 2"]
}

Be strict but constructive. Score below 7.5 means revisions are needed."""

_CRITIC_LENSES = {
    "brand": "Evaluate from brand voice and consistency perspective.",
    "audience": "Evaluate from target audience resonance and clarity perspective.",
    "legal": "Flag any potentially problematic claims, superlatives, or compliance risks.",
    "cta": "Evaluate the call-to-action strength and clarity.",
}


# ── ReflectionLoop class ──────────────────────────────────────────────────────

class ReflectionLoop:
    """
    Runs up to max_iterations of Actor → Critic → improve cycles.

    Usage:
        loop = ReflectionLoop(max_iterations=3, threshold=7.5, mode="peer")
        result = await loop.run(
            draft="...",
            brief="...",
            brand_guidelines="...",
        )
    """

    def __init__(
        self,
        max_iterations: int = 3,
        threshold: float = 7.5,
        mode: str = "peer",    # "self" | "peer" | "multi"
        actor_model: str = "gpt-4o",
        critic_model: str = "gpt-4o",
    ):
        self.max_iterations = max_iterations
        self.threshold = threshold
        self.mode = mode
        self.actor_model = actor_model
        self.critic_model = critic_model

    async def run(
        self,
        draft: str,
        brief: str,
        brand_guidelines: str = "",
        lenses: list[str] | None = None,
    ) -> ReflectionResult:
        """Execute the full reflection loop."""
        lenses = lenses or (["brand", "audience"] if self.mode == "multi" else ["brand"])
        steps: list[ReflectionStep] = []
        current_draft = draft

        for i in range(1, self.max_iterations + 1):
            if self.mode == "multi":
                # Run all lenses concurrently, merge critiques
                critique_results = await asyncio.gather(
                    *[
                        self._critique(current_draft, brief, brand_guidelines, lens)
                        for lens in lenses
                    ]
                )
                # Aggregate: lowest score wins, merge improvements
                score = min(r["score"] for r in critique_results)
                critique_texts = "; ".join(r["critique"] for r in critique_results)
                improvements = []
                for r in critique_results:
                    improvements.extend(r.get("improvements", []))
            else:
                result = await self._critique(current_draft, brief, brand_guidelines, lenses[0])
                score = result["score"]
                critique_texts = result["critique"]
                improvements = result.get("improvements", [])

            passed = score >= self.threshold
            step = ReflectionStep(
                iteration=i,
                draft=current_draft,
                critique=critique_texts,
                score=score,
                passed=passed,
                improvements=improvements,
            )
            steps.append(step)

            if passed:
                return ReflectionResult(
                    final_draft=current_draft,
                    steps=steps,
                    converged=True,
                    final_score=score,
                    iterations_used=i,
                )

            # Actor revises
            if i < self.max_iterations:
                current_draft = await self._revise(
                    current_draft, brief, brand_guidelines, critique_texts, improvements
                )

        return ReflectionResult(
            final_draft=current_draft,
            steps=steps,
            converged=False,
            final_score=steps[-1].score,
            iterations_used=self.max_iterations,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _critique(
        self,
        draft: str,
        brief: str,
        brand_guidelines: str,
        lens: str = "brand",
    ) -> dict[str, Any]:
        import json
        from openai import AsyncOpenAI

        api_key = await vault.get("openai", "api_key")
        client = AsyncOpenAI(api_key=api_key)

        lens_instruction = _CRITIC_LENSES.get(lens, "")
        system = _CRITIC_SYSTEM + f"\n\nFocus lens: {lens_instruction}"

        user_msg = (
            f"BRIEF:\n{brief}\n\n"
            f"BRAND GUIDELINES:\n{brand_guidelines or 'Not provided'}\n\n"
            f"COPY TO EVALUATE:\n{draft}\n\n"
            f"THRESHOLD: {self.threshold}"
        )

        resp = await client.chat.completions.create(
            model=self.critic_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=600,
        )
        raw = json.loads(resp.choices[0].message.content or "{}")
        return {
            "score": float(raw.get("score", 5.0)),
            "critique": raw.get("critique", ""),
            "improvements": raw.get("improvements", []),
        }

    async def _revise(
        self,
        draft: str,
        brief: str,
        brand_guidelines: str,
        critique: str,
        improvements: list[str],
    ) -> str:
        from openai import AsyncOpenAI

        api_key = await vault.get("openai", "api_key")
        client = AsyncOpenAI(api_key=api_key)

        improvement_list = "\n".join(f"- {imp}" for imp in improvements)
        user_msg = (
            f"BRIEF:\n{brief}\n\n"
            f"BRAND GUIDELINES:\n{brand_guidelines or 'Not provided'}\n\n"
            f"CURRENT DRAFT:\n{draft}\n\n"
            f"CRITIC FEEDBACK:\n{critique}\n\n"
            f"REQUIRED IMPROVEMENTS:\n{improvement_list}\n\n"
            "Please revise the copy addressing all feedback."
        )

        resp = await client.chat.completions.create(
            model=self.actor_model,
            messages=[
                {"role": "system", "content": _ACTOR_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=1200,
        )
        return (resp.choices[0].message.content or draft).strip()


# ── Convenience factory ───────────────────────────────────────────────────────

def make_reflection_loop(
    mode: str = "peer",
    max_iterations: int = 3,
    threshold: float = 7.5,
) -> ReflectionLoop:
    return ReflectionLoop(
        mode=mode,
        max_iterations=max_iterations,
        threshold=threshold,
        actor_model="gpt-4o",
        critic_model="gpt-4o",
    )
