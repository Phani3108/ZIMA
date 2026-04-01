"""
SEMrush integration — keyword research & competitive intelligence.
Uses the SEMrush API with a simple REST interface.
"""

import csv
import io

import httpx

from zeta_ima.integrations.vault import vault

SEMRUSH_API = "https://api.semrush.com"


async def _key() -> str:
    return await vault.get("semrush", "api_key") or ""


async def _query(params: dict) -> dict:
    """Execute a SEMrush API query, parse TSV response."""
    key = await _key()
    if not key:
        return {"ok": False, "error": "SEMrush not configured — add API key in Settings."}

    params["key"] = key
    params.setdefault("export_columns", "")

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(SEMRUSH_API, params=params)

    if not r.is_success:
        return {"ok": False, "error": f"SEMrush API error {r.status_code}: {r.text[:300]}"}

    text = r.text.strip()
    if text.startswith("ERROR"):
        return {"ok": False, "error": text[:200]}

    # Parse TSV
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    rows = [dict(row) for row in reader]
    return {"ok": True, "data": rows, "count": len(rows)}


async def keyword_overview(
    keyword: str,
    database: str = "us",
) -> dict:
    """
    Get keyword overview: volume, CPC, competition, trend.

    Returns:
        {"ok": bool, "data": [{Keyword, Search Volume, CPC, Competition, ...}]}
    """
    return await _query({
        "type": "phrase_all",
        "phrase": keyword,
        "database": database,
        "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
    })


async def related_keywords(
    keyword: str,
    database: str = "us",
    limit: int = 20,
) -> dict:
    """
    Get related keywords with volume data.

    Returns:
        {"ok": bool, "data": [{Keyword, Search Volume, CPC, ...}]}
    """
    return await _query({
        "type": "phrase_related",
        "phrase": keyword,
        "database": database,
        "display_limit": str(limit),
        "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
    })


async def domain_overview(
    domain: str,
    database: str = "us",
) -> dict:
    """
    Get domain overview: organic traffic, keywords, ads.

    Returns:
        {"ok": bool, "data": [{Domain, Organic Keywords, Organic Traffic, ...}]}
    """
    return await _query({
        "type": "domain_ranks",
        "domain": domain,
        "database": database,
        "export_columns": "Dn,Rk,Or,Ot,Oc,Ad,At,Ac",
    })


async def domain_organic_keywords(
    domain: str,
    database: str = "us",
    limit: int = 20,
) -> dict:
    """
    Get a domain's top organic keywords.

    Returns:
        {"ok": bool, "data": [{Keyword, Position, Search Volume, ...}]}
    """
    return await _query({
        "type": "domain_organic",
        "domain": domain,
        "database": database,
        "display_limit": str(limit),
        "export_columns": "Ph,Po,Nq,Cp,Ur,Tr,Tc",
    })
