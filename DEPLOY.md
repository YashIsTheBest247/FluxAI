# Deployment — Fragment

Two halves: Next.js frontend on **Vercel**, Python backend on **Render**.

The backend cannot run on Vercel because video generation takes 5–10 minutes
per job (Vercel functions cap at 60s Hobby / 300s Pro), needs a writable
filesystem during the render, and shells out to ffmpeg. Render's container
service handles all of that on its free tier — no credit card required.

---

## 1. Backend → Render (free tier)

### What "free" means here

- **512 MB RAM**, 0.1 CPU
- **Sleeps after 15 minutes** of no traffic. First request after sleep takes ~30s
  to wake the container.
- **No persistent disk.** `/tmp/storage` is wiped on every restart and after
  long sleeps. The library shows whatever's been rendered since the last wake.
  Auto-upload to YouTube is the recommended way to keep clips permanently —
  the YouTube URL stays in the library row.
- **Image size cap**: 4 GB (our image is ~1 GB, plenty of headroom).

If those tradeoffs bite, the fixes are: upgrade to Render Starter ($7/mo, no
sleep, persistent disk add-on), or switch back to Fly.io ([backend/fly.toml](backend/fly.toml)
is still in the repo — see the **Alternative: Fly.io** section below).

### Setup

1. Push this repo to GitHub.
2. https://dashboard.render.com/ → **New +** → **Blueprint** → connect the repo.
3. Render reads [`render.yaml`](render.yaml) at the repo root and creates the
   `fragment-backend` web service automatically.
4. Before the first deploy, set the secret env vars in the dashboard (they're
   marked `sync: false` in the blueprint):
   - `GEMINI_API_KEY`
   - `OPENAI_API_KEY` (or leave blank)
   - `ALLOWED_ORIGINS` → leave blank for now; we'll come back to it after Vercel
   - `FLUX_CHANNEL_URL` → optional, shows in the nav
5. Click **Apply**. The first build takes 8–12 minutes (ffmpeg + Python deps).
6. When it's up, Render gives you a URL like `https://fragment-backend.onrender.com`.

### Sanity check

```bash
curl https://fragment-backend.onrender.com/api/health
# → {"status":"ok","provider":"gemini",...}
```

If you get a long wait followed by 502 Bad Gateway, the container probably
OOM'd during startup or assembly. Check Render's **Logs** tab; if you see
`Killed` or `MemoryError`, your only options are to drop output resolution
in [backend/app/services/assembly_service.py](backend/app/services/assembly_service.py)
(`VIDEO_W, VIDEO_H = 854, 480`) or move to Render Starter.

---

## 2. Frontend → Vercel

1. https://vercel.com → **Add New Project** → import the same repo.
2. **Root Directory:** `frontend`
3. **Environment Variables:**
   - `NEXT_PUBLIC_API_URL` = `https://fragment-backend.onrender.com` (no trailing slash)
4. Click **Deploy**.

`lib/api.ts` prepends `NEXT_PUBLIC_API_URL` to every API call and media URL,
so the browser talks to Render directly — Vercel doesn't proxy any video bytes
(which would otherwise eat into your 100 GB/mo Vercel bandwidth).

### After deploying

Back on Render, set the actual Vercel URL on the backend:

```
ALLOWED_ORIGINS = https://your-real-name.vercel.app,http://localhost:3000
```

Editing an env var triggers an automatic redeploy on Render.

---

## 3. YouTube auto-upload (optional)

Render free has no persistent disk, which means the OAuth token would be
re-derived on every restart — painful. Two ways to handle it:

**A. Keep auto-upload off** (default, easiest)
Leave `YOUTUBE_AUTO_UPLOAD=false` in the blueprint. Renders stay on the box
until the next restart and the user downloads them from the library before
the container sleeps.

**B. Enable it with token-as-env-var**
Run `python -m app.setup_youtube` locally, base64-encode the resulting
`secrets/youtube_token.json` and `secrets/youtube_client_secret.json`, then
set them as env vars in Render and add a small startup hook that writes them
to `/tmp/secrets/`. Ask if you want this wired up — it's ~15 lines of code
in `app/main.py`.

---

## Local development (unchanged)

`NEXT_PUBLIC_API_URL` empty → frontend uses relative paths → Next.js rewrites
in `next.config.js` proxy `/api/*` and `/media/*` to `http://127.0.0.1:8000`.

```powershell
# Terminal 1
cd backend; .venv\Scripts\python -m uvicorn app.main:app --reload

# Terminal 2
cd frontend; npm run dev
```

---

## Updating

```bash
# Both ends auto-deploy on push to main:
git push
```

---

## Alternative: Fly.io (needs a card on file)

If you'd rather avoid the cold-start and want persistent storage, the Fly
config is still in the repo:

```powershell
cd backend
fly launch --no-deploy --copy-config --region bom
fly volumes create fragment_data --region bom --size 3
fly secrets set GEMINI_API_KEY=... ALLOWED_ORIGINS=https://your.vercel.app
fly deploy
```

Then point Vercel's `NEXT_PUBLIC_API_URL` at `https://your-app.fly.dev`
instead of the Render URL. Fly requires a payment method but the actual bill
is ~$3–5/mo with the auto-suspend setup in [backend/fly.toml](backend/fly.toml).
