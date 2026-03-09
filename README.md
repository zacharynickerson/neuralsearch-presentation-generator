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

## Deploy to Railway

1. **Create a Railway project** at [railway.app](https://railway.app) and connect your GitHub repo.

2. **Set the Root Directory** in Railway project settings to `neuralsearch_generator` (so the Procfile and app are at the deploy root).

3. **Deploy** — Railway will:
   - Install Python dependencies
   - Run `playwright install --with-deps chromium` for PDF export
   - Start the app with gunicorn

4. **Generate a public URL** in Railway → Settings → Networking → Generate Domain.

5. **If "Application failed to respond"**: In Railway → your service → Settings → Networking, ensure the domain's **target port** is `8080` (or matches `$PORT`).

6. **Optional**: Set `SECRET_KEY` in Railway Variables for production.

The app is self-contained: the template `BFLStore_NeuralSearch_Slides.html` is bundled in `neuralsearch_generator/` for deployment.

## Hosting (generic)

For production:

- Set `SECRET_KEY` environment variable
- Use gunicorn: `gunicorn -w 1 -b 0.0.0.0:5000 app:app --timeout 600`
- Run behind HTTPS
