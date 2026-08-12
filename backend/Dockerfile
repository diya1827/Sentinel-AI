# ─────────────────────────────────────────────────────────────────
# Sentinel AI — Backend image
# FastAPI + Semgrep/Checkov (pip) + Gitleaks & OSV-Scanner (Go binaries)
# ─────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ── System deps + Gitleaks + OSV-Scanner ─────────────────────────
# Both are distributed as static Go binaries; we pull pinned releases.
ARG GITLEAKS_VERSION=8.21.2
ARG OSV_SCANNER_VERSION=1.9.2
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
        | tar -xz -C /usr/local/bin gitleaks \
    && chmod +x /usr/local/bin/gitleaks \
    && curl -sSL -o /usr/local/bin/osv-scanner "https://github.com/google/osv-scanner/releases/download/v${OSV_SCANNER_VERSION}/osv-scanner_linux_amd64" \
    && chmod +x /usr/local/bin/osv-scanner \
    && apt-get purge -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps (cached layer) ───────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Checkov (IaC scanner) — installed isolated via pipx ──────────
# Checkov's dependency pins conflict with semgrep's, so it gets its own venv;
# pipx puts the `checkov` CLI on PATH without touching the app environment.
ARG CHECKOV_VERSION=3.2.334
RUN pip install --no-cache-dir pipx \
    && PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin \
       pipx install "checkov==${CHECKOV_VERSION}"

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
