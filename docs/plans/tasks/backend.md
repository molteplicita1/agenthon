# Backend tasks (Claude Code)

Read `CONTRACT.md` and `DEMO.md` in full first.
You own `backend/` (except `backend/data/seed/`), `CONTRACT.md` and `handoff/backend.md`.

## Rules

- **Simplicity first.** No database, no agent framework, no vector search, no
  background workers. If two ways work, pick the one with less code.
- Write only in the files you own. Never touch `bot/` or `frontend/`.
- `backend/data/seed/` belongs to the data agent. Read it, never write it. If the
  seed is wrong or missing something, say so in `handoff/backend.md`.
- `handoff/backend.md` is the only handoff file you write. If you change
  `CONTRACT.md`, add a line there.
- Before each task read `handoff/bot.md`, `handoff/frontend.md` and `handoff/data.md`.
- **No git commands that change the repository** (add, commit, checkout, stash,
  reset). Several agents share this folder; the humans commit.
- Never print or log API keys. Read them from the `.env` file at the project root
  (`CONTRACT.md` section 2). Do not create or edit `.env`.
- **No real connections to the team's tools.** No code that reads from or writes
  to Gmail, Slack, Google Drive, GitHub, Jira or similar. The backend calls only
  Gemini and ElevenLabs. Telegram is the bot's job, not yours.
- The rules of `CONTRACT.md` section 5 live in code, with tests.

## Setup

- Python 3.12 with `uv`. FastAPI + uvicorn on port 8000.
- Model: Gemini through the `google-genai` SDK. Check the current SDK docs for
  JSON-schema (structured) output before writing the wrapper. Build the client with
  `vertexai=True` when `GOOGLE_GENAI_USE_VERTEXAI` is `true`.

Suggested modules: `main.py` (routes), `store.py` (load, save, reset), `access.py`,
`llm.py` (one function: prompt + schema → parsed object), `ask.py`, `brief.py`,
`watcher.py`, `actions.py`, `voice.py`.

## Tasks, in order

**B0 — Skeleton (target: 30 minutes).**
Every endpoint of `CONTRACT.md` section 7 exists and returns data in the right
shape, with no model calls. Load the seed files (section 10) and validate them at
startup. The core seed arrives when `handoff/data.md` says `SEED CORE READY`; until
then build the loader and the routes. Approve and reject of memory and actions
work. `/ask` always returns the fixed "I don't know" message. `/demo/reset` restores
the seed and gives each person a brief built from a plain template (the real brief
comes in B3). Message ids are unique forever (section 6). Then append
`BACKEND SKELETON READY` to `handoff/backend.md`, with the command that starts the server.

**B1 — Access rules and tests.**
Implement section 5 rules 1, 2, 3 and 6. Pytest cases: Giulia gets `403` on
`src_doc_contract`; Marco cannot approve `mem_pg`; Luca cannot approve `act_golive`;
a proposed item is embedded only in its lead's brief; approving `act_golive` changes
the task date and adds one outbox message; rejecting an action changes nothing.

**B2 — Ask.**
Collect approved memory visible to the user. One model call returns
`{ answerable, answer, used_memory_ids }`. In code: drop unknown ids; if not
answerable or no valid id is left, return the fixed text. Build citations from the
used items. Check the questions of `DEMO.md` steps 6, 8, 9, 10, 11, 12.

**B3 — Brief.**
At reset, for each person, code selects the items: pending actions for them,
memory proposals they can decide, facts approved since yesterday that they can see.
One model call writes the text (90 words at most, plain spoken English, `[n]`
markers). If the call fails or a marker is invalid, fall back to the template.
The brief embeds the actions and memory items (section 11).

**B4 — Voice.**
`GET /brief/audio`: strip `[n]` markers, call ElevenLabs text-to-speech (check the
current docs), cache the MP3 on disk keyed by a hash of the text.

**B5 — Watcher: the active memory.**
Implement `POST /demo/next-event` exactly as `CONTRACT.md` section 12 describes: one
model call, then the checks and templates in code. This is the feature that makes
the product different, so check both cases by hand:
- with `mem_pg` approved, the pull request gives Giulia one alert with two
  citations and the "Ask Marco to hold …" action;
- with `mem_pg` still proposed or rejected, no conflict alert appears.

**B6 — Switch to the full seed.**
When `handoff/data.md` says `SEED FULL READY`, reset and check that the seed loads,
that the tests still pass and that each person's brief reads well.

**B7 — Check `DEMO.md` through the API, three times in a row, with reset in between.**
Call the endpoints in the order of the demo steps, including the counter-test for
step 13. Fix anything that is not stable. Report the result in `handoff/backend.md`.

## Done when

Every step of `DEMO.md` and the counter-test give the expected result through the
API, three runs in a row.

## Only if time is left (ask the humans first)

- Compare `gemini-3.8-flash` and `gemini-4-hydrogen` on the `DEMO.md` questions (speed and correctness).
- When a memory item is approved, check it against the open tasks and alert the
  task owner (the go-live story, which today is seeded).
- When the Brain says "I don't know", propose an action "Ask <person>".

## Change set 2 (do these now)

Read `CONTRACT.md` section 15 first, then sections 6, 7, 11 and 12, and the new
`DEMO.md`. Where they disagree with the tasks above, they win. You are the one who
keeps `CONTRACT.md` right: if you find a mistake in it, fix it and log it.

**B8 — Brief without cards.**
The brief message has `actions: []` and `memory_items: []`. Its text still mentions
what is waiting for the person and says the items will arrive one at a time; it
must not say "below" or refer to cards. During the reset, prepare the audio of
every brief (in parallel; a voice failure must not fail the reset).

**B9 — Demo script.**
`backend/demo_script.json` with the steps of section 12, in that order.
`POST /demo/next-event` runs the next step: a release step (no model call) or the
watcher step. `remaining_events`, `last_event` and the new `next_step` in the
overview follow the script.

**B10 — Caught.**
New `caught` list on memory items. The watcher adds the new source's label to the
item it conflicts with. It is reset by "Start the day".

**B10b — Conflict alert written by the model.**
In the watcher's single model call, also ask for `alert_text` and
`message_to_author` (section 12, steps 2 to 4). Check them in code and fall back to
the templates when they are unusable. The title of the action, the citations and
the decision that a conflict exists stay in code. Add a test for the fallback.

**B11 — Tests and check.**
Update the tests that the changes break. Then run `DEMO.md` (all 14 steps and the
counter-test) through the API once. Tell the humans before you start: the tied
Telegram chats will receive those messages. Write `CHANGE SET 2 READY` in
`handoff/backend.md` when the API matches the contract.
