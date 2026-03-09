#!/usr/bin/env python3
"""
NeuralSearch Presentation Generator — Flask app.
Sales reps enter customer details and Algolia credentials, then generate a custom presentation.
"""

import os
import uuid
import threading
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, send_file, jsonify

# Add app directory to path for generator imports (works for local + Railway)
import sys
APP_DIR = Path(__file__).parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from generator.pipeline import run_pipeline
except ImportError:
    # Fallback when run from project root (e.g. neuralsearch_generator as package)
    PROJECT_ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    from neuralsearch_generator.generator.pipeline import run_pipeline

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# Store generated presentations and job status in memory (or use Redis/DB in production)
presentations = {}
jobs = {}  # job_id -> {"status": "pending"|"done"|"error", "pid": str, "error": str}
OUTPUT_DIR = Path(__file__).parent / "generated"
OUTPUT_DIR.mkdir(exist_ok=True)


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NeuralSearch Presentation Generator</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 40px; background: #f5f5f7; }
    .container { max-width: 640px; margin: 0 auto; background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
    h1 { color: #1a1a2e; margin-bottom: 8px; font-size: 24pt; }
    .subtitle { color: #5c5c7a; margin-bottom: 32px; font-size: 14pt; }
    label { display: block; font-weight: 600; color: #1a1a2e; margin-bottom: 6px; font-size: 12pt; }
    input, select { width: 100%; padding: 12px 16px; border: 1px solid #ddd; border-radius: 8px; font-size: 14pt; margin-bottom: 20px; }
    input:focus { outline: none; border-color: #5468FF; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    button { background: #5468FF; color: white; border: none; padding: 14px 28px; font-size: 15pt; font-weight: 600; border-radius: 8px; cursor: pointer; width: 100%; }
    button:hover { background: #4358e0; }
    button:disabled { background: #ccc; cursor: not-allowed; }
    .error { background: #fee; color: #c00; padding: 12px; border-radius: 8px; margin-bottom: 20px; }
    .note { font-size: 11pt; color: #5c5c7a; margin-top: -12px; margin-bottom: 20px; }
    .required::after { content: " *"; color: #c00; }
  </style>
</head>
<body>
  <div class="container">
    <h1>NeuralSearch Presentation Generator</h1>
    <p class="subtitle">Enter customer details and Algolia credentials to generate a custom NeuralSearch sales deck.</p>
    <p style="font-size: 12pt; color: #5468FF; margin-bottom: 24px; padding: 12px 16px; background: rgba(84,104,255,0.08); border-radius: 8px;"><strong>Read-only:</strong> All Algolia API calls are read-only. No index, analytics, or customer data is modified.</p>

    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}

    <form method="POST" action="/generate">
      <label class="required">Customer name</label>
      <input type="text" name="customer_name" placeholder="e.g. BFL Store" required value="{{ request.form.get('customer_name', '') }}">

      <label class="required">Algolia App ID</label>
      <input type="text" name="app_id" placeholder="e.g. 2MMV84221Y" required value="{{ request.form.get('app_id', '') }}">

      <label class="required">Index name</label>
      <input type="text" name="index_name" placeholder="e.g. p_bflstore_product_rfc" required value="{{ request.form.get('index_name', '') }}">

      <label class="required">Search API key</label>
      <input type="password" name="search_api_key" placeholder="Search-only key for query evaluation" required>
      <p class="note">Used to run searches with/without NeuralSearch. Not the Admin key.</p>

      <label class="required">Analytics API key</label>
      <input type="password" name="analytics_api_key" placeholder="Admin key with analytics permission" required>
      <p class="note">Used to fetch top 10K queries from Algolia Analytics. Requires Admin or Analytics API key.</p>

      <label>Region</label>
      <select name="region">
        <option value="US">US</option>
        <option value="EU">EU</option>
      </select>

      <label>Days of analytics data</label>
      <input type="number" name="days_back" value="90" min="30" max="365">

      <button type="submit" id="submitBtn">Generate Presentation</button>
    </form>
  </div>
  <script>
    document.querySelector('form').addEventListener('submit', function() {
      document.getElementById('submitBtn').disabled = true;
      document.getElementById('submitBtn').textContent = 'Generating... (this may take 2–5 minutes)';
    });
  </script>
</body>
</html>
"""


@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def index():
    return render_template_string(INDEX_HTML, error=request.args.get("error"))


def _run_generation(job_id: str, **kwargs):
    """Background task: run pipeline and store result."""
    try:
        result = run_pipeline(**kwargs)
        pid = str(uuid.uuid4())[:8]
        out_path = OUTPUT_DIR / f"presentation_{pid}.html"
        out_path.write_text(result["html"], encoding="utf-8")
        presentations[pid] = {"path": str(out_path), "customer": kwargs["customer_name"]}
        jobs[job_id] = {"status": "done", "pid": pid}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}


PROCESSING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Generating… — NeuralSearch</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 40px; background: #f5f5f7; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
    .box { max-width: 480px; background: white; padding: 48px; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; }
    .spinner { width: 48px; height: 48px; border: 4px solid #eee; border-top-color: #5468FF; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 24px; }
    @keyframes spin { to { transform: rotate(360deg); } }
    h2 { color: #1a1a2e; margin-bottom: 8px; }
    p { color: #5c5c7a; }
    .error { background: #fee; color: #c00; padding: 16px; border-radius: 8px; margin-top: 20px; }
    a { color: #5468FF; }
  </style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <h2>Generating presentation…</h2>
    <p>Fetching analytics, evaluating queries, and building your deck. This usually takes 2–5 minutes.</p>
    <p style="font-size: 12pt; margin-top: 16px;">Please keep this tab open. You'll be redirected when it's ready.</p>
    <div id="error" class="error" style="display:none;"></div>
  </div>
  <script>
    const jobId = "{{ job_id }}";
    function poll() {
      fetch("/status/" + jobId)
        .then(r => r.json())
        .then(data => {
          if (data.status === "done") {
            window.location.href = "/view/" + data.pid;
          } else if (data.status === "error") {
            document.querySelector(".spinner").style.display = "none";
            document.getElementById("error").style.display = "block";
            document.getElementById("error").textContent = data.error || "An error occurred.";
            document.getElementById("error").innerHTML += '<br><a href="/">← Try again</a>';
          } else {
            setTimeout(poll, 3000);
          }
        })
        .catch(() => setTimeout(poll, 3000));
    }
    poll();
  </script>
</body>
</html>
"""


@app.route("/generate", methods=["POST"])
def generate():
    customer_name = request.form.get("customer_name", "").strip()
    app_id = request.form.get("app_id", "").strip()
    index_name = request.form.get("index_name", "").strip()
    search_api_key = request.form.get("search_api_key", "").strip()
    analytics_api_key = request.form.get("analytics_api_key", "").strip()
    region = request.form.get("region", "US")
    days_back = int(request.form.get("days_back", 90))

    if not all([customer_name, app_id, index_name, search_api_key, analytics_api_key]):
        return redirect(url_for("index", error="All required fields must be filled."))

    job_id = str(uuid.uuid4())[:12]
    jobs[job_id] = {"status": "pending"}

    thread = threading.Thread(
        target=_run_generation,
        kwargs={
            "job_id": job_id,
            "app_id": app_id,
            "index_name": index_name,
            "search_api_key": search_api_key,
            "analytics_api_key": analytics_api_key,
            "customer_name": customer_name,
            "region": region,
            "days_back": days_back,
        },
    )
    thread.daemon = True
    thread.start()

    return render_template_string(PROCESSING_HTML, job_id=job_id)


@app.route("/status/<job_id>")
def status(job_id):
    if job_id not in jobs:
        return jsonify({"status": "error", "error": "Job not found"}), 404
    return jsonify(jobs[job_id])


@app.route("/view/<pid>")
def view(pid):
    if pid not in presentations:
        return redirect(url_for("index", error="Presentation not found or expired."))
    return render_template_string(VIEW_HTML, pid=pid, customer=presentations[pid].get("customer", ""))

@app.route("/embed/<pid>")
def embed(pid):
    """Serve raw HTML for iframe embedding."""
    if pid not in presentations:
        return "Not found", 404
    path = Path(presentations[pid]["path"])
    if not path.exists():
        return "File not found", 404
    return send_file(path, mimetype="text/html")


@app.route("/download/<pid>")
def download(pid):
    if pid not in presentations:
        return redirect(url_for("index", error="Presentation not found or expired."))
    path = Path(presentations[pid]["path"])
    if not path.exists():
        return redirect(url_for("index", error="Presentation file not found."))
    customer = presentations[pid].get("customer", "NeuralSearch")
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in customer)
    return send_file(path, as_attachment=True, download_name=f"NeuralSearch_{safe_name}.html")


@app.route("/pdf/<pid>")
def pdf(pid):
    """Generate PDF via Playwright (optional)."""
    if pid not in presentations:
        return jsonify({"error": "Presentation not found"}), 404
    path = Path(presentations[pid]["path"])
    if not path.exists():
        return jsonify({"error": "File not found"}), 404

    try:
        from playwright.sync_api import sync_playwright
        pdf_path = OUTPUT_DIR / f"presentation_{pid}.pdf"
        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()
            page.goto(f"file://{path.absolute()}")
            page.wait_for_timeout(2000)  # Let slides render
            page.pdf(path=str(pdf_path), format="A4", print_background=True)
            browser.close()
        return send_file(pdf_path, as_attachment=True, download_name=f"NeuralSearch_{pid}.pdf")
    except ImportError:
        return jsonify({"error": "Playwright not installed. Run: playwright install chromium"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


VIEW_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>View Presentation — NeuralSearch</title>
  <style>
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; }
    .toolbar { position: fixed; top: 0; left: 0; right: 0; padding: 12px 24px; background: rgba(0,0,0,0.8); display: flex; gap: 12px; align-items: center; z-index: 100; }
    .toolbar a, .toolbar button { padding: 8px 16px; background: #5468FF; color: white; border: none; border-radius: 6px; text-decoration: none; font-size: 13pt; cursor: pointer; }
    .toolbar a:hover, .toolbar button:hover { background: #4358e0; }
    .toolbar .spacer { flex: 1; }
    iframe { width: 100%; height: calc(100vh - 52px); margin-top: 52px; border: none; }
  </style>
</head>
<body>
  <div class="toolbar">
    <a href="/">← New presentation</a>
    <a href="/download/{{ pid }}">Download HTML</a>
    <a href="/pdf/{{ pid }}">Download PDF</a>
    <span class="spacer"></span>
    <span style="color: #888;">{{ customer }}</span>
  </div>
  <iframe src="/embed/{{ pid }}" title="NeuralSearch Presentation"></iframe>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # 5001 avoids macOS AirPlay on 5000
    app.run(host="0.0.0.0", port=port, debug=True)
