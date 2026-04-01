"""
Confluence agent node — publishes content to Confluence or searches pages.
"""

from zeta_ima.agents.state import AgentState
from zeta_ima.integrations.confluence import publish_page, search_pages


async def confluence_node(state: AgentState) -> dict:
    brief = state.get("current_brief", "")
    lower = brief.lower()
    tool_results = dict(state.get("tool_results", {}))

    if any(w in lower for w in ["find", "search", "read", "look up", "what"]):
        results = await search_pages(brief)
        tool_results["confluence_search"] = results
        msg = f"Found {len(results)} Confluence page(s)."
    else:
        # Use the current draft if available, otherwise use the brief
        draft = state.get("current_draft", {}).get("text") or brief
        title = brief[:100]
        body_html = f"<p>{draft.replace(chr(10), '</p><p>')}</p>"

        result = await publish_page(title=title, body_html=body_html)
        tool_results["confluence_publish"] = result
        if result["ok"]:
            msg = f"Published to Confluence: {result['url']}"
        else:
            msg = f"Confluence error: {result.get('error', 'Unknown')}"

    return {
        "tool_results": tool_results,
        "messages": [{"role": "assistant", "content": f"[Confluence] {msg}"}],
    }
