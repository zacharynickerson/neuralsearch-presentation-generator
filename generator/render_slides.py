"""
Render NeuralSearch presentation HTML from context.
Uses the BFL Store template (BFLStore_NeuralSearch_Slides_STATIC_ONLY.html) with dynamic data injection.
"""

import html
import re
from pathlib import Path
from typing import Dict, Any, List


def _chip(text: str) -> str:
    return f'<span style="padding: 5px 10px; background: #f2f4ff; border: 1px solid #bbd1ff; border-radius: 4px; color: #23263b; font-size: 13px;">{html.escape(text)}</span>'


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


def render_presentation(ctx: Dict[str, Any]) -> str:
    """Render full presentation HTML from context using BFL template."""
    customer = ctx.get("customer_name", "Customer")
    metrics = ctx.get("metrics", {})
    intro_chips = ctx.get("intro_chips", [])
    long_tail = ctx.get("long_tail_sample", [])
    thin_results = ctx.get("thin_results", [])
    no_results_rows = ctx.get("no_results", [])
    natural_language = ctx.get("natural_language", [])
    conceptual = ctx.get("conceptual", [])
    relevancy = ctx.get("relevancy", [])
    top100 = ctx.get("top100_queries", [])
    opportunities = ctx.get("opportunities", {})
    english_sample = ctx.get("english_sample", ["shoes for men", "jacket for men", "watches for women"])
    arabic_sample = ctx.get("arabic_sample", [])

    # Metrics
    thin_q = metrics.get("thin_results_queries", 0)
    thin_searches = metrics.get("thin_results_searches", 0)
    thin_rate = metrics.get("thin_results_rate_pct", 0)
    no_results_queries = metrics.get("no_results_queries", 0)
    no_results_rate = metrics.get("no_results_rate_pct", 0)
    avg_ctr = metrics.get("avg_ctr_pct", 0)
    avg_cvr = metrics.get("avg_conversion_pct", 0)
    total_monthly = metrics.get("total_monthly_searches", metrics.get("total_searches", 0))
    monthly_str = f"~{total_monthly / 1e6:.1f}M" if total_monthly >= 1e6 else f"~{int(total_monthly):,}"
    thin_searches_str = f"{thin_searches/1000:.0f}K" if thin_searches >= 1000 else f"{thin_searches:,}"

    # Build intro chips HTML
    intro_html = "".join(_chip(c) for c in intro_chips[:12])
    if not intro_html:
        intro_html = _chip("lipstick 5→101") + _chip("watches for women 44→100") + _chip("waterproof shoes 6→97") + _chip("perfumes for men 25→98")

    # Long tail chips (slide 3)
    long_tail_html = "".join(
        f'<span style="padding: 5px 10px; background: #f2f4ff; border: 1px solid #bbd1ff; border-radius: 4px; color: #23263b; font-size: 12px;">{html.escape(str(q))}</span>'
        for q in long_tail[:12]
    )
    if not long_tail_html:
        long_tail_html = '<span style="padding: 5px 10px; background: #f2f4ff; border: 1px solid #bbd1ff; border-radius: 4px; color: #23263b; font-size: 12px;">watches for women</span><span style="padding: 5px 10px; background: #f2f4ff; border: 1px solid #bbd1ff; border-radius: 4px; color: #23263b; font-size: 12px;">formal shoes for men</span><span style="padding: 5px 10px; background: #f2f4ff; border: 1px solid #bbd1ff; border-radius: 4px; color: #23263b; font-size: 12px;">waterproof shoes</span>'

    # Tables
    thin_rows = "".join(_table_row_thin(r) for r in thin_results[:12])
    if not thin_rows:
        thin_rows = '<tr><td class="search-term">lipstick</td><td>5</td><td>101</td><td>2,780</td></tr><tr><td class="search-term">bath robe</td><td>6</td><td>96</td><td>1,647</td></tr><tr><td class="search-term">thermal leggings</td><td>3</td><td>101</td><td>1,076</td></tr>'

    no_results_rows_html = "".join(_table_row_thin(r) for r in no_results_rows[:12])
    if not no_results_rows_html:
        no_results_rows_html = '<tr><td class="search-term">addidas</td><td>0</td><td>89</td><td>—</td></tr><tr><td class="search-term">cologne for men</td><td>0</td><td>95</td><td>—</td></tr><tr><td class="search-term">makeup</td><td>0</td><td>102</td><td>—</td></tr><tr><td class="search-term">mens perfume</td><td>0</td><td>88</td><td>—</td></tr><tr><td class="search-term">nike runing shoes</td><td>0</td><td>76</td><td>—</td></tr><tr><td class="search-term">womens watches</td><td>0</td><td>112</td><td>—</td></tr>'

    nl_rows = "".join(_table_row_thin(r) for r in natural_language[:12])
    if not nl_rows:
        nl_rows = '<tr><td class="search-term">watches for women</td><td>44</td><td>118</td><td>17,600</td></tr><tr><td class="search-term">formal shoes for men</td><td>20</td><td>105</td><td>8,500</td></tr>'

    conc_rows = "".join(_table_row_thin(r) for r in conceptual[:12])
    if not conc_rows:
        conc_rows = '<tr><td class="search-term">waterproof shoes</td><td>6</td><td>97</td><td>1,444</td></tr><tr><td class="search-term">safety shoes for men</td><td>5</td><td>100</td><td>1,761</td></tr>'

    rel_rows = "".join(_table_row_relevancy(r) for r in relevancy[:12])
    if not rel_rows:
        rel_rows = '<tr><td class="search-term">perfumes for men</td><td>25</td><td>98</td><td>27.4%</td><td>6.2%</td><td>12,000</td></tr>'

    # No results slide visual (0 → X)
    no_first = no_results_rows[0] if no_results_rows else {}
    no_with = no_first.get("with_neural", 42)

    # Relevancy slide highlight
    rel_first = relevancy[0] if relevancy else {}
    rel_wo = rel_first.get("without_neural", 25)
    rel_w = rel_first.get("with_neural", 98)
    rel_q = html.escape(rel_first.get("query", "perfumes for men"))
    rel_cnt = rel_first.get("count", 12000)
    rel_cvr = rel_first.get("cr", 0.062)
    rel_cvr_pct = f"{rel_cvr * 100:.1f}%" if isinstance(rel_cvr, (int, float)) else "6.2%"

    # Revenue slide: thin_searches * (avg_cvr/100) * 2.5% uplift * $80 AOV
    uplift = int(thin_searches * (avg_cvr / 100) * 0.025 * 80)
    uplift_str = f"${uplift:,}" if uplift >= 1000 else f"${uplift}"
    annual_str = f"≈ ${uplift * 12:,} annually" if uplift >= 1000 else f"≈ ${uplift * 12} annually"

    # Top 100 grid
    top100_spans = "".join(f'<span>{html.escape(str(q))}</span>' for q in top100[:100])
    if not top100_spans:
        top100_spans = '<span>shoes for men</span><span>jacket for men</span><span>watches for women</span>'

    # Multi-lingual
    eng_spans = "".join(_chip(str(q)) for q in english_sample[:6])
    ar_items = arabic_sample[:6]
    if ar_items:
        ar_spans = "".join(
            f'<span style="padding: 5px 10px; background: #f2f4ff; border: 1px solid #bbd1ff; border-radius: 4px; color: #23263b; font-size: 12px;">{html.escape(str(q))}</span>'
            for q in ar_items
        )
    else:
        ar_spans = '<span style="padding: 5px 10px; background: #f5f5fa; border: 1px solid #d6d6e7; border-radius: 4px; color: #5a5e9a; font-size: 12px; font-style: italic;">No non-English queries in top searches — NeuralSearch supports 50+ languages when you have international traffic</span>'

    # Load template — BFLStore_NeuralSearch_Slides_STATIC_ONLY.html
    app_dir = Path(__file__).parent.parent
    template_path = app_dir / "BFLStore_NeuralSearch_Slides_STATIC_ONLY.html"
    if not template_path.exists():
        template_path = app_dir.parent / "BFLStore_NeuralSearch_Slides_STATIC_ONLY.html"
    if not template_path.exists():
        template_path = app_dir / "BFLStore_NeuralSearch_Slides.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found. Tried: {app_dir / 'BFLStore_NeuralSearch_Slides_STATIC_ONLY.html'}")

    with open(template_path, encoding="utf-8") as f:
        html_content = f.read()

    # ─── Customer name ───
    html_content = html_content.replace("<title>NeuralSearch — BFL Store</title>", f"<title>NeuralSearch — {html.escape(customer)}</title>", 1)
    html_content = html_content.replace("<span class=\"algolia\">NeuralSearch · BFL Store</span>", f"<span class=\"algolia\">NeuralSearch · {html.escape(customer)}</span>", 1)
    html_content = html_content.replace("BFL Store — AI-powered search that understands intent", f"{html.escape(customer)} — AI-powered search that understands intent", 1)

    # ─── Slide 2 — Metrics (4 cards) ───
    html_content = html_content.replace(
        ';">907</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">Thin-result queries',
        f';">{thin_q}</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">Thin-result queries',
        1
    )
    html_content = html_content.replace(
        ';">674K searches affected</span>\n      </div>\n      <div style="padding: 16px 14px',
        f';">{thin_searches_str} searches affected</span>\n      </div>\n      <div style="padding: 16px 14px',
        1
    )
    html_content = html_content.replace(
        ';">3.1%</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">Searches hitting thin results</span>\n        <span style="font-size: 10px; color: var(--grey-500);">907 queries affected</span>',
        f';">{thin_rate}%</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">Searches hitting thin results</span>\n        <span style="font-size: 10px; color: var(--grey-500);">{thin_q} queries affected</span>',
        1
    )
    html_content = html_content.replace(
        ';">0.06%</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">No-results rate</span>\n        <span style="font-size: 10px; color: var(--grey-500);">13 queries affected</span>',
        f';">{no_results_rate}%</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">No-results rate</span>\n        <span style="font-size: 10px; color: var(--grey-500);">{no_results_queries} queries affected</span>',
        1
    )
    html_content = html_content.replace(
        ';">4.2%</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">Avg. conversion rate</span>',
        f';">{avg_cvr}%</span>\n        <span style="display: block; font-size: 11px; color: var(--grey-600); margin-top: 2px;">Avg. conversion rate</span>',
        1
    )
    html_content = html_content.replace("~21.7M monthly searches", f"{monthly_str} monthly searches", 2)

    # Slide 2 talk-track
    html_content = html_content.replace(
        "Your data shows 907 thin-result queries affecting 674K searches a month — that's 3.1%",
        f"Your data shows {thin_q} thin-result queries affecting {thin_searches_str} searches a month — that's {thin_rate}%",
        1
    )

    # ─── Slide 1 — Intro chips ───
    html_content = re.sub(
        r'(<div class="intro-chips" style="display: flex; flex-wrap: wrap; gap: 8px 12px; margin-top: 16px; font-size: 12pt;">)(.*?)(</div>\s*<div class="talk-track">)',
        r'\1' + intro_html + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Slide 3 — Long tail chips ───
    html_content = re.sub(
        r'(<div style="display: flex; flex-wrap: wrap; gap: 6px 10px; padding: 14px 16px; background: var\(--grey-000\); border-radius: 8px; border: 1px solid var\(--grey-200\);">)(.*?)(</div>\s*</div>\s*</div>\s*<p>)',
        r'\1' + long_tail_html + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Slide 4 — Thin results table ───
    html_content = re.sub(
        r'(<tr><td class="search-term">lipstick</td><td>5</td><td>101</td><td>2,780</td></tr>.*?<tr><td class="search-term">long socks</td><td>9</td><td>99</td><td>1,286</td></tr>)',
        thin_rows,
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Slide 5 — No results table + visual ───
    html_content = html_content.replace(
        '<span style="font-size: 32px; font-weight: 700; color: var(--xenon-600);">42</span>\n          <span style="display: block; font-size: 11px; color: var(--xenon-700);">With NS</span>',
        f'<span style="font-size: 32px; font-weight: 700; color: var(--xenon-600);">{no_with}</span>\n          <span style="display: block; font-size: 11px; color: var(--xenon-700);">With NS</span>',
        1
    )
    html_content = re.sub(
        r'(<tr><td class="search-term">addidas</td><td>0</td><td>89</td><td>—</td></tr>.*?<tr><td class="search-term">womens watches</td><td>0</td><td>112</td><td>—</td></tr>)',
        no_results_rows_html,
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Slide 6 — Natural language table ───
    html_content = re.sub(
        r'(<tr><td class="search-term">watches for women</td><td>44</td><td>118</td><td>17,600</td></tr>.*?<tr><td class="search-term">perfume for her</td><td>35</td><td>102</td><td>1,798</td></tr>)',
        nl_rows,
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Slide 7 — Conceptual table ───
    html_content = re.sub(
        r'(<tr><td class="search-term">waterproof shoes</td><td>6</td><td>97</td><td>1,444</td></tr>.*?<tr><td class="search-term">evening dress</td><td>8</td><td>98</td><td>1,240</td></tr>)',
        conc_rows,
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Slide 8 — Relevancy table + highlight ───
    html_content = html_content.replace(
        '>25</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Without NS</span>',
        f'>{rel_wo}</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Without NS</span>',
        1
    )
    html_content = html_content.replace(
        '>98</span><br><span style="font-size: 10pt; color: var(--algolia-purple);">With NS</span>',
        f'>{rel_w}</span><br><span style="font-size: 10pt; color: var(--algolia-purple);">With NS</span>',
        1
    )
    html_content = html_content.replace(
        "perfumes for men · 12K searches · 6.2% CVR",
        f"{rel_q} · {rel_cnt/1000:.0f}K searches · {rel_cvr_pct} CVR",
        1
    )
    html_content = re.sub(
        r'(<tr><td class="search-term">perfumes for men</td><td>25</td><td>98</td><td>27.4%</td><td>6.2%</td><td>12,000</td></tr>.*?<tr><td class="search-term">vans shoes for men</td><td>63</td><td>112</td><td>47.0%</td><td>8.6%</td><td>8,117</td></tr>)',
        rel_rows,
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Slide 9 — Revenue impact ───
    html_content = html_content.replace(
        '<p style="font-size: 48px; font-weight: 800; margin: 0; letter-spacing: -0.02em; line-height: 1; color: white;">$57,000</p>\n        <p style="font-size: 14px; margin: 8px 0 0; color: white;">≈ $684K annually</p>',
        f'<p style="font-size: 48px; font-weight: 800; margin: 0; letter-spacing: -0.02em; line-height: 1; color: white;">{uplift_str}</p>\n        <p style="font-size: 14px; margin: 8px 0 0; color: white;">{annual_str}</p>',
        1
    )
    html_content = html_content.replace(
        '<span class="revenue-thin-searches">674,000</span>',
        f'<span class="revenue-thin-searches">{thin_searches:,}</span>',
        1
    )
    html_content = html_content.replace(
        '<span class="revenue-baseline-cvr">4.2</span>',
        f'<span class="revenue-baseline-cvr">{avg_cvr}</span>',
        1
    )
    aov50 = int(thin_searches * (avg_cvr / 100) * 0.025 * 50)
    aov100 = int(thin_searches * (avg_cvr / 100) * 0.025 * 100)
    aov50_str = f"${aov50/1000:.0f}K" if aov50 >= 1000 else f"${aov50}"
    aov100_str = f"${aov100/1000:.0f}K" if aov100 >= 1000 else f"${aov100}"
    html_content = html_content.replace(
        '674K × 4.2% × 2.5% × AOV</p>\n          <p style="font-size: 12px; color: var(--grey-600); margin-top: 8px;">$50 AOV → $35K/mo · $100 AOV → $71K/mo</p>',
        f'{thin_searches_str} × {avg_cvr}% × 2.5% × AOV</p>\n          <p style="font-size: 12px; color: var(--grey-600); margin-top: 8px;">$50 AOV → {aov50_str}/mo · $100 AOV → {aov100_str}/mo</p>',
        1
    )
    html_content = html_content.replace(
        "674K searches a month",
        f"{thin_searches_str} searches a month",
        1
    )

    # ─── Top 100 query grid ───
    html_content = re.sub(
        r'(<div class="query-grid">)(.*?)(</div>)',
        r'\1' + top100_spans + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # ─── Multi-lingual slide ───
    html_content = re.sub(
        r'(<p style="font-size: 11pt; color: var\(--algolia-muted\); margin-bottom: 12px;">English queries \(your data\)</p>\s*<div style="display: flex; flex-wrap: wrap; gap: 8px 10px;">)(.*?)(</div>\s*</div>\s*<div style="padding: 20px 24px)',
        r'\1' + eng_spans + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )
    html_content = re.sub(
        r'(<p style="font-size: 11pt; color: var\(--algolia-muted\); margin-bottom: 12px;">Arabic queries \(same intent — your data\)</p>\s*<div style="display: flex; flex-wrap: wrap; gap: 8px 10px;">)(.*?)(</div>\s*</div>\s*</div>\s*<p>Keyword search)',
        r'\1' + ar_spans + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )
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
