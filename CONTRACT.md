# Company Brain — Contract

Single source of truth shared by the four agents (backend, bot, frontend, data).

- **Owner: backend agent.** The other agents read this file and never edit it.
- Any change to this file must be logged in `handoff/backend.md`.
- Everything user-facing (bot messages, web page, data) is in **English**.
- **Simplicity first.** If two ways work, pick the one with less code.

## 1. What we are building

A working prototype of "Company Brain" for a fictional software house, **Brightloop** (Turin).
The Brain watches the team's work (email, chat, tasks, docs, pull requests), keeps a
shared memory that team leads approve or reject, and tells each person what needs
their attention.

**Where people meet it: Telegram.** The Brain is a real Telegram bot. It sends the
morning brief and the alerts, answers questions, and shows Approve / Reject buttons.
Nobody has to open a new app.

**What makes it different: the memory is active.** Approved memory is not only used
to answer questions. Every new piece of work is checked against it, and the Brain
speaks up when work goes against a decision the team approved (section 12).
In one line: a linter for company decisions.

Three pieces:

| Piece | What it is | Folder |
|---|---|---|
| Backend | The Brain: data, rules, model calls. | `backend/` |
| Bot | A thin Telegram adapter over the backend API. No logic of its own. | `bot/` |
| Web page | A "control room" for the demo: the simulated task board (Jira-style), the simulated sent messages, the company memory, the demo buttons. Not part of the product. | `frontend/` |

The demo must pass the seven checks in `DEMO.md`. That file is the acceptance test.

### Fictional data, one real channel

- Every email, chat thread, task, document and pull request is **invented** and
  lives in the JSON files of `backend/data/seed/`. That folder is the only data source.
- **Nothing is fetched** from Gmail, Slack, Google Drive, GitHub, Jira or any other
  platform. No connector, no OAuth, no API client, no scraping, no webhook for them.
  Those names are only labels that say which tool a source type *would* come from.
- Approved actions are **simulated**: they change `state.json` only. No real email
  is sent, no real task or repository is touched. "Sent messages" on the web page
  is a simulated outbox.
- **The only real channel is the Telegram bot**, used to talk with the people in
  the demo. Only fictional text goes through it.
- Outside services called: Gemini (model), ElevenLabs (voice), Telegram (bot). Nothing else.
- No real companies, people, email addresses or documents appear anywhere.

## 2. Layout, ports, configuration

```
agenthon/
  CONTRACT.md  DEMO.md  .env  .env.example
  TASKS_BACKEND.md  TASKS_BOT.md  TASKS_FRONTEND.md  TASKS_DATA.md
  handoff/            backend.md  bot.md  frontend.md  data.md   (one log per agent)
  backend/            FastAPI, Python 3.12, uv      → http://localhost:8000
  backend/data/seed/  synthetic data (owned by the data agent)
  bot/                Telegram bot, Python 3.12, uv (no port: it polls)
  frontend/           Vite + React + TypeScript     → http://localhost:5173
```

Four agents work in parallel. Each one writes only in its own folder and its own handoff log.

- No database. Seed data in `backend/data/seed/`, live state in `backend/data/state.json`.
- Backend enables CORS for `http://localhost:5173`.
- The web page reads the API base URL from `VITE_API_URL` (default `http://localhost:8000`). It needs no keys.
- The bot reaches Telegram by long polling (`getUpdates`). No webhook, no public URL.

**One `.env` file at the project root**, read by the backend and by the bot.
Values in `.env` win over variables already set in the shell.
An empty value in `.env` counts as missing.

| Variable | Used by | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | backend | Model key. If missing in `.env`, the one already exported in the user's shell is used. |
| `GOOGLE_GENAI_USE_VERTEXAI` | backend | `false` (default) for an AI Studio key, `true` for a Vertex AI key. |
| `GEMINI_MODEL` | backend | Default `gemini-3.8-flash`. |
| `ELEVENLABS_API_KEY` | backend | Voice. If missing, `GET /brief/audio` returns `503`. |
| `ELEVENLABS_VOICE_ID` | backend | Which voice reads the brief. |
| `TELEGRAM_BOT_TOKEN` | bot | Token from @BotFather. |
| `BACKEND_URL` | bot | Default `http://localhost:8000`. |

## 3. Identity (no login)

- Per-person endpoints need the header `X-User-Id: giulia`. Missing or unknown id → `401`.
  The backend looks the person up and derives team and lead status. No client ever sends a role.
- **The bot** ties each Telegram account to one of the four people (section 13) and
  sends that person's id.
- **The web page** has no identity. It uses only the `/demo/*` endpoints, which show everything.

## 4. People (fixed)

| id | name | team | is_lead | title |
|---|---|---|---|---|
| `sara` | Sara Conti | sales | true | Head of Sales |
| `giulia` | Giulia Ferri | tech | true | Tech Lead |
| `marco` | Marco Riva | tech | false | Backend Developer |
| `luca` | Luca Moretti | finance | true | Finance Manager |

Client company in the story: **Alpilog** (logistics). Contact: Elisa Brandt, Project Manager.

Fictional "now" at reset: **Tuesday 24 Nov 2026, 09:00**. It advances with real time after reset.

## 5. Rules enforced by backend code (never by the prompt)

1. **Visibility.** Every source has `visible_to` (`"all"` or a list of teams).
   A memory item inherits `team` and `visible_to` from its source.
   A person sees a source or an approved memory item only if `visible_to`
   contains `"all"` or their team.
2. **Proposed and rejected memory items** are visible only to the lead of the item's `team`.
3. **Only the lead of the item's `team`** can approve or reject it. Others → `403`.
4. **Answers use approved memory only**, filtered by rule 1 *before* the model is called.
5. **Every answer with `answerable: true` has at least one citation**, and every
   citation points to a source of a memory item that was given to the model.
   Otherwise the answer is replaced by the fixed "I don't know" text (section 8).
6. **Actions do nothing until approved.** Effects run only inside
   `POST /actions/{id}/approve`, and only the action's `for_user` can call it.
7. **An unapproved fact never reaches anyone except the lead who must review it.**
8. **The conflict check uses approved memory only.** The memory item named by the
   model must be one that was given to it, otherwise there is no conflict.
   If the PostgreSQL decision is not approved, the pull request raises no alert.

The `/demo/*` endpoints skip rules 1 and 2 on purpose: they feed the control room.

## 6. Types

Timestamps are local ISO strings without timezone: `"2026-11-23T16:40:00"`. Dates: `"2026-12-09"`.

Ids use only `a-z`, `0-9` and `_`, and are at most 40 characters (they travel inside
Telegram buttons). Message ids are never reused, not even after a reset.

```ts
type Team = "sales" | "tech" | "finance";
type Visibility = Team | "all";

interface Person {
  id: string; name: string; team: Team; is_lead: boolean; title: string;
}

interface Source {
  id: string;                    // "src_…" or "task_…"
  type: "email" | "chat" | "doc" | "task" | "pr";
  title: string;                 // email subject, channel name, doc title, task title, PR title
  author: string;                // display name
  timestamp: string;
  body: string;                  // chat: one short thread, one line per message ("Marco: …")
  team: Team;                    // owning team
  visible_to: Visibility[];
  // only when type === "task":
  assignee?: string;             // person id
  due_date?: string;
  status?: "todo" | "in_progress" | "done";
}

interface Citation {
  n: number;                     // 1-based; matches "[n]" markers in text
  source_id: string;
  type: Source["type"];
  label: string;                 // "Email · Elisa Brandt (Alpilog) · Mon 23 Nov 16:40"
  quote: string | null;          // exact excerpt of the source body, or null
}

interface MemoryItem {
  id: string;                    // "mem_…"
  statement: string;
  team: Team;
  visible_to: Visibility[];
  status: "proposed" | "approved" | "rejected";
  citations: Citation[];
  created_at: string;
  decided_by: string | null;     // person id
  decided_at: string | null;
  can_decide: boolean;           // computed for the current user; false in the overview
}

type Effect =
  | { type: "update_task"; task_id: string; changes: { due_date?: string; status?: string } }
  | { type: "create_task"; title: string; assignee: string; due_date: string }
  | { type: "send_message"; to: string; text: string };   // to: "#tech" or a person id

interface Action {
  id: string;                    // "act_…"
  title: string;                 // one line, imperative
  reason: string;                // why the Brain proposes it
  for_user: string;              // person id who must approve
  status: "pending" | "approved" | "rejected";
  effects: Effect[];
  citations: Citation[];
  created_at: string;
  decided_at: string | null;
}

interface Message {
  id: string;                    // "msg_…", unique forever
  from: "brain" | "user";
  kind: "brief" | "alert" | "question" | "answer";
  text: string;                  // may contain [1], [2] markers
  answerable: boolean | null;    // only for kind "answer", else null
  citations: Citation[];
  actions: Action[];             // embedded with their current status
  memory_items: MemoryItem[];    // embedded with their current status
  created_at: string;
}

interface OutboxMessage {
  id: string; to: string; text: string; sent_at: string; action_id: string;
}

interface State {                // what one person sees; used by the bot
  me: Person;
  now: string;
  thread: Message[];             // my conversation with the Brain, oldest first
}

interface Overview {             // everything; used by the web page
  now: string;
  tasks: Source[];               // all sources of type "task"
  outbox: OutboxMessage[];
  memory: MemoryItem[];          // all items, any status
  last_event: Source | null;     // last source injected by /demo/next-event
  remaining_events: number;
}
```

The five source types stand for the tools a software house already uses.
They are labels only; the data is invented (section 1).

| type | Label shown | Tool it would come from |
|---|---|---|
| `email` | Email | Gmail |
| `chat` | Chat | Slack (channels #tech, #sales, #finance, #random) |
| `task` | Task | A Jira-style board |
| `doc` | Doc | Google Drive |
| `pr` | Pull request | GitHub |

## 7. Endpoints

Errors use FastAPI's default shape: `{ "detail": "human readable message" }`.
Codes: `401` unknown user · `403` not allowed · `404` not found · `409` already decided · `503` external service failed.

"Id" in the table means the `X-User-Id` header is required.

| Method and path | Id | Body | Returns | Notes |
|---|---|---|---|---|
| `GET /health` | no | – | `{ "ok": true }` | |
| `GET /people` | no | – | `Person[]` | |
| `GET /state` | yes | – | `State` | The bot polls this every 2 s. Must be fast: no model calls. |
| `POST /ask` | yes | `{ "question": string }` | `Message` (the answer) | Appends question and answer to my thread. Takes 2–6 s. |
| `POST /memory/{id}/approve` | yes | – | `MemoryItem` | Lead of the item's team only. |
| `POST /memory/{id}/reject` | yes | – | `MemoryItem` | Same permission. |
| `POST /actions/{id}/approve` | yes | – | `Action` | `for_user` only. Runs the effects, then returns. |
| `POST /actions/{id}/reject` | yes | – | `Action` | `for_user` only. Nothing runs. |
| `GET /sources/{id}` | yes | – | `Source` | `403` if not visible to me. Works for task ids too. |
| `GET /brief/audio` | yes | – | `audio/mpeg` | My latest brief, spoken. Cached on disk. `503` if voice is not configured. |
| `GET /demo/overview` | no | – | `Overview` | The web page polls this every 2 s. No model calls. |
| `POST /demo/next-event` | no | – | `{ "event": Source \| null, "remaining": number }` | Injects the next scripted event and runs the watcher (section 12). Returns when done (2–6 s). `event` is `null` when the queue is empty. |
| `POST /demo/reset` | no | – | `{ "ok": true }` | "Start the day": restores the seed and writes a fresh morning brief for every person (section 11). Returns when done. |

Example — `POST /ask` as `giulia`, after the PostgreSQL item is approved:

```json
{
  "id": "msg_8f3a1c",
  "from": "brain",
  "kind": "answer",
  "text": "PostgreSQL was chosen over MongoDB because Alpilog's reporting needs joins across shipments and invoices [1].",
  "answerable": true,
  "citations": [
    {
      "n": 1,
      "source_id": "src_chat_pg",
      "type": "chat",
      "label": "Chat · #tech · Mon 23 Nov 10:15",
      "quote": "reporting needs joins across shipments and invoices"
    }
  ],
  "actions": [],
  "memory_items": [],
  "created_at": "2026-11-24T09:04:10"
}
```

Example — an action waiting for approval:

```json
{
  "id": "act_golive",
  "title": "Move 'Alpilog – API migration' to 2 Dec and notify #tech",
  "reason": "Alpilog go-live moved to 4 Dec, but this task is due 9 Dec.",
  "for_user": "giulia",
  "status": "pending",
  "effects": [
    { "type": "update_task", "task_id": "task_api_migration", "changes": { "due_date": "2026-12-02" } },
    { "type": "send_message", "to": "#tech", "text": "Heads-up: Alpilog go-live moved to 4 Dec. API migration is now due 2 Dec." }
  ],
  "citations": [
    { "n": 1, "source_id": "src_email_golive", "type": "email", "label": "Email · Elisa Brandt (Alpilog) · Mon 23 Nov 16:40", "quote": "bring the go-live forward to 4 December" },
    { "n": 2, "source_id": "task_api_migration", "type": "task", "label": "Task · Alpilog – API migration · due 9 Dec", "quote": null }
  ],
  "created_at": "2026-11-23T17:06:00",
  "decided_at": null
}
```

## 8. Fixed strings

- No answer available (not in data, not approved, or not visible):
  `I don't know. I can't find this in the memory you have access to.`
  The response has `answerable: false` and `citations: []`.
- The same text is used whether the fact does not exist or the person may not see it,
  so the Brain never reveals that restricted information exists.

## 9. Scenario data that must exist in the seed (ids are pinned)

The seed needs about 45 sources in total so the company looks alive, but these
items are required exactly, because `DEMO.md` depends on them.

| id | What | team | visible_to |
|---|---|---|---|
| `src_email_golive` | Email, Mon 23 Nov 16:40, Elisa Brandt (Alpilog) → Sara: go-live moves from 11 Dec to **4 Dec**. | sales | all |
| `mem_golive` | "Alpilog go-live moved from 11 Dec to 4 Dec 2026." **Approved** by `sara`, Mon 23 Nov 17:05. | sales | all |
| `task_api_migration` | Task "Alpilog – API migration", assignee `giulia`, due **9 Dec**, in progress. | tech | all |
| `act_golive` | Pending action for `giulia` (see example in section 7). | – | – |
| `src_chat_key` | Chat #tech, Mon 23 Nov 11:12, Marco: he will rotate the staging API key by Friday. No task exists for it. | tech | tech |
| `act_key` | Pending action for `giulia`: create task "Rotate staging API key", assignee `marco`, due 27 Nov. | – | – |
| `src_chat_pg` | Chat #tech, Mon 23 Nov 10:15, Giulia and Marco agree on PostgreSQL over MongoDB for Alpilog because reporting needs joins across shipments and invoices. | tech | tech |
| `mem_pg` | "For Alpilog we chose PostgreSQL over MongoDB because reporting needs joins across shipments and invoices." **Proposed.** | tech | tech |
| `src_chat_azure` | Chat #random, Mon 23 Nov 13:30, Marco jokes that the company will move from AWS to Azure next year. | tech | all |
| `mem_azure` | "Brightloop will migrate from AWS to Azure in 2027." **Proposed.** | tech | all |
| `src_doc_contract` | Doc "Alpilog – contract summary 2026": value **€84,000**, three milestones, 30-day payment terms. | finance | finance |
| `mem_contract` | "The Alpilog contract for 2026 is worth €84,000, invoiced in three milestones." **Approved** by `luca`. | finance | finance |
| `src_pr_mongo` | **The only item of `incoming.json`.** Pull request "Add MongoDB store for Alpilog reports", author Marco Riva, open, reviewer Giulia Ferri. The body says it adds a MongoDB collection for pre-aggregated shipment and invoice reports. | tech | tech |

Nothing in the seed may mention a parental leave policy (used for the "I don't know" check).
Apart from `src_chat_pg` and `src_pr_mongo`, nothing in the seed may mention MongoDB.

Giulia's brief after reset must cover, with citations: the go-live clash (`act_golive`),
the forgotten promise (`act_key`), and the two memory proposals waiting for her (`mem_pg`, `mem_azure`).

## 10. Seed files (written by the data agent, loaded by the backend)

All in `backend/data/seed/`. The backend validates them at startup and fails loudly.

| File | Content |
|---|---|
| `people.json` | `Person[]` — exactly the four people of section 4. |
| `sources.json` | `Source[]` — all five types, tasks included. |
| `memory.json` | `StoredMemoryItem[]` |
| `actions.json` | `StoredAction[]` |
| `incoming.json` | `Source[]` — the queue for `POST /demo/next-event`. One item: `src_pr_mongo`. Its timestamp is replaced by the fictional "now" when it is injected. |

Stored shapes differ from the API shapes only in how evidence is kept
(the backend builds `citations` and `can_decide` when it answers):

```ts
interface Cite { source_id: string; quote: string | null; }

interface StoredMemoryItem {
  id: string; statement: string;
  team: Team; visible_to: Visibility[];
  status: "proposed" | "approved" | "rejected";
  cites: Cite[];                 // at least one
  created_at: string; decided_by: string | null; decided_at: string | null;
}

interface StoredAction {
  id: string; title: string; reason: string; for_user: string;
  status: "pending" | "approved" | "rejected";
  effects: Effect[];
  cites: Cite[];
  created_at: string; decided_at: string | null;
}
```

Rules every seed file must respect:

1. Every `quote` is an exact substring of the body of its source.
2. A memory item has the same `team` and `visible_to` as its first source.
3. `visible_to` is `["all"]` or a list that contains the item's `team`.
4. Every id referenced anywhere exists. Ids are unique and follow the id rule of section 6.
5. No timestamp is later than Tue 24 Nov 2026 09:00, except in `incoming.json`.
6. Fictional names only. No real companies, people or email domains.

## 11. How the Brain reaches people

**One channel: a direct chat with the Brain bot on Telegram.** No email, no web chat.

The Brain starts a conversation in two ways only:

| | `brief` | `alert` |
|---|---|---|
| Triggered by | The start of the day | An event |
| About | Everything waiting for the person, plus what changed since yesterday | One thing, right when it happens |
| Created when | `POST /demo/reset` ("Start the day") | The watcher handles a new source (section 12) |
| Spoken version | Yes (`GET /brief/audio`) | No |

**After a reset each person's thread holds exactly one message: the brief.**
It embeds everything waiting for that person: the pending actions where they are
`for_user`, and the proposed memory items they can decide.

**Where things are approved:** on Telegram, with the Approve / Reject buttons under
each item. Every pending item appears once: in the brief if it comes from the seed,
in the alert if the watcher created it live.

## 12. Active memory: the watcher

`POST /demo/next-event` is the one place where the Brain reacts live to new work.
It does these steps in order, then returns:

1. Take the next source from the queue, set its timestamp to the fictional "now",
   add it to the sources.
2. Make **one** model call. Input: the new source, plus the approved memory items
   that the lead of the source's team may see. Output:

   ```ts
   {
     conflict_memory_id: string | null;   // approved item this source goes against
     conflict_quote: string | null;       // exact words of the new source that show it
     facts: { statement: string; quote: string }[];   // at most 2 things worth remembering
   }
   ```
3. Check in code:
   - `conflict_memory_id` must be one of the items given to the model, else treat it as `null`.
   - A quote that is not an exact substring of the source body becomes `null`
     (for the conflict) or drops the fact.
4. **If there is a conflict**, add one `alert` to the thread of the lead of the
   source's team. Everything is built from templates, no second model call:
   - Text: `<author>'s <type label> "<title>" goes against a decision the team approved: <statement> [1][2]`
   - Citations: `[1]` the source of the memory item, `[2]` the new source.
   - If the author is one of the four people and is not that lead, embed one
     pending action for the lead: title `Ask <first name> to hold "<title>"`, with one
     `send_message` effect to the author:
     `Your <type label> "<title>" goes against a team decision: <statement> Can we talk before it is merged?`
   - Facts from this source are discarded.
5. **Otherwise**, for each valid fact create a proposed memory item (`team` and
   `visible_to` copied from the source) and add one `alert` to the lead's thread
   that embeds them.

**What is live and what is seeded.** Live, through real code: answers, the morning
brief, approvals and their effects, memory proposals from a new source, and the
conflict alert above. Seeded as yesterday's history by the data agent: the two
memory proposals, the forgotten-promise action and the go-live action. Spotting a
clash between a newly approved fact and a task (the go-live story) is not built.

## 13. The Telegram bot

A thin adapter: it shows what the backend returns and sends back what people do.
It holds no rules and makes no model calls.

**Who is who.** On `/start` the bot asks "Who are you?" with one button per person
(from `GET /people`). The choice ties that Telegram chat to that person until the
next `/start`. The bot keeps this in `bot/bot_state.json`.

**Delivering what the Brain says.** Every 2 seconds, for each tied chat, the bot
calls `GET /state` and sends every thread message with `from: "brain"` and kind
`brief` or `alert` that it has not sent to that chat yet (it remembers message ids).
A chat that has just been tied receives what is already in the thread.

One Brain message becomes several Telegram messages:

| What | Telegram message | Buttons |
|---|---|---|
| `brief` | "Morning brief", the text, then the sources as footnotes | `Listen to the brief`, one button per source |
| `alert` | "Alert", the text, footnotes | one button per source |
| each embedded action | title, reason, effects in plain words, footnotes | `Approve`, `Reject` (only if `pending`), sources |
| each embedded memory item | "Should I remember this?", the statement, footnotes | `Approve`, `Reject` (only if `proposed` and `can_decide`), sources |
| answer to a question | the text, footnotes | one button per source |

A footnote line looks like: `[1] Email · Elisa Brandt (Alpilog) · Mon 23 Nov 16:40 — "bring the go-live forward to 4 December"`.

**What people do.**

| The person… | The bot… |
|---|---|
| sends any text | shows "typing", calls `POST /ask`, replies with the answer |
| taps `Approve` / `Reject` | calls the matching endpoint, then edits that message: buttons removed, "Approved" or "Rejected" added. On `403` or `409` it shows the error and changes nothing. |
| taps a source button | calls `GET /sources/{id}` and sends type, title, author, time and body. On `403`: "You don't have access to this source." |
| taps `Listen to the brief` | calls `GET /brief/audio` and sends it as a voice message |

Button payloads (Telegram allows 64 bytes): `who:<person_id>`, `act:approve:<id>`,
`act:reject:<id>`, `mem:approve:<id>`, `mem:reject:<id>`, `src:<source_id>`, `brief:audio`.

## 14. The web page (control room)

One page, shown next to the Telegram window during the demo. It is the audience's
window on the simulated tools; it is not where people work.

It polls `GET /demo/overview` every 2 seconds and shows:

- **Task board**, Jira-style: one column per status, a card per task with title,
  assignee and due date.
- **Sent messages**: the simulated outbox. Empty state: "Nothing has been sent."
- **Company memory**: every memory item with its status (Proposed / Approved /
  Rejected), who can see it, and who decided.
- **Demo controls**: `Start the day` (`POST /demo/reset`) and
  `Simulate incoming event` (`POST /demo/next-event`), plus a card with the last event.

Anything that changes is highlighted for a moment, so the audience sees the effect
of a tap on Telegram.
