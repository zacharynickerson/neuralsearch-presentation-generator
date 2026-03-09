# Playwright image has Chromium pre-installed — no 15-min download during build
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verify app loads (fails build if import error)
RUN python -c "from app import app; print('App OK')"

RUN mkdir -p generated

EXPOSE 8080
ENV PORT=8080
CMD ["python", "run.py"]
