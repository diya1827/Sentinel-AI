# Sentinel AI — Backend (API)

FastAPI service that ingests a repository, runs **Semgrep** + **Gitleaks**, and
runs an **agentic LLM** (Google Gemini, free tier) that investigates the code to
triage, deduplicate, prioritize, and remediate findings.

Deployed as a Docker web service (see [`../render.yaml`](../render.yaml) and
[`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md)). The dashboard UI is deployed
separately (Vercel) and points at this service's URL.

## Run locally

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Requires `semgrep`, `gitleaks`, and `git` on `PATH`. Copy `.env.example` to
`.env` and set `LLM_API_KEY`.

## Endpoints

- `GET /health` — liveness
- `GET /docs` — Swagger UI
- `POST /api/v1/repositories/github` — ingest a public repo
- `POST /api/v1/repositories/upload` — ingest a `.zip`
- `POST /api/v1/repositories/{id}/scan` — Semgrep + Gitleaks
- `POST /api/v1/repositories/{id}/analyze` — scan + AI review

## Configuration (env)

| Variable | Purpose | Default |
| --- | --- | --- |
| `LLM_API_KEY` | Google Gemini key | — |
| `LLM_MODEL` | Model name | `gemini-flash-lite-latest` |
| `SEMGREP_CONFIG` | Semgrep ruleset | `p/default` |
| `SEMGREP_MAX_MEMORY` | Cap Semgrep RAM (MB); 0 = unbounded | `0` |
| `SEMGREP_JOBS` | Semgrep parallelism; 0 = all cores | `0` |
| `SCAN_WORKSPACE_DIR` | Where repos are staged | `/tmp/sentinel-scans` |
| `CORS_ORIGINS` / `CORS_ORIGIN_REGEX` | Allowed frontend origins | localhost |
