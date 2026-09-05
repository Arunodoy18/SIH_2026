# Deployment

Two hosts, one deploy each: **Netlify serves the frontend, Render serves the backend.**
This isn't a workaround — it's the correct shape for this app, for reasons that matter
enough to explain rather than just assert.

## Why not "all on Netlify"

Netlify is a **static-site host with a Node/Go serverless-function runtime** bolted on. It
is excellent at exactly one thing: take a build command, produce static files (HTML/CSS/JS),
serve them off a global CDN. Netlify Functions extend that with small, short-lived,
stateless request handlers — first-class for JavaScript and Go.

This backend is a different shape entirely:

| Requirement | Netlify Functions | This backend |
|---|---|---|
| Runtime | Node.js / Go (first-class) | Python 3.11 |
| Native deps | none expected | GDAL, GEOS, PROJ (via rasterio / GeoPandas / Shapely) |
| Package size | ~50 MB zipped limit | GeoPandas + rasterio + scikit-learn + a trained model file alone exceed this |
| State | stateless, per-invocation | a multi-stage pipeline that writes intermediate GeoParquet/GeoTIFF/joblib artifacts to disk and reads them back across requests |
| Execution time | short, request-scoped | seed → train → analyse pipeline takes 1.5–2 s, and a cold boot (see below) runs it once at startup |

None of that fits a serverless function bundle. It needs an actual, persistent Python
process with a writable filesystem — a real (if small) server, not a function.

**The frontend is the opposite** — a Vite build producing static files with zero server-side
logic (it calls the backend's API over HTTP). That's precisely Netlify's job, and it's
free, instant, and globally cached there.

So: **Netlify for `frontend/`, Render for `backend/`**, talking to each other over HTTPS with
CORS already open on the backend (`allow_origins=["*"]` in `redzone/api/main.py` — fine for
a hackathon demo; scope it to your Netlify domain before any real production use).

## Deploy the backend (Render)

1. Push this repo to GitHub (already done).
2. On [render.com](https://render.com): **New → Blueprint**, point it at this repo. Render
   reads `render.yaml` at the repo root and proposes one service, `nirnay-backend`, built
   from `backend/Dockerfile` — accept it. (No Blueprint access? **New → Web Service**,
   pick the repo, runtime **Docker**, root directory `backend`, and it finds the Dockerfile.)
3. Render prompts for the env vars marked `sync: false` in `render.yaml` — set:
   - `GROQ_API_KEY` — from [console.groq.com](https://console.groq.com) (optional; the API
     works without it, falling back to a template report narrative)
   - `ANTHROPIC_API_KEY` — optional secondary provider, same fallback behaviour
   - Leave anything you don't have blank; nothing here is required for the app to run.
4. Deploy. First boot runs `docker-entrypoint.sh`: generates the synthetic Sikkim seed,
   trains the landslide model, runs the full pipeline, *then* starts serving — watch the
   log for `pipeline OK in ...s` before it's ready. Health check: `GET /health`.
5. Copy the assigned URL (`https://nirnay-backend-xxxx.onrender.com`) — the frontend needs it.

**Free-tier cold starts.** Render's free plan spins the container down after 15 minutes of
no traffic and boots a fresh one on the next request — which means the *entire* seed →
train → pipeline sequence above runs again, so the first hit after idle takes something
like 30–60 seconds before it answers. That's normal, not a bug — if you're demoing live to
judges, hit `/health` yourself a minute before you go on stage to warm it up.

## Deploy the frontend (Netlify)

1. On [netlify.com](https://netlify.com): **Add new site → Import an existing project**,
   pick this repo. Netlify reads `frontend/netlify.toml` — set **Base directory** to
   `frontend` if it doesn't infer it automatically (build command `npm run build`, publish
   directory `dist`, both already declared in `netlify.toml`).
2. **Site configuration → Environment variables**, add:
   - `VITE_API_BASE_URL` = the Render URL from above, **no trailing slash**
     (e.g. `https://nirnay-backend-xxxx.onrender.com`)
3. Deploy. Vite bakes `VITE_API_BASE_URL` into the static build at build time (it's not
   read at runtime — changing it later means triggering a new Netlify build, not just
   restarting anything).

Local dev is unaffected either way: leave `VITE_API_BASE_URL` unset and `frontend/src/api.ts`
falls back to `/api`, which `vite.config.ts`'s dev-server proxy forwards to
`http://127.0.0.1:8000` — exactly the existing `make api` / `make web` workflow.

## Secrets — the one rule that matters

**Never put a real API key in a file that gets committed.** `.env.example` files in both
`backend/` and `frontend/` document every variable the app reads; the real values live only
in your local shell (`export GROQ_API_KEY=...`, or a git-ignored `backend/.env`) and in each
host's dashboard (Render's Environment tab, Netlify's Environment variables tab) — never in
source. `.gitignore` at the repo root already excludes `.env`, `.env.local`, and friends.

If a key is ever pasted into a chat, a commit, a log, or anywhere else outside those two
places, treat it as compromised and regenerate it — a leaked key is a liability the moment
it's visible anywhere it can be copied from, whether or not it's actually been misused yet.

## Verifying a deploy

```bash
curl https://<your-render-url>/health
# {"status":"ok","interim_ready":true,"processed_ready":true}

curl https://<your-render-url>/summary | head -c 200

# from the Netlify site itself: open it, the dashboard should load real data,
# not a blank map — if it's blank, check the browser console for a CORS or
# "failed to fetch" error, which almost always means VITE_API_BASE_URL is wrong
# or missing the https:// scheme.
```
