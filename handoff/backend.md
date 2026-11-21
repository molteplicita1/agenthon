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
