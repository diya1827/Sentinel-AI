# ─────────────────────────────────────────────────────────────────
# Sentinel AI — Backend image
# FastAPI + Semgrep (pip) + Gitleaks (Go binary)
# ─────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ── System deps + Gitleaks ───────────────────────────────────────
# Gitleaks is distributed as a static Go binary; we pull a pinned release.
ARG GITLEAKS_VERSION=8.21.2
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
        | tar -xz -C /usr/local/bin gitleaks \
    && chmod +x /usr/local/bin/gitleaks \
    && apt-get purge -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps (cached layer) ───────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Application code ─────────────────────────────────────────────
COPY . .

# ── Non-root runtime user ────────────────────────────────────────
RUN useradd --create-home --uid 1001 appuser \
    && mkdir -p /tmp/sentinel-scans \
    && chown -R appuser:appuser /app /tmp/sentinel-scans
USER appuser

EXPOSE 8000

# Healthcheck hits the API's /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,httpx,sys; p=os.getenv('PORT','8000'); sys.exit(0 if httpx.get(f'http://localhost:{p}/health').status_code==200 else 1)"

# Shell form so ${PORT} (injected by hosts like Hugging Face Spaces / Cloud Run)
# is honored, defaulting to 8000 for local runs.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
