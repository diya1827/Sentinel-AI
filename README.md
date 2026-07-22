# 🛡️ Sentinel AI

> An AI-powered Application Security Reviewer that combines software engineering, security engineering, and agentic AI.

Sentinel AI ingests a codebase (or a diff), runs industry-standard static analysis and secret-scanning tools, and then uses an **agentic LLM layer** to triage, explain, and prioritize findings the way a senior application security engineer would — separating real, exploitable issues from noise and proposing concrete remediations.

---

## ✨ What it does (product vision)

| Capability | Description |
| --- | --- |
| **Static Analysis** | Runs [Semgrep](https://semgrep.dev) rulesets over the target code to find insecure patterns (injection, SSRF, weak crypto, etc.). |
| **Secret Detection** | Runs [Gitleaks](https://github.com/gitleaks/gitleaks) to detect committed credentials, API keys, and tokens. |
| **AI Triage Agent** | An LLM agent reviews raw scanner output, deduplicates, removes false positives, and assigns exploitability/priority. |
| **Explain & Remediate** | For each confirmed finding, the agent produces a plain-English explanation and a suggested fix. |
| **Review Report** | Aggregated, prioritized findings surfaced through a clean Next.js dashboard. |

> ⚠️ **Status:** This repository currently contains the **project scaffold only** — architecture, folder structure, tooling, and configuration. Feature logic is intentionally not implemented yet.

---

## 🏗️ Architecture

```
                         ┌──────────────────────────────┐
                         │      Next.js 15 Frontend      │
                         │  (App Router · TS · Tailwind) │
                         └───────────────┬──────────────┘
                                         │ REST / JSON
                                         ▼
                         ┌──────────────────────────────┐
                         │        FastAPI Backend        │
                         │                               │
                         │  api/       ← HTTP routes     │
                         │  services/  ← orchestration   │
                         │  agents/    ← LLM agent layer │
                         │  scanners/  ← Semgrep/Gitleaks│
                         │  models/    ← Pydantic schemas│
                         │  utils/     ← helpers         │
                         │  config/    ← settings        │
                         └───────┬───────────────┬───────┘
                                 │               │
                    ┌────────────▼──┐      ┌─────▼──────────┐
                    │  LLM Provider │      │ Security Tools │
                    │ (OpenAI /     │      │ Semgrep        │
                    │  Claude)      │      │ Gitleaks       │
                    └───────────────┘      └────────────────┘
```

### Design principles

- **Clean architecture / separation of concerns.** Each backend layer has one responsibility and depends only inward:
  - `api` handles transport (request/response, validation, status codes) and nothing else.
  - `services` orchestrate a use case (e.g. "run a full review") by coordinating scanners + agents.
  - `agents` own all LLM reasoning and are provider-agnostic.
  - `scanners` wrap external CLI tools behind a uniform interface.
  - `models` define the data contracts shared across layers (Pydantic).
  - `config`/`utils` are cross-cutting and depend on nothing in the app.
- **Provider abstraction.** The `agents` layer talks to an `LLMProvider` interface, so OpenAI and Claude are drop-in swappable via configuration — no call-site changes.
- **Tool abstraction.** Every scanner implements a common `Scanner` contract, so adding a tool (e.g. Trivy) means adding one class, not touching the pipeline.
- **Stateless core, containerized delivery.** The backend is a stateless API; Semgrep and Gitleaks ship inside the backend image so the pipeline is reproducible.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full breakdown.

---

## 📂 Repository structure

```
sentinel-ai/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers (transport layer)
│   │   ├── services/      # Use-case orchestration
│   │   ├── agents/        # LLM agent layer (provider-agnostic)
│   │   ├── scanners/      # Semgrep / Gitleaks wrappers
│   │   ├── models/        # Pydantic domain & API schemas
│   │   ├── utils/         # Cross-cutting helpers
│   │   ├── config/        # Settings & environment loading
│   │   └── main.py        # FastAPI app entrypoint
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── app/               # Next.js App Router pages/layouts
│   ├── components/        # Reusable UI components
│   ├── lib/               # API client & shared logic
│   ├── hooks/             # React hooks
│   ├── types/             # Shared TypeScript types
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
│
├── docs/
│   └── ARCHITECTURE.md
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 🚀 Getting started

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose (recommended path)
- Or, for local dev: **Python 3.11+**, **Node.js 20+**, and the `semgrep` / `gitleaks` CLIs on your `PATH`.
- An LLM API key (OpenAI by default).

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# then edit the files and add your API keys
```

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- API docs (Swagger) → http://localhost:8000/docs

### 3. Run locally (without Docker)

**Backend**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔐 Environment variables

Full reference lives in each `.env.example`. Highlights:

**Backend** (`backend/.env`)

| Variable | Description | Default |
| --- | --- | --- |
| `LLM_PROVIDER` | `gemini` \| `groq` \| `ollama` \| `openrouter` \| `openai` \| `anthropic` | `gemini` |
| `LLM_MODEL` | Model name | `gemini-2.0-flash` |
| `LLM_API_KEY` | API key for the chosen provider (not needed for `ollama`) | — |
| `LLM_BASE_URL` | Override endpoint; blank = provider default | — |
| `ANTHROPIC_API_KEY` | Claude key (when provider = anthropic) | — |
| `SEMGREP_TIMEOUT` | Max seconds for a Semgrep run | `300` |
| `GITLEAKS_TIMEOUT` | Max seconds for a Gitleaks run | `120` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000` |
| `ALLOWED_GIT_HOSTS` | Hosts a clone URL may resolve to | `github.com` |
| `GIT_CLONE_DEPTH` | Shallow-clone depth | `1` |
| `GIT_CLONE_TIMEOUT` | Max seconds for a clone | `120` |
| `MAX_UPLOAD_SIZE_MB` | Max ZIP upload size | `100` |
| `MAX_ARCHIVE_FILES` | Max entries in an uploaded ZIP | `20000` |
| `MAX_ARCHIVE_TOTAL_SIZE_MB` | Max uncompressed archive size | `500` |
| `MAX_TREE_FILES` | Cap on files walked into the tree | `20000` |

**Frontend** (`frontend/.env.local`)

| Variable | Description | Default |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL | `http://localhost:8000` |

---

## 🧪 Quality & tooling

- **Backend:** `ruff` (lint) · `black` (format) · `mypy` (types) · `pytest` (tests)
- **Frontend:** `eslint` · `prettier` · `typescript` strict mode
- **Security tools:** Semgrep · Gitleaks (the very tools the app orchestrates)

---

## 🔌 API

Base path: `/api/v1`. Interactive docs at `/docs`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/repositories/github` | Ingest a public GitHub repo. Body: `{ "repo_url": "https://github.com/owner/repo" }`. Returns repository metadata (tree, languages, package managers). |
| `POST` | `/repositories/upload` | Ingest a `.zip` upload (`multipart/form-data`, field `file`). Returns the same metadata. |
| `DELETE` | `/repositories/{repository_id}` | Delete a staged repository's temporary files. |
| `POST` | `/repositories/{repository_id}/scan` | Run **Semgrep** + **Gitleaks** on a staged repo. Returns a `ScanReport`: per-scanner results plus a merged `findings[]` in the unified schema and a severity tally. |
| `POST` | `/repositories/{repository_id}/analyze` | Scan **and** run the AI AppSec-engineer agent. Returns an `AgentReport`: correlated/deduplicated/prioritized issues with explanations and remediations, plus **executive** and **developer** summaries. |

**Unified finding schema.** Every scanner normalizes into one `Finding` shape — `{ scanner, severity, file, line, title, description, remediation, ruleId? }` — so the frontend consumes a single schema regardless of the underlying tool. Scanners run concurrently and each is isolated: if one tool is missing or errors, it's reported as a `failed` result inside a still-successful `200` report rather than failing the whole scan. (No AI in this layer — it's pure static analysis + secret scanning.)

### 🤖 The AI agent

The `/analyze` step is not a summarizer. The LLM is prompted to act as a **senior Application Security Engineer**: it receives the repository structure and the indexed Semgrep + Gitleaks findings and then **correlates** across tools, **deduplicates**, **prioritizes** by real-world risk, **explains why each issue matters** for *this* app, **suggests remediation**, and writes both an **executive summary** and a **developer summary** — all returned as structured `AgentReport` JSON (never free prose).

- **Free by default.** Uses **Google Gemini**'s free tier via its OpenAI-compatible endpoint. Get a key at <https://aistudio.google.com/apikey> and set `LLM_API_KEY`.
- **Swappable.** `LLM_PROVIDER` also supports `groq`, `ollama` (fully local/offline, no key), `openrouter`, `openai`, and `anthropic` — a base-URL/key/model change, no code edits.
- **Prompts are externalized** under `backend/app/agents/prompts/` (`system.md`, `analysis.md`).
- **Agentic — it investigates the code.** The agent has read-only, sandboxed tools (`read_file`, `search_code`, `list_directory`) and is prompted to *verify* findings before triaging: it opens the referenced file/line, traces user input to sinks, and checks whether a flagged "secret" is a live credential or a dummy value. This is what separates real, exploitable issues from noise — and turns the LLM from a summarizer into an investigator. The tool sandbox is confined to the repository root (traversal rejected, symlink-escape rejected, output size-capped), because the code under review is untrusted.
- **Structured & validated.** Output is parsed against the `AgentReport` Pydantic schema with a bounded retry that feeds validation errors back to the model.

**Ingestion hardening** (this is a security product, so untrusted input is treated as hostile):
- GitHub URLs are allow-listed (`https` + `ALLOWED_GIT_HOSTS` only), credentials stripped, and cloned with no shell (no command injection) and no interactive auth prompts.
- ZIP uploads are guarded against **zip-slip** (path traversal) and **zip bombs** (entry-count and uncompressed-size caps), streamed with a size limit.
- Symlinks are skipped during tree building so nothing escapes the workspace.
- Every ingestion is staged in an isolated workspace directory and removed on failure or via `DELETE`.

## 🗺️ Roadmap

- [x] Project scaffold & clean architecture skeleton
- [x] Repository ingestion (ZIP upload + GitHub clone, language/package detection)
- [x] Scanner wrappers (Semgrep, Gitleaks) + unified findings schema
- [x] LLM provider abstraction (Gemini/Groq/Ollama/OpenAI/Anthropic, swappable)
- [x] AI AppSec-engineer agent (correlate, dedup, prioritize, remediate, summaries)
- [x] Agentic tool-calling — the agent reads/searches the code to verify findings (sandboxed)
- [x] Dashboard UI (upload/GitHub, animated scan, risk score, findings, summaries, export)
- [ ] Review orchestration service (persist reviews, history)
- [ ] Dashboard UI (findings, filtering, reports)
- [ ] Auth & persistence
- [ ] CI pipeline

---

## 📄 License

MIT — see `LICENSE`.
