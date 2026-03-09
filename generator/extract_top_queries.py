"""
Extract top 100 NeuralSearch-fit queries for slides.
Excludes: brands, single words, typos/noise, numbers, URLs, IDs.
"""

import re
from typing import List, Set

# Patterns for URLs, IDs, numeric-only
URL_PATTERN = re.compile(r'https?://|www\.|\.com|\.org|\.net|\.io|/', re.I)
NUMERIC_PATTERN = re.compile(r'^\d+$|^\d[\d\s\-\.]*\d?$')  # all digits, or mostly digits with separators

# Known brand names / brand-like terms to exclude
BRAND_PATTERNS = {
    "coach", "tumi", "zara", "aldo", "ugg", "levi", "levis", "nike", "adidas", "puma",
    "converse", "skechers", "vans", "crocs", "timberland", "under armour", "swarovski",
    "balenciaga", "versace", "oakley", "yeezy", "hackett", "michael kors", "ralph lauren",
    "cole haan", "tommy", "tommy hilfiger", "charles", "on cloud", "alpha industries",
}

# Single-char / typo noise
EXCLUDE = {"ad", "adi", "adid", "adida", "ba", "be", "bla", "bl", "bo", "ca", "cal",
           "cha", "cham", "co", "coa", "coac", "cro", "ja", "jac", "jaco", "jo", "ki",
           "lac", "laco", "lacos", "la", "le", "ma", "me", "mi", "nee", "nik", "ni",
           "nile", "pa", "per", "pu", "pum", "ra", "re", "ree", "sa", "sh", "sho",
           "sk", "ske", "so", "swar", "swaro", "to", "tra", "un", "wa", "wat", "wom",
           "wome", "qv", "jw", "hod", "shies", "balen", "versa", "inner", "next",
           "terno", "nee", "jw"}


def is_brand_query(query: str) -> bool:
    """Heuristic: query is or starts with known brand."""
    q = query.strip().lower()
    words = q.split()
    if not words:
        return True
    first = words[0]
    for brand in BRAND_PATTERNS:
        if brand in q or q.startswith(brand) or first == brand:
            return True
    return False


def is_single_word(query: str) -> bool:
    return len(query.strip().split()) < 2


def is_numeric_url_or_id(query: str) -> bool:
    """Exclude queries that are numbers, URLs, or IDs — not usable by NeuralSearch."""
    q = query.strip()
    if not q or len(q) < 2:
        return True
    # All digits or mostly digits (e.g. "12345", "123-456", "1.0")
    if NUMERIC_PATTERN.match(q):
        return True
    if q.replace(" ", "").isdigit():
        return True
    # URLs
    if URL_PATTERN.search(q):
        return True
    # Long alphanumeric IDs (e.g. product SKUs, UUIDs)
    if len(q) >= 10 and sum(c.isalnum() or c in "-_" for c in q) / max(len(q), 1) > 0.9 and not any(c.isalpha() for c in q[:3]):
        return True
    # Mostly digits
    digit_ratio = sum(c.isdigit() for c in q) / max(len(q), 1)
    if digit_ratio > 0.7:
        return True
    return False


def extract_top_queries(
    opportunities: dict,
    max_queries: int = 100,
) -> List[str]:
    """
    Extract top NeuralSearch-fit queries from opportunities.
    Combines zero_low_result, semantic, revenue_opportunity.
    Excludes brands, single words, noise.
    """
    seen: dict = {}
    for cat in ("zero_low_result", "semantic", "revenue_opportunity"):
        for e in opportunities.get(cat, [])[:150]:
            q = (e.get("query") or "").strip()
            if not q or len(q) < 3:
                continue
            if q.lower() in EXCLUDE:
                continue
            if is_single_word(q):
                continue
            if is_brand_query(q):
                continue
            if is_numeric_url_or_id(q):
                continue
            count = e.get("count", 0)
            if q not in seen or seen[q]["count"] < count:
                seen[q] = {"query": q, "count": count, "category": cat}

    sorted_queries = sorted(seen.values(), key=lambda x: -x["count"])[:max_queries]
    return [x["query"] for x in sorted_queries]
