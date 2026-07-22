---
title: Sentinel AI Backend
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# Sentinel AI — Backend (API)

FastAPI service that ingests a repository, runs **Semgrep** + **Gitleaks**, and
runs an **agentic LLM** (Google Gemini, free tier) that investigates the code to
triage, deduplicate, prioritize, and remediate findings.

This Space runs the backend only. The dashboard UI is deployed separately
(Vercel) and points at this Space's URL.

## Required configuration (set as Space *secrets/variables*)

| Variable | Value | Kind |
| --- | --- | --- |
| `LLM_API_KEY` | your Google Gemini key | **secret** |
| `LLM_MODEL` | `gemini-flash-lite-latest` | variable |
| `SEMGREP_CONFIG` | `p/default` | variable |
| `LLM_TIMEOUT` | `120` | variable |
| `SCAN_WORKSPACE_DIR` | `/tmp/sentinel-scans` | variable |
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://sentinel-ai.vercel.app` | variable |
| `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` | variable |

## Endpoints

- `GET /health` — liveness
- `GET /docs` — Swagger UI
- `POST /api/v1/repositories/github` — ingest a public repo
- `POST /api/v1/repositories/{id}/analyze` — scan + AI review

See the [main project README](https://github.com/) for full architecture.
