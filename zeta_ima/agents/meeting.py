"""
Scrum Meeting Engine — agents discuss a brief before execution.

One multi-persona LLM call generates the entire meeting transcript
(fast, cheap, coherent). The execution phase still uses separate
per-agent calls.

Flow:
  1. CMO frames the task, identifies participants from pipeline
  2. LLM generates multi-persona meeting transcript
  3. Transcript is parsed into individual agent messages
  4. Structured MeetingPlan is extracted
  5. User is shown the plan and can approve / modify / cancel
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from zeta_ima.agents.roles import AgentRole, role_registry
from zeta_ima.config import settings, get_openai_client

log = logging.getLogger(__name__)


@dataclass
class MeetingMessage:
    """Single message in the meeting transcript."""
    agent_id: str
    agent_title: str
    avatar: str
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_title": self.agent_title,
            "avatar": self.avatar,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class MeetingPlan:
    """Structured execution plan produced by the meeting."""
    tasks: List[dict] = field(default_factory=list)
    assigned_agents: dict = field(default_factory=dict)
    estimated_duration: str = ""
    summary: str = ""
    transcript: List[MeetingMessage] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tasks": self.tasks,
            "assigned_agents": self.assigned_agents,
            "estimated_duration": self.estimated_duration,
            "summary": self.summary,
        }


def _build_meeting_system_prompt(
    participants: List[AgentRole],
    brief: str,
    pipeline: List[str],
    kb_context: List[str],
    brain_context: List[str],
    modifications: str = "",
) -> str:
    """Build the multi-persona system prompt for the meeting LLM call."""

    participant_block = "\n".join(
        f"- {r.avatar_emoji} **{r.title}** ({r.id}): {'; '.join(r.responsibilities[:2])}"
        for r in participants
    )

    context_block = ""
    if kb_context:
        context_block += "\n\nKnowledge Base Context:\n" + "\n".join(f"- {c[:200]}" for c in kb_context[:3])
    if brain_context:
        context_block += "\n\nAgency Brain Insights:\n" + "\n".join(f"- {c[:200]}" for c in brain_context[:3])

    modification_block = ""
    if modifications:
        modification_block = f"\n\nUSER MODIFICATIONS TO INCORPORATE:\n{modifications}\n"

    return f"""You are simulating a quick planning meeting at Zeta Marketing Agency.
The meeting participants are:

{participant_block}

The user has submitted this brief:
\"{brief}\"

Pipeline that will execute: {pipeline}
{context_block}
{modification_block}
RULES:
1. Each participant speaks ONCE in order, starting with the CMO/lead.
2. Each message is 1-3 sentences. Be concise and actionable.
3. Each participant states: what they will do, what they need, any concerns.
4. The CMO/lead speaks last to summarize the plan.
5. Format each message EXACTLY as:
   [{agent_id}]: <message>

After the transcript, output a JSON plan block:
```json
{{
  "tasks": [
    {{"step": 1, "agent": "<agent_id>", "action": "<what they will do>"}},
    ...
  ],
  "estimated_duration": "<e.g. ~45 seconds>",
  "summary": "<one sentence plan summary>"
}}
```"""


def _parse_transcript(
    raw: str,
    participants: List[AgentRole],
) -> tuple[List[MeetingMessage], dict]:
    """Parse LLM output into individual messages and structured plan."""

    role_lookup = {r.id: r for r in participants}
    messages: List[MeetingMessage] = []
    plan = {}

    # Split into transcript lines and JSON plan
    json_start = raw.find("```json")
    json_end = raw.find("```", json_start + 7) if json_start >= 0 else -1

    transcript_text = raw[:json_start] if json_start >= 0 else raw
    json_text = raw[json_start + 7:json_end].strip() if json_start >= 0 and json_end >= 0 else ""

    # Parse transcript lines: [agent_id]: message
    for line in transcript_text.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("["):
            continue

        bracket_end = line.find("]:")
        if bracket_end < 0:
            bracket_end = line.find("]")
            if bracket_end < 0:
                continue

        agent_id = line[1:bracket_end].strip()
        content = line[bracket_end + 2:].strip() if line[bracket_end + 1:bracket_end + 2] == ":" else line[bracket_end + 1:].strip()

        # Look up role
        role = role_lookup.get(agent_id)
        if role:
            messages.append(MeetingMessage(
                agent_id=agent_id,
                agent_title=role.title,
                avatar=role.avatar_emoji,
                content=content,
            ))
        else:
            # Try fuzzy match by checking if agent_id appears in any role's id
            for rid, r in role_lookup.items():
                if agent_id.lower() in rid.lower() or rid.lower() in agent_id.lower():
                    messages.append(MeetingMessage(
                        agent_id=rid,
                        agent_title=r.title,
                        avatar=r.avatar_emoji,
                        content=content,
                    ))
                    break

    # Parse JSON plan
    if json_text:
        try:
            plan = json.loads(json_text)
        except json.JSONDecodeError:
            # Try extracting JSON from anywhere in the remaining text
            try:
                brace_start = json_text.find("{")
                brace_end = json_text.rfind("}") + 1
                if brace_start >= 0 and brace_end > brace_start:
                    plan = json.loads(json_text[brace_start:brace_end])
            except (json.JSONDecodeError, ValueError):
                log.debug("Failed to parse meeting plan JSON")

    return messages, plan


async def run_meeting(
    brief: str,
    pipeline: List[str],
    kb_context: List[str] | None = None,
    brain_context: List[str] | None = None,
    modifications: str = "",
) -> MeetingPlan:
    """
    Run a scrum meeting for the given brief and pipeline.

    Returns a MeetingPlan with transcript and structured tasks.
    """
    participants = role_registry.get_meeting_participants(pipeline)
    if not participants:
        # Fallback: no roles loaded, return empty plan
        return MeetingPlan(summary="No agent roles configured.", transcript=[])

    system_prompt = _build_meeting_system_prompt(
        participants=participants,
        brief=brief,
        pipeline=pipeline,
        kb_context=kb_context or [],
        brain_context=brain_context or [],
        modifications=modifications,
    )

    client = get_openai_client()
    resp = await client.chat.completions.create(
        model=settings.llm_copy,  # Use capable model for multi-persona reasoning
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Run the planning meeting for this brief: \"{brief}\""},
        ],
        temperature=0.4,
    )

    raw = resp.choices[0].message.content or ""
    messages, plan_data = _parse_transcript(raw, participants)

    return MeetingPlan(
        tasks=plan_data.get("tasks", []),
        assigned_agents={
            t["agent"]: t.get("action", "")
            for t in plan_data.get("tasks", [])
            if isinstance(t, dict) and "agent" in t
        },
        estimated_duration=plan_data.get("estimated_duration", "~30 seconds"),
        summary=plan_data.get("summary", ""),
        transcript=messages,
    )


def should_skip_meeting(brief: str) -> bool:
    """Return True if the brief is too simple to warrant a planning meeting."""
    word_count = len(brief.split())
    return word_count < settings.meeting_skip_word_threshold
