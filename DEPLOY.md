# Deploying to Railway

Ship the prototype to a public URL in ~20 minutes of clicking.

## Prerequisites

1. **GitHub account** with this code pushed to a repo
2. **Railway account** (sign up at https://railway.com — free $5 trial credit)
3. **Anthropic API key** (get at https://console.anthropic.com/settings/keys)
4. **Credit card** for Railway billing after the trial runs out (~$5–10/month for light use)

## Deployment steps

### 1. Create a Railway project

Sign in at https://railway.com → New Project → **Deploy from GitHub repo** → authorize Railway on your GitHub → pick this repo.

Railway will create an initial service. Delete or ignore it — we're going to add three services explicitly.

### 2. Add the Postgres database

In the Railway project canvas: **New → Database → Add PostgreSQL**.

Railway spins up a managed Postgres instance and exposes a `DATABASE_URL` variable you can reference from other services.

### 3. Add the backend service

**New → GitHub Repo → select your repo again.**

In the new service's settings:

- **Root Directory:** `backend`
- **Service Name:** `backend` (important — the frontend references this name)
- **Variables** (add via Settings → Variables):
  - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (Railway variable reference)
  - `ANTHROPIC_API_KEY` = `sk-ant-…` (your key)
  - `CLAUDE_MODEL` = `claude-sonnet-4-6`
  - `CORS_ORIGINS` = `*` (fine for prototype)

Under **Settings → Networking**, click **Generate Domain** to get a public URL like `https://cmc-backend-production.up.railway.app`. Copy this — you'll need it in Step 4.

Verify the backend is up: visit `https://<your-backend-domain>/health` and you should see `{"status":"ok"}`.

### 4. Add the frontend service

**New → GitHub Repo → select your repo.**

In the new service's settings:

- **Root Directory:** `frontend`
- **Service Name:** `frontend`
- **Build → Build Args:**
  - `NEXT_PUBLIC_API_URL` = `https://<your-backend-domain>` (from Step 3)
- **Variables:**
  - `NEXT_PUBLIC_API_URL` = `https://<your-backend-domain>` (same URL — belt and braces)

Under **Settings → Networking**, click **Generate Domain** to get the frontend's public URL.

### 5. Open the app

Visit the frontend URL. You should see the "Clinical Monitoring Copilot" landing page with the three upload panels.

### 6. Test with synthetic data

Upload the sample protocol PDF and the 4 CSV files from this repo's `data/synthetic/` directory (after running `python3 data/generate_synthetic.py` locally). Then click "Run analysis." Within ~30 seconds you should see deviation findings.

## Troubleshooting

- **Backend crashes with "connection refused"**: Postgres takes ~30s to become ready on first boot. Railway retries the backend automatically.
- **Frontend shows API errors**: the `NEXT_PUBLIC_API_URL` build arg must be set at **build time** (not just as a runtime variable). If you set it late, force a redeploy via **Service → Deployments → Redeploy**.
- **CORS errors in the browser console**: make sure `CORS_ORIGINS=*` is set on the backend.
- **Build fails on frontend with peer-dependency errors**: already handled by `--legacy-peer-deps` in the Dockerfile. If it still fails, check Railway's build logs for the actual error.

## Costs

Expect **~$5–10/month** for a prototype with light use:
- Postgres: ~$5/mo (1GB DB)
- Backend: ~$2–5/mo (scales with CPU)
- Frontend: ~$1–3/mo (mostly idle)

Railway's first $5 trial is free. Stop services you aren't actively using to save cost.
