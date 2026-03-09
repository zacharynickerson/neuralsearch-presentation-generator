"""
Evaluate queries with and without NeuralSearch.
Uses Search API (search-only key).

READ-ONLY: The /query endpoint executes searches and returns results.
It does not modify the index, add records, or change any settings.
"""

import requests
import time
from typing import List, Dict, Any, Optional

# Common product title attribute patterns across Algolia indices
TITLE_ATTRS = ["title_rfc_v3", "title", "name", "product_name"]
BRAND_ATTRS = ["brand_rfc_v3", "brand", "vendor"]


def get_hit_title(hit: dict) -> str:
    """Extract displayable title from hit (handles various index schemas)."""
    for attr in TITLE_ATTRS:
        val = hit.get(attr)
        if val is None:
            continue
        if isinstance(val, dict):
            name = val.get("en") or val.get("ar", "")[:50] if isinstance(val.get("ar"), str) else ""
            if name:
                brand_val = hit.get("brand_rfc_v3") or hit.get("brand") or {}
                brand = ""
                if isinstance(brand_val, dict):
                    brand = brand_val.get("en") or brand_val.get("key", "")
                elif isinstance(brand_val, str):
                    brand = brand_val
                if brand and name:
                    return f"{brand}: {name}"[:55]
                return str(name)[:55]
        if isinstance(val, str):
            return val[:55]
    return "(no title)"


def search(
    app_id: str,
    search_api_key: str,
    index_name: str,
    query: str,
    with_neural: bool,
    hits_per_page: int = 10,
) -> dict:
    """Run Algolia search. with_neural=True uses enableNeuralSearchPOV."""
    url = f"https://{app_id}-dsn.algolia.net/1/indexes/{index_name}/query"
    body = {
        "query": query,
        "hitsPerPage": hits_per_page,
        "disableNeuralSearch": not with_neural,
    }
    if with_neural:
        body["enableNeuralSearchPOV"] = True
    try:
        r = requests.post(
            url,
            headers={
                "x-algolia-application-id": app_id,
                "x-algolia-api-key": search_api_key,
                "content-type": "application/json",
                "accept": "application/json",
            },
            json=body,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "nbHits": 0, "hits": []}


def evaluate_queries(
    app_id: str,
    search_api_key: str,
    index_name: str,
    queries: List[str],
    analytics_lookup: Optional[Dict[str, dict]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate each query with and without NeuralSearch.
    analytics_lookup: {query_lower: {count, ctr, cr}} for relevancy metrics.
    """
    results = []
    for q in queries:
        resp_without = search(app_id, search_api_key, index_name, q, with_neural=False)
        time.sleep(0.1)
        resp_with = search(app_id, search_api_key, index_name, q, with_neural=True)
        time.sleep(0.1)

        hits_without = resp_without.get("nbHits", 0) if "error" not in resp_without else 0
        hits_with = resp_with.get("nbHits", 0) if "error" not in resp_with else 0
        hit_list_with = resp_with.get("hits", []) if "error" not in resp_with else []
        hit_list_without = resp_without.get("hits", []) if "error" not in resp_without else []

        entry = {
            "query": q,
            "without_neural": hits_without,
            "with_neural": hits_with,
            "improvement": hits_with - hits_without,
            "top3": [get_hit_title(h) for h in hit_list_with[:3]],
            "top3_without": [get_hit_title(h) for h in hit_list_without[:3]],
            "error": resp_without.get("error") or resp_with.get("error"),
        }
        if analytics_lookup:
            a = analytics_lookup.get(q.lower().strip(), {})
            entry["count"] = a.get("count", 0)
            entry["ctr"] = a.get("ctr", 0)
            entry["cr"] = a.get("cr", 0)
        results.append(entry)
    return results
