# Playwright image - Chromium pre-installed, faster builds
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -c "from app import app; print('App OK')"
RUN mkdir -p generated

EXPOSE 8080

# Python reads PORT from env - no shell expansion, works with Railway
CMD ["python", "run.py"]
