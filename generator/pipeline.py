"""
Full pipeline: fetch analytics → compute metrics → analyze → evaluate → render.
"""

from typing import Dict, Any, Optional
from .fetch_analytics import fetch_all_top_queries
from .compute_metrics import compute_metrics
from .analyze_opportunities import analyze_opportunities
from .evaluate_queries import evaluate_queries
from .extract_top_queries import extract_top_queries, is_numeric_url_or_id as _is_invalid_query
from .render_slides import render_presentation


def build_demo_queries(opportunities: dict) -> Dict[str, list]:
    """Build demo query lists for each category from opportunities. Excludes numbers, URLs, IDs."""
    from .extract_top_queries import is_numeric_url_or_id
    def _valid(q):
        return q and not is_numeric_url_or_id(q)
    thin = [e["query"] for e in opportunities.get("zero_low_result", [])[:20] if e.get("nbHits", 0) <= 10 and _valid(e.get("query", ""))][:15]
    semantic = [e["query"] for e in opportunities.get("semantic", [])[:20] if _valid(e.get("query", ""))][:15]
    conceptual = [e["query"] for e in opportunities.get("zero_low_result", []) if _valid(e.get("query", "")) and ("for " in e.get("query", "") or " " in e.get("query", ""))][:12]
    relevancy = [e["query"] for e in opportunities.get("semantic", []) if _valid(e.get("query", "")) and e.get("count", 0) >= 1000][:12]

    # Fallback: use curated lists if not enough from opportunities
    if len(thin) < 5:
        thin = ["lipstick", "bath robe", "thermal leggings", "diaper bag", "waterproof shoes"] + thin
    if len(semantic) < 5:
        semantic = ["watches for women", "formal shoes for men", "wallet for men", "perfumes for women"] + semantic
    if len(conceptual) < 5:
        conceptual = ["waterproof shoes", "safety shoes for men", "gift set for women", "diaper bag"] + conceptual
    if len(relevancy) < 3:
        relevancy = ["perfumes for men", "wallet for men", "perfumes for women"] + relevancy

    return {
        "thin_results": thin[:12],
        "natural_language": semantic[:12],
        "conceptual": conceptual[:12],
        "relevancy": relevancy[:12],
    }


def run_pipeline(
    app_id: str,
    index_name: str,
    search_api_key: str,
    analytics_api_key: str,
    customer_name: str,
    region: str = "US",
    days_back: int = 90,
) -> Dict[str, Any]:
    """
    Run full pipeline and return presentation data + HTML.
    """
    # 1. Fetch analytics
    analytics_data = fetch_all_top_queries(
        app_id=app_id,
        analytics_api_key=analytics_api_key,
        index_name=index_name,
        region=region,
        days_back=days_back,
    )

    # 2. Compute metrics
    metrics = compute_metrics(analytics_data)

    # 3. Analyze opportunities
    opportunities = analyze_opportunities(analytics_data)

    # 4. Build demo queries and evaluate
    demo_queries = build_demo_queries(opportunities)
    all_queries = list(set(
        demo_queries["thin_results"] +
        demo_queries["natural_language"] +
        demo_queries["conceptual"] +
        demo_queries["relevancy"]
    ))

    analytics_lookup = {s.get("search", "").lower(): {"count": s.get("count", 0), "ctr": s.get("clickThroughRate") or 0, "cr": s.get("conversionRate") or 0} for s in analytics_data.get("searches", [])}

    evaluation = evaluate_queries(
        app_id=app_id,
        search_api_key=search_api_key,
        index_name=index_name,
        queries=all_queries,
        analytics_lookup=analytics_lookup,
    )

    eval_by_query = {r["query"]: r for r in evaluation}

    # 5. Extract top 100 NS-fit queries
    top100 = extract_top_queries(opportunities, max_queries=100)

    # 6. Build opportunity summaries for slides
    thin_results = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0}) for q in demo_queries["thin_results"] if q in eval_by_query]
    natural_language = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0}) for q in demo_queries["natural_language"] if q in eval_by_query]
    conceptual = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0}) for q in demo_queries["conceptual"] if q in eval_by_query]
    relevancy = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0, "ctr": 0, "cr": 0}) for q in demo_queries["relevancy"] if q in eval_by_query]

    # 7. Get sample intro chips (query with improvement)
    intro_chips = []
    for r in evaluation:
        if r.get("with_neural", 0) > r.get("without_neural", 0) and not r.get("error"):
            intro_chips.append(f"{r['query']} {r['without_neural']}→{r['with_neural']}")
    intro_chips = intro_chips[:12]

    # 8. Get long-tail sample for slide 3
    long_tail_sample = [e.get("query", "") for e in opportunities.get("long_tail_sample", [])[:12] if e.get("query")]

    # 9. Multi-lingual: pull from current customer's index — Arabic, Hebrew, Cyrillic, CJK, Thai, etc.
    import re
    all_queries_flat = [s.get("search", "") for s in analytics_data.get("searches", [])[:5000] if (s.get("search") or "").strip()]
    # Non-Latin scripts: Arabic, Hebrew, Cyrillic, CJK, Thai, etc. (exclude numbers/URLs)
    non_latin = re.compile(
        r'[\u0600-\u06FF\u0590-\u05FF\u0400-\u04FF\u4E00-\u9FFF\u0E00-\u0E7F]',
        re.U
    )
    arabic_or_other = [q for q in all_queries_flat if non_latin.search(q) and not _is_invalid_query(q)][:6]
    english_sample = [q for q in all_queries_flat if q and not non_latin.search(q) and not _is_invalid_query(q)][:6]

    context = {
        "customer_name": customer_name,
        "metrics": metrics,
        "intro_chips": intro_chips,
        "long_tail_sample": long_tail_sample or ["shoes for men", "jacket for men", "watches for women"][:12],
        "thin_results": thin_results,
        "natural_language": natural_language,
        "conceptual": conceptual,
        "relevancy": relevancy,
        "top100_queries": top100,
        "opportunities": opportunities,
        "analytics_data": analytics_data,
        "english_sample": english_sample,
        "arabic_sample": arabic_or_other,
    }

    html = render_presentation(context)
    return {"html": html, "context": context}
