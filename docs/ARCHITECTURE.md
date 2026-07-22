# Sentinel AI — Architecture

This document explains *why* the codebase is shaped the way it is. It is the
reference for contributors deciding where a new piece of logic belongs.

## 1. Guiding goal

Sentinel AI mimics a **senior application-security engineer's review loop**:

> run the tools → read the raw output → throw away the noise → prioritize what's
> exploitable → explain it → suggest a fix.

The architecture maps each of those steps to a layer with a single
responsibility, so any one of them can be changed (new tool, new model, new UI)
without disturbing the others.

## 2. High-level shape

```
Next.js frontend  ──REST──▶  FastAPI backend  ──▶  { LLM provider, Security CLIs }
```

- **Frontend** is a pure client: it renders reviews and reports and never talks
  to the LLM or the scanners directly.
- **Backend** owns the entire review pipeline and exposes it over a small REST
  API.

## 3. Backend layers (clean architecture)

Dependencies point **inward**. Outer layers know about inner layers, never the
reverse.

```
        api  ─▶  services  ─▶  agents  ─▶  provider abstraction
                    │              │
                    └──▶ scanners ─┘
                    └──▶ models  (shared, depended on by all)
        config / utils  (cross-cutting, depend on nothing app-specific)
```

| Layer | Package | Responsibility | May depend on |
| --- | --- | --- | --- |
| **Transport** | `api/` | HTTP routing, request/response schemas, status codes, dependency injection. No business logic. | `services`, `models` |
| **Use cases** | `services/` | Orchestrate a full review by coordinating scanners + agents. The only layer allowed to touch both. | `scanners`, `agents`, `models` |
| **Reasoning** | `agents/` | All LLM logic (triage, remediation). Provider-agnostic via `LLMProvider`. | `provider`, `models` |
| **Tools** | `scanners/` | Wrap external CLIs (Semgrep, Gitleaks) behind one `Scanner` contract. | `models`, `utils` |
| **Contracts** | `models/` | Pydantic types shared across every layer. No behavior. | — |
| **Config** | `config/` | Typed settings from env. Single source of environment truth. | — |
| **Helpers** | `utils/` | Logging, subprocess, workspace helpers. Dependency-free. | — |

### Why these boundaries matter

- **Swap the model with a config flag.** Agents depend on the `LLMProvider`
  protocol, not on `openai` or `anthropic`. `get_llm_provider()` picks the
  implementation from `LLM_PROVIDER`. Adding a provider = one new class.
- **Add a scanner without touching the pipeline.** Every tool implements
  `Scanner.scan(target) -> list[Finding]`. The service iterates over a registry
  of scanners; it doesn't know or care which tools are in it.
- **One vocabulary everywhere.** Tools emit wildly different JSON; each wrapper
  normalizes into `Finding`. From that point on, agents, services, and the API
  speak only `Finding` / `ReviewReport`.
- **Testability.** Because dependencies are injected (providers into agents,
  scanners into services), each layer can be unit-tested with fakes.

## 4. The review pipeline (target flow)

```
POST /api/v1/reviews
        │
        ▼
ReviewService.run_review()
        │  1. stage code into SCAN_WORKSPACE_DIR
        │  2. run scanners concurrently ──▶ [raw Semgrep, raw Gitleaks]
        │  3. normalize ──────────────────▶ list[Finding]
        │  4. TriageAgent  ───────────────▶ dedup + drop false positives + prioritize
        │  5. RemediationAgent ───────────▶ explanation + suggested fix per finding
        │  6. assemble ───────────────────▶ ReviewReport
        ▼
  JSON response ──▶ frontend dashboard
```

> All of steps 1–6 are **scaffolded but not implemented** in this milestone.

## 5. Frontend structure

| Folder | Responsibility |
| --- | --- |
| `app/` | Next.js App Router routes, layouts, and server components. |
| `components/` | Reusable presentational/container components (FindingCard, SeverityBadge, …). |
| `lib/` | Framework-agnostic logic — chiefly the typed `apiFetch` client. |
| `hooks/` | Reusable React hooks (data fetching, polling, UI state). |
| `types/` | TypeScript mirrors of the backend contracts (`Finding`, `ReviewReport`). |

The `types/` folder deliberately mirrors `backend/app/models` so the API
contract is typed on both ends.

## 6. Deployment

- Each service has its own multi-stage `Dockerfile`.
- The **backend image bundles Semgrep (pip) and the Gitleaks binary**, so the
  scanning environment is reproducible and the app has no host-tool
  dependencies.
- `docker-compose.yml` wires the two together for local/one-box deployment; the
  frontend waits on the backend's `/health` check before starting.
- Both images run as **non-root users** — a baseline hardening practice fitting
  a security product.

## 7. Extension points

| Want to… | Do this |
| --- | --- |
| Add an LLM vendor | Implement `LLMProvider`, register it in `get_llm_provider()`. |
| Add a scanner | Implement `Scanner`, add it to the service's scanner registry. |
| Persist reviews | Add a `repositories/` layer + a DB service in compose. |
| Add auth | Add middleware/dependencies in the `api` layer only. |
