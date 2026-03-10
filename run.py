#!/usr/bin/env python3
"""Start gunicorn with PORT from environment (for local use)."""
import os

port = os.environ.get("PORT", "8080")
bind = f"0.0.0.0:{port}"
os.execvp("gunicorn", [
    "gunicorn", "app:app",
    "--bind", bind,
    "--workers", "1",
    "--timeout", "600",
])
