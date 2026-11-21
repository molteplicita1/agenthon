# Handover — Company Brain (state at 15:05, Sat 21 Nov 2026)

Read this first. It tells you what the project is, what was decided and why,
what works today, and what is still open. For details, the binding documents are
`CONTRACT.md` (how everything works) and `DEMO.md` (the acceptance test).

## 1. Context

- **Event:** a one-day hackathon, track "Agentic AI for business". Two people on the
  team, about six hours in total. The demo and pitch happen today.
- **Challenge ("Company Brain"):** one tool that watches a team's work (email,
  chat, tasks, docs), keeps a shared memory that people curate, and tells each
  person what needs their attention before they ask. "A chatbot over documents
  doesn't count."
- **The jury marks seven checks, yes or no:**
  1. It speaks first (a brief or alert made on its own).
  2. People curate the memory (approve one item and reject one, live; then ask a
     question only the approved item can answer).
  3. It knows who's asking (same question as finance and as tech: one gets the
     answer, the other doesn't).
  4. It cites (every answer shows its source).
  5. It admits gaps ("I don't know").
  6. It only proposes (an action waits for approval; nothing happens before).
  7. It fits the team's day (shown where the team would meet it).
- **Judged on:** innovation, fit with the track, feasibility beyond the prototype,
  technical execution, pitch.
- **The team's guiding word is simplicity.** Prefer the option with less code.
- The humans talk in Italian. Everything in the product and in the project files
  is in English. They want plain, short explanations.

## 2. What was built

A fictional software house, **Brightloop**, with four people: Giulia Ferri (Tech
Lead), Marco Riva (developer), Luca Moretti (Finance Manager), Sara Conti (Head of
Sales). The client in the story is **Alpilog**. All data is invented.

| Piece | Folder | What it does |
|---|---|---|
| Data | `backend/data/seed/` | 45 sources (emails, chat threads, tasks, docs, pull requests), 18 memory items, 4 pending actions. |
| Backend | `backend/` | FastAPI. The Brain: access rules, memory, model calls (Gemini), voice (ElevenLabs). |
| Bot | `bot/` | A real Telegram bot. A thin adapter over the backend API, with no logic of its own. |
| Web page | `frontend/` | Vite + React. A read-only "control room" shown beside Telegram: Jira-style task board, simulated sent messages, company memory, two demo buttons. |

**The idea that sets it apart:** the memory is active. Approved decisions are not
only used to answer questions; new work is checked against them. In the demo, a
lead approves "PostgreSQL over MongoDB", then a pull request that adds MongoDB
arrives, and the Brain alerts the lead on its own. Pitch line: "a linter for
company decisions."

## 3. Decisions, in the order they were taken, with the reason

1. **Guarantee the seven checks in code, not in the prompt.** Visibility is
   filtered before the model is called; answers use approved memory only;
   citations are checked in code; actions run only inside the approve endpoint.
2. **No login.** Identity is the `X-User-Id` header; the backend derives team and
   lead status from a people table.
3. **Team leads curate the memory**, not a dedicated curator: the lead of the team
   that owns the source knows the topic and already has access. An unapproved
   fact is seen only by that lead.
4. **Gemini 3.8 Flash** (`gemini-3.8-flash`) as the model. It was confirmed still
   available; the newer Gemini 4 models cost more. The backend sends a low
   thinking level and a 25 s timeout, because default thinking timed out.
5. **All data fictional, no connection to real work tools** (Gmail, Slack, Drive,
   GitHub, Jira are labels only). The challenge says no real connection is needed.
6. **First design was a Slack-style web chat. It was dropped** because it looked
   like "Slack plus a bot" that nobody would open. The Brain now lives in a **real
   Telegram bot**, and the web page shrank to the control room.
7. **Brief and alerts were separated** after the first real test confused the
   team: "Start the day" sends only the morning brief (text, then a voice message
   automatically). Everything else arrives one message per press of "Simulate
   incoming event", following a fixed script. The page shows what the next press sends.
10. **Change set 3 (after the first full test, `CONTRACT.md` section 16).** An alert
   and its card are now one Telegram message (two were confusing and doubled the
   notifications). The demo uses only Giulia and Luca, so the script has two tracks
   and the page two buttons: "Simulate tech event" and "Simulate finance event".
   The finance alert is now "Kestrel Freight has not paid": the old #finance chat had
   Luca saying "I'll ask Sara", and the Brain then proposed the same thing.
8. **The conflict alert is written by the model** (same single call that decides
   whether there is a conflict), with a fixed template as fallback. The code still
   decides the citations, the action title and whether the conflict is valid.
9. **A "Caught" tag** on the memory item shows on the web page that a decision
   caught conflicting work.

## 4. What is live and what is seeded (be honest about this in the pitch)

- **Live, with the model:** answers to questions, the morning brief, the conflict
  on the pull request (decision, alert text, note to the author).
- **Live, plain code:** approvals and their effects on tasks and sent messages,
  access rules, citation checks.
- **Seeded and only released by the demo script:** the go-live action, the
  forgotten-promise action, the PostgreSQL and Azure memory proposals.
- **Not built:** spotting a clash between a newly approved fact and a task (the
  go-live story is seeded history); any real connector; "Sent messages" is a
  simulated outbox.

## 5. Current status

| Part | Status | Evidence |
|---|---|---|
| Data | Done | `check_seed.py` prints SEED OK. |
| Backend | Done, including change set 2 | 26 offline tests pass. The backend agent ran all 14 demo steps and the counter-test through the API once, with the real model and voice. |
| Bot | Done, including change set 2 | Tested with a human on two real Telegram accounts: steps 1, 2, 5, 7, 8 and 14 worked. |
| Web page | Done, including change set 2 | "Next: …" verified against the real backend. The "Caught" tag was verified by its agent on mock data only. |

**Not yet done by anyone:** a full run of all 14 steps on Telegram, in order, three
times in a row. Steps 3, 6 and 9 to 13 on real Telegram are unconfirmed.

All three programs were running at 15:05.

## 6. How to run

One `.env` file at the project root holds the keys (never print or commit it).
`.env.example` lists the variables.

```
cd backend  && uv run uvicorn main:app --port 8000
cd bot      && uv run python main.py
cd frontend && npm run dev          # http://localhost:5173
```

Backend tests, offline: `cd backend && uv run pytest -q`.

To try the demo: in two Telegram accounts send `/start` to the bot and pick Giulia
in one and Luca in the other, clear both chats, then follow `DEMO.md` starting
with "Start the day" on the web page.

## 7. Open items, most important first

1. **Run `DEMO.md` three times in a row on Telegram** and fix what is unstable.
   Read the model-written texts each time (brief, conflict alert): they vary.
2. **Commit.** The last commit is from 13:38; change set 2 is uncommitted
   (23 changed paths). `git add -A && git commit`.
3. **Switch to the Google Cloud event credits:** put a Vertex AI key in
   `GEMINI_API_KEY`, set `GOOGLE_GENAI_USE_VERTEXAI=true`, restart the backend, run
   the demo once. Today the backend uses an AI Studio key, which does not spend
   the event credits. This path is untested.
4. **Fallbacks for the stage:** a recorded video of the demo and a phone hotspot.
   The demo needs the network (Telegram, Gemini).
5. **Pitch and slides.** Not started. Points agreed so far: "a linter for company
   decisions"; the channel is a thin adapter, so Slack or Teams is the next step;
   leads curate, the Brain only proposes.

Known rough edges:

- "Start the day" takes 6 to 8 seconds (four briefs plus audio), once 18 seconds
  on a slow model call.
- Briefs are capped at about 60 words so the voice message stays near 25 seconds.
- A chat tied before the latest bot change may receive one stray brief when the
  bot restarts. A new `/start` fixes it.

## 8. Rules the agents work under

- Each agent writes only in its own folder and its own log in `handoff/`
  (`backend.md`, `bot.md`, `frontend.md`, `data.md`). The backend agent owns `CONTRACT.md`.
- **No git commands that change the repository.** The humans commit. One agent
  broke this once (it switched branch and the seed vanished from disk for a while).
- No code that connects to real work tools. Outside services: Gemini, ElevenLabs,
  Telegram only.
- Agents do not watch files while idle: a human relays "X is ready" messages.
- Where an older task list and `CONTRACT.md` section 15 ("Change set 2") disagree,
  section 15 wins.

## 9. File map

| File | What it is |
|---|---|
| `CONTRACT.md` | Types, endpoints, rules, pinned scenario data, bot and web page behaviour. Section 15 lists the latest changes. |
| `DEMO.md` | The 14 demo steps with expected results, plus the counter-test. |
| `TASKS_BACKEND.md`, `TASKS_BOT.md`, `TASKS_FRONTEND.md`, `TASKS_DATA.md` | Task lists. All tasks in them are done. |
| `handoff/*.md` | What each agent did, verified and left open. The most detailed record of the build. |
| `backend/demo_script.json` | The steps behind the two buttons, one list per track (`tech`, `finance`). |
| `.env.example` | The variables the `.env` file needs. |
