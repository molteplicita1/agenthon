# Development

## Requirements

- Python 3.12 and [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+ and `npm`
- A Gemini API key (AI Studio, or Vertex AI with `GOOGLE_GENAI_USE_VERTEXAI=true`)
- An ElevenLabs API key and voice id (optional: without them the brief is sent as text only)
- A Telegram bot token from [@BotFather](https://t.me/BotFather), and two Telegram accounts
- For the demo video only: Google Chrome and `ffmpeg`

## Configuration

```bash
cp .env.example .env
```

One `.env` file at the project root, read by both the backend and the bot. Values in it win over
the shell; an empty value counts as missing. Never commit it.

| Variable | Used by | Default | Meaning |
|---|---|---|---|
| `GEMINI_API_KEY` | backend | — | Model key. |
| `GOOGLE_GENAI_USE_VERTEXAI` | backend | `false` | `true` for a Vertex AI key. |
| `GEMINI_MODEL` | backend | `gemini-3.8-flash` | Model id. |
| `GEMINI_THINKING` | backend | `low` | Thinking level of every call. |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | backend | — | Voice of the morning brief. |
| `ELEVENLABS_MODEL` | backend | `eleven_multilingual_v2` | Voice model. |
| `TELEGRAM_BOT_TOKEN` | bot | — | Token from @BotFather. |
| `BACKEND_URL` | bot | `http://localhost:8000` | Where the bot finds the backend. |
| `BRAIN_NO_LLM`, `BRAIN_NO_VOICE` | backend | — | `1` turns off Gemini or ElevenLabs (used by the tests). |
| `BRAIN_SEED_DIR`, `BRAIN_STATE_PATH` | backend | `backend/data/seed`, `backend/data/state.json` | Another seed folder or state file. |
| `VITE_API_URL`, `VITE_USE_MOCK` | control room | `http://localhost:8000`, `false` | See [Control room](control-room.md). |

## Running

One terminal each:

```bash
cd backend && uv run uvicorn main:app --port 8000
```

```bash
cd bot && uv run python main.py
```

```bash
cd frontend && npm install && npm run dev
```

`uv run` creates the virtual environment and installs the locked dependencies on first use;
`--port` sets the port uvicorn listens on. API docs are at <http://localhost:8000/docs>, the
control room at <http://localhost:5173>.

First time only: in each Telegram account open the bot, send `/start` and pick **Giulia** in one
and **Luca** in the other. Then follow [`demo-video/demo.md`](../demo-video/demo.md), starting
with **Start the day**. Restarting the backend and the bot starts a new demo from the seed.

### Without Telegram or keys

- Control room on mock data, no backend: `cd frontend && VITE_USE_MOCK=true npm run dev`.
- The API directly with `curl`: see the examples in the [API reference](api.md#examples).
- Without `GEMINI_API_KEY` questions and events return `503` and briefs use the template.

## Tests

```bash
cd backend && uv run pytest -q
```

28 tests, offline: `conftest.py` sets `BRAIN_NO_LLM=1` and `BRAIN_NO_VOICE=1`, uses a temporary
state file and replaces the model with a fake where a test needs one. `-q` keeps the output short.

| File | Covers |
|---|---|
| `tests/test_access.py` | Identity, visibility, who may decide memory and actions, approve and reject effects, unique message ids. |
| `tests/test_brain.py` | `/ask` (filtering, dropped ids, citations, model failure), the demo script and the watcher (conflict, templates, facts, failures), the brief (fallbacks, no repetitions, word limit), a fresh start. |

```bash
python3 backend/data/seed/check_seed.py
```

Validates the seed files and prints `SEED OK`.

```bash
cd frontend && npm run build
```

Type-checks the control room with `tsc` and builds it into `frontend/dist/`.

## Recording the demo video

`demo-video/stage.html` puts the control room and two simulated phones (Giulia and Luca) on one
1920×1080 stage. `record.mjs` plays the demo script on it with Playwright and the installed
Google Chrome against the real backend; `assemble.mjs` builds the MP4 with `ffmpeg` (shortened
waits, message chimes, the brief's voice, the narrator and background music that ducks under the
voices, normalised to -16 LUFS). Restart the backend and the control room first so the demo starts
from the seed; the bot is not needed.

The narrator's lines are in `narration.json`. `narrate.mjs` turns them into speech with
ElevenLabs (the key in `.env`), caching each clip by its text, and `record.mjs` holds every scene
until its line has been spoken. `music.py` composes the music from code (needs `numpy` and
`scipy`), so there is no licence to clear.

```bash
cd demo-video && npm install && npm run narrate && npm run record && npm run assemble
```

The result is `demo-video/out/brightloop-demo.mp4` (ignored by Git); the committed
`demo-video/brightloop-demo.mp4` is a re-encoded, smaller copy.

## Repository layout

```
.
├── README.md            introduction and quick start
├── .env.example         the variables .env needs
├── backend/             the Brain (FastAPI)
│   ├── data/seed/       fictional company data + check_seed.py
│   ├── demo_script.json the steps behind the demo button
│   └── tests/
├── bot/                 Telegram adapter
├── frontend/            control room (Vite + React)
├── demo-video/          demo script, pitch, video and the tools that record it
└── docs/                this documentation
    ├── assets/          logo
    └── plans/           development plans from the hackathon
```

## Conventions

- Everything in the product and in the project files is in English.
- Simplicity first: if two ways work, pick the one with less code.
- Business rules belong in the backend, with a test; the bot and the control room stay thin.
- The only outside services are Gemini, ElevenLabs and Telegram; no code connects to real work
  tools.
- Never print or log API keys.
