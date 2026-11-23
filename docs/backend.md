# Backend: the Brain

A FastAPI app in `backend/`, started with `uv run uvicorn main:app --port 8000`. All business
rules, data and model calls live here. The endpoints are listed in the [API reference](api.md).

## Modules

| File | Responsibility |
|---|---|
| [`main.py`](../backend/main.py) | Loads `.env`, builds the FastAPI app (CORS for `localhost:5173`), resolves the caller from `X-User-Id`, enforces who may decide what, maps model and voice failures to `503`. |
| [`store.py`](../backend/store.py) | Seed loading and validation, the live state and its lock, the fictional clock, ids, lookups, rendering to API shapes. |
| [`access.py`](../backend/access.py) | Pure functions for visibility and lead rules. No state. |
| [`ask.py`](../backend/ask.py) | `POST /ask`: answers from approved, visible memory only. |
| [`brief.py`](../backend/brief.py) | The morning brief: code selects, the model writes, a template is the fallback. |
| [`watcher.py`](../backend/watcher.py) | `POST /demo/next-event`: the demo script and the watcher that checks new work against approved decisions. |
| [`actions.py`](../backend/actions.py) | Effects of an approved action. They change the state only; nothing real is sent. |
| [`llm.py`](../backend/llm.py) | One function: prompt + Pydantic schema → parsed object, via Gemini structured output. |
| [`voice.py`](../backend/voice.py) | ElevenLabs text-to-speech, cached on disk by a hash of the text. |
| [`demo_script.json`](../backend/demo_script.json) | The steps behind the demo button. |

## Access rules

Enforced in code and covered by the tests in `backend/tests/`.

1. A source or approved memory item is visible only if its `visible_to` contains `"all"` or the
   person's team. Memory items inherit team and visibility from their first cited source.
2. Proposed and rejected memory items are visible only to the lead of the item's team.
3. Only that lead can approve or reject them (`403` otherwise, `409` if already decided).
4. Answers use approved memory only, filtered **before** the model is called.
5. An answer marked answerable must cite at least one memory item given to the model; otherwise
   it becomes the fixed "I don't know" text. The same text is used whether a fact is missing or
   restricted, so the Brain never reveals that restricted information exists.
6. Action effects run only in `POST /actions/{id}/approve`, called by the person the action is for.
7. The watcher compares new work with approved memory only.

The fixed text is `store.IDK`: *"I don't know. I can't find this in the memory you have access to."*

## Answering a question (`ask.py`)

1. Take the approved memory items the person may see. If there are none, answer `IDK` without
   calling the model.
2. One model call with the items (`id: statement`) and the question. The schema is
   `{answerable, answer, used_memory_ids}`; the prompt forbids guessing and outside knowledge.
3. Drop any id that was not given to the model; strip any bracket the model wrote.
4. If the answer is not answerable, uses no valid id or is empty → `IDK`.
5. Otherwise collect the citations of the used items (one per source, in order) and append the
   markers `[1][2]…` before the final punctuation.

A model failure returns `503` and the question is not stored.

## The morning brief (`brief.py`)

`POST /demo/reset` calls `make_briefs` on a fresh state.

- **Selection, in code.** A brief holds only approved facts the person can see, decided since
  yesterday, whose sources the demo script will not bring up later as alerts
  (`script_sources`). Actions and memory proposals are left out: each arrives later as its own
  alert, so the brief never repeats them.
- **Writing, by the model.** One call per person, in parallel (four threads). The prompt asks for
  spoken English of about 60 words, starting with "Good morning, {first name}.", with each item's
  `[n]` markers placed exactly as given. A draft over 70 words gets one more call to shorten it.
- **Checks, in code.** The template replaces the text if it is empty, uses no marker or a marker
  not given, contains other brackets, is over 70 spoken words, or mentions "below" or "cards".
  With nothing to say, the template is used directly.
- **Voice.** The audio of each brief is generated during the reset so that `GET /brief/audio`
  answers at once. A voice failure never fails the reset.

## The demo script and the watcher (`watcher.py`)

`demo_script.json` holds one list of steps per track (`tech`, `finance`); only `tech` has steps
and a button. Each press runs the next step of the track:

| Step | Kind | What happens |
|---|---|---|
| 1 | `release act_golive` | The seeded action reaches Giulia as an alert: the Alpilog go-live moved to 4 Dec but the API migration task is due 9 Dec. Approve moves the task to 2 Dec and messages `#tech`. |
| 2 | `release mem_pg` | The seeded proposal "PostgreSQL over MongoDB for Alpilog" reaches Giulia, the tech lead: "Should I remember it?" |
| 3 | `source src_pr_mongo` | Marco's pull request adding a MongoDB store goes to the watcher. |

A **release** step needs no model call: it adds an alert to the decider's thread (the action's
owner, or the lead of the memory item's team) with the item embedded.

A **source** step is the watcher:

1. Take the incoming source and the approved memory the team lead can see.
2. One model call, **outside the lock**, returning a `Verdict`: the id of one conflicting
   decision (or null), the exact quote from the new work, an alert text (≤ 50 words), a note to
   the author (≤ 40 words) and at most two new facts worth remembering.
3. Back under the lock, skip the result if a reset or another press happened meanwhile.
4. Move the source from `incoming` to `sources` and make it the `last_event`.
5. **Conflict**, valid only if the decision id was given to the model: the lead gets an alert
   citing the decision and the new work (`[1][2]`), with a new action "Ask {author} to hold …"
   whose effect is a message to the author. The decision gets a **Caught** tag. Model texts are
   used only if non-empty, within their limit (+20%) and without `[n]` markers; templates otherwise.
6. **No conflict but new facts** (each quote must be an exact substring of the body): they become
   proposed memory items for the lead.

If the PostgreSQL decision was not approved, step 3 raises no alert: the memory the team curates
is exactly what the Brain uses to watch new work. A model failure returns `503` and the step stays
in the queue, so the next press retries it.

## Actions (`actions.py`)

Three effect types, run in order when an action is approved:

| Effect | Change |
|---|---|
| `update_task` | Applies `changes` (e.g. `due_date`) to a task source. |
| `create_task` | Adds a task source assigned to a person, visible to that person's team. |
| `send_message` | Adds a message to the simulated outbox (`to` is a person id or a channel such as `#tech`). |

## Model calls (`llm.py`)

`ask_json(prompt, schema)` calls Gemini with `response_mime_type: application/json`, the
Pydantic `response_schema`, temperature 0 and `thinking_level` low (`GEMINI_THINKING` overrides
it). The client has a 25-second timeout and the call is retried once. Any failure raises
`LLMError`. `BRAIN_NO_LLM=1` disables the model, which the tests use.

## Voice (`voice.py`)

`speak(text)` removes the `[n]` markers, then returns the cached MP3 in `backend/data/audio/` if
there is one, or calls ElevenLabs (`eleven_multilingual_v2` by default, `ELEVENLABS_MODEL`
overrides it) and caches the result. Missing keys or an ElevenLabs error raise `VoiceError`
(`503` on the endpoint). `BRAIN_NO_VOICE=1` disables the call.

## Seed validation (`store.validate`)

At startup the server refuses to run if: the people are not exactly `sara`, `giulia`, `marco`,
`luca`; an id is malformed (`^[a-z0-9_]{1,40}$`) or duplicated; a source has a bad type, team or
`visible_to`; a task lacks `assignee`, `due_date` or `status`; a citation points to an unknown
source or quotes text that is not in its body; a memory item's team or visibility differ from its
first source; an action is for an unknown person or updates an unknown task; the demo script has
other tracks than `tech` and `finance` or a step that cannot be run.
