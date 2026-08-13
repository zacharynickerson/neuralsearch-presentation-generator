"""
Render NeuralSearch presentation HTML from context.
Uses the BFL Store template (BFLStore_NeuralSearch_Slides_STATIC_ONLY.html) with dynamic data injection.
"""

import base64
import html
import mimetypes
import re
from pathlib import Path
from typing import Dict, Any, List

from .multilingual_samples import build_multilingual_payload

# Measured relative CVR lift from A/B tests (meeting benchmark)
MEASURED_RELATIVE_UPLIFT = 0.029
DEFAULT_AOV = 80


def _chip(text: str) -> str:
    return f"<span>{html.escape(text)}</span>"


def _empty_state(title: str, message: str) -> str:
    return (
        f'<div class="empty-state">'
        f'<div class="empty-state-label">{html.escape(title)}</div>'
        f"<p>{message}</p>"
        f"</div>"
    )


def _empty_table_row(show_neural: bool, title: str, message: str) -> str:
    cols = 4 if show_neural else 3
    return (
        f'<tr><td colspan="{cols}" style="padding: 0; border: none; background: transparent;">'
        f"{_empty_state(title, message)}"
        f"</td></tr>"
    )


def _inject_default_omit(html_content: str, omit: list) -> str:
    """Bake suggested omits into generated HTML so weak slides stay out of customer exports."""
    if not omit:
        return html_content
    omit_json = "[" + ", ".join(str(n) for n in omit) + "]"
    snippet = (
        f"<!--NS_OMIT_INJECT-->"
        f"<script>window.__OMITTED_SLIDES__={omit_json};</script>\n"
    )
    if "<!--NS_OMIT_INJECT-->" in html_content:
        return re.sub(
            r"<!--NS_OMIT_INJECT--><script>window\.__OMITTED_SLIDES__=.*?</script>\s*",
            snippet,
            html_content,
            count=1,
            flags=re.DOTALL,
        )
    if "</head>" in html_content:
        return html_content.replace("</head>", snippet + "</head>", 1)
    return snippet + html_content


def _embed_logo_assets(html_content: str, logos_dir: Path) -> str:
    """Rewrite logos/* img src to data URIs so HTML/PDF work offline and without file:// asset paths."""

    def replacer(match: re.Match) -> str:
        rel = match.group(1)
        name = Path(rel).name
        path = logos_dir / name
        if not path.exists():
            return match.group(0)
        mime, _ = mimetypes.guess_type(str(path))
        if path.suffix.lower() == ".svg":
            mime = "image/svg+xml"
        if not mime:
            mime = "application/octet-stream"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'src="data:{mime};base64,{b64}"'

    return re.sub(r'src="(logos/[^"]+)"', replacer, html_content)


def _table_row_thin(r: dict, *, show_neural: bool) -> str:
    q = html.escape(r.get("query", ""))
    wo = r.get("without_neural", 0)
    w = r.get("with_neural", 0)
    cnt = r.get("count", 0)
    cnt_str = f"{cnt:,}" if cnt else "—"
    if show_neural:
        w_cell = f'<td class="delta-up">{w}</td>' if (w or 0) > (wo or 0) else f"<td>{w}</td>"
        return f'<tr><td class="search-term">{q}</td><td>{wo}</td>{w_cell}<td>{cnt_str}</td></tr>'
    return f'<tr><td class="search-term">{q}</td><td>{wo}</td><td>{cnt_str}</td></tr>'


def _ml_chip(q: str) -> str:
    return f"<span>{html.escape(str(q))}</span>"


def _build_multilingual_grid(ml: Dict[str, Any]) -> str:
    """Inner HTML for slide 17 (grid + optional second column)."""
    col1_qs = ml.get("col1_queries") or []
    col2_qs = ml.get("col2_queries") or []
    if not col1_qs and not col2_qs:
        return _empty_state(
            "No multilingual signal",
            "This index’s recent top queries look primarily monolingual. "
            "We can still cover NeuralSearch’s multilingual capability in conversation without a weak sample slide.",
        )
    col1 = "".join(_ml_chip(q) for q in col1_qs)
    t1 = html.escape(ml.get("col1_title") or "Queries (your data)")
    if ml.get("mode") == "single" or not ml.get("col2_title"):
        return f"""    <div style="display: grid; grid-template-columns: 1fr; gap: 16px; margin: 20px 0;">
      <div style="padding: 20px 24px; background: linear-gradient(180deg,#fff,#f7f8fd); border-radius: 14px; border: 1px solid var(--grey-200); box-shadow: 0 2px 10px rgba(21,24,43,0.05);">
        <p style="font-size: 12px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: var(--algolia-muted); margin-bottom: 12px;">{t1}</p>
        <div class="long-tail-chips" style="display: flex; flex-wrap: wrap; gap: 8px 10px;">{col1}</div>
      </div>
    </div>"""
    col2 = "".join(_ml_chip(q) for q in col2_qs)
    t2 = html.escape(ml.get("col2_title") or "")
    return f"""    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0;">
      <div style="padding: 20px 24px; background: linear-gradient(180deg,#fff,#f7f8fd); border-radius: 14px; border: 1px solid var(--grey-200); box-shadow: 0 2px 10px rgba(21,24,43,0.05);">
        <p style="font-size: 12px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: var(--algolia-muted); margin-bottom: 12px;">{t1}</p>
        <div class="long-tail-chips" style="display: flex; flex-wrap: wrap; gap: 8px 10px;">{col1}</div>
      </div>
      <div style="padding: 20px 24px; background: linear-gradient(180deg,#fff,#f7f8fd); border-radius: 14px; border: 1px solid var(--grey-200); box-shadow: 0 2px 10px rgba(21,24,43,0.05);">
        <p style="font-size: 12px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: var(--algolia-muted); margin-bottom: 12px;">{t2}</p>
        <div class="long-tail-chips" style="display: flex; flex-wrap: wrap; gap: 8px 10px;">{col2}</div>
      </div>
    </div>"""


def _table_row_relevancy(r: dict, *, show_neural: bool) -> str:
    q = html.escape(r.get("query", ""))
    wo = r.get("without_neural", 0)
    w = r.get("with_neural", 0)
    ctr = r.get("ctr", 0)
    cr = r.get("cr", 0)
    cnt = r.get("count", 0)
    ctr_pct = f"{ctr * 100:.1f}%" if isinstance(ctr, (int, float)) else "—"
    cr_pct = f"{cr * 100:.1f}%" if isinstance(cr, (int, float)) else "—"
    cnt_str = f"{cnt:,}" if cnt else "—"
    if show_neural:
        w_cell = f'<td class="delta-up">{w}</td>' if (w or 0) > (wo or 0) else f"<td>{w}</td>"
        return f'<tr><td class="search-term">{q}</td><td>{wo}</td>{w_cell}<td>{ctr_pct}</td><td>{cr_pct}</td><td>{cnt_str}</td></tr>'
    return f'<tr><td class="search-term">{q}</td><td>{wo}</td><td>{ctr_pct}</td><td>{cr_pct}</td><td>{cnt_str}</td></tr>'


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
    multilingual = ctx.get("multilingual") or {}
    show_neural = ctx.get("neural_comparison_available", True)

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

    # Intro chips — real evidence only; fall back to clean metric chips (never apology copy)
    intro_html = "".join(_chip(c) for c in intro_chips[:12])
    if not intro_html:
        intro_html = "".join(
            _chip(c)
            for c in [
                f"{thin_searches_str} thin searches/mo",
                f"{thin_rate}% thin-result rate",
                f"{avg_cvr}% baseline CVR",
                f"{monthly_str} monthly searches",
            ]
        )

    # Long tail chips (slide 3)
    long_tail_html = "".join(_chip(str(q)) for q in long_tail[:12])
    if not long_tail_html:
        long_tail_html = _empty_state(
            "Long-tail sample unavailable",
            "We’ll still frame the long-tail opportunity conceptually — unique phrases and intent queries that keyword matching often misses.",
        )

    empty_title = "Not a primary signal here"
    empty_msg = (
        "We didn’t find strong live examples for this opportunity on this index. "
        "Skip this slide in the customer conversation and lean on opportunities with proof."
    )

    # Tables
    thin_rows = "".join(_table_row_thin(r, show_neural=show_neural) for r in thin_results[:12])
    if not thin_rows:
        thin_rows = _empty_table_row(show_neural, empty_title, empty_msg)

    no_results_rows_html = "".join(_table_row_thin(r, show_neural=show_neural) for r in no_results_rows[:12])
    if not no_results_rows_html:
        no_results_rows_html = _empty_table_row(
            show_neural,
            "No live zero-result queries",
            "Live keyword search didn’t return current zero-hit examples. "
            "Historical analytics may still show no-result traffic — treat this as a secondary talking point.",
        )

    nl_rows = "".join(_table_row_thin(r, show_neural=show_neural) for r in natural_language[:12])
    if not nl_rows:
        nl_rows = _empty_table_row(show_neural, empty_title, empty_msg)

    conc_rows = "".join(_table_row_thin(r, show_neural=show_neural) for r in conceptual[:12])
    if not conc_rows:
        conc_rows = _empty_table_row(show_neural, empty_title, empty_msg)

    rel_source = relevancy[:12] if relevancy else thin_results[:12]
    rel_rows = "".join(_table_row_relevancy(r, show_neural=show_neural) for r in rel_source)
    if not rel_rows:
        rel_cols = 6 if show_neural else 5
        rel_rows = (
            f'<tr><td colspan="{rel_cols}" style="padding: 0; border: none; background: transparent;">'
            f"{_empty_state(empty_title, empty_msg)}"
            f"</td></tr>"
        )

    # No results slide visual (0 → X)
    no_first = no_results_rows[0] if no_results_rows else {}
    no_with = no_first.get("with_neural", 0) if no_first else 0
    no_wo = no_first.get("without_neural", 0) if no_first else 0

    # Relevancy slide highlight — same source as table rows
    rel_first = rel_source[0] if rel_source else {}
    rel_wo = rel_first.get("without_neural", 0) if rel_first else 0
    rel_w = rel_first.get("with_neural", 0) if rel_first else 0
    rel_q = html.escape(rel_first.get("query", "—"))
    rel_cnt = rel_first.get("count", 0) or 0
    rel_cvr = rel_first.get("cr", 0) or 0
    rel_cvr_pct = f"{rel_cvr * 100:.1f}%" if isinstance(rel_cvr, (int, float)) and rel_cvr else "—"

    # Revenue: Uplift = CVR delta × affected searches × AOV (CVR delta = baseline × measured relative uplift)
    baseline_cvr_dec = (avg_cvr / 100) if avg_cvr else 0
    measured_relative_uplift = MEASURED_RELATIVE_UPLIFT
    lift_pct_str = f"{measured_relative_uplift * 100:.1f}".rstrip("0").rstrip(".")
    cvr_delta_dec = baseline_cvr_dec * measured_relative_uplift
    new_cvr_dec = baseline_cvr_dec + cvr_delta_dec
    try:
        example_aov = float(ctx.get("aov") if ctx.get("aov") is not None else DEFAULT_AOV)
    except (TypeError, ValueError):
        example_aov = float(DEFAULT_AOV)
    if example_aov <= 0:
        example_aov = float(DEFAULT_AOV)
    example_aov_int = int(round(example_aov))
    aov_source = ctx.get("aov_source") or "default"
    aov_label = (
        f"manual ${example_aov_int} AOV"
        if aov_source == "manual"
        else f"example: ${example_aov_int} AOV"
    )
    rev_without = thin_searches * baseline_cvr_dec * example_aov
    rev_with = thin_searches * new_cvr_dec * example_aov
    uplift = int(thin_searches * cvr_delta_dec * example_aov)
    uplift_str = f"${uplift:,}" if uplift >= 1000 else f"${uplift}"
    annual_str = f"≈ ${uplift * 12:,} annually" if uplift >= 1000 else f"≈ ${uplift * 12} annually"
    rev_without_str = f"${int(rev_without):,}" if rev_without >= 1000 else f"${int(rev_without)}"
    rev_with_str = f"${int(rev_with):,}" if rev_with >= 1000 else f"${int(rev_with)}"
    revenue_weak = uplift <= 0 or thin_searches <= 0 or avg_cvr <= 0

    # Top 100 grid
    top100_spans = "".join(f"<span>{html.escape(str(q))}</span>" for q in top100[:100])
    if not top100_spans:
        top100_spans = (
            '<div class="empty-state" style="grid-column: 1 / -1;">'
            '<div class="empty-state-label">Query list unavailable</div>'
            "<p>We’ll pull a high-fit query list in follow-up — this slide isn’t needed for the core story.</p>"
            "</div>"
        )

    if not multilingual:
        from .extract_top_queries import is_numeric_url_or_id as _inv
        multilingual = build_multilingual_payload(ctx.get("analytics_data") or {}, _inv)

    multilingual_grid_html = _build_multilingual_grid(multilingual)

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

    # Embed logos as data URIs (portable HTML download + reliable PDF via file://)
    logos_dir = app_dir / "logos"
    html_content = _embed_logo_assets(html_content, logos_dir)

    # Suggest omitting weak/empty slides so customer decks stay polished
    suggest_omit = []
    if not thin_results:
        suggest_omit.append(4)
    if not no_results_rows:
        suggest_omit.append(5)
    if not natural_language:
        suggest_omit.append(6)
    if not conceptual:
        suggest_omit.append(7)
    if not rel_source:
        suggest_omit.append(8)
    if revenue_weak:
        suggest_omit.append(9)
    ml_empty = not (multilingual.get("col1_queries") or multilingual.get("col2_queries"))
    if ml_empty:
        suggest_omit.append(17)
        multilingual = {
            **multilingual,
            "benefit": "NeuralSearch supports 50+ languages on one index — useful when international traffic grows.",
            "footnote": "No strong second-language sample appeared in this index’s recent top queries.",
            "talk_track": "Keep this brief: multilingual is available out of the box. If this account is monolingual today, don’t over-index on the sample — focus on opportunities with live proof.",
        }
    if not top100:
        suggest_omit.append(19)
    suggest_omit = sorted(set(suggest_omit))

    # Meta for view UI
    html_content = html_content.replace(
        "<head>",
        (
            f'<head>\n  <meta name="ns-uplift" content="{uplift}">\n'
            f'  <meta name="ns-aov" content="{example_aov_int}">\n'
            f'  <meta name="ns-suggest-omit" content="{",".join(str(n) for n in suggest_omit)}">'
        ),
        1,
    )

    # ─── Customer name ───
    html_content = html_content.replace("<title>NeuralSearch — BFL Store</title>", f"<title>NeuralSearch — {html.escape(customer)}</title>", 1)
    html_content = html_content.replace("<span class=\"algolia\">NeuralSearch · BFL Store</span>", f"<span class=\"algolia\">NeuralSearch · {html.escape(customer)}</span>", 1)
    html_content = html_content.replace("BFL Store — AI-powered search that understands intent", f"{html.escape(customer)} — AI-powered search that understands intent", 1)
    html_content = html_content.replace("<!--CUSTOMER_NAME_EXEC_SUMMARY-->", html.escape(customer), 1)
    html_content = html_content.replace("<!--MULTILINGUAL_BENEFIT-->", html.escape(multilingual.get("benefit", "")), 1)
    html_content = html_content.replace("<!--MULTILINGUAL_GRID-->", multilingual_grid_html, 1)
    html_content = html_content.replace("<!--MULTILINGUAL_FOOTNOTE-->", html.escape(multilingual.get("footnote", "")), 1)
    html_content = html_content.replace("<!--MULTILINGUAL_TALK-->", html.escape(multilingual.get("talk_track", "")), 1)

    pp_delta = cvr_delta_dec * 100
    new_cvr_pct = new_cvr_dec * 100
    if revenue_weak:
        revenue_formula_lines = (
            "Projected uplift needs eligible thin-result searches, a baseline CVR, and an AOV. "
            "Enter AOV on generate when purchase events aren’t in Algolia analytics."
        )
    else:
        revenue_formula_lines = (
            f"Revenue without NeuralSearch = baseline CVR × affected searches × AOV = "
            f"{avg_cvr}% × {thin_searches:,} × ${example_aov_int} ≈ <strong>{rev_without_str}/mo</strong><br>"
            f"Revenue with NeuralSearch = new CVR × affected searches × AOV = "
            f"{new_cvr_pct:.2f}% × {thin_searches:,} × ${example_aov_int} ≈ <strong>{rev_with_str}/mo</strong><br>"
            f"Uplift = ΔCVR × affected searches × AOV — ΔCVR = baseline × {lift_pct_str}% (relative) = +{pp_delta:.3f} pp"
        )
    html_content = html_content.replace("<!--REVENUE_FORMULA_LINES-->", revenue_formula_lines, 1)
    html_content = html_content.replace(
        "<!--REVENUE_UPLIFT_EQUATION-->",
        f"ΔCVR × {thin_searches_str} searches × AOV  &nbsp;·&nbsp;  ΔCVR = {avg_cvr}% × {lift_pct_str}%",
        1,
    )
    html_content = html_content.replace(
        "Projected monthly uplift (example: $80 AOV)",
        f"Projected monthly uplift ({aov_label})",
        1,
    )

    if not show_neural:
        html_content = html_content.replace(
            "<tr><th>Search</th><th>Without NS</th><th>With NS</th><th>Searches</th></tr>",
            "<tr><th>Search</th><th>Results</th><th>Searches</th></tr>",
        )
        html_content = html_content.replace(
            "<tr><th>Search</th><th>Without NS</th><th>With NS</th><th>CTR</th><th>CVR</th><th>Searches</th></tr>",
            "<tr><th>Search</th><th>Results</th><th>CTR</th><th>CVR</th><th>Searches</th></tr>",
            1,
        )
        _slide4_graphic_ns = """    <div class="slide-graphic" style="margin-bottom: 20px;">
      <div style="display: flex; align-items: flex-end; gap: 20px;">
        <div style="text-align: center;">
          <span style="font-size: 10px; color: var(--grey-500); display: block; margin-bottom: 4px;">Without NS</span>
          <div class="bar-chart" style="height: 50px;">
            <div class="bar" style="height: 10px; width: 26px;"></div>
            <div class="bar" style="height: 15px; width: 26px;"></div>
            <div class="bar" style="height: 8px; width: 26px;"></div>
            <div class="bar" style="height: 20px; width: 26px;"></div>
          </div>
          <span class="bar-label" style="font-size: 9px;">5, 6, 3, 8</span>
        </div>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--xenon-600)" stroke-width="2" style="margin-bottom: 20px;"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        <div style="text-align: center;">
          <span style="font-size: 10px; color: var(--xenon-600); font-weight: 600; display: block; margin-bottom: 4px;">With NS</span>
          <div class="bar-chart" style="height: 50px;">
            <div class="bar" style="height: 50px; width: 26px; opacity: 1;"></div>
            <div class="bar" style="height: 48px; width: 26px; opacity: 1;"></div>
            <div class="bar" style="height: 50px; width: 26px; opacity: 1;"></div>
            <div class="bar" style="height: 35px; width: 26px; opacity: 1;"></div>
          </div>
          <span class="bar-label" style="font-size: 9px;">101, 96, 101, 69</span>
        </div>
      </div>
    </div>"""
        _slide4_graphic_kw = """    <div class="slide-graphic" style="margin-bottom: 20px;">
      <div style="padding: 14px 18px; background: var(--grey-000); border-radius: 8px; border: 1px solid var(--grey-200); max-width: 560px;">
        <p style="font-size: 12px; color: var(--grey-600); margin: 0;">Counts below are from your current keyword search. NeuralSearch preview is not available on this account — we still surface opportunities from your analytics.</p>
      </div>
    </div>"""
        html_content = html_content.replace(_slide4_graphic_ns, _slide4_graphic_kw, 1)
        _slide5_graphic_ns = """    <div class="slide-graphic" style="margin-bottom: 20px;">
      <div style="display: flex; align-items: center; gap: 20px; flex-wrap: wrap;">
        <div style="padding: 16px 24px; background: var(--grey-000); border-radius: 8px; border: 1px solid var(--grey-200); text-align: center;">
          <span style="font-size: 32px; font-weight: 700; color: var(--algolia-muted);">0</span>
          <span style="display: block; font-size: 11px; color: var(--grey-500);">Without NS</span>
        </div>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--xenon-600)" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        <div style="padding: 16px 24px; background: var(--xenon-100); border-radius: 8px; border: 2px solid var(--xenon-600); text-align: center;">
          <span style="font-size: 32px; font-weight: 700; color: var(--xenon-600);">42</span>
          <span style="display: block; font-size: 11px; color: var(--xenon-700);">With NS</span>
        </div>
      </div>
    </div>"""
        _slide5_graphic_kw = f"""    <div class="slide-graphic" style="margin-bottom: 20px;">
      <div style="display: flex; align-items: center; gap: 20px; flex-wrap: wrap;">
        <div style="padding: 16px 24px; background: var(--grey-000); border-radius: 8px; border: 1px solid var(--grey-200); text-align: center;">
          <span style="font-size: 32px; font-weight: 700; color: var(--algolia-muted);">{no_wo}</span>
          <span style="display: block; font-size: 11px; color: var(--grey-500);">Keyword search — results</span>
        </div>
      </div>
    </div>"""
        html_content = html_content.replace(_slide5_graphic_ns, _slide5_graphic_kw, 1)
        _slide8_graphic_ns = """      <div style="display: flex; gap: 16px; align-items: center; flex-wrap: wrap;">
        <div style="text-align: center; padding: 16px 24px; background: var(--grey-000); border-radius: 8px; border: 1px solid var(--grey-200);"><span style="font-size: 24pt; font-weight: 700; color: var(--algolia-muted);">25</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Without NS</span></div>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--xenon-600)" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        <div style="text-align: center; padding: 16px 24px; background: var(--xenon-100); border-radius: 8px; border: 2px solid var(--xenon-600);"><span style="font-size: 24pt; font-weight: 700; color: var(--algolia-purple);">98</span><br><span style="font-size: 10pt; color: var(--algolia-purple);">With NS</span></div>
        <span style="font-size: 12px; color: var(--grey-500);">perfumes for men · 12K searches · 6.2% CVR</span>
      </div>"""
        _slide8_graphic_kw = f"""      <div style="display: flex; gap: 16px; align-items: center; flex-wrap: wrap;">
        <div style="text-align: center; padding: 16px 24px; background: var(--grey-000); border-radius: 8px; border: 1px solid var(--grey-200);"><span style="font-size: 24pt; font-weight: 700; color: var(--algolia-muted);">{rel_wo}</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Keyword search — results</span></div>
        <span style="font-size: 12px; color: var(--grey-500);">perfumes for men · 12K searches · 6.2% CVR</span>
      </div>"""
        html_content = html_content.replace(_slide8_graphic_ns, _slide8_graphic_kw, 1)

        html_content = html_content.replace(
            '<div class="talk-track">We ran your search data through our NeuralSearch engine. Here\'s what we found — and where we see clear opportunities. Let me show you the five opportunities we identified.</div>',
            '<div class="talk-track">We analyzed your search data. Here\'s what we found — and where we see clear opportunities. Let me show you the five opportunity areas we identified.</div>',
            1,
        )
        html_content = html_content.replace(
            "<h2>We ran your top 10,000 queries through NeuralSearch. Here's what we found.</h2>",
            "<h2>Here's what we found in your top 10,000 queries.</h2>",
            1,
        )
        html_content = html_content.replace(
            '<span style="font-size: 10px; color: var(--grey-500);">NS improves conversion</span>',
            '<span style="font-size: 10px; color: var(--grey-500);">Baseline from your analytics</span>',
            1,
        )
        html_content = html_content.replace(
            "We ran 10,000 of your top queries through NeuralSearch. Your data shows ",
            "Your data shows ",
            1,
        )
        html_content = html_content.replace(
            '<p style="font-size: 10px; color: var(--grey-500);">NeuralSearch improves both segments — the top 10K and the long tail beyond.</p>',
            '<p style="font-size: 10px; color: var(--grey-500);">Opportunity exists in both segments — the top 10K we analyzed and the long tail beyond.</p>',
            1,
        )
        html_content = html_content.replace(
            "We can show you the before/after in a live demo. These are high-intent searches",
            "We can walk through a live demo when NeuralSearch is available on your account. These are high-intent searches",
            1,
        )

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
        r'(<div class="intro-chips"[^>]*>)(.*?)(</div>\s*<div class="talk-track">)',
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
    if show_neural:
        html_content = html_content.replace(
            '<span style="font-size: 32px; font-weight: 700; color: var(--xenon-600);">42</span>\n          <span style="display: block; font-size: 11px; color: var(--xenon-700);">With NS</span>',
            f'<span style="font-size: 32px; font-weight: 700; color: var(--xenon-600);">{no_with}</span>\n          <span style="display: block; font-size: 11px; color: var(--xenon-700);">With NS</span>',
            1,
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
    if show_neural:
        html_content = html_content.replace(
            '>25</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Without NS</span>',
            f'>{rel_wo}</span><br><span style="font-size: 10pt; color: var(--algolia-muted);">Without NS</span>',
            1,
        )
        html_content = html_content.replace(
            '>98</span><br><span style="font-size: 10pt; color: var(--algolia-purple);">With NS</span>',
            f'>{rel_w}</span><br><span style="font-size: 10pt; color: var(--algolia-purple);">With NS</span>',
            1,
        )
    rel_cnt_k = f"{rel_cnt/1000:.1f}K" if rel_cnt >= 1000 else (f"{rel_cnt:,}" if rel_cnt else "—")
    html_content = html_content.replace(
        "perfumes for men · 12K searches · 6.2% CVR",
        f"{rel_q} · {rel_cnt_k} searches · {rel_cvr_pct} CVR",
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
    if revenue_weak:
        html_content = html_content.replace(
            'class="revenue-hero" id="revenueHero"',
            'class="revenue-hero revenue-weak" id="revenueHero"',
            1,
        )
        html_content = html_content.replace(
            'id="revenueUpliftValue" style="font-family: Outfit, DM Sans, sans-serif; font-size: 52px; font-weight: 800; margin: 0; letter-spacing: -0.03em; line-height: 1; color: white;">$57,000</p>\n        <p id="revenueAnnualValue" style="font-size: 15px; margin: 10px 0 0; color: rgba(255,255,255,0.92);">≈ $684K annually</p>',
            (
                'id="revenueUpliftValue" style="font-family: Outfit, DM Sans, sans-serif; font-size: 34px; font-weight: 800; margin: 0; letter-spacing: -0.03em; line-height: 1.15; color: white;">'
                "Need AOV + conversion inputs</p>\n"
                '        <p id="revenueAnnualValue" style="font-size: 14px; margin: 10px 0 0; color: rgba(255,255,255,0.92);">'
                "Re-run with a manual AOV (or ensure conversion analytics are present) to size the opportunity.</p>"
            ),
            1,
        )
    else:
        html_content = html_content.replace(
            'id="revenueUpliftValue" style="font-family: Outfit, DM Sans, sans-serif; font-size: 52px; font-weight: 800; margin: 0; letter-spacing: -0.03em; line-height: 1; color: white;">$57,000</p>\n        <p id="revenueAnnualValue" style="font-size: 15px; margin: 10px 0 0; color: rgba(255,255,255,0.92);">≈ $684K annually</p>',
            f'id="revenueUpliftValue" style="font-family: Outfit, DM Sans, sans-serif; font-size: 52px; font-weight: 800; margin: 0; letter-spacing: -0.03em; line-height: 1; color: white;">{uplift_str}</p>\n        <p id="revenueAnnualValue" style="font-size: 15px; margin: 10px 0 0; color: rgba(255,255,255,0.92);">{annual_str}</p>',
            1,
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
    aov50 = int(thin_searches * (avg_cvr / 100) * measured_relative_uplift * 50)
    aov100 = int(thin_searches * (avg_cvr / 100) * measured_relative_uplift * 100)
    aov50_str = f"${aov50/1000:.0f}K" if aov50 >= 1000 else f"${aov50}"
    aov100_str = f"${aov100/1000:.0f}K" if aov100 >= 1000 else f"${aov100}"
    scenario_line = f"$50 AOV → {aov50_str}/mo · $100 AOV → {aov100_str}/mo"
    if aov_source == "manual":
        scenario_line = f"Using ${example_aov_int} AOV · {scenario_line}"
    html_content = html_content.replace(
        '<p style="font-size: 12px; color: var(--grey-600); margin-top: 8px;">$50 AOV → $35K/mo · $100 AOV → $71K/mo</p>',
        f'<p style="font-size: 12px; color: var(--grey-600); margin-top: 8px;">{scenario_line}</p>',
        1
    )
    html_content = html_content.replace(
        "674K searches a month",
        f"{thin_searches_str} searches a month",
        1
    )
    html_content = html_content.replace(
        "A 2.9% CVR uplift from measured A/B tests",
        f"A {lift_pct_str}% CVR uplift from measured A/B tests",
        1,
    )

    # Soften BFL-specific talk tracks that leak into other customer decks
    html_content = html_content.replace(
        "You have the inventory — lipstick, bath robes, thermal leggings, tweed — but keyword search only surfaces a handful.",
        "You have the inventory — but keyword search only surfaces a handful of products for high-intent queries.",
        1,
    )
    html_content = html_content.replace(
        'Shoppers don\'t search like your catalog. They type "watches for women" or "formal shoes for men" — natural phrases.',
        "Shoppers don’t search like your catalog. They type natural phrases and modifiers — not attribute-perfect keywords.",
        1,
    )
    html_content = html_content.replace(
        '17,600 searches for "watches for women" alone. This is the natural language benefit — shoppers search the way they talk, and NeuralSearch gets it.',
        "This is the natural language benefit — shoppers search the way they talk, and NeuralSearch gets it.",
        1,
    )
    html_content = html_content.replace(
        'Keyword search can\'t connect concepts. "Waterproof shoes" won\'t match "Rain Cover" or "Snow Boot" — those words aren\'t in the query. NeuralSearch understands semantics and surfaces the right products: rain covers, snow boots, Safety Jogger shoes, diaper bags.',
        "Keyword search can’t connect concepts when the catalog wording doesn’t match the query. NeuralSearch understands semantics and surfaces the right products even when the words differ.",
        1,
    )
    html_content = html_content.replace(
        'High volume + few results means the right products are buried. "Perfumes for men" — 12,000 searches, only 25 results shown. "Wallet for men" — 8,745 searches, 42 results. NeuralSearch surfaces more <strong>relevant</strong> options.',
        "High volume + few results means the right products are buried. NeuralSearch surfaces more <strong>relevant</strong> options on those high-intent queries.",
        1,
    )
    html_content = html_content.replace(
        "Example use cases: thin results (lipstick, bath robe), natural language (watches for women), conceptual (waterproof shoes), relevancy (perfumes for men), typos (addidas→adidas), synonyms (cologne→perfume)",
        "Example use cases: thin results, natural language, conceptual queries, relevancy gaps, typos, and synonyms — without maintaining brittle keyword maps.",
        1,
    )

    # ─── Top 100 query grid ───
    html_content = re.sub(
        r'(<div class="query-grid">)(.*?)(</div>)',
        r'\1' + top100_spans + r'\3',
        html_content,
        count=1,
        flags=re.DOTALL
    )

    # Bake suggested omits into the file so shared HTML/PDF skip weak slides by default
    html_content = _inject_default_omit(html_content, suggest_omit)

    return html_content
