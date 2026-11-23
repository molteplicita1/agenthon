# Architecture

## The three programs

```
                    ┌─────────────────────────────┐
 Telegram users ───▶│  bot/  (Telegram adapter)   │  long polling, no webhook
 (Giulia, Luca)     │  no logic of its own        │
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
| Backend | `backend/` | Python 3.12, FastAPI, `google-genai`, `httpx`, `uv` | The Brain. Every rule, all data, every model call. Port `8000`. |
| Bot | `bot/` | Python 3.12, `httpx`, `uv` | Thin Telegram adapter: shows what the backend returns, sends back what people do. |
| Control room | `frontend/` | Vite 6, React 19, TypeScript | Read-only page beside Telegram during the demo. Not part of the product. Port `5173`. |
| Demo video | `demo-video/` | Node, Playwright, `ffmpeg` | Records the demo script on a 1920×1080 stage. Not part of the product. |

The backend is the only program with logic. The bot and the control room are clients of its
HTTP API; replacing Telegram with Slack or Teams means writing one more adapter over the same API.

## Data flow

1. **Start the day.** The control room calls `POST /demo/reset`. The backend rebuilds the state
   from the seed, writes one morning brief per person (model + template fallback) and prepares
   the brief audio (ElevenLabs, cached on disk).
2. **Delivery.** Every 2 seconds the bot calls `GET /state` for each tied chat and sends the
   briefs and alerts it has not sent yet, then the brief's voice message.
3. **Events.** Each press of *Simulate tech event* calls `POST /demo/next-event?track=tech`,
   which runs the next step of `backend/demo_script.json`: it either releases a seeded item to
   the person who must decide, or feeds a new piece of work to the watcher.
4. **Decisions.** Tapping Approve or Reject in Telegram makes the bot call
   `POST /memory/{id}/approve|reject` or `POST /actions/{id}/approve|reject`. Approving an action
   runs its effects (move a task, add a message to the simulated outbox).
5. **Questions.** Any text sent to the bot becomes `POST /ask`; the answer comes back with
   numbered citations.
6. The control room polls `GET /demo/overview` every 2 seconds and highlights what changed.

## State

- **No database.** The seed in `backend/data/seed/` is loaded and validated at startup; a broken
  seed stops the server with a list of errors.
- The live state is one dictionary in memory (`store.S`), guarded by a re-entrant lock and saved
  atomically to `backend/data/state.json` after each change. It is rebuilt from the seed on every
  start and on every reset, so each restart is a new demo.
- **A fictional clock.** "Now" starts at `2026-11-24T09:00:00` at each reset and advances in real
  time, so the seed's dates always read the same way.
- The bot keeps its own small state in `bot/bot_state.json`: which chat is tied to which person,
  which messages were already delivered, and the Telegram message ids to delete at the next start.

## Identity

There is **no login**. Every per-person request carries `X-User-Id: <person id>`; the backend
looks the person up in the people table and derives their team and lead status from it. An
unknown or missing id is a `401`.

## Design principles

- **Guarantees live in code, not in the prompt.** Visibility is filtered before the model is
  called; answers use approved memory only; citations are built by code from the items the model
  was given; action effects run only inside the approve endpoint; the watcher's verdict is checked
  in code (decision id given, quotes are exact substrings, texts within word limits).
- **The model writes words, code decides.** For the brief and the conflict alert, code picks the
  items, the citations and the action; the model only phrases the text, and a fixed template
  replaces it whenever it fails or breaks a rule.
- **Nothing happens without a person.** Memory items are proposed to the lead of their team;
  actions wait for the person they are for.
- **Simplicity first.** No database, no agent framework, no vector search, no background workers.
- **Fictional data, one real channel.** Gmail, Slack, Drive, GitHub and Jira are labels on seeded
  sources; the only outside services are Gemini, ElevenLabs and Telegram.

## What is live and what is seeded

| | |
|---|---|
| Live, with the model | Answers to questions, the morning brief, the conflict check on the pull request (decision, alert text, note to the author). |
| Live, plain code | Access rules, citation checks, approvals and their effects. |
| Seeded, released by the demo script | The go-live action and the PostgreSQL memory proposal. |
| Not built | Real connectors to work tools; spotting a clash between a newly approved fact and an existing task. "Sent messages" is a simulated outbox. |

## Key decisions

The full history with reasons is in [`plans/handover.md`](plans/handover.md) and in the change
sets at the end of [`plans/contract.md`](plans/contract.md). The ones that shaped the code:

1. **Team leads curate the memory.** The lead of the team that owns a source knows the topic and
   already has access; an unapproved fact is seen only by that lead.
2. **Telegram instead of a web chat.** A first Slack-style web chat looked like "Slack plus a
   bot" nobody would open; the Brain moved into a real Telegram bot and the web page became the
   control room.
3. **Brief and alerts are separate.** "Start the day" sends only the brief; every other message
   arrives one per press of the demo button, and an alert and its card are one Telegram message.
4. **Gemini 3.8 Flash with low thinking.** Default thinking ran into the server deadline; low
   thinking answers in about 4 seconds, with a 25-second timeout and one retry.
