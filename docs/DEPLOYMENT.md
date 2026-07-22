# Deploying Sentinel AI

Two pieces, deployed separately and wired together:

| Piece | Host | Why |
| --- | --- | --- |
| **Frontend** (Next.js dashboard) | **Vercel** | Free, no card, first-class Next.js support |
| **Backend** (FastAPI + Semgrep + Gitleaks) | **Hugging Face Spaces** (Docker) | Free, no card, 16 GB RAM — enough for Semgrep |

```
GitHub (whole repo)
   ├── frontend/  ──▶ Vercel        →  https://sentinel-ai.vercel.app
   └── backend/   ──▶ HF Space      →  https://<user>-sentinel-ai.hf.space
                         ▲                     │
                         └──── CORS + API URL ─┘
```

---

## 1. Push the code to GitHub

```bash
cd sentinel-ai
git init -b main
git add .
git commit -m "Sentinel AI"
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<you>/sentinel-ai.git
git push -u origin main
```

> `.env` files, the local venv, `node_modules`, and scanner binaries are
> git-ignored — no secrets or bulk are committed.

---

## 2. Backend → Hugging Face Space (Docker)

1. Create a Space: <https://huggingface.co/new-space> → **SDK: Docker**, **blank
   template**, visibility **Public**. Name it e.g. `sentinel-ai`.
2. Push the **`backend/` subtree** to the Space's git remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<user>/sentinel-ai
   git subtree push --prefix backend space main
   ```
   The Space's root then has the `Dockerfile` + `README.md` (with the HF
   metadata block) and builds automatically.
3. In the Space: **Settings → Variables and secrets**, add:

   | Name | Value | Kind |
   | --- | --- | --- |
   | `LLM_API_KEY` | your Gemini key | **secret** |
   | `LLM_MODEL` | `gemini-flash-lite-latest` | variable |
   | `SEMGREP_CONFIG` | `p/default` | variable |
   | `LLM_TIMEOUT` | `120` | variable |
   | `SCAN_WORKSPACE_DIR` | `/tmp/sentinel-scans` | variable |
   | `CORS_ORIGINS` | your Vercel URL (fill in after step 3) | variable |
   | `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` | variable |

4. Wait for the build; confirm `https://<user>-sentinel-ai.hf.space/health`
   returns `{"status":"ok"}`.

---

## 3. Frontend → Vercel

1. <https://vercel.com/new> → import the GitHub repo.
2. **Root Directory:** `frontend`. Framework preset: **Next.js** (auto).
3. **Environment Variable:**
   `NEXT_PUBLIC_API_BASE_URL = https://<user>-sentinel-ai.hf.space`
4. Deploy. Note the resulting URL (e.g. `https://sentinel-ai.vercel.app`).

---

## 4. Close the loop (CORS)

Put the real Vercel URL into the Space's `CORS_ORIGINS` variable (step 2.3) and
**restart the Space**. Done — open the Vercel URL and run a scan.

---

## Notes & limits (free tier)

- **Cold start:** the Space sleeps after ~48 h idle; the first request wakes it
  (~30–60 s). Vercel has no cold start.
- **Big repos:** a very large clone + Semgrep + multi-turn AI can approach the
  proxy timeout. Small/medium repos (the demo targets) are comfortable.
- **Cost:** $0. No credit card required for either host.
