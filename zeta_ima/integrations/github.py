"""
GitHub integration — adapted from AAH/services/integrations/github_app.py.
Uses GitHub App JWT auth. Credentials loaded from vault.
"""

import time
import jwt
import httpx

from zeta_ima.integrations.vault import vault


async def _creds() -> tuple[str, str, str]:
    app_id = await vault.get("github", "app_id") or ""
    installation_id = await vault.get("github", "installation_id") or ""
    pem = await vault.get("github", "private_key_pem") or ""
    return app_id, installation_id, pem


def _app_jwt(app_id: str, pem: str) -> str:
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + (9 * 60), "iss": app_id}
    return jwt.encode(payload, pem, algorithm="RS256")


async def _install_token(app_id: str, installation_id: str, pem: str) -> str:
    app_token = _app_jwt(app_id, pem)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {app_token}", "Accept": "application/vnd.github+json"},
        )
        r.raise_for_status()
    return r.json()["token"]


async def create_pull_request(
    owner: str, repo: str, title: str, body: str, head: str, base: str = "main"
) -> dict:
    """Create a GitHub PR. Returns {"ok": bool, "url": "..."}"""
    app_id, install_id, pem = await _creds()
    if not all([app_id, install_id, pem]):
        return {"ok": False, "error": "GitHub not configured — add credentials in Settings."}

    token = await _install_token(app_id, install_id, pem)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"title": title, "body": body, "head": head, "base": base},
        )

    if not r.is_success:
        return {"ok": False, "error": f"GitHub error {r.status_code}: {r.text[:200]}"}

    data = r.json()
    return {"ok": True, "url": data.get("html_url", ""), "number": data.get("number")}


async def get_file_content(owner: str, repo: str, path: str, ref: str = "main") -> dict:
    """Read a file from a GitHub repo."""
    app_id, install_id, pem = await _creds()
    if not all([app_id, install_id, pem]):
        return {"ok": False, "error": "GitHub not configured."}

    token = await _install_token(app_id, install_id, pem)
    import base64
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"ref": ref},
        )

    if not r.is_success:
        return {"ok": False, "error": f"GitHub error {r.status_code}"}

    data = r.json()
    content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
    return {"ok": True, "content": content, "sha": data.get("sha", "")}
