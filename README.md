# Flux

**Type a topic. Get a finished video. Auto-published to YouTube.**

Flux is an AI-driven media pipeline that turns a single sentence into a captioned,
narrated MP4 (or long-form podcast MP3) and ships it straight to the operator's
YouTube channel — no editor, no recording session, no per-user sign-in.

```
Topic ─► AI script ─► AI imagery ─► Neural TTS ─► Subtitles ─► Video assembly ─► YouTube
```

End users never authenticate. The operator wires one YouTube account via CLI
once; every render published through the app lands on that channel.

---

## What it actually costs to make a video

| Approach                                   | Cost per 60-second video |
| ------------------------------------------ | ------------------------ |
| Hiring a freelance editor (Fiverr / Upwork) | **$50 – $200**           |
| SaaS tools (Synthesia, Pictory, InVideo)   | **$1 – $3**              |
| **Flux on free providers** (default)       | **$0.00**                |
| Flux on premium providers (OpenAI + Gemini) | ~$0.25                   |

Flux's default chain is **Pollinations.ai + Microsoft Edge Neural TTS + Google
Gemini 2.5 Flash** — all free tier, no credit card. A creator producing 50 short
videos a month who would otherwise spend ~$2,500–10,000 on freelancers (or
~$60–180 on a SaaS tool) pays **nothing** with Flux — only the host bill
(Render free tier or ~$3–5/mo on Fly.io).

---

## What you get from one topic

- **MP4** (1280×720, H.264 + AAC) — cinematic scenes, narrated voiceover, burned-in subtitles
- **MP3** (podcast mode) — long-form audio with chapter-style narration
- **Thumbnail** auto-generated from the first scene
- **SRT caption track** — uploaded alongside the YouTube video for accessibility
- **YouTube URL** — your channel, your visibility setting (`unlisted` / `public` / `private`)

Render time: ~3–6 minutes per 60-second clip on Render free; ~1 minute on a
modern laptop.

---

## Pipeline

Six async stages, fully observable via `/api/jobs/{id}`:

| Stage     | What it does                                      | Provider chain (in order)                                  |
| --------- | ------------------------------------------------- | ---------------------------------------------------------- |
| Script    | Topic → scene-by-scene narration + image prompts  | Gemini 2.5 Flash → OpenAI GPT-4o → deterministic mock     |
| Image     | Image prompt → 1024×1024 PNG per scene            | Pollinations.ai → Gemini Flash Image → OpenAI gpt-image-1 → poster-style PIL placeholder |
| Voice     | Narration text → MP3 per scene                    | Microsoft Edge Neural TTS → gTTS → Kokoro (local) → silent track |
| Subtitles | Align text against measured audio lengths         | pysrt (deterministic)                                      |
| Assembly  | Scenes + audio + subtitles → final MP4 / MP3      | ffmpeg + libass / MoviePy                                  |
| Publish   | Upload MP4, attach SRT, set thumbnail             | YouTube Data API v3 (OAuth 2.0)                            |

Each provider tier is **memoised per-process**: once it returns a structural
failure (402 / 429 / 403), it's marked down and skipped for the rest of the
session — no quota-burning retry storm, no slow render because of a dead
upstream.

---

## Tech stack

**Frontend** — Next.js 14 (App Router), React, TypeScript, Tailwind CSS, Framer Motion. Deployed on **Vercel**.

**Backend** — Python 3.11, FastAPI, Pydantic v2, Uvicorn. Containerised with Docker, deployed on **Render** (Fly.io config also in repo).

**Media** — ffmpeg (libass for burned subtitles), MoviePy 1.0.3, Pillow + NumPy (deterministic poster fallback), pysrt.

**AI** — OpenAI GPT-4o + gpt-image-1, Google Gemini 2.5 Flash + Flash Image, Pollinations.ai, Microsoft Edge Neural TTS, gTTS, Kokoro.

**Auth & integrations** — YouTube Data API v3 (OAuth 2.0 installed-app flow), refresh-token persistence with env-var hydration for stateless hosts.

---

## Layout

```
flux/
├─ backend/                 # FastAPI + pipeline
│  ├─ app/
│  │  ├─ main.py            # API entry + YouTube credential hydration
│  │  ├─ config.py          # env-driven settings (pydantic-settings)
│  │  ├─ pipeline.py        # six-stage orchestrator
│  │  ├─ storage.py         # on-disk job + video index
│  │  ├─ setup_youtube.py   # one-time operator OAuth (CLI)
│  │  ├─ models/schemas.py
│  │  ├─ routers/           # generation · library · youtube
│  │  └─ services/          # script · image · voice · subtitle · assembly · podcast · youtube
│  ├─ Dockerfile            # python:3.11-slim + ffmpeg + libass
│  ├─ fly.toml              # Fly.io alternative deploy
│  └─ requirements.txt
├─ frontend/                # Next.js 14 + Tailwind + Framer Motion
│  ├─ app/                  # / · /creator · /pipeline · /library
│  ├─ components/
│  └─ lib/api.ts            # NEXT_PUBLIC_API_URL aware
├─ render.yaml              # Render Blueprint for backend
└─ DEPLOY.md                # full deployment guide
```

---

## Quickstart

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>
- Mock mode is **on** by default — the full UI works without any API keys.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. Next.js rewrites `/api/*` and `/media/*` to
`http://127.0.0.1:8000` in dev.

---

## Going live

Set `MOCK_MODE=false` and pick a provider in `backend/.env`:

```ini
PROVIDER=gemini                              # or "openai"
GEMINI_API_KEY=...                           # free tier at aistudio.google.com
ALLOWED_ORIGINS=https://your-frontend.app
```

For deploying the backend to Render or Fly.io and the frontend to Vercel,
see **[DEPLOY.md](DEPLOY.md)** — covers Docker config, persistent disk
strategy, CORS, and the env-var path for YouTube OAuth on stateless hosts.

### YouTube auto-publish (one-time setup)

1. Google Cloud Console → **enable YouTube Data API v3**.
2. Create an OAuth client of type **Desktop app** → download JSON →
   save at `backend/secrets/youtube_client_secret.json`.
3. Run the operator OAuth flow once:

   ```powershell
   cd backend
   python -m app.setup_youtube
   ```

   A browser tab opens — sign in with the Google account that owns the channel
   Flux should publish to. The refresh token is persisted at
   `backend/secrets/youtube_token.json` and rotates automatically.

On stateless hosts (Render free), paste the contents of those two JSON files
into `YOUTUBE_CLIENT_SECRET_JSON` and `YOUTUBE_TOKEN_JSON` env vars — they're
materialised to disk on boot.

---

## API surface

| Method | Path                       | Purpose                                |
| ------ | -------------------------- | -------------------------------------- |
| POST   | `/api/generate`            | Submit a new job (video or podcast)    |
| GET    | `/api/jobs`                | List recent jobs                       |
| GET    | `/api/jobs/{id}`           | Job + live stage progress              |
| DELETE | `/api/jobs/pending`        | Clear queued / in-progress / failed    |
| GET    | `/api/videos?q=`           | List / search finished renders         |
| DELETE | `/api/videos/{id}`         | Remove a video (file + index)          |
| POST   | `/api/youtube/upload`      | Re-upload an existing video manually   |
| GET    | `/api/health`              | Service status / mock-mode flag        |

`POST /api/generate`:

```json
{
  "topic": "How black holes evaporate",
  "duration": 60,
  "key_points": "Hawking radiation, event horizon, time scale",
  "privacy": "unlisted",
  "media_type": "video"
}
```

- `media_type` — `"video"` (default) or `"podcast"`
- `duration` — 10–600 seconds (podcasts up to 10 min)
- `privacy` — YouTube visibility: `unlisted` · `public` · `private`

---

## Pages

- **/** — hero, channel preview, pipeline visualization.
- **/creator** — format toggle (video/podcast) + topic + duration + key points + visibility → submit.
- **/pipeline** — left rail of jobs, right pane with live per-stage progress.
- **/library** — search, filter by format / published status, sort, video grid with modal player.

---

## License

MIT.
