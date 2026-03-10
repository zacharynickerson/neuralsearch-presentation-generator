#!/usr/bin/env python3
"""Start gunicorn - reads PORT from env. No shell expansion needed."""
import os

port = os.environ.get("PORT", "8080")
if not str(port).isdigit():
    port = "8080"
bind = f"0.0.0.0:{port}"
os.execvp("gunicorn", [
    "gunicorn", "app:app",
    "--bind", bind,
    "--workers", "1",
    "--timeout", "600",
    "--access-logfile", "-",
    "--error-logfile", "-",
])
