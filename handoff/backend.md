# Handoff log — backend agent

Only the backend agent writes in this file. The other agents read it.

- Append at the bottom. Never edit or delete older lines.
- One line per message. To address another agent, start the line with `@BACKEND`, `@BOT`, `@FRONTEND` or `@DATA`.
- Write `BACKEND SKELETON READY` here when the bot and the web page can switch to the real API.

---
BACKEND SKELETON READY — start: `cd backend && uv sync && uv run uvicorn main:app --port 8000` (http://localhost:8000). Every endpoint of CONTRACT section 7 answers in the contract shape. Approve/reject work and run effects. /ask still always says "I don't know" and briefs use a plain template until B2/B3 land; /brief/audio returns 503 until B4.
@BOT @FRONTEND state lives in backend/data/state.json; it survives restarts. Press Start the day (POST /demo/reset) to get a clean day. Message ids are "msg_" + 12 hex chars, never reused.
B1 done — rules 1, 2, 3, 6 in backend/access.py and main.py; tests: `cd backend && uv run pytest -q` (17 tests, no outside calls: BRAIN_NO_LLM=1 and a fake model).
B2 done — /ask: approved memory filtered by visibility before one Gemini call; unknown ids dropped; no valid id → the fixed "I don't know" text. Markers [n] are added by code. Model failure → 503 (question is not stored).
B3 done — reset writes one brief per person (one model call each, in parallel, ~4 s total). Bad marker, empty text, over 110 words or model failure → plain template. The brief embeds pending actions for_user and proposals the person can decide.
B4 done — /brief/audio: ElevenLabs TTS (eleven_multilingual_v2, mp3), cached in backend/data/audio/ by text hash. 503 if key/voice missing or ElevenLabs fails; 404 if the person has no brief yet.
B5 done — /demo/next-event per CONTRACT section 12. Checked by hand: mem_pg approved → one alert to giulia, citations [src_chat_pg, src_pr_mongo], action "Ask Marco to hold …" whose approval adds an outbox message to marco; mem_pg proposed or rejected → no alert. Model failure → 503 and the event stays in the queue.
Model note: gemini-3.8-flash with default thinking hit 504 DEADLINE_EXCEEDED after ~2 min on the brief prompt. The backend now sends thinking_level=low (override with GEMINI_THINKING) and a 25 s timeout with one retry.
DEMO.md steps 1-13 and the counter-test pass through the API (one run so far; B7's three runs not done yet).
@DATA backend/data/seed/ disappeared from disk at 13:03 (the checkout moved from branch data/seed to main). The backend fails loudly at startup without it. Until it is back, the server can read a copy with BRAIN_SEED_DIR=<folder>.
@BOT alerts have kind "alert"; a conflict alert embeds one action, a facts alert embeds memory_items. Answers are not added to /state deliveries (kind "answer"), as the contract says.
@DATA seed is back: backend/data/seed/ is on main (commit 6c56829) and on disk, identical to the commit, SEED OK. The backend runs on it again (no BRAIN_SEED_DIR); tests and DEMO.md steps 1-13 + counter-test pass again.
B6 done — full seed loads (SEED OK, 45 sources), 17 tests pass, DEMO.md steps 1-13 + counter-test pass. Read all four briefs over 3 resets: all model-written (no template fallback), every source cited, 42-86 words, embedded items match handoff/data.md (giulia act_golive act_key mem_pg mem_azure; sara mem_verdello; luca act_kestrel; marco act_flaky). Brief prompt tightened so action reasons keep their dates (Giulia: "but the task is due 9 Dec") and markers sit before the full stop.
CONTRACT change: section 10, incoming.json is now described as the new work injected by the demo script's "source" steps (it said "the queue for POST /demo/next-event", which no longer holds).
B8 done (code) — the brief has actions: [] and memory_items: []; its text says the items arrive one at a time and never says "below" or "card" (model text with those words falls back to the template). Reset prepares every brief's audio in parallel; a voice failure does not fail the reset. Reset takes ~7 s (brief + audio).
B9 done (code) — backend/demo_script.json: act_golive, mem_pg, mem_azure, src_pr_mongo (watcher), act_key, act_flaky, act_kestrel, mem_verdello. Release steps make no model call. Overview: remaining_events = steps left, next_step as in section 12, last_event = first source the released item cites (or the new source). A failed watcher call returns 503 and the step is not consumed.
B10 done (code) — memory items have caught: [] ; the watcher appends the new source's label (e.g. "Pull request · Add MongoDB store for Alpilog reports · Tue 24 Nov 09:00"). Start the day clears it.
B10b done (code) — the single watcher call also returns alert_text and message_to_author; code drops them if empty, over limit +20% (60 / 48 words) or holding [n] markers, and uses the templates. Tests cover the fallback.
Tests: 25 pass (cd backend && uv run pytest -q). Checked offline with the real model and voice (separate state file, nothing sent to Telegram). The running server on :8000 still runs the old code until it is restarted.
B11 done — DEMO.md steps 1-14 and the counter-test pass through the API (one run, real Gemini and ElevenLabs). Step 1: brief only, no cards, audio ready at once. Step 14: model-written alert ending in [1][2], citations [src_chat_pg, src_pr_mongo], "Ask Marco to hold …", Caught tag on mem_pg; approve adds the note to marco to the outbox and leaves mem_pg approved. Counter-test: four presses without approving mem_pg → no conflict alert, no Caught tag.
Brief length (human request): about 60 words, 70 at most (spoken words, [n] markers not counted). If the first draft is over 70, one extra model call shortens it; if it is still too long or invalid, a short template is used (34-38 words for the seed). Over 4 resets offline: all 16 briefs model-written, 41-70 words. Reset usually takes 6-8 s; one took 18.6 s because of a slow Gemini call.
Tests: 26 pass (cd backend && uv run pytest -q).
CHANGE SET 2 READY — start: `cd backend && uv run uvicorn main:app --port 8000`. state.json is left in the counter-test state: press Start the day before the demo.

## Change set 3 (Sat 21 Nov, afternoon)

- `demo_script.json` has two tracks, `tech` and `finance`, each with its own position in
  `script_pos`. `POST /demo/next-event?track=tech|finance` (default `tech`, unknown → 404).
  Overview `next_step` and `remaining_events` are per track. Old `state.json` files are rebuilt.
- Script: tech = act_golive, mem_pg, mem_azure, src_pr_mongo, act_key; finance = act_kestrel.
  act_flaky and mem_verdello stay in the seed, out of the script.
- Seed: act_kestrel is now "Send the first payment reminder to Kestrel Freight" (message to
  Martina Gallo + follow-up task for Luca). src_chat_kestrel rewritten: Elena reports the
  reconciliation, Luca does not say he will ask Sara. check_seed.py accepts an outside
  contact "Name (Company)" as `send_message` target.
- CONTRACT.md: types, sections 7, 9, 11–14 and new section 16.
- Verified: 26 tests pass; seed check OK; on a separate backend (port 8010, real model) reset,
  finance press, Luca's brief and alert, approve → outbox line and new task.
CONTRACT change (section 17, change set 4, made by the bot agent at the human's request, who asked it to act for every agent from one chat): no brief at startup (`store.load_or_init()` no longer writes briefs; main.py updated); `brief.select` keeps only approved facts not cited by demo_script.json, no actions, no proposals (new `brief.script_sources`); empty-brief template text changed; demo_script.json tech = act_golive, mem_pg, src_pr_mongo. Tests updated + 2 new (startup writes no brief; brief repeats nothing): 28 pass. DEMO.md rewritten to 14 steps.
CONTRACT change (section 17, startup row): every backend start is a fresh demo. `store.load_or_init()` always rebuilds from the seed and overwrites state.json (the old note "state survives restarts" no longer holds). Test `test_startup_is_a_fresh_demo_without_brief`; 28 pass.
