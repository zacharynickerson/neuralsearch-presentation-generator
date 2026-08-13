# NeuralSearch Presentation Generator

A web app that lets sales reps generate custom NeuralSearch sales decks for any Algolia customer. Enter credentials, and the system fetches analytics, runs NeuralSearch evaluation, and produces a presentation in the same template as the BFL Store deck.

## Read-only: No customer data is modified

**All Algolia API calls are read-only.** The generator never writes to the customer's index, analytics, or any Algolia resource.

| Operation | API | Method | Effect |
|-----------|-----|--------|--------|
| Fetch top queries | Analytics API `/2/searches` | **GET** | Reads search analytics only |
| Evaluate queries | Search API `/1/indexes/{index}/query` | POST (query) | **Read-only search** — returns results, does not modify index |

The only writes are **local files** on the server: generated HTML and PDF in the `generated/` folder. Customer data stays unchanged.

## Requirements

- **Admin API key** — One key covers everything: query evaluation (search) and fetching top 10K queries (analytics).

## Setup

```bash
cd neuralsearch_generator
pip3 install -r requirements.txt
python3 -m playwright install chromium   # For PDF export (optional)
```

Or with a virtual environment:

```bash
cd neuralsearch_generator
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
python3 app.py
```

Open http://localhost:5001 (or set `PORT` env var to use a different port)

## AE workflow

Typical field motion:

1. **Qualify** the account (qualifier / unit cost / volume checks).
2. **Open the generator** from the qual dashboard deep-link when available (`customer_name`, `app_id`, `index_name`, `region`, `days_back`, `neural_access`, optional `aov`).
3. Paste the **Admin API key** (security review pending for a safer key-access path — do not expand key sharing until that lands).
4. Optionally enter **Average order value ($)** when the customer is not sending purchase/revenue events into Algolia analytics.
5. **Generate** the deck (2–5 minutes).
6. On the view page, use **Customize slides** to omit weak or zeroed slides (e.g. Revenue impact when uplift is `$0`).
7. **Download HTML** (portable — logos inlined) or **Download PDF** (16:9) and share with the customer.

## Usage

1. Enter **Customer name** (e.g. "BFL Store")
2. Enter **Algolia App ID**, **Index name**
3. Enter **Admin API key** (covers search + analytics)
4. Select **Region** (US or EU — use EU if your app is in the EU region)
5. Optionally enter **Average order value ($)** for revenue math (defaults to $80 example AOV; uplift uses a **2.9%** relative CVR lift)
6. Click **Generate Presentation**

Generation takes 2–5 minutes (fetches 10K queries, evaluates opportunity queries with/without NeuralSearch).

7. **View** the presentation in-browser
8. **Customize slides** to omit slides before export
9. **Download HTML** to share or present (single self-contained file)
10. **Download PDF** (requires Playwright)

## Template

The presentation uses `BFLStore_NeuralSearch_Slides_STATIC_ONLY.html` as the base template — the same 20-slide BFL deck structure with 5 opportunities (Thin results, No results, Natural language, Conceptual, Relevancy), revenue impact, and case studies. Customer-specific data (metrics, tables, top queries) is injected dynamically. Example tables prefer live NeuralSearch wins and avoid cross-vertical placeholder queries.

## Export notes

- Presentations are indexed in `generated/index.json` so downloads still work after a process restart (while HTML files remain on disk).
- HTML export inlines logo assets as data URIs so the file works offline (email, Drive upload).
- PDF export uses Playwright against the generated HTML at **11in × 6.1875in** (16:9), matching the deck print CSS.

## Google Drive / editable copy (spike)

Not built into the app yet. After HTML/PDF export is reliable, recommended approach:

| Approach | Pros | Cons |
|----------|------|------|
| Manual upload of HTML/PDF to a shared Drive folder | Zero OAuth in the app; works today | Not automatic |
| Service account → Shared Drive folder upload | Server-side, no user OAuth dance | Needs Workspace Shared Drive + secret management on Railway |
| User OAuth (Drive API) | Uploads to the AE's My Drive | OAuth consent + token storage complexity |
| Convert to Google Slides | Truly editable | HTML→Slides conversion is lossy; often needs a Docs/Slides intermediary |

**Recommendation:** keep using portable HTML/PDF uploads for now. Revisit Drive API upload only after export is stable in production and security signs off on storing Google credentials alongside Admin API key handling.

## Follow-ups (out of scope for current ship)

- Safer API-key access (avoid AE personification in admin) — pending security review
- Offline evaluator (Hex / Solutions) keyword-vs-neural evidence ingested into the deck
- Native Google Slides / PPTX generation

## Deploy to Railway

1. Create a project at [railway.app](https://railway.app) and connect the repo.
2. **Settings → Deploy**: Clear any Custom Start Command (leave blank).
3. **Settings → Networking**: Generate Domain.
4. Deploy.

## Hosting (generic)

For production:

- Set `SECRET_KEY` environment variable
- Use gunicorn: `gunicorn -w 1 -b 0.0.0.0:5000 app:app --timeout 600`
- Run behind HTTPS
