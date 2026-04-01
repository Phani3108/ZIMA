"""
Analytics Pull — connectors for external campaign performance data.

Each connector returns a list of dicts:
  [{"campaign_id": ..., "metrics": {...}, "composite_score": float}]

Start with Mailchimp (simplest), then GA4, then LinkedIn.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


async def pull_mailchimp(
    credentials: dict[str, str],
    campaign_id: str = "",
) -> list[dict[str, Any]]:
    """
    Pull campaign stats from Mailchimp API.

    credentials: {"api_key": "...", "server_prefix": "us1"}
    """
    api_key = credentials.get("api_key", "")
    server = credentials.get("server_prefix", "us1")

    if not api_key:
        log.warning("Mailchimp: no API key provided")
        return []

    import httpx
    base_url = f"https://{server}.api.mailchimp.com/3.0"
    headers = {"Authorization": f"Bearer {api_key}"}

    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        if campaign_id:
            url = f"{base_url}/reports/{campaign_id}"
        else:
            url = f"{base_url}/reports?count=10&sort_field=send_time&sort_dir=DESC"

        resp = await client.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        campaigns = data.get("reports", [data]) if "reports" in data else [data]

        for camp in campaigns:
            opens = camp.get("opens", {})
            clicks = camp.get("clicks", {})
            metrics = {
                "emails_sent": camp.get("emails_sent", 0),
                "open_rate": opens.get("open_rate", 0),
                "click_rate": clicks.get("click_rate", 0),
                "unique_opens": opens.get("unique_opens", 0),
                "unique_clicks": clicks.get("unique_subscriber_clicks", 0),
                "unsubscribes": camp.get("unsubscribed", 0),
                "bounce_rate": camp.get("bounces", {}).get("hard_bounces", 0),
            }

            # Composite: weighted average of open_rate and click_rate
            open_rate = metrics["open_rate"] * 100 if isinstance(metrics["open_rate"], float) else metrics["open_rate"]
            click_rate = metrics["click_rate"] * 100 if isinstance(metrics["click_rate"], float) else metrics["click_rate"]
            composite = (open_rate * 0.4) + (click_rate * 0.6)

            results.append({
                "campaign_id": camp.get("id", campaign_id),
                "metrics": metrics,
                "composite_score": round(composite, 1),
            })

    return results


async def pull_ga4(
    credentials: dict[str, str],
    campaign_id: str = "",
) -> list[dict[str, Any]]:
    """
    Pull campaign data from Google Analytics 4 Data API.

    credentials: {"property_id": "...", "service_account_json": "..."}
    """
    # Placeholder — GA4 requires google-analytics-data SDK
    log.info("GA4 connector: not yet implemented (requires google-analytics-data SDK)")
    return []


async def pull_linkedin(
    credentials: dict[str, str],
    campaign_id: str = "",
) -> list[dict[str, Any]]:
    """
    Pull campaign analytics from LinkedIn Marketing API.

    credentials: {"access_token": "...", "ad_account_id": "..."}
    """
    # Placeholder — LinkedIn Marketing API requires OAuth2 token
    log.info("LinkedIn connector: not yet implemented (requires Marketing API access)")
    return []
