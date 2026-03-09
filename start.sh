#!/bin/sh
set -e
PORT="${PORT:-8080}"
echo "Starting on port $PORT"
mkdir -p /app/generated
exec gunicorn app:app --bind "0.0.0.0:$PORT" --workers 1 --timeout 600
