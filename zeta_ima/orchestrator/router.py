"""
Orchestrator Router — hybrid static config + LLM intent classification.

Routing decision flow:
  1. Check static pipelines.yaml for keyword matches
  2. If no match, use LLM classification (extended classify_intent)
  3. Return RoutingDecision with pipeline, priority, and rationale
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from zeta_ima.agents.router import classify_intent
from zeta_ima.config import settings

log = logging.getLogger(__name__)

_PIPELINES_PATH = Path(__file__).parent / "pipelines.yaml"


@dataclass
class RoutingDecision:
    pipeline_name: str              # e.g. "full_campaign"
    pipeline: list[str]             # e.g. ["research", "pm", "copy", "design", "review", "approval"]
    priority: int                   # 1=low, 2=medium, 3=high
    rationale: str                  # Why this pipeline was chosen
    source: str = "static"          # "static" | "llm" | "fallback"


def _load_pipelines() -> dict:
    """Load pipeline definitions from YAML."""
    try:
        with open(_PIPELINES_PATH) as f:
            return yaml.safe_load(f)
    except Exception as e:
        log.warning(f"Failed to load pipelines.yaml: {e}")
        return {"pipelines": {}, "default_pipeline": "quick_copy", "priorities": {"high": 3, "medium": 2, "low": 1}}


def _match_static(brief: str) -> Optional[RoutingDecision]:
    """Check if the brief matches any static pipeline keywords."""
    config = _load_pipelines()
    pipelines = config.get("pipelines", {})
    priority_map = config.get("priorities", {"high": 3, "medium": 2, "low": 1})

    brief_lower = brief.lower()

    # Score each pipeline by keyword matches
    best_match = None
    best_score = 0

    for name, defn in pipelines.items():
        keywords = defn.get("keywords", [])
        score = sum(1 for kw in keywords if kw.lower() in brief_lower)
        if score > best_score:
            best_score = score
            best_match = (name, defn)

    if best_match and best_score > 0:
        name, defn = best_match
        priority_str = defn.get("priority", "medium")
        return RoutingDecision(
            pipeline_name=name,
            pipeline=defn["agents"],
            priority=priority_map.get(priority_str, 2),
            rationale=f"Static match: '{name}' ({best_score} keyword hits)",
            source="static",
        )

    return None


# Maps intent names from classify_intent to pipeline names
_INTENT_TO_PIPELINE = {
    "copy": "quick_copy",
    "jira": "jira_task",
    "confluence": "confluence_publish",
    "canva": "design_only",
    "research": "research_report",
    "github": "quick_copy",  # No dedicated github pipeline; use copy as wrapper
}


async def route_task(brief: str) -> RoutingDecision:
    """
    Determine the best pipeline for a given brief.

    1. Try static keyword matching
    2. Fall back to LLM intent classification
    3. Map intents to pipeline names
    """
    # Step 1: Static match
    static = _match_static(brief)
    if static:
        return static

    # Step 2: LLM classification
    config = _load_pipelines()
    pipelines = config.get("pipelines", {})
    default_name = config.get("default_pipeline", "quick_copy")
    priority_map = config.get("priorities", {"high": 3, "medium": 2, "low": 1})

    try:
        intents = await classify_intent(brief)
        primary = intents[0] if intents else "copy"

        # Multi-intent → upgrade to full_campaign if copy + design both present
        if "copy" in intents and ("canva" in intents or "design" in intents):
            pipeline_name = "copy_and_design"
        else:
            pipeline_name = _INTENT_TO_PIPELINE.get(primary, default_name)

        defn = pipelines.get(pipeline_name, pipelines.get(default_name, {}))
        priority_str = defn.get("priority", "medium")

        return RoutingDecision(
            pipeline_name=pipeline_name,
            pipeline=defn.get("agents", ["research", "copy", "review", "approval"]),
            priority=priority_map.get(priority_str, 2),
            rationale=f"LLM classified intents={intents} → pipeline='{pipeline_name}'",
            source="llm",
        )

    except Exception as e:
        log.warning(f"LLM routing failed, using default: {e}")
        defn = pipelines.get(default_name, {})
        return RoutingDecision(
            pipeline_name=default_name,
            pipeline=defn.get("agents", ["research", "copy", "review", "approval"]),
            priority=2,
            rationale=f"Fallback to default pipeline (LLM error: {e})",
            source="fallback",
        )
