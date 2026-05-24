# Flux

Type a topic. Get a finished video. Auto-published to the operator's YouTube channel.

```
Topic → GPT-4 → DALL·E 3 → Kokoro TTS → Subtitles → MoviePy → YouTube
```

End users never sign in. The operator wires up a single YouTube account once via CLI, and every render published through the app lands on that channel.

---

## Layout

```
flux/
├─ backend/                 # FastAPI + pipeline
│  ├─ app/
│  │  ├─ main.py            # API entrypoint
│  │  ├─ config.py          # env-driven settings
│  │  ├─ pipeline.py        # orchestrator
│  │  ├─ storage.py         # on-disk job + video index
│  │  ├─ setup_youtube.py   # one-time operator OAuth (run via CLI)
│  │  ├─ models/schemas.py
│  │  ├─ routers/           # generation, library, youtube
│  │  └─ services/          # script, image, voice, subtitle, assembly, youtube
│  ├─ secrets/              # operator OAuth client + token (gitignored)
│  └─ requirements.txt
└─ frontend/                # Next.js 14 + Tailwind + Framer Motion
   ├─ app/                  # / · /creator · /pipeline · /library
   ├─ components/
   └─ lib/api.ts
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
- Mock mode is **on** by default — full UI works without any API keys.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. Next rewrites `/api/*` and `/media/*` to the backend.

---

## Going live

Set `MOCK_MODE=false` in `backend/.env` and add `OPENAI_API_KEY`. That's enough for real script + image + voice + assembly. Uploads stay off until you wire YouTube.

### YouTube (one-time operator setup)

1. Google Cloud Console → enable **YouTube Data API v3**.
2. Create an OAuth client of type **Desktop app**.
3. Download the JSON → save it at `backend/secrets/youtube_client_secret.json`.
4. From the `backend/` directory:

```powershell
.\.venv\Scripts\Activate.ps1
python -m app.setup_youtube
```

A browser tab opens — pick the Google account that owns the channel Flux should publish to.
The token is persisted at `backend/secrets/youtube_token.json` and refreshed automatically.
From then on, every render published through the app lands on that channel.

---

## API surface

| Method | Path                       | Purpose                              |
| ------ | -------------------------- | ------------------------------------ |
| POST   | `/api/generate`            | Submit a new job                     |
| GET    | `/api/jobs`                | List recent jobs                     |
| GET    | `/api/jobs/{id}`           | Job + live stage progress            |
| GET    | `/api/videos?q=`           | List / search generated videos       |
| DELETE | `/api/videos/{id}`         | Remove a video (file + index)        |
| POST   | `/api/youtube/upload`      | Re-upload an existing video manually |
| GET    | `/api/health`              | Service status / mock-mode flag      |

`POST /api/generate`:

```json
{
  "topic": "How black holes evaporate",
  "duration": 60,
  "key_points": "Hawking radiation, event horizon, time scale",
  "privacy": "unlisted"
}
```

`privacy` is the YouTube visibility for the published video (`unlisted` · `public` · `private`).

---

## Pages

- **/** — hero, sample render preview, pipeline visualization.
- **/creator** — topic + duration + key points + visibility → submit. Renders appear below as they finish.
- **/pipeline** — left rail of jobs, right pane with live per-stage progress.
- **/library** — search, filter, sort, video grid with modal player.

---

## License

MIT.
