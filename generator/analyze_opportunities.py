"""
Analyze search queries for NeuralSearch opportunities.
Identifies: zero/low-result, semantic, low-engagement, long-tail, revenue-potential.
Excludes: numbers, URLs, IDs (not usable by NeuralSearch).
"""

import re
from typing import Dict, Any

from .extract_top_queries import is_numeric_url_or_id

EXCLUDE_PATTERNS = {"", "/", "s", "a", "b", "c", "p", "t", "l", "m", "d", "w"}


def is_excluded(query: str) -> bool:
    q = query.strip()
    if not q or len(q) < 2:
        return True
    if q.lower() in EXCLUDE_PATTERNS:
        return True
    if is_numeric_url_or_id(q):
        return True
    return False


def is_semantic_query(query: str) -> bool:
    q = query.strip().lower()
    if len(q) < 4:
        return False
    words = q.split()
    if len(words) < 2:
        return False
    if re.search(r'\b(what|how|where|when|why|which|who)\b', q):
        return True
    if re.search(r'\b(how to|what is|what are|which one|which size)\b', q):
        return True
    if re.search(r'\b(versus|vs|compared|compare|difference|between|better|best|worst|cheapest)\b', q):
        return True
    if re.search(r'\b(looking for|searching for|want|need|recommend|suggest|find)\b', q):
        return True
    if re.search(r'\b(for men|for women|for kids|for boys|for girls|for him|for her)\b', q):
        return True
    if re.search(r'\b(gift for|present for|ideas for)\b', q):
        return True
    if re.search(r'\b(cheap|affordable|quality|comfortable|waterproof|breathable)\b', q):
        return True
    if re.search(r'\b(size guide|size chart|how to measure)\b', q):
        return True
    if re.search(r'\b(for running|for gym|for work|for casual|for formal)\b', q):
        return True
    return False


def get_total_revenue(currencies: dict) -> float:
    if not currencies or not isinstance(currencies, dict):
        return 0.0
    total = 0.0
    for curr_data in currencies.values():
        if isinstance(curr_data, dict) and "revenue" in curr_data:
            total += float(curr_data.get("revenue", 0) or 0)
    return total


def analyze_opportunities(analytics_data: dict) -> Dict[str, Any]:
    """Run full opportunity analysis on analytics data."""
    searches = analytics_data.get("searches", []) or []
    filtered = [s for s in searches if not is_excluded(s.get("search", ""))]
    n_filtered = len(filtered)

    ctrs = [s.get("clickThroughRate") or 0 for s in filtered if s.get("clickThroughRate") is not None]
    crs = [s.get("conversionRate") or 0 for s in filtered if s.get("conversionRate") is not None]
    counts = [s.get("count", 0) for s in filtered]
    ctrs_sorted = sorted(ctrs) if ctrs else [0]
    crs_sorted = sorted(crs) if crs else [0]
    counts_sorted = sorted(counts) if counts else [0]
    p25_count = counts_sorted[int(0.25 * len(counts_sorted))] if counts_sorted else 0
    median_ctr = ctrs_sorted[len(ctrs_sorted) // 2] if ctrs_sorted else 0
    median_cr = crs_sorted[len(crs_sorted) // 2] if crs_sorted else 0

    zero_low_result = []
    semantic = []
    low_engagement = []
    long_tail = []
    revenue_opportunity = []

    for s in filtered:
        query = s.get("search", "")
        count = s.get("count", 0)
        hits = s.get("nbHits", 0)
        ctr = s.get("clickThroughRate") or 0
        cr = s.get("conversionRate") or 0
        currencies = s.get("currencies") or {}
        total_rev = get_total_revenue(currencies)
        rev_per_search = total_rev / count if count > 0 else 0

        entry = {
            "query": query,
            "count": count,
            "nbHits": hits,
            "clickThroughRate": ctr,
            "conversionRate": cr,
            "revenue": total_rev,
            "revenuePerSearch": rev_per_search,
            "averageClickPosition": s.get("averageClickPosition"),
        }

        if hits <= 10:
            zero_low_result.append(entry)
        if is_semantic_query(query):
            semantic.append(entry)
        if count >= 500 and (ctr < median_ctr or cr < median_cr):
            low_engagement.append(entry)
        if count <= p25_count and count > 0:
            long_tail.append(entry)
        if count >= 500 and rev_per_search < 0.05 and len(query) >= 3:
            revenue_opportunity.append(entry)

    def opportunity_score(e):
        return e["count"] * (1 - (e.get("clickThroughRate") or 0))

    low_engagement.sort(key=opportunity_score, reverse=True)
    zero_low_result.sort(key=lambda x: x["count"], reverse=True)
    semantic.sort(key=lambda x: x["count"], reverse=True)
    revenue_opportunity.sort(key=lambda x: x["count"], reverse=True)

    def agg(entries):
        return {
            "count": len(entries),
            "total_searches": sum(e["count"] for e in entries),
            "total_revenue": sum(e.get("revenue", 0) or 0 for e in entries),
        }

    return {
        "summary": {
            "total_queries": len(searches),
            "filtered_queries": n_filtered,
            "zero_low_result_count": len(zero_low_result),
            "semantic_count": len(semantic),
            "low_engagement_count": len(low_engagement),
            "long_tail_count": len(long_tail),
            "revenue_opportunity_count": len(revenue_opportunity),
            "segment_aggregates": {
                "zero_low_result": agg(zero_low_result),
                "semantic": agg(semantic),
                "low_engagement": agg(low_engagement),
                "revenue_opportunity": agg(revenue_opportunity),
            },
        },
        "zero_low_result": zero_low_result[:200],
        "semantic": semantic[:200],
        "low_engagement": low_engagement[:200],
        "long_tail_sample": long_tail[:100],
        "revenue_opportunity": revenue_opportunity[:200],
        "top_queries_by_volume": [
            {"query": s.get("search", ""), "count": s.get("count", 0), "nbHits": s.get("nbHits", 0),
             "ctr": s.get("clickThroughRate"), "cr": s.get("conversionRate")}
            for s in sorted(filtered, key=lambda x: x.get("count", 0), reverse=True)[:50]
        ],
    }
