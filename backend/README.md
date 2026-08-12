# Sentinel AI — Backend (API)

FastAPI service that ingests a repository, runs a **defense-in-depth scanner
suite** — each tool covering a distinct OWASP Top 10 (2021) category — and runs
an **agentic LLM** (Google Gemini, free tier) that investigates the code to
triage, deduplicate, prioritize, and remediate findings. Every finding is tagged
with its OWASP category and CWE ids, and the report includes an OWASP-coverage
summary.

| Scanner | Purpose | OWASP |
| --- | --- | --- |
| Semgrep | SAST (code vulnerabilities) | A01/A03/… |
| XSS ruleset | Cross-site scripting | A03 |
| Gitleaks | Secret detection | A07 |
| OSV-Scanner | Dependency/SCA vulnerabilities | A06 |
| Checkov | IaC misconfiguration (Terraform/Docker/K8s) | A05 |

A missing scanner binary degrades gracefully to a `FAILED` result — the rest of
the suite still runs. See [`../docs/THREAT_MODEL.md`](../docs/THREAT_MODEL.md)
for the app's own threat model.

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
- `POST /api/v1/repositories/{id}/scan` — Semgrep + XSS + Gitleaks + OSV + Checkov
- `POST /api/v1/repositories/{id}/analyze` — scan + AI review

## Configuration (env)

| Variable | Purpose | Default |
| --- | --- | --- |
| `LLM_API_KEY` | Google Gemini key | — |
| `LLM_MODEL` | Model name | `gemini-flash-lite-latest` |
| `SEMGREP_CONFIG` | Semgrep ruleset | `p/default` |
| `SEMGREP_MAX_MEMORY` | Cap Semgrep RAM (MB); 0 = unbounded | `0` |
| `SEMGREP_JOBS` | Semgrep parallelism; 0 = all cores | `0` |
| `OSV_TIMEOUT` | osv-scanner (SCA) timeout, seconds | `180` |
| `CHECKOV_TIMEOUT` | checkov (IaC) timeout, seconds | `180` |
| `SCAN_WORKSPACE_DIR` | Where repos are staged | `/tmp/sentinel-scans` |
| `CORS_ORIGINS` / `CORS_ORIGIN_REGEX` | Allowed frontend origins | localhost |
