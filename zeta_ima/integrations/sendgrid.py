"""
SendGrid integration — transactional and marketing email.
Uses the SendGrid v3 Mail Send API.
"""

import httpx

from zeta_ima.integrations.vault import vault

SENDGRID_API = "https://api.sendgrid.com/v3"


async def _key() -> str:
    return await vault.get("sendgrid", "api_key") or ""


async def _request(method: str, path: str, json: dict | None = None) -> dict:
    key = await _key()
    if not key:
        return {"ok": False, "error": "SendGrid not configured — add API key in Settings."}

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=30,
    ) as client:
        r = await client.request(method, f"{SENDGRID_API}{path}", json=json)

    if not r.is_success:
        return {"ok": False, "error": f"SendGrid API error {r.status_code}: {r.text[:300]}"}

    # SendGrid returns 202 for accepted, sometimes with empty body
    try:
        return {"ok": True, "data": r.json() if r.content else {}}
    except Exception:
        return {"ok": True, "data": {}}


async def get_profile() -> dict:
    """Test connection by fetching user profile."""
    return await _request("GET", "/user/profile")


async def send_email(
    to: str | list[str],
    subject: str,
    html_content: str,
    from_email: str = "noreply@example.com",
    from_name: str = "Zeta IMA",
    text_content: str = "",
) -> dict:
    """
    Send a single email.

    Args:
        to: Email address or list of addresses
        subject: Email subject
        html_content: HTML body
        from_email: Sender email (must be verified in SendGrid)
        from_name: Sender display name

    Returns:
        {"ok": bool}
    """
    if isinstance(to, str):
        to = [to]

    personalizations = [{"to": [{"email": addr} for addr in to]}]
    content = [{"type": "text/html", "value": html_content}]
    if text_content:
        content.insert(0, {"type": "text/plain", "value": text_content})

    return await _request("POST", "/mail/send", json={
        "personalizations": personalizations,
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": content,
    })


async def send_batch(
    recipients: list[dict],
    subject: str,
    html_template: str,
    from_email: str = "noreply@example.com",
    from_name: str = "Zeta IMA",
) -> dict:
    """
    Send personalized emails in batch.

    Args:
        recipients: [{"email": "...", "name": "...", "vars": {"first_name": "Jo"}}]
        subject: Subject line (can use {{first_name}} substitutions)
        html_template: HTML with {{var}} placeholders
        from_email: Sender email
        from_name: Sender name

    Returns:
        {"ok": bool, "sent_count": int}
    """
    if not recipients:
        return {"ok": False, "error": "No recipients provided"}

    personalizations = []
    for recip in recipients:
        p: dict = {
            "to": [{"email": recip["email"], "name": recip.get("name", "")}],
        }
        # Add dynamic template data for substitution
        if recip.get("vars"):
            p["dynamic_template_data"] = recip["vars"]
        personalizations.append(p)

    result = await _request("POST", "/mail/send", json={
        "personalizations": personalizations,
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_template}],
    })

    if result["ok"]:
        result["sent_count"] = len(recipients)

    return result
