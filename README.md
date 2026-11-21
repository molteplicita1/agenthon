# Company Brain

**A linter for company decisions.**

Company Brain is a prototype built in one day for the "Agentic AI for business" track of a
hackathon. It watches a team's work (emails, chat threads, tasks, docs, pull requests), keeps a
shared memory that team leads approve or reject, and tells each person what needs their
attention before they ask. It lives where the team already is: a real **Telegram bot**.

What sets it apart is that **the memory is active**. Approved decisions are not only used to
answer questions: new work is checked against them. When a lead approves "PostgreSQL over
MongoDB" and a pull request that adds MongoDB shows up later, the Brain alerts the lead on its own,
cites both sources and proposes a note to the author. Nothing happens until a person approves it.

> All data is fictional. The story follows **Brightloop**, an invented software house in Turin,
> and its client **Alpilog**. Nothing is fetched from Gmail, Slack, Drive, GitHub or Jira: those
> names are labels only. The only real channel is Telegram.

---

## What it does

The prototype is built to pass seven yes/no checks:

| # | Check | How the Brain meets it |
|---|---|---|
| 1 | **It speaks first** | Sends a morning brief (text + voice) and alerts without being asked. |
| 2 | **People curate the memory** | Proposed facts reach the team lead with Approve / Reject buttons. Only approved facts are used. |
| 3 | **It knows who's asking** | Every source has a visibility; the same question gets different answers for Tech and Finance. |
| 4 | **It cites** | Every answer and alert carries numbered footnotes pointing to the sources. |
| 5 | **It admits gaps** | When the approved, visible memory doesn't hold the answer: *"I don't know. I can't find this in the memory you have access to."* |
| 6 | **It only proposes** | Actions (move a task, send a message) run only when the person taps Approve. |
| 7 | **It fits the team's day** | Everything happens in a Telegram chat; no new app to open. |

These guarantees are **enforced in code, not in the prompt**: visibility is filtered before the
model is called, citations are checked against the items that were given to the model, and
action effects run only inside the approve endpoint.

---

## Architecture

```
                    ┌─────────────────────────────┐
 Telegram users ───▶│  bot/  (Telegram adapter)    │  long polling, no webhook
 (Giulia, Luca)     │  no logic of its own         │
                    └──────────────┬──────────────┘
                                   │ HTTP + X-User-Id header
                                   ▼
 ┌────────────────────┐   ┌─────────────────────────────┐    ┌──────────────────────┐
 │ frontend/          │──▶│ backend/  (FastAPI)         │───▶│ Gemini (structured   │
 │ Control room       │   │ The Brain: access rules,    │    │ JSON output)         │
 │ Vite + React       │   │ memory, watcher, brief,     │    ├──────────────────────┤
 │ /demo/* endpoints  │   │ actions                     │───▶│ ElevenLabs (voice)   │
 └────────────────────┘   └──────────────┬──────────────┘    └──────────────────────┘
                                         │
                          backend/data/seed/*.json  (read-only seed)
                          backend/data/state.json   (live state, rebuilt on every start)
```

| Piece | Folder | Stack | Role |
|---|---|---|---|
| **Backend** | `backend/` | Python 3.12, FastAPI, `google-genai`, `uv` | The Brain. All rules, data and model calls. Port `8000`. |
| **Bot** | `bot/` | Python 3.12, `httpx`, `uv` | Thin Telegram adapter: shows what the backend returns, sends back what people do. |
| **Control room** | `frontend/` | Vite, React 19, TypeScript | Read-only page shown next to Telegram during the demo: task board, simulated outbox, company memory, demo buttons. Port `5173`. Not part of the product. |
| **Seed data** | `backend/data/seed/` | JSON | 4 people, 45 sources, 17 memory items, 4 actions, 1 incoming pull request. |

There is **no database** and **no login**. Seed data is loaded and validated at startup; the live
state is kept in memory and saved to `backend/data/state.json`. Identity is the `X-User-Id`
header; the backend derives team and lead status from the people table.

### Backend modules

| File | What it does |
|---|---|
| `main.py` | FastAPI app and endpoints. Loads `.env`, enforces who may approve what. |
| `store.py` | Seed loading and validation, live state, fictional clock, rendering to API shapes. |
| `access.py` | Pure functions for the visibility and lead rules. |
| `ask.py` | Answers questions from approved, visible memory only; drops unknown ids; adds citations in code. |
| `watcher.py` | The demo script and the live watcher that checks new work against approved decisions. |
| `brief.py` | Morning brief: code selects the items, the model writes the text, a template is the fallback. |
| `actions.py` | Effects of an approved action (`update_task`, `create_task`, `send_message`). Simulated only. |
| `llm.py` | One function: prompt + Pydantic schema → parsed object (Gemini, low thinking, 25 s timeout, one retry). |
| `voice.py` | ElevenLabs text-to-speech, cached on disk by a hash of the text. |

### The people

| id | Name | Team | Lead | Title |
|---|---|---|---|---|
| `sara` | Sara Conti | sales | yes | Head of Sales |
| `giulia` | Giulia Ferri | tech | yes | Tech Lead |
| `marco` | Marco Riva | tech | no | Backend Developer |
| `luca` | Luca Moretti | finance | yes | Finance Manager |

The demo uses two Telegram accounts: one plays Giulia, the other plays Luca.

---

## How it works

### Access rules (enforced by backend code)

1. A source or approved memory item is visible only if its `visible_to` contains `"all"` or the
   person's team. Memory items inherit team and visibility from their first source.
2. Proposed and rejected memory items are visible only to the lead of the item's team.
3. Only that lead can approve or reject them (`403` otherwise, `409` if already decided).
4. Answers use approved memory only, filtered **before** the model is called.
5. An answer marked answerable must cite at least one source of a memory item given to the model;
   otherwise it becomes the fixed "I don't know" text. The same text is used whether a fact is
   missing or restricted, so the Brain never reveals that restricted information exists.
6. Action effects run only in `POST /actions/{id}/approve`, called by the action's owner.
7. The conflict check uses approved memory only.

### Answering a question

The bot sends `POST /ask`. The backend gives the model only the approved memory items the person
may see, asks for a structured JSON answer (`answerable`, `answer`, `used_memory_ids`), discards
any id it didn't provide, and builds the `[1][2]` citations itself from the sources of the items
used.

### The morning brief

"Start the day" (`POST /demo/reset`) rebuilds the state from the seed and writes one short brief
per person (about 60 words, since it is read aloud). Code picks what goes in; the model only writes
the words. If the model fails or breaks a rule (wrong markers, too long, mentions "cards"), a
template is used. The audio is prepared during the reset, and the bot sends the text followed by
the voice message.

### The watcher: active memory

Each press of **Simulate tech event** runs the next step of `backend/demo_script.json`:

1. **release `act_golive`**: the Alpilog go-live moved to 4 Dec but Giulia's task is due 9 Dec.
   Giulia gets an alert with a proposed action (move the task to 2 Dec and notify `#tech`).
2. **release `mem_pg`**: Giulia is asked whether to remember the decision "PostgreSQL over
   MongoDB for Alpilog".
3. **source `src_pr_mongo`**: Marco opens a pull request adding a MongoDB store. This step is live:
   one model call receives the new pull request and the approved decisions Giulia can see, and
   returns whether it conflicts with one of them, the exact quote, an alert text and a note to the
   author. Code then checks that the decision id was actually given, that quotes are exact
   substrings, and that texts respect word limits (falling back to templates otherwise). On a
   conflict Giulia gets an alert citing the decision and the pull request, with a proposed action
   "Ask Marco to hold …", and the memory item gets a **Caught** tag on the control room.

If the PostgreSQL decision was **not** approved, step 3 raises no alert: the memory the team
curates is exactly what the Brain uses to watch new work.

### The Telegram bot

- `/start` asks "Who are you?" and ties the chat to one person (saved in `bot/bot_state.json`).
- Every 2 seconds it polls `GET /state` for each tied chat and delivers new briefs and alerts.
  An alert and its card arrive as one message with **Approve** / **Reject** and source buttons.
- Any text is a question (`POST /ask`); tapping a source button shows the source, if visible.
- On every start it deletes the messages of the previous run from the chats, so each start is a
  clean demo.

---

## How to try it

### Requirements

- Python 3.12 and [`uv`](https://docs.astral.sh/uv/)
- Node.js 18+ and `npm`
- A Gemini API key (AI Studio, or Vertex AI with `GOOGLE_GENAI_USE_VERTEXAI=true`)
- An ElevenLabs API key and voice id (optional: without them the brief is sent as text only)
- A Telegram bot token from [@BotFather](https://t.me/BotFather), and two Telegram accounts

### 1. Configure

```bash
cp .env.example .env
```

Fill in `.env` at the project root. It is read by both the backend and the bot; values there win
over the shell, and an empty value counts as missing.

| Variable | Used by | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | backend | Model key. |
| `GOOGLE_GENAI_USE_VERTEXAI` | backend | `false` for AI Studio, `true` for Vertex AI. |
| `GEMINI_MODEL` | backend | Default `gemini-3.8-flash`. |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | backend | Voice of the morning brief. |
| `TELEGRAM_BOT_TOKEN` | bot | Token from @BotFather. |
| `BACKEND_URL` | bot | Default `http://localhost:8000`. |

### 2. Start the three programs (one terminal each)

```bash
cd backend && uv run uvicorn main:app --port 8000
```

```bash
cd bot && uv run python main.py
```

```bash
cd frontend && npm install && npm run dev
```

The control room opens at <http://localhost:5173>. API docs are at <http://localhost:8000/docs>.

### 3. Tie the Telegram accounts (first time only)

In each Telegram account, open the bot, send `/start` and pick a person: **Giulia** in one,
**Luca** in the other. Nothing else arrives until you start the day.

### 4. Run the demo

The full script with expected results is in [`DEMO.md`](DEMO.md). In short:

1. On the web page, press **Start the day**: Giulia and Luca each get a brief, as text and voice.
2. Press **Simulate tech event**: Giulia gets the go-live alert. Tap **Approve**: the task moves
   to 2 Dec and a message to `#tech` appears in "Sent messages".
3. As Giulia, ask `Why did we choose PostgreSQL for Alpilog?` → "I don't know…".
4. Press **Simulate tech event** again and **Approve** the PostgreSQL decision.
5. Ask the same question → an answer with a footnote citing the `#tech` chat.
6. Press **Simulate tech event** a third time: Marco's MongoDB pull request triggers a conflict
   alert, and the memory item shows **Caught** on the web page.
7. As Giulia, ask `What is the Alpilog contract value?` → "I don't know…".
   As Luca, ask the same → `€84,000`, citing the contract summary.

Restarting the backend and the bot starts a new demo from the seed.

### Without Telegram or keys

- **Control room on mock data**, no backend needed:
  ```bash
  cd frontend && VITE_USE_MOCK=true npm run dev
  ```
- **The API directly**, e.g. ask a question as Giulia (`-X` sets the method, `-H` adds a header,
  `-d` sends the JSON body):
  ```bash
  curl -X POST localhost:8000/ask -H 'X-User-Id: giulia' -H 'Content-Type: application/json' -d '{"question":"What is the Alpilog contract value?"}'
  ```

### Tests

```bash
cd backend && uv run pytest -q
```

The 28 backend tests run offline: `BRAIN_NO_LLM=1` and `BRAIN_NO_VOICE=1` turn off the outside
services, so they cover access rules, approvals, the demo script and the fallbacks.

```bash
python3 backend/data/seed/check_seed.py
```

Validates the seed files and prints `SEED OK`.

---

## API at a glance

Per-person endpoints need `X-User-Id: <person id>`. Errors: `401` unknown user, `403` not allowed,
`404` not found, `409` already decided, `503` outside service failed.

| Method and path | Id | What it does |
|---|---|---|
| `GET /health` | no | Liveness check. |
| `GET /people` | no | The four people. |
| `GET /state` | yes | My thread of messages (the bot polls it). |
| `POST /ask` | yes | Ask a question; returns the answer with citations. |
| `POST /memory/{id}/approve` · `/reject` | yes | Lead of the item's team only. |
| `POST /actions/{id}/approve` · `/reject` | yes | The action's owner only. Approve runs the effects. |
| `GET /sources/{id}` | yes | A source, if visible to me. |
| `GET /brief/audio` | yes | My latest brief as MP3. |
| `GET /demo/overview` | no | Everything the control room shows. |
| `POST /demo/next-event?track=tech` | no | Runs the next step of the demo script. |
| `POST /demo/reset` | no | "Start the day": restore the seed and write the briefs. |

---

## What is live and what is seeded

- **Live, with the model:** answers to questions, the morning brief, the conflict check on the
  pull request (the decision, the alert text, the note to the author).
- **Live, plain code:** access rules, citation checks, approvals and their effects.
- **Seeded, released by the demo script:** the go-live action and the PostgreSQL memory proposal.
- **Not built:** real connectors to work tools, and spotting a clash between a newly approved fact
  and an existing task. "Sent messages" is a simulated outbox.

The bot is a thin adapter, so moving the Brain to Slack or Teams means writing a new adapter over
the same API.

---

## Repository map

| Path | What it is |
|---|---|
| [`CONTRACT.md`](CONTRACT.md) | The full specification: types, endpoints, rules, scenario data, bot and page behaviour, change sets. |
| [`DEMO.md`](DEMO.md) | The demo script, used as the acceptance test. |
| [`HANDOVER.md`](HANDOVER.md) | Context, decisions and their reasons, status during the hackathon. |
| `TASKS_*.md`, `handoff/*.md` | Task lists and work logs of the agents that built each piece. |
| `backend/demo_script.json` | The steps behind the demo button. |
| `backend/data/seed/` | The fictional company data and its check script. |
