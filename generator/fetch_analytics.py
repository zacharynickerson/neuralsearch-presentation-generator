"""
Fetch top 10,000 queries from Algolia Analytics API.
Requires Admin API key (or key with analytics permission).

READ-ONLY: Uses GET requests only. No data is written to Algolia.
"""

import json
import requests
import time
from datetime import datetime, timedelta
from typing import Optional

LIMIT_PER_REQUEST = 1000
TOTAL_QUERIES = 10_000


def get_analytics_base_url(region: str) -> str:
    """US: analytics.algolia.com, EU: analytics.de.algolia.com"""
    return "https://analytics.de.algolia.com" if region.upper() == "EU" else "https://analytics.algolia.com"


def fetch_top_queries(
    app_id: str,
    analytics_api_key: str,
    index_name: str,
    region: str = "US",
    limit: int = 1000,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Fetch a page of top searches from Algolia Analytics API."""
    base_url = get_analytics_base_url(region)
    params = {
        "index": index_name,
        "limit": limit,
        "offset": offset,
        "orderBy": "searchCount",
        "direction": "desc",
        "clickAnalytics": "true",
        "revenueAnalytics": "true",
    }
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date

    response = requests.get(
        f"{base_url}/2/searches",
        headers={
            "x-algolia-application-id": app_id,
            "x-algolia-api-key": analytics_api_key,
            "accept": "application/json",
        },
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_all_top_queries(
    app_id: str,
    analytics_api_key: str,
    index_name: str,
    region: str = "US",
    days_back: int = 90,
) -> dict:
    """Fetch top 10,000 queries with pagination."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    all_searches = []
    offset = 0

    while offset < TOTAL_QUERIES:
        remaining = TOTAL_QUERIES - offset
        limit = min(LIMIT_PER_REQUEST, remaining)

        data = fetch_top_queries(
            app_id=app_id,
            analytics_api_key=analytics_api_key,
            index_name=index_name,
            region=region,
            limit=limit,
            offset=offset,
            start_date=start_str,
            end_date=end_str,
        )
        searches = data.get("searches", [])

        if not searches:
            break

        all_searches.extend(searches)

        if len(searches) < limit:
            break

        offset += limit
        if offset < TOTAL_QUERIES:
            time.sleep(0.7)

    return {
        "searches": all_searches,
        "total_count": len(all_searches),
        "metadata": {
            "index": index_name,
            "start_date": start_str,
            "end_date": end_str,
            "fetched_at": datetime.now().isoformat(),
        },
    }
