#!/bin/sh
set -e
cd /app
exec gunicorn app:app --bind 0.0.0.0:8080 --workers 1 --timeout 600 --access-logfile - --error-logfile -
