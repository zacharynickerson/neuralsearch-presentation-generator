# Playwright image - Chromium pre-installed, faster builds
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -c "from app import app; print('App OK')"
RUN mkdir -p generated

EXPOSE 8080

# Shell form - $PORT expands at runtime. Railway injects PORT.
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 600 --access-logfile - --error-logfile -
