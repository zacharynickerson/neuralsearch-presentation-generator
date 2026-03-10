#!/usr/bin/env python3
"""Start gunicorn with PORT from environment (avoids shell expansion issues)."""
import os
import sys

port = os.environ.get("PORT", "8080")
bind = f"0.0.0.0:{port}"
print(f"Starting gunicorn on {bind}", flush=True)
sys.stdout.flush()
sys.stderr.flush()

os.execvp("gunicorn", [
    "gunicorn", "app:app",
    "--bind", bind,
    "--workers", "1",
    "--timeout", "600",
    "--access-logfile", "-",
    "--error-logfile", "-",
])
