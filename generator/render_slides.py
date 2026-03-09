"""
Render NeuralSearch presentation HTML from context.
Uses the BFL Store template structure with dynamic data injection.
"""

import html
from pathlib import Path
from typing import Dict, Any, List


def _chip(text: str) -> str:
    return f'<span style="padding: 6px 12px; background: rgba(84,104,255,0.08); border-radius: 6px;">{html.escape(text)}</span>'


def _table_row_thin(r: dict) -> str:
    q = html.escape(r.get("query", ""))
    wo = r.get("without_neural", 0)
    w = r.get("with_neural", 0)
    cnt = r.get("count", 0)
    cnt_str = f"{cnt:,}" if cnt else "—"
    return f'<tr><td class="search-term">{q}</td><td>{wo}</td><td>{w}</td><td>{cnt_str}</td></tr>'


def _table_row_relevancy(r: dict) -> str:
    q = html.escape(r.get("query", ""))
    wo = r.get("without_neural", 0)
    w = r.get("with_neural", 0)
    ctr = r.get("ctr", 0)
    cr = r.get("cr", 0)
    cnt = r.get("count", 0)
    ctr_pct = f"{ctr * 100:.1f}%" if isinstance(ctr, (int, float)) else "—"
    cr_pct = f"{cr * 100:.1f}%" if isinstance(cr, (int, float)) else "—"
    cnt_str = f"{cnt:,}" if cnt else "—"
    return f'<tr><td class="search-term">{q}</td><td>{wo}</td><td>{w}</td><td>{ctr_pct}</td><td>{cr_pct}</td><td>{cnt_str}</td></tr>'


def _format_list(items: List[str], max_items: int = 10) -> str:
    return ", ".join(html.escape(str(x)) for x in (items or [])[:max_items])


def render_presentation(ctx: Dict[str, Any]) -> str:
    """Render full presentation HTML from context."""
    customer = ctx.get("customer_name", "Customer")
    metrics = ctx.get("metrics", {})
    intro_chips = ctx.get("intro_chips", [])
    long_tail = ctx.get("long_tail_sample", [])
    thin_results = ctx.get("thin_results", [])
    natural_language = ctx.get("natural_language", [])
    conceptual = ctx.get("conceptual", [])
    relevancy = ctx.get("relevancy", [])
    top100 = ctx.get("top100_queries", [])
    opportunities = ctx.get("opportunities", {})
    english_sample = ctx.get("english_sample", ["shoes for men", "jacket for men", "watches for women"])
    arabic_sample = ctx.get("arabic_sample", [])

    # Build intro chips HTML
    intro_html = "".join(_chip(c) for c in intro_chips[:12])
    if not intro_html:
        intro_html = _chip("lipstick 5→101") + _chip("watches for women 44→100") + _chip("waterproof shoes 6→97")

    # Long tail chips
    long_tail_html = "".join(
        f'<span style="padding: 5px 10px; background: rgba(84,104,255,0.06); border-radius: 6px;">{html.escape(str(q))}</span>'
        for q in long_tail[:12]
    )
    if not long_tail_html:
        long_tail_html = '<span style="padding: 5px 10px; background: rgba(84,104,255,0.06); border-radius: 6px;">shoes for men</span>' * 3

    # Metrics
    thin_q = metrics.get("thin_results_queries", 0)
    thin_searches = metrics.get("thin_results_searches", 0)
    thin_rate = metrics.get("thin_results_rate_pct", 0)
    no_results = metrics.get("no_results_queries", 0)
    avg_ctr = metrics.get("avg_ctr_pct", 0)
    avg_cvr = metrics.get("avg_conversion_pct", 0)
    total_searches = metrics.get("total_searches", 0)
    total_monthly = metrics.get("total_monthly_searches", total_searches)
    monthly_str = f"~{total_monthly / 1e6:.1f}M" if total_monthly >= 1e6 else f"~{total_monthly:,}"

    # Opportunity summaries for slide 8
    thin_queries = [e["query"] for e in opportunities.get("zero_low_result", [])[:10]]
    sem_queries = [e["query"] for e in opportunities.get("semantic", [])[:10]]
    rev_queries = [e["query"] for e in opportunities.get("semantic", []) if e.get("count", 0) >= 500][:5]
    thin_list = _format_list(thin_queries or ["lipstick", "bath robe", "thermal leggings", "diaper bag"])
    sem_list = _format_list(sem_queries or ["watches for women", "formal shoes for men", "wallet for men"])
    rev_list = _format_list(rev_queries or ["perfumes for men", "wallet for men", "perfumes for women"])

    # Tables
    thin_rows = "".join(_table_row_thin(r) for r in thin_results[:12])
    if not thin_rows:
        thin_rows = '<tr><td class="search-term">lipstick</td><td>5</td><td>101</td><td>2,780</td></tr>'

    nl_rows = "".join(_table_row_thin(r) for r in natural_language[:12])
    if not nl_rows:
        nl_rows = '<tr><td class="search-term">watches for women</td><td>44</td><td>100</td><td>17,600</td></tr>'

    conc_rows = "".join(_table_row_thin(r) for r in conceptual[:12])
    if not conc_rows:
        conc_rows = '<tr><td class="search-term">waterproof shoes</td><td>6</td><td>97</td><td>1,444</td></tr>'

    rel_rows = "".join(_table_row_relevancy(r) for r in relevancy[:12])
    if not rel_rows:
        rel_rows = '<tr><td class="search-term">perfumes for men</td><td>25</td><td>98</td><td>27.4%</td><td>6.2%</td><td>12,000</td></tr>'

    # Top 100 grid
    top100_spans = "".join(f'<span>{html.escape(str(q))}</span>' for q in top100[:100])
    if not top100_spans:
        top100_spans = '<span>shoes for men</span><span>jacket for men</span><span>watches for women</span>'

    # Multi-lingual: always use customer's data — never fall back to BFL/other customer data
    eng_spans = "".join(_chip(str(q)) for q in english_sample[:6])
    ar_items = arabic_sample[:6]
    if ar_items:
        ar_spans = "".join(
            f'<span style="padding: 6px 12px; background: rgba(84,104,255,0.08); border-radius: 6px;">{html.escape(str(q))}</span>'
            for q in ar_items
        )
    else:
        # No non-English queries in customer's index — show generic message, never BFL data
        ar_spans = '<span style="padding: 6px 12px; background: rgba(84,104,255,0.06); border-radius: 6px; font-style: italic;">No non-English queries in top searches — NeuralSearch supports 50+ languages when you have international traffic</span>'

    # Relevancy slide highlight (first relevancy row)
    rel_first = relevancy[0] if relevancy else {}
    rel_wo = rel_first.get("without_neural", 25)
    rel_w = rel_first.get("with_neural", 98)
    rel_q = html.escape(rel_first.get("query", "perfumes for men"))
    rel_cnt = rel_first.get("count", 12000)
    rel_cvr = rel_first.get("cr", 0.062)
    rel_cvr_pct = f"{rel_cvr * 100:.1f}%" if isinstance(rel_cvr, (int, float)) else "6.2%"

    # Load base template — check app dir first (Railway), then project root (local dev)
    app_dir = Path(__file__).parent.parent
    template_path = app_dir / "BFLStore_NeuralSearch_Slides.html"
    if not template_path.exists():
        template_path = app_dir.parent / "BFLStore_NeuralSearch_Slides.html"
    if not template_path.exists():
        template_path = app_dir / "templates" / "presentation_base.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found. Expected at {template_path}")

    with open(template_path, encoding="utf-8") as f:
        html_content = f.read()

    # Replace customer name in specific places only
    html_content = html_content.replace("<title>NeuralSearch — BFL Store</title>", f"<title>NeuralSearch — {html.escape(customer)}</title>", 1)
    html_content = html_content.replace("<span class=\"algolia\">NeuralSearch · BFL Store</span>", f"<span class=\"algolia\">NeuralSearch · {html.escape(customer)}</span>", 1)
    html_content = html_content.replace("BFL Store — AI-powered search that understands intent", f"{html.escape(customer)} — AI-powered search that understands intent", 1)

    # Replace metrics in slide 3
    html_content = html_content.replace("907</span>", f"{thin_q}</span>", 1)
    html_content = html_content.replace("674K searches affected", f"{thin_searches/1000:.0f}K searches affected" if thin_searches >= 1000 else f"{thin_searches:,} searches affected", 1)
    html_content = html_content.replace("3.1%</span>", f"{thin_rate}%</span>", 1)
    html_content = html_content.replace("No-results: 13 queries", f"No-results: {no_results} queries", 1)
    html_content = html_content.replace("17.9%</span>", f"{avg_ctr}%</span>", 1)
    html_content = html_content.replace("4.2%</span>", f"{avg_cvr}%</span>", 1)
    html_content = html_content.replace("~21.7M monthly searches", f"{monthly_str} monthly searches", 1)

    # Replace intro chips (slide 1) - find the div with chips
    import re
    html_content = re.sub(
        r'(<div style="display: flex; flex-wrap: wrap; gap: 8px 12px; margin-top: 16px; font-size: 12pt;">)(.*?)(</div>)',
        r'\1' + intro_html + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Replace long tail chips (slide 3)
    html_content = re.sub(
        r'(<div style="font-size: 11pt; margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px 10px;">)(.*?)(</div>\s*<p style="font-size: 10pt)',
        r'\1' + long_tail_html + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Replace opportunity summaries (slide 8)
    html_content = html_content.replace("lipstick, bath robe, thermal leggings, diaper bag, waterproof shoes, helmet, snow pants, keychain, tennis skirt, christmas sweater", thin_list, 1)
    html_content = html_content.replace("watches for women, formal shoes for men, wallet for men, perfumes for women, caps for men, heels for women, belt for men, sandals for men, crocs for men, bags for men", sem_list, 1)
    html_content = html_content.replace("perfumes for men, wallet for men, perfumes for women, watches for women, formal shoes for men", rev_list, 1)

    # Replace thin results table
    html_content = re.sub(
        r'(<tr><td class="search-term">lipstick</td><td>5</td><td>101</td><td>2,780</td></tr>.*?<tr><td class="search-term">long socks</td><td>9</td><td>99</td><td>1,286</td></tr>)',
        thin_rows if thin_rows else r'\1',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Replace natural language table
    html_content = re.sub(
        r'(<tr><td class="search-term">watches for women</td><td>44</td><td>100</td><td>17,600</td></tr>.*?<tr><td class="search-term">perfume for her</td><td>35</td><td>100</td><td>1,798</td></tr>)',
        nl_rows if nl_rows else r'\1',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Replace conceptual table
    html_content = re.sub(
        r'(<tr><td class="search-term">waterproof shoes</td><td>6</td><td>97</td><td>1,444</td></tr>.*?<tr><td class="search-term">evening dress</td><td>8</td><td>98</td><td>1,240</td></tr>)',
        conc_rows if conc_rows else r'\1',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Replace relevancy table
    html_content = re.sub(
        r'(<tr><td class="search-term">perfumes for men</td><td>25</td><td>98</td><td>27.4%</td><td>6.2%</td><td>12,000</td></tr>.*?<tr><td class="search-term">vans shoes for men</td><td>63</td><td>100</td><td>47.0%</td><td>8.6%</td><td>8,117</td></tr>)',
        rel_rows if rel_rows else r'\1',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Replace relevancy highlight numbers
    html_content = html_content.replace('>25</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Without NS</span>', f'>{rel_wo}</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Without NS</span>', 1)
    html_content = html_content.replace('>98</span><br><span style="font-size: 10pt; color: var(--algolia-purple);">With NS</span>', f'>{rel_w}</span><br><span style="font-size: 10pt; color: var(--algolia-purple);">With NS</span>', 1)
    html_content = html_content.replace("perfumes for men · 12K searches · 6.2% CVR", f"{rel_q} · {rel_cnt/1000:.0f}K searches · {rel_cvr_pct} CVR", 1)

    # Replace top 100 query grid
    html_content = re.sub(
        r'(<div class="query-grid">)(.*?)(</div>)',
        r'\1' + top100_spans + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Replace multi-lingual slide (slide 6) — always use customer's data
    # English column
    html_content = re.sub(
        r'(<p style="font-size: 11pt; color: var\(--algolia-muted\); margin-bottom: 12px;">English queries \(your data\)</p>\s*<div style="display: flex; flex-wrap: wrap; gap: 8px 10px;">)(.*?)(</div>\s*</div>\s*<div style="padding: 20px 24px)',
        r'\1' + eng_spans + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )
    # Non-English column (Arabic / other scripts from customer's index)
    html_content = re.sub(
        r'(<p style="font-size: 11pt; color: var\(--algolia-muted\); margin-bottom: 12px;">Arabic queries \(same intent — your data\)</p>\s*<div style="display: flex; flex-wrap: wrap; gap: 8px 10px;">)(.*?)(</div>\s*</div>\s*</div>\s*<p>Keyword search)',
        r'\1' + ar_spans + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )
    # Update talk-track if no non-English (avoid mentioning Arabic specifically)
    if not ar_items:
        html_content = re.sub(
            r'<div class="talk-track">NeuralSearch is multi-lingual out of the box\. It understands 50\+ languages with no configuration\. Your shoppers search in both English and Arabic — جاکیت means jacket, فستان means dress, ملابس means clothes\. Keyword search can\'t connect these to your English catalog\. NeuralSearch does\. Cross-lingual matching: one index, no separate language indices, no translation layers\. It\'s a huge benefit for retailers in multilingual markets like the Gulf\.</div>',
            '<div class="talk-track">NeuralSearch is multi-lingual out of the box. It understands 50+ languages with no configuration. When you have international traffic, shoppers can search in their language and find your catalog — cross-lingual matching, one index, no separate language indices, no translation layers.</div>',
            html_content,
            count=1
        )
        html_content = html_content.replace(
            'Keyword search can\'t connect "فستان" to "dress" or "جاکیت" to "jacket" — different scripts, no exact match. NeuralSearch understands intent across languages. One index. No translation layers. Works out of the box.',
            'Keyword search can\'t connect different scripts — no exact match. NeuralSearch understands intent across 50+ languages. One index. No translation layers. Works out of the box when you have multilingual traffic.'
        )

    return html_content
