"""
URL extractor — fetches a web page and extracts clean text.
"""

import httpx
from bs4 import BeautifulSoup


async def extract_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "ZetaIMA-Bot/1.0"})
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # Remove boilerplate
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Prefer <article> or <main> if present
    content = soup.find("article") or soup.find("main") or soup.find("body")
    if content is None:
        return soup.get_text(separator="\n", strip=True)

    return content.get_text(separator="\n", strip=True)
