# NeuralSearch Presentation Generator — Claude Handoff

Use this prompt to start a new Claude Code session with full project context:

---

## Handoff Prompt (copy everything below)

```
I'm continuing work on the **NeuralSearch Presentation Generator** — a Flask web app that generates custom Algolia NeuralSearch sales decks for any customer.

## Project Overview
- **Purpose**: Sales reps enter customer name + Algolia credentials; the app fetches analytics, evaluates queries with/without NeuralSearch, and produces a presentation (HTML + PDF).
- **Location**: `/Users/zachary.nickerson/Desktop/Pokemon/neuralsearch_generator/` (also a standalone repo: `github.com/zacharynickerson/neuralsearch-presentation-generator`)
- **Stack**: Flask, gunicorn, Playwright (Chromium for PDF), Algolia Analytics + Search APIs

## Key Files
- `app.py` — Flask app, form, background generation, download routes
- `generator/pipeline.py` — fetch analytics → compute metrics → analyze → evaluate → render
- `generator/extract_top_queries.py` — filters brands, single words, numbers, URLs, IDs
- `generator/analyze_opportunities.py` — zero/low-result, semantic, long-tail opportunities
- `generator/render_slides.py` — injects data into `BFLStore_NeuralSearch_Slides.html`
- `run.py` — startup script that reads PORT from env (for Railway)
- `Dockerfile` — Playwright v1.58 image, CMD runs `python run.py`

## Implemented Fixes (already done)
1. **Multilingual**: Multi-lingual slide pulls from current customer's index (Arabic/Hebrew/Cyrillic/CJK); no BFL fallback. If no non-English queries, shows generic message.
2. **Invalid queries**: Excluded numbers, URLs, IDs from all report tables (like brand names) — in `extract_top_queries.py`, `analyze_opportunities.py`, `build_demo_queries`.
3. **PDF full deck**: Added `@media print` CSS so all slides appear in PDF, one per page.
4. **Railway deployment**: Fixed PORT issues — use `python run.py` (reads PORT from os.environ). No Procfile. Playwright image v1.58.0 to match pip package. railway.toml sets builder=dockerfile.

## Current State
- App is deployed on Railway and working (form, generation, HTML download).
- PDF download works after Playwright image update to v1.58.0.
- All Algolia calls are read-only.

## Gotchas
- **Railway**: Must clear Custom Start Command in Settings → Deploy. Use Dockerfile CMD only.
- **Playwright**: Keep Docker image version in sync with `playwright` pip package (e.g. v1.58.0).
- **Template**: `BFLStore_NeuralSearch_Slides.html` is bundled in neuralsearch_generator/ for deployment.
```

---

## Quick Reference

| What | Where |
|------|-------|
| Form / routes | `app.py` |
| Pipeline logic | `generator/pipeline.py` |
| Query filtering | `generator/extract_top_queries.py` |
| Slide template | `BFLStore_NeuralSearch_Slides.html` |
| PDF generation | `app.py` `/pdf/<pid>` route, Playwright |
| Railway start | `run.py` → gunicorn |
