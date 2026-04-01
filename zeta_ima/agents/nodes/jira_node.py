"""
Jira agent node — creates tickets or searches issues based on the brief.
"""

from zeta_ima.agents.state import AgentState
from zeta_ima.integrations.jira import create_ticket, search_issues


async def jira_node(state: AgentState) -> dict:
    """Create a Jira ticket from the brief, or search if 'find'/'search' in intent."""
    brief = state.get("current_brief", "")
    lower = brief.lower()
    tool_results = dict(state.get("tool_results", {}))

    if any(w in lower for w in ["find", "search", "look up", "status", "what"]):
        results = await search_issues(brief)
        tool_results["jira_search"] = results
        msg = f"Found {len(results)} Jira issue(s)."
        if results:
            msg += " " + ", ".join(f"{r['key']}: {r['summary'][:60]}" for r in results[:3])
    else:
        # Extract project key from brief or use default
        import re
        match = re.search(r"\b([A-Z]{2,10})\b", brief)
        project_key = match.group(1) if match else "MARK"

        result = await create_ticket(
            summary=brief[:255],
            description=brief,
            project_key=project_key,
        )
        tool_results["jira_create"] = result
        if result["ok"]:
            msg = f"Created Jira ticket {result['key']}: {result['url']}"
        else:
            msg = f"Jira error: {result.get('error', 'Unknown')}"

    return {
        "tool_results": tool_results,
        "messages": [{"role": "assistant", "content": f"[Jira] {msg}"}],
    }
