"""
Agent Coordinator — dependency-aware multi-agent execution.

Extends the simple agent pool with:
  1. Dependency DAG resolution — stages run in topological order
  2. Context passing — output from stage A auto-injected into stage B's context
  3. Parallel execution of independent stages
  4. Failure isolation — one agent failing doesn't block unrelated agents

Usage:
    from zeta_ima.agents.coordinator import coordinator

    results = await coordinator.execute_workflow(
        stages=[...],
        variables={...},
        context={...},
    )
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Optional

from zeta_ima.agents.pool import agent_pool, AgentResult
from zeta_ima.integrations.actions import execute_action

log = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Orchestrates multi-agent execution with dependency tracking.

    Unlike the simple pool which runs everything independently,
    the coordinator:
    - Builds a dependency graph from stage definitions
    - Runs independent stages in parallel
    - Passes outputs between dependent stages
    - Isolates failures (one agent error doesn't cascade)
    """

    async def execute_workflow(
        self,
        stages: list[dict],
        variables: dict,
        context: dict,
    ) -> dict[str, AgentResult]:
        """
        Execute a list of stages respecting dependencies.

        Each stage dict should have:
          - name: str
          - agent: str (agent_name)
          - skill_id: str
          - prompt_id: str
          - depends_on: list[str] (stage names this depends on)
          - passes_to: dict[str, str] (output_key -> target_stage_name)
          - tool_action: str (optional, integration action to run)

        Returns:
            {stage_name: AgentResult}
        """
        # Build dependency graph
        graph = self._build_dag(stages)
        results: dict[str, AgentResult] = {}
        stage_outputs: dict[str, str] = {}  # name -> output text

        # Topological sort into execution layers
        layers = self._topological_layers(stages, graph)

        log.info(
            f"Coordinator: {len(stages)} stages in {len(layers)} layers: "
            + " → ".join([str([s["name"] for s in layer]) for layer in layers])
        )

        for layer in layers:
            # Execute all stages in this layer in parallel
            tasks = []
            for stage in layer:
                # Build enriched context with outputs from dependencies
                enriched = dict(context)
                for dep_name in stage.get("depends_on", []):
                    if dep_name in stage_outputs:
                        enriched[f"{dep_name}_output"] = stage_outputs[dep_name]

                tasks.append(
                    self._execute_stage(stage, variables, enriched)
                )

            # Run in parallel with failure isolation
            layer_results = await asyncio.gather(*tasks, return_exceptions=True)

            for stage, result in zip(layer, layer_results):
                if isinstance(result, Exception):
                    log.error(f"Stage '{stage['name']}' failed: {result}")
                    results[stage["name"]] = AgentResult(
                        status="error",
                        output="",
                        error=str(result),
                    )
                else:
                    results[stage["name"]] = result
                    if result.status == "success":
                        stage_outputs[stage["name"]] = result.output

        return results

    async def _execute_stage(
        self,
        stage: dict,
        variables: dict,
        context: dict,
    ) -> AgentResult:
        """Execute a single stage — LLM call and/or tool action."""
        result = AgentResult(status="success", output="")

        # Step 1: Run the LLM prompt (if prompt_id is specified)
        prompt_id = stage.get("prompt_id") or stage.get("prompt")
        if prompt_id and prompt_id != "none":
            result = await agent_pool.execute(
                agent_name=stage.get("agent", "copy"),
                skill_id=stage.get("skill_id", ""),
                prompt_id=prompt_id,
                variables=variables,
                context=context,
            )

        # Step 2: Run tool action (if specified)
        tool_action = stage.get("tool_action")
        if tool_action and result.status == "success":
            # Build tool args from stage config + LLM output
            tool_args = stage.get("tool_args", {})
            if result.output:
                tool_args["text"] = result.output
                tool_args["prompt"] = result.output[:500]

            action_result = await execute_action(tool_action, **tool_args)

            if action_result.get("ok"):
                # Merge tool result into agent result
                result = AgentResult(
                    status="success",
                    output=result.output,
                    preview_type=self._infer_preview_type(tool_action, action_result),
                    preview_url=action_result.get("url") or action_result.get("view_url") or action_result.get("edit_url"),
                    llm_used=result.llm_used,
                    metadata={
                        **(result.metadata or {}),
                        "tool_action": tool_action,
                        "tool_result": {k: v for k, v in action_result.items() if k != "ok"},
                    },
                )
            else:
                log.warning(
                    f"Tool action '{tool_action}' failed: {action_result.get('error')} "
                    f"— LLM output preserved."
                )
                # Don't fail the stage, just note the tool error
                result = AgentResult(
                    status="success",
                    output=result.output,
                    llm_used=result.llm_used,
                    metadata={
                        **(result.metadata or {}),
                        "tool_action": tool_action,
                        "tool_error": action_result.get("error"),
                    },
                )

        return result

    def _infer_preview_type(self, action: str, result: dict) -> Optional[str]:
        """Determine the preview type from the action name."""
        if action in ("generate_image", "generate_image_variations"):
            return "image"
        if action in ("create_design",):
            return "canva"
        if action in ("post_linkedin", "post_linkedin_image", "schedule_social"):
            return "social_mock"
        if action in ("create_email_campaign", "send_email"):
            return "html"
        return None

    def _build_dag(self, stages: list[dict]) -> dict[str, set[str]]:
        """Build adjacency list: stage_name -> set of stages it depends on."""
        graph: dict[str, set[str]] = {}
        for stage in stages:
            graph[stage["name"]] = set(stage.get("depends_on", []))
        return graph

    def _topological_layers(
        self,
        stages: list[dict],
        graph: dict[str, set[str]],
    ) -> list[list[dict]]:
        """
        Sort stages into layers for parallel execution.

        Layer 0: stages with no dependencies
        Layer 1: stages that only depend on layer 0
        ...and so on.
        """
        stage_map = {s["name"]: s for s in stages}
        remaining = set(stage_map.keys())
        completed: set[str] = set()
        layers: list[list[dict]] = []

        while remaining:
            # Find stages whose dependencies are all completed
            ready = [
                name for name in remaining
                if graph.get(name, set()).issubset(completed)
            ]

            if not ready:
                # Circular dependency or missing dependency — execute remaining sequentially
                log.warning(
                    f"Dependency cycle detected in stages: {remaining}. "
                    f"Executing remaining sequentially."
                )
                layers.append([stage_map[name] for name in remaining])
                break

            layers.append([stage_map[name] for name in ready])
            completed.update(ready)
            remaining -= set(ready)

        return layers


# Module-level singleton
coordinator = AgentCoordinator()
