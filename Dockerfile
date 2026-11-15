# One image serves both the API and the built UI (same origin, so no CORS to configure).

# --- Stage 1: build the frontend ---
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: runtime ---
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

ENV STATIC_DIR=/app/static
ENV DATABASE_PATH=/app/data/ecommerce.db
ENV LOG_LEVEL=INFO

# Install only the runtime dependencies declared in pyproject.toml (the app runs from source).
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY docker/deps.py ./deps.py
RUN python deps.py backend/pyproject.toml > /tmp/requirements.txt && pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt deps.py
COPY backend/app ./backend/app
COPY --from=frontend /frontend/dist ./static

# The sample database is deterministic, so it is generated at build time (opened read-only at runtime).
RUN mkdir -p data && cd backend && python -m app.db.seed --force

RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health')"

# Render injects $PORT. --proxy-headers lets the rate limiter see real client IPs behind its proxy.
CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
