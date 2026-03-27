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
from .multilingual_samples import build_multilingual_payload


def neural_comparison_available(evaluation: list) -> bool:
    """
    True when the NeuralSearch search path returns at least one non-zero hit count.
    If the account cannot run NeuralSearch (e.g. pre-sales), all with_neural values are 0
    while keyword search may still return results — we should not show misleading NS columns.
    """
    return any((r.get("with_neural") or 0) > 0 for r in evaluation)


def build_demo_queries(opportunities: dict) -> Dict[str, list]:
    """Build demo query lists for each category from opportunities. Excludes numbers, URLs, IDs."""
    from .extract_top_queries import is_numeric_url_or_id
    def _valid(q):
        return q and not is_numeric_url_or_id(q)
    thin = [e["query"] for e in opportunities.get("zero_low_result", [])[:20] if e.get("nbHits", 0) <= 10 and _valid(e.get("query", ""))][:15]
    # Pool for live search: analytics zero-hit queries only (no static BFL fallbacks)
    no_result_candidates = [
        e["query"] for e in opportunities.get("no_results", [])
        if _valid(e.get("query", ""))
    ][:100]
    semantic = [e["query"] for e in opportunities.get("semantic", [])[:20] if _valid(e.get("query", ""))][:15]
    conceptual = [e["query"] for e in opportunities.get("zero_low_result", []) if _valid(e.get("query", "")) and ("for " in e.get("query", "") or " " in e.get("query", ""))][:12]

    # Fallback: use curated lists if not enough from opportunities
    if len(thin) < 5:
        thin = ["lipstick", "bath robe", "thermal leggings", "diaper bag", "waterproof shoes"] + thin
    if len(semantic) < 5:
        semantic = ["watches for women", "formal shoes for men", "wallet for men", "perfumes for women"] + semantic
    if len(conceptual) < 5:
        conceptual = ["waterproof shoes", "safety shoes for men", "gift set for women", "diaper bag"] + conceptual

    return {
        "thin_results": thin[:12],
        "no_result_candidates": no_result_candidates,
        "natural_language": semantic[:12],
        "conceptual": conceptual[:12],
    }


def build_relevancy_queries(opportunities: dict, analytics_data: dict) -> list:
    """High-volume queries with relatively few catalog hits — from customer analytics (not static BFL)."""
    from .extract_top_queries import is_numeric_url_or_id as _inv

    def _ok(q: str) -> bool:
        return bool(q and not _inv(q))

    searches = analytics_data.get("searches", []) or []
    candidates = []
    for s in searches:
        q = (s.get("search") or "").strip()
        if not _ok(q):
            continue
        c = int(s.get("count", 0) or 0)
        h = int(s.get("nbHits", 999) or 0)
        if c >= 500 and 0 < h <= 120:
            candidates.append((q, c, h))
    candidates.sort(key=lambda x: (-x[1], x[2]))
    out = []
    seen = set()
    for q, c, h in candidates:
        if q in seen:
            continue
        seen.add(q)
        out.append(q)
        if len(out) >= 12:
            break
    if len(out) < 5:
        for e in opportunities.get("semantic", [])[:40]:
            q = e.get("query", "")
            if _ok(q) and int(e.get("count", 0) or 0) >= 1000 and q not in seen:
                seen.add(q)
                out.append(q)
                if len(out) >= 12:
                    break
    return out[:12]


def run_pipeline(
    app_id: str,
    index_name: str,
    search_api_key: str,
    analytics_api_key: str,
    customer_name: str,
    region: str = "US",
    days_back: int = 90,
    include_neural_comparison: bool = True,
) -> Dict[str, Any]:
    """
    Run full pipeline and return presentation data + HTML.
    include_neural_comparison: False when the customer cannot run NeuralSearch preview — deck uses
    keyword-only result counts and analytics (no With NS columns or side-by-side comparisons).
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
    relevancy_queries = build_relevancy_queries(opportunities, analytics_data)
    all_queries = list(set(
        demo_queries["thin_results"] +
        demo_queries["no_result_candidates"] +
        demo_queries["natural_language"] +
        demo_queries["conceptual"] +
        relevancy_queries
    ))

    analytics_lookup = {s.get("search", "").lower(): {"count": s.get("count", 0), "ctr": s.get("clickThroughRate") or 0, "cr": s.get("conversionRate") or 0} for s in analytics_data.get("searches", [])}

    evaluation = evaluate_queries(
        app_id=app_id,
        search_api_key=search_api_key,
        index_name=index_name,
        queries=all_queries,
        analytics_lookup=analytics_lookup,
        compare_neural=include_neural_comparison,
    )

    eval_by_query = {r["query"]: r for r in evaluation}

    # 5. Extract top 100 NS-fit queries
    top100 = extract_top_queries(opportunities, max_queries=100)

    # 6. Build opportunity summaries for slides
    thin_results = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0}) for q in demo_queries["thin_results"] if q in eval_by_query]
    # No-results slide: only queries that return 0 hits on live keyword search (not analytics-only zeros)
    no_results = []
    for q in demo_queries["no_result_candidates"]:
        if q not in eval_by_query:
            continue
        r = eval_by_query[q]
        if r.get("without_neural", -1) == 0:
            no_results.append(r)
        if len(no_results) >= 12:
            break
    natural_language = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0}) for q in demo_queries["natural_language"] if q in eval_by_query]
    conceptual = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0}) for q in demo_queries["conceptual"] if q in eval_by_query]
    relevancy = [eval_by_query.get(q, {"query": q, "without_neural": 0, "with_neural": 0, "count": 0, "ctr": 0, "cr": 0}) for q in relevancy_queries if q in eval_by_query]

    # 7. Intro chips: NS before/after when preview works; keyword result counts otherwise
    ns_ok = include_neural_comparison and neural_comparison_available(evaluation)
    intro_chips = []
    if ns_ok:
        for r in evaluation:
            if r.get("with_neural", 0) > r.get("without_neural", 0) and not r.get("error"):
                intro_chips.append(f"{r['query']} {r['without_neural']}→{r['with_neural']}")
        intro_chips = intro_chips[:12]
    else:
        for r in sorted(evaluation, key=lambda x: (x.get("count") or 0), reverse=True):
            q = r.get("query")
            if not q:
                continue
            wo = r.get("without_neural", 0)
            intro_chips.append(f"{q} · {wo} results")
        intro_chips = intro_chips[:12]

    # 8. Get long-tail sample for slide 3
    long_tail_sample = [e.get("query", "") for e in opportunities.get("long_tail_sample", [])[:12] if e.get("query")]

    # 9. Multi-lingual slide: derived from this customer's query languages/scripts (see multilingual_samples.py)
    multilingual = build_multilingual_payload(analytics_data, _is_invalid_query)

    context = {
        "customer_name": customer_name,
        "metrics": metrics,
        "intro_chips": intro_chips,
        "long_tail_sample": long_tail_sample or ["shoes for men", "jacket for men", "watches for women"][:12],
        "thin_results": thin_results,
        "no_results": no_results,
        "natural_language": natural_language,
        "conceptual": conceptual,
        "relevancy": relevancy,
        "top100_queries": top100,
        "opportunities": opportunities,
        "analytics_data": analytics_data,
        "multilingual": multilingual,
        "neural_comparison_available": ns_ok,
        "include_neural_comparison": include_neural_comparison,
    }

    html = render_presentation(context)
    return {"html": html, "context": context}
