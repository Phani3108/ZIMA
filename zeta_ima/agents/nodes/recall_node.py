"""
Recall node — runs before meeting_node to surface similar past work.

If similar prior work is found, the graph pauses (interrupt) to let the user
choose: "Use similar approach" / "Modify" / "Start fresh".
"""

import logging
from dataclasses import asdict

from langgraph.types import interrupt

from zeta_ima.agents.state import AgentState

log = logging.getLogger(__name__)


async def recall_node(state: AgentState) -> dict:
    """
    Search all memory sources for similar past work.
    If found, populate prior_work for the interrupt card.
    """
    from zeta_ima.memory.recall import check_prior_work

    brief = state.get("current_brief", "")
    team_id = state.get("team_id", "__default__")

    result = await check_prior_work(team_id=team_id, brief=brief, top_k=5)

    prior_items = [
        {
            "id": item.id,
            "source": item.source,
            "brief": item.brief,
            "text_preview": item.text_preview,
            "similarity": round(item.similarity, 2),
            "campaign_score": item.campaign_score,
            "final_rank": round(item.final_rank, 2),
            "metadata": item.metadata,
        }
        for item in result.similar_briefs
    ]

    if not prior_items or result.recommendation == "start_fresh" and result.confidence < 0.5:
        # No meaningful prior work — skip straight to meeting
        log.info("Recall: no prior work found, skipping to meeting")
        return {
            "prior_work": [],
            "recall_decision": "start_fresh",
        }

    return {
        "prior_work": prior_items,
        "recall_decision": "",  # Will be set by await_recall_node
        "messages": [
            {
                "role": "assistant",
                "content": result.message,
            }
        ],
    }


def await_recall_node(state: AgentState) -> dict:
    """
    Interrupt to show prior work card and await user decision.
    Skips if no prior work was found.
    """
    prior_work = state.get("prior_work", [])
    if not prior_work:
        return {"recall_decision": "start_fresh"}

    decision_payload = interrupt(
        {
            "type": "prior_work",
            "prior_work": prior_work,
            "brief": state.get("current_brief", ""),
        }
    )

    decision = decision_payload.get("decision", "start_fresh")
    selected_id = decision_payload.get("selected_id", "")

    log.info("Recall decision: %s (selected: %s)", decision, selected_id)

    updates: dict = {
        "recall_decision": decision,
    }

    # If reusing, inject the selected prior work's context
    if decision in ("reuse", "modify") and selected_id:
        for item in prior_work:
            if item["id"] == selected_id:
                updates["messages"] = [
                    {
                        "role": "system",
                        "content": (
                            f"USER CHOSE TO {'REUSE' if decision == 'reuse' else 'MODIFY'} PRIOR WORK.\n"
                            f"Previous brief: {item.get('brief', '')}\n"
                            f"Previous output preview: {item.get('text_preview', '')}\n"
                            f"Campaign score: {item.get('campaign_score', 'N/A')}\n"
                            "Apply the same patterns and tone"
                            + (" with modifications per user's new brief." if decision == "modify" else ".")
                        ),
                    }
                ]
                break

    return updates
