"""
Workflow Engine — executes workflows stage-by-stage using the Agent Pool.

The engine:
1. Creates workflows from skill definitions or templates
2. Advances workflows by executing the next pending stage
3. Handles approvals and rejections
4. Supports retry with different LLMs
5. Marks workflows as blocked/completed based on stage status
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from zeta_ima.agents.pool import agent_pool
from zeta_ima.memory.brand import search_brand_examples
from zeta_ima.skills.registry import get_skill
from zeta_ima.workflows.events import workflow_events
from zeta_ima.workflows.models import (
    advance_current_stage,
    create_workflow,
    get_workflow,
    update_stage,
    update_workflow_status,
)
from zeta_ima.workflows.templates import WORKFLOW_TEMPLATES

log = logging.getLogger(__name__)


class WorkflowEngine:
    """Orchestrates workflow creation and stage execution."""

    async def create_from_template(
        self,
        template_id: str,
        variables: dict,
        user_id: str,
        name: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> dict:
        """Create a workflow from a pre-built template."""
        template = WORKFLOW_TEMPLATES.get(template_id)
        if template is None:
            raise ValueError(f"Template '{template_id}' not found")

        wf_name = name or template["name"]

        return await create_workflow(
            name=wf_name,
            skill_id=template.get("skill_id", template_id),
            template_id=template_id,
            created_by=user_id,
            variables=variables,
            stages=template["stages"],
            campaign_id=campaign_id,
        )

    async def create_from_skill(
        self,
        skill_id: str,
        prompt_id: str,
        variables: dict,
        user_id: str,
        name: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> dict:
        """Create a simple single-stage workflow from a skill + prompt."""
        skill = get_skill(skill_id)
        if skill is None:
            raise ValueError(f"Skill '{skill_id}' not found")

        prompt = skill.get_prompt(prompt_id)
        if prompt is None:
            raise ValueError(f"Prompt '{prompt_id}' not found in skill '{skill_id}'")

        wf_name = name or f"{skill.name}: {prompt.name}"
        stages = [
            {
                "name": prompt.name,
                "agent": prompt.agent,
                "prompt": prompt_id,
                "skill_id": skill_id,
                "requires_approval": True,
            }
        ]

        return await create_workflow(
            name=wf_name,
            skill_id=skill_id,
            template_id=None,
            created_by=user_id,
            variables=variables,
            stages=stages,
            campaign_id=campaign_id,
        )

    async def advance(self, workflow_id: str) -> dict:
        """
        Execute the next pending stage in the workflow.

        Returns the updated workflow dict.
        """
        wf = await get_workflow(workflow_id)
        if wf is None:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        if wf["status"] != "active":
            raise ValueError(f"Workflow is '{wf['status']}', cannot advance")

        # Find the next pending stage
        stages = wf["stages"]
        current_idx = wf["current_stage_index"]

        if current_idx >= len(stages):
            await update_workflow_status(workflow_id, "completed")
            return await get_workflow(workflow_id)

        stage = stages[current_idx]

        # Check if stage requires approval and is awaiting it
        if stage["status"] == "awaiting_review":
            return wf  # Can't advance past approval gate

        # Build context (brand voice + KB)
        context = await self._build_context(wf["variables"])

        # Mark stage as in_progress
        await update_stage(
            stage["id"],
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )

        # Emit event: stage started
        await workflow_events.emit(workflow_id, {
            "type": "stage_started",
            "stage_id": stage["id"],
            "stage_name": stage["name"],
            "stage_index": current_idx,
            "agent": stage["agent_name"],
        })

        # Execute via agent pool
        result = await agent_pool.execute(
            agent_name=stage["agent_name"],
            skill_id=stage.get("skill_id") or wf["skill_id"],
            prompt_id=stage.get("prompt_id") or "default",
            variables=wf["variables"],
            context=context,
        )

        # Update stage with result
        if result.status == "success":
            new_status = "awaiting_review" if stage["requires_approval"] else "approved"
            await update_stage(
                stage["id"],
                status=new_status,
                output={"text": result.output, "metadata": result.metadata},
                preview_type=result.preview_type,
                preview_url=result.preview_url,
                llm_used=result.llm_used,
                completed_at=result.completed_at,
            )

            # Emit event: stage completed
            await workflow_events.emit(workflow_id, {
                "type": "stage_completed",
                "stage_id": stage["id"],
                "stage_name": stage["name"],
                "stage_index": current_idx,
                "status": new_status,
                "llm_used": result.llm_used,
                "preview_type": result.preview_type,
                "output_preview": (result.output or "")[:200],
            })

            # Send notification
            try:
                from zeta_ima.notify.service import notifications
                await notifications.send(
                    user_id=wf["created_by"],
                    title=f"Stage Complete: {stage['name']}",
                    body=f"'{stage['name']}' in workflow '{wf['name']}' is {'ready for review' if new_status == 'awaiting_review' else 'done'}.",
                    action_url=f"/workflows/{workflow_id}",
                    metadata={"workflow_id": workflow_id, "stage_id": stage["id"]},
                )
            except Exception as e:
                log.debug(f"Notification send failed: {e}")

            # Record to audit log
            try:
                from zeta_ima.memory.audit import audit_log
                await audit_log.record(
                    actor=stage["agent_name"],
                    action="stage_completed",
                    resource_type="stage",
                    resource_id=stage["id"],
                    details={"workflow_id": workflow_id, "status": new_status, "llm_used": result.llm_used},
                )
            except Exception:
                pass

            # If no approval needed, auto-advance
            if not stage["requires_approval"]:
                await advance_current_stage(workflow_id)

            # Check if workflow is now complete
            updated = await get_workflow(workflow_id)
            if updated and updated["current_stage_index"] >= len(updated["stages"]):
                await update_workflow_status(workflow_id, "completed")
                await workflow_events.emit(workflow_id, {"type": "workflow_completed"})
                workflow_events.close_workflow(workflow_id)
        else:
            await update_stage(
                stage["id"],
                status="needs_retry",
                error=result.error,
                completed_at=result.completed_at,
            )

            # Emit event: stage failed
            await workflow_events.emit(workflow_id, {
                "type": "stage_failed",
                "stage_id": stage["id"],
                "stage_name": stage["name"],
                "error": result.error,
            })

        return await get_workflow(workflow_id)

    async def approve_stage(
        self,
        workflow_id: str,
        stage_id: str,
        decision: str,
        comment: str = "",
    ) -> dict:
        """
        Approve or reject a stage.

        decision: "approve" or "reject"
        """
        if decision == "approve":
            await update_stage(
                stage_id,
                status="approved",
                completed_at=datetime.now(timezone.utc),
            )
            await advance_current_stage(workflow_id)

            # Check if workflow is complete
            wf = await get_workflow(workflow_id)
            if wf and wf["current_stage_index"] >= len(wf["stages"]):
                await update_workflow_status(workflow_id, "completed")
        elif decision == "reject":
            await update_stage(
                stage_id,
                status="needs_retry",
                error=f"Rejected: {comment}" if comment else "Rejected by reviewer",
            )
        else:
            raise ValueError(f"Invalid decision: {decision}")

        return await get_workflow(workflow_id)

    async def retry_stage(
        self,
        workflow_id: str,
        stage_id: str,
        llm_override: Optional[str] = None,
    ) -> dict:
        """Retry a failed/rejected stage, optionally with a different LLM."""
        wf = await get_workflow(workflow_id)
        if wf is None:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        # Find the stage
        stage = next((s for s in wf["stages"] if s["id"] == stage_id), None)
        if stage is None:
            raise ValueError(f"Stage '{stage_id}' not found")

        context = await self._build_context(wf["variables"])

        await update_stage(
            stage_id,
            status="in_progress",
            error=None,
            started_at=datetime.now(timezone.utc),
        )

        result = await agent_pool.execute(
            agent_name=stage["agent_name"],
            skill_id=stage.get("skill_id") or wf["skill_id"],
            prompt_id=stage.get("prompt_id") or "default",
            variables=wf["variables"],
            context=context,
            llm_override=llm_override,
        )

        if result.status == "success":
            new_status = "awaiting_review" if stage["requires_approval"] else "approved"
            await update_stage(
                stage_id,
                status=new_status,
                output={"text": result.output, "metadata": result.metadata},
                preview_type=result.preview_type,
                llm_used=result.llm_used,
                error=None,
                completed_at=result.completed_at,
            )
        else:
            await update_stage(
                stage_id,
                status="needs_retry",
                error=result.error,
                completed_at=result.completed_at,
            )

        return await get_workflow(workflow_id)

    async def _build_context(self, variables: dict) -> dict:
        """Build shared context for prompt rendering."""
        context = {
            "brand_voice_context": "",
            "brand_examples": "",
            "kb_context": "",
        }

        # Load brand examples from Qdrant
        brief = variables.get("topic") or variables.get("product_name") or ""
        if brief:
            try:
                examples = await search_brand_examples(brief, top_k=3)
                context["brand_examples"] = "\n---\n".join(examples)
            except Exception as e:
                log.warning(f"Failed to load brand examples: {e}")

        return context


# Module-level singleton
workflow_engine = WorkflowEngine()
