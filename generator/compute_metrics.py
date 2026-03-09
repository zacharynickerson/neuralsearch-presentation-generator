"""
Compute search metrics for NeuralSearch slides.
"""

EXCLUDE = {"", "/", "s", "a", "b", "c", "p", "t", "l", "m", "d", "w"}


def compute_metrics(analytics_data: dict) -> dict:
    """Compute slide metrics from analytics searches."""
    searches = analytics_data.get("searches", []) or []
    filtered = [
        s
        for s in searches
        if (q := (s.get("search") or "").strip())
        and len(q) >= 2
        and q.lower() not in EXCLUDE
    ]

    total_queries = len(filtered)
    total_searches = sum(s.get("count", 0) for s in filtered)

    no_result = [s for s in filtered if s.get("nbHits", 0) == 0]
    no_result_searches = sum(s.get("count", 0) for s in no_result)
    no_results_rate = no_result_searches / total_searches if total_searches else 0

    thin_result = [s for s in filtered if s.get("nbHits", 999) <= 10]
    thin_result_searches = sum(s.get("count", 0) for s in thin_result)
    thin_results_rate = thin_result_searches / total_searches if total_searches else 0

    ctr_sum = sum((s.get("clickThroughRate") or 0) * s.get("count", 0) for s in filtered)
    cr_sum = sum((s.get("conversionRate") or 0) * s.get("count", 0) for s in filtered)
    avg_ctr = ctr_sum / total_searches if total_searches else 0
    avg_conversion = cr_sum / total_searches if total_searches else 0

    return {
        "total_queries": total_queries,
        "total_searches": total_searches,
        "no_results_queries": len(no_result),
        "no_results_searches": no_result_searches,
        "no_results_rate_pct": round(no_results_rate * 100, 2),
        "thin_results_queries": len(thin_result),
        "thin_results_searches": thin_result_searches,
        "thin_results_rate_pct": round(thin_results_rate * 100, 1),
        "avg_ctr_pct": round(avg_ctr * 100, 1),
        "avg_conversion_pct": round(avg_conversion * 100, 2),
        "total_monthly_searches": total_searches,
        "total_searches_date_range": f"{analytics_data.get('metadata', {}).get('start_date', '')} to {analytics_data.get('metadata', {}).get('end_date', '')}",
    }
