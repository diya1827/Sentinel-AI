# Deploying Sentinel AI

Two pieces, deployed separately and wired together:

| Piece | Host | Why |
| --- | --- | --- |
| **Frontend** (Next.js dashboard) | **Vercel** | Free, no card, first-class Next.js support |
| **Backend** (FastAPI + Semgrep + Gitleaks) | **Render** (Docker web service) | Free, no card, deploys from `render.yaml` |

```
GitHub (whole repo)
   ├── frontend/  ──▶ Vercel     →  https://sentinel-ai.vercel.app
   └── backend/   ──▶ Render      →  https://sentinel-ai-backend.onrender.com
                         ▲                     │
                         └──── CORS + API URL ─┘
```

> **Note on hosting:** Hugging Face Spaces (Docker) became a paid feature in
> mid-2026, so the backend uses Render's free tier instead. Render free is
> 512 MB RAM, so Semgrep runs with `--max-memory 400 --jobs 1` (set via env in
> `render.yaml`) to stay in budget.

---

## 1. Push the code to GitHub  ✅ (done)

```bash
git remote add origin https://github.com/<you>/Sentinel-AI.git
git push -u origin main
```

`.env` files, the venv, `node_modules`, and scanner binaries are git-ignored.

---

## 2. Backend → Render (Docker web service)

1. Sign up at <https://render.com> with **GitHub** (no credit card for free tier).
2. **New → Blueprint**, pick the `Sentinel-AI` repo. Render reads
   [`render.yaml`](../render.yaml) and provisions `sentinel-ai-backend`
   (Docker, free plan, `rootDir: backend`).
3. When prompted, set the one secret it asks for:
   `LLM_API_KEY = <your Gemini key>`  (the rest are pre-filled by the blueprint).
4. Apply / deploy. First build takes a few minutes (installs Semgrep, downloads
   Gitleaks). Watch the build logs.
5. Verify: `https://sentinel-ai-backend.onrender.com/health` → `{"status":"ok"}`.

> `render.yaml` already sets `CORS_ORIGIN_REGEX = https://.*\.vercel\.app`, so
> any Vercel URL (prod + previews) is allowed — no CORS step needed later.

---

## 3. Frontend → Vercel

1. <https://vercel.com/new> → import the GitHub repo.
2. **Root Directory:** `frontend`. Framework preset: **Next.js** (auto-detected).
3. **Environment Variable:**
   `NEXT_PUBLIC_API_BASE_URL = https://sentinel-ai-backend.onrender.com`
4. Deploy. Open the resulting URL and run a scan. Done. 🎉

---

## Notes & limits (free tier)

- **Cold start:** Render's free service spins down after 15 min idle; the first
  request then takes ~50 s to wake. Vercel has no cold start. (Tip: the very
  first scan after idle may feel slow — that's the wake-up, not the scan.)
- **Memory:** 512 MB. Semgrep is capped (`--max-memory 400`); very large repos
  may scan partially. The demo repos (leaky-repo, nodejs-goof) are comfortable.
- **Cost:** $0. No credit card required for either host.

## Redeploying

Both hosts auto-deploy on push to `main`. Just `git push` and they rebuild.
