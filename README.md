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

- **Search API key** — For running queries with/without NeuralSearch (evaluation). Use a search-only key, not the Admin key.
- **Analytics API key** — For fetching top 10K queries. Requires Admin key or a key with `analytics` permission.

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

## Usage

1. Enter **Customer name** (e.g. "BFL Store")
2. Enter **Algolia App ID**, **Index name**
3. Enter **Search API key** (for query evaluation)
4. Enter **Analytics API key** (for top queries)
5. Select **Region** (US or EU)
6. Click **Generate Presentation**

Generation takes 2–5 minutes (fetches 10K queries, evaluates ~40 queries with/without NeuralSearch).

7. **View** the presentation in-browser
8. **Download HTML** to share or present
9. **Download PDF** (requires Playwright)

## Template

The presentation uses `BFLStore_NeuralSearch_Slides.html` as the base template (bundled in `neuralsearch_generator/` for deployment, or from the project root for local dev). Customer-specific data (metrics, tables, top queries) is injected dynamically.

## Deploy to Render (recommended)

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo `neuralsearch-presentation-generator`
3. Render auto-detects the Dockerfile — click **Create Web Service**
4. Build takes ~10 min (Chromium install). Free tier works.
5. Get your URL from the dashboard.

## Deploy to Railway

1. Create a project at [railway.app](https://railway.app) and connect the repo.
2. **Critical**: Service → Settings → Deploy → **clear Custom Start Command** (leave blank).
3. Settings → Networking → Generate Domain. Set target port **8080**.
4. Redeploy.

## Hosting (generic)

For production:

- Set `SECRET_KEY` environment variable
- Use gunicorn: `gunicorn -w 1 -b 0.0.0.0:5000 app:app --timeout 600`
- Run behind HTTPS
