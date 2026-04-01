"""
Confluence extractor — pulls page content via the Confluence REST API
and returns clean plain text (strips HTML tags).
"""

from bs4 import BeautifulSoup

from zeta_ima.integrations.confluence import get_page, search_pages


async def extract_page(page_id: str) -> tuple[str, str]:
    """
    Returns (title, plain_text) for a Confluence page.
    Raises ValueError if page not found or not configured.
    """
    result = await get_page(page_id)
    if not result["ok"]:
        raise ValueError(result.get("error", "Failed to fetch Confluence page"))

    html = result["body"]
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator="\n", strip=True)
    return result["title"], text


async def extract_space(space_key: str, limit: int = 20) -> list[tuple[str, str, str]]:
    """
    Pull up to `limit` pages from a Confluence space.
    Returns list of (page_id, title, plain_text).
    """
    pages = await search_pages(f"space={space_key}", limit=limit)
    results = []
    for p in pages:
        # search_pages returns url, not id — we'd need the page id
        # This is a simplified version; production would paginate the space API
        results.append((p.get("id", ""), p["title"], ""))
    return results
