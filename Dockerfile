# --- Stage 1: build the web app ---------------------------------------------
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python API that also serves the built web app -----------------
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=web /web/build ./app/static

ENV IRONROD_DB=/data/ironrod.db \
    PYTHONUNBUFFERED=1

# The server runs as the non-root "ironrod" user. The entrypoint starts as
# root just to fix ownership of /data, then drops to that user.
RUN useradd --uid 1000 --create-home ironrod && mkdir -p /data && chown ironrod /data
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
VOLUME /data
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
