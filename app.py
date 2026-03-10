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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f5f5fa;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
      -webkit-font-smoothing: antialiased;
    }
    .card {
      width: 100%;
      max-width: 560px;
      background: #ffffff;
      border: 1px solid #d6d6e7;
      border-radius: 8px;
      box-shadow: 0 1px 4px rgba(35,38,59,0.06);
      overflow: hidden;
    }
    .card-header {
      padding: 24px 32px 20px;
      border-bottom: 1px solid #d6d6e7;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .card-header svg { height: 22px; width: auto; flex-shrink: 0; }
    .card-header-text h1 { font-size: 16px; font-weight: 700; color: #23263b; margin-bottom: 2px; }
    .card-header-text p { font-size: 13px; color: #5a5e9a; }
    .card-body { padding: 24px 32px 28px; }
    .notice {
      font-size: 12px;
      color: #003dff;
      margin-bottom: 20px;
      padding: 10px 14px;
      background: #f2f4ff;
      border: 1px solid #bbd1ff;
      border-radius: 6px;
    }
    label {
      display: block;
      font-weight: 600;
      font-size: 12px;
      color: #23263b;
      margin-bottom: 5px;
      letter-spacing: 0.01em;
    }
    input, select {
      width: 100%;
      padding: 9px 12px;
      border: 1px solid #d6d6e7;
      border-radius: 6px;
      font-size: 14px;
      font-family: inherit;
      color: #23263b;
      background: #ffffff;
      margin-bottom: 16px;
      transition: border-color 0.15s;
    }
    input:focus, select:focus { outline: none; border-color: #003dff; box-shadow: 0 0 0 3px #f2f4ff; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
    button {
      background: #003dff;
      color: #ffffff;
      border: none;
      padding: 11px 20px;
      font-size: 14px;
      font-weight: 600;
      font-family: inherit;
      border-radius: 6px;
      cursor: pointer;
      width: 100%;
      margin-top: 4px;
      transition: background 0.15s;
    }
    button:hover { background: #022eb9; }
    button:disabled { background: #9698c3; cursor: not-allowed; }
    .error {
      background: #ffe6e9;
      color: #d4142a;
      border: 1px solid #fc95a1;
      padding: 10px 14px;
      border-radius: 6px;
      font-size: 13px;
      margin-bottom: 16px;
    }
    .note { font-size: 11px; color: #777aaf; margin-top: -10px; margin-bottom: 16px; }
    .required::after { content: " *"; color: #d4142a; }
  </style>
</head>
<body>
  <div class="card">
    <div class="card-header">
      <svg viewBox="-2 -2 108 108" xmlns="http://www.w3.org/2000/svg" aria-label="Algolia">
        <path d="M16.8-1.001h88.4c8.7 0 15.8 7.065 15.8 15.8v88.405c0 8.7-7.065 15.795-15.8 15.795H16.8c-8.7 0-15.8-7.06-15.8-15.795V14.759c0-8.695 7.06-15.76 15.8-15.76z" fill="#003dff"/>
        <path d="M73.505 25.788v-4.115a5.209 5.209 0 0 0-5.21-5.205H56.15a5.209 5.209 0 0 0-5.21 5.205v4.225c0 .47.435.8.91.69a37.966 37.966 0 0 1 10.57-1.49c3.465 0 6.895.47 10.21 1.38.44.11.875-.215.875-.69M40.22 31.173l-2.075-2.075a5.206 5.206 0 0 0-7.365 0l-2.48 2.475a5.185 5.185 0 0 0 0 7.355l2.04 2.04c.33.325.805.25 1.095-.075a39.876 39.876 0 0 1 3.975-4.66 37.68 37.68 0 0 1 4.7-4c.364-.22.4-.73.11-1.06m22.164 13.065v17.8c0 .51.55.875 1.02.62l15.825-8.19c.36-.18.47-.62.29-.98-3.28-5.755-9.37-9.685-16.405-9.94-.365 0-.73.29-.73.69m0 42.88c-13.195 0-23.915-10.705-23.915-23.88 0-13.175 10.72-23.875 23.915-23.875 13.2 0 23.916 10.7 23.916 23.875s-10.68 23.88-23.916 23.88m0-57.8c-18.74 0-33.94 15.18-33.94 33.92 0 18.745 15.2 33.89 33.94 33.89s33.94-15.18 33.94-33.925c0-18.745-15.165-33.885-33.94-33.885z" fill="#FFF"/>
      </svg>
      <div class="card-header-text">
        <h1>NeuralSearch Presentation Generator</h1>
        <p>Enter customer details and Algolia credentials to generate a custom sales deck.</p>
      </div>
    </div>
    <div class="card-body">
      <div class="notice"><strong>Read-only:</strong> All Algolia API calls are read-only. No index, analytics, or customer data is modified.</div>

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

        <label class="required">Admin API key</label>
        <input type="password" name="admin_api_key" placeholder="Admin key (covers search + analytics)" required>
        <p class="note">Used for both query evaluation and fetching top 10K queries. One key covers everything.</p>

        <div class="row">
          <div>
            <label>Region</label>
            <select name="region">
              <option value="US">US</option>
              <option value="EU">EU</option>
            </select>
            <p class="note">Analytics endpoint — use EU if your app is in the EU region.</p>
          </div>
          <div>
            <label>Days of analytics data</label>
            <input type="number" name="days_back" value="90" min="30" max="365">
          </div>
        </div>

        <button type="submit" id="submitBtn">Generate Presentation</button>
      </form>
    </div>
  </div>
  <script>
    document.querySelector('form').addEventListener('submit', function() {
      document.getElementById('submitBtn').disabled = true;
      document.getElementById('submitBtn').textContent = 'Generating… (this may take 2–5 minutes)';
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #f5f5fa;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 40px 20px;
      -webkit-font-smoothing: antialiased;
    }
    .box {
      max-width: 440px;
      width: 100%;
      background: #ffffff;
      border: 1px solid #d6d6e7;
      border-radius: 8px;
      box-shadow: 0 1px 4px rgba(35,38,59,0.06);
      padding: 40px 36px;
      text-align: center;
    }
    .spinner {
      width: 40px; height: 40px;
      border: 3px solid #d6d6e7;
      border-top-color: #003dff;
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
      margin: 0 auto 24px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    h2 { font-size: 17px; font-weight: 700; color: #23263b; margin-bottom: 8px; }
    p { font-size: 14px; color: #5a5e9a; line-height: 1.6; margin-bottom: 8px; }
    .error {
      background: #ffe6e9; color: #d4142a;
      border: 1px solid #fc95a1;
      padding: 12px 16px; border-radius: 6px;
      font-size: 13px; margin-top: 20px; text-align: left;
    }
    a { color: #003dff; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <h2>Generating presentation…</h2>
    <p>Fetching analytics, evaluating queries, and building your deck.</p>
    <p>This usually takes 2–5 minutes. Please keep this tab open.</p>
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
            document.getElementById("error").innerHTML += '<br><br><a href="/">← Try again</a>';
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
    admin_api_key = request.form.get("admin_api_key", "").strip()
    region = request.form.get("region", "US")
    days_back = int(request.form.get("days_back", 90))

    if not all([customer_name, app_id, index_name, admin_api_key]):
        return redirect(url_for("index", error="All required fields must be filled."))

    job_id = str(uuid.uuid4())[:12]
    jobs[job_id] = {"status": "pending"}

    thread = threading.Thread(
        target=_run_generation,
        kwargs={
            "job_id": job_id,
            "app_id": app_id,
            "index_name": index_name,
            "search_api_key": admin_api_key,
            "analytics_api_key": admin_api_key,
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #23263b; -webkit-font-smoothing: antialiased; }
    .toolbar {
      position: fixed; top: 0; left: 0; right: 0;
      height: 48px;
      padding: 0 20px;
      background: #23263b;
      border-bottom: 1px solid #36395a;
      display: flex;
      gap: 8px;
      align-items: center;
      z-index: 100;
    }
    .toolbar a {
      padding: 6px 14px;
      background: #36395a;
      color: #d6d6e7;
      border: 1px solid #484c7a;
      border-radius: 5px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
      transition: background 0.15s;
    }
    .toolbar a:hover { background: #484c7a; color: #ffffff; }
    .toolbar a.primary {
      background: #003dff;
      color: #ffffff;
      border-color: #003dff;
    }
    .toolbar a.primary:hover { background: #022eb9; border-color: #022eb9; }
    .toolbar .spacer { flex: 1; }
    .toolbar .customer-label { font-size: 12px; color: #777aaf; font-weight: 500; }
    iframe { width: 100%; height: calc(100vh - 48px); margin-top: 48px; border: none; }
  </style>
</head>
<body>
  <div class="toolbar">
    <a href="/">← New</a>
    <a href="/download/{{ pid }}">Download HTML</a>
    <a href="/pdf/{{ pid }}" class="primary">Download PDF</a>
    <span class="spacer"></span>
    <span class="customer-label">{{ customer }}</span>
  </div>
  <iframe src="/embed/{{ pid }}" title="NeuralSearch Presentation"></iframe>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # 5001 avoids macOS AirPlay on 5000
    app.run(host="0.0.0.0", port=port, debug=True)
