# Standard Python - more compatible with Railway than Playwright image
FROM python:3.11-slim

# Playwright install --with-deps handles Chromium deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

RUN python -c "from app import app; print('App OK')"
RUN mkdir -p generated

EXPOSE 8080

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "600", "--access-logfile", "-", "--error-logfile", "-"]
