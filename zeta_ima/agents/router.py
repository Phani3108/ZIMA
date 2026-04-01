"""
Intent router — classifies the user's brief and determines which agent(s) to invoke.

Uses GPT-4o-mini for speed. Returns a list of agent names to route to.
Multi-intent supported: "Write a post AND create a Jira ticket" → ["copy", "jira"]

Intent map:
  copy        → write/draft/post/email/headline/copy/content
  jira        → ticket/jira/task/issue/bug/sprint/create ticket
  confluence  → confluence/wiki/page/document/save to/publish
  github      → github/pr/pull request/commit/code/branch
  canva       → design/canva/template/visual/banner/image
  research    → find/search/what does/tell me about/summarise/look up
"""

import json
import re
from typing import List

from openai import AsyncOpenAI

from zeta_ima.config import settings

_SYSTEM = """You are an intent classifier for a marketing AI agent.
Given a user message, return a JSON array of intents from this set:
["copy", "jira", "confluence", "github", "canva", "research"]

Rules:
- Return ["copy"] for writing/drafting/content requests
- Return ["jira"] for ticket/task/issue creation or lookup
- Return ["confluence"] for reading or saving Confluence pages
- Return ["github"] for PRs, code files, commits
- Return ["canva"] for design/visual/template requests
- Return ["research"] for search/lookup/summary requests
- Return multiple if the message clearly asks for multiple actions
- Default to ["copy"] if unclear

Return ONLY the JSON array, nothing else. Example: ["copy", "jira"]"""


async def classify_intent(brief: str) -> List[str]:
    """Returns list of agent intents for this brief."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.llm_router,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": brief},
        ],
        max_tokens=50,
    )
    raw = resp.choices[0].message.content.strip()
    try:
        intents = json.loads(raw)
        if isinstance(intents, list) and all(isinstance(i, str) for i in intents):
            return intents
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: keyword matching
    lower = brief.lower()
    found = []
    if any(w in lower for w in ["write", "draft", "post", "email", "headline", "copy", "content"]):
        found.append("copy")
    if any(w in lower for w in ["ticket", "jira", "task", "issue", "bug"]):
        found.append("jira")
    if any(w in lower for w in ["confluence", "wiki", "publish page"]):
        found.append("confluence")
    if any(w in lower for w in ["github", "pull request", " pr ", "commit"]):
        found.append("github")
    if any(w in lower for w in ["canva", "design", "template", "visual", "banner"]):
        found.append("canva")
    if any(w in lower for w in ["find", "search", "what", "tell me", "summarise", "look up"]):
        found.append("research")

    return found or ["copy"]
