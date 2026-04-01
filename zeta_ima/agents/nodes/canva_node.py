"""
Canva agent node — creates a design from the brief using Canva Connect API.
"""

import re
from zeta_ima.agents.state import AgentState
from zeta_ima.integrations.canva import create_design_from_template, list_templates


async def canva_node(state: AgentState) -> dict:
    brief = state.get("current_brief", "")
    draft_text = state.get("current_draft", {}).get("text") or brief
    tool_results = dict(state.get("tool_results", {}))

    # Look for template ID hint in brief (e.g. "use template DAF123")
    match = re.search(r"\bDAF\w+\b", brief, re.IGNORECASE)
    template_id = match.group(0) if match else None

    if not template_id:
        # Try to find a relevant template
        templates = await list_templates(keyword=brief[:50])
        if templates:
            template_id = templates[0]["id"]
            msg_prefix = f"Using template '{templates[0]['title']}'. "
        else:
            tool_results["canva"] = {"ok": False, "error": "No Canva templates found. Add a template ID to your brief."}
            return {
                "tool_results": tool_results,
                "messages": [{"role": "assistant", "content": "[Canva] No templates found. Please specify a template ID."}],
            }
    else:
        msg_prefix = ""

    result = await create_design_from_template(
        template_id=template_id,
        title=brief[:80],
        text_fields={"headline": draft_text[:200], "body": draft_text},
    )

    tool_results["canva"] = result
    if result["ok"]:
        msg = f"{msg_prefix}Design created: {result.get('edit_url', result.get('view_url', ''))}"
    else:
        msg = f"Canva error: {result.get('error', 'Unknown')}"

    return {
        "tool_results": tool_results,
        "messages": [{"role": "assistant", "content": f"[Canva] {msg}"}],
    }
