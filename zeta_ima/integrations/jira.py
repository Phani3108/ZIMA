"""
Jira integration — adapted from RDT 6/skills/jira.py.
Credentials loaded from vault at call time (not env vars).
"""

from typing import Optional
import httpx

from zeta_ima.integrations.vault import vault


async def _creds() -> tuple[str, str, str]:
    """Load Jira credentials from vault."""
    base_url = await vault.get("jira", "base_url") or ""
    email = await vault.get("jira", "email") or ""
    token = await vault.get("jira", "api_token") or ""
    return base_url.rstrip("/"), email, token


async def create_ticket(summary: str, description: str, project_key: str, issue_type: str = "Task") -> dict:
    """Create a Jira issue. Returns {"ok": bool, "key": "PROJ-123", "url": "..."}"""
    base_url, email, token = await _creds()
    if not all([base_url, email, token]):
        return {"ok": False, "error": "Jira not configured — add credentials in Settings."}

    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": description}]}
            ]},
            "issuetype": {"name": issue_type},
        }
    }
    async with httpx.AsyncClient(auth=(email, token), timeout=10) as client:
        r = await client.post(f"{base_url}/rest/api/3/issue", json=payload)

    if r.status_code in (401, 403):
        return {"ok": False, "error": "Jira authentication failed — check credentials in Settings."}
    if not r.is_success:
        return {"ok": False, "error": f"Jira API error {r.status_code}: {r.text[:200]}"}

    data = r.json()
    key = data.get("key", "")
    return {"ok": True, "key": key, "url": f"{base_url}/browse/{key}"}


async def search_issues(query: str, max_results: int = 5) -> list[dict]:
    """Search Jira issues by text. Returns list of {key, summary, status, url}."""
    base_url, email, token = await _creds()
    if not all([base_url, email, token]):
        return []

    jql = f'text ~ "{query}" ORDER BY updated DESC'
    async with httpx.AsyncClient(auth=(email, token), timeout=10) as client:
        r = await client.get(
            f"{base_url}/rest/api/3/search",
            params={"jql": jql, "maxResults": max_results, "fields": "summary,status,assignee"},
        )

    if not r.is_success:
        return []

    issues = r.json().get("issues", [])
    return [
        {
            "key": i["key"],
            "summary": i["fields"]["summary"],
            "status": i["fields"]["status"]["name"],
            "url": f"{base_url}/browse/{i['key']}",
        }
        for i in issues
    ]
