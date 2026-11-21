# Handoff log — bot agent

Only the bot agent writes in this file. The other agents read it.

- Append at the bottom. Never edit or delete older lines.
- One line per message. To address another agent, start the line with `@BACKEND`, `@BOT`, `@FRONTEND` or `@DATA`.
- Write here what you need from the backend (a field, an endpoint, a fix).

---
- T0 done: `cd bot && uv run python main.py` starts long polling; `/start` shows "Who are you?" with one button per person and ties the chat in `bot/bot_state.json`. People come from a constant until BACKEND SKELETON READY.
- T1–T5 written in `bot/main.py` (httpx + long polling, HTML parse mode, ~400 lines). People now come from `GET /people` (constant only as fallback when the backend is down).
- T1: a thread polls `GET /state` every 2 s per tied chat; sends new brain `brief`/`alert` messages, then one card per embedded action and memory item. Sent ids kept per chat in `bot/bot_state.json`; re-tying with /start resends the thread.
- T2: any text → "typing" (refreshed every 4 s) → `POST /ask` → answer + footnotes + `[n]` source buttons.
- T3: Approve/Reject call the endpoint; on 200 the card is edited (Approve/Reject removed, source buttons kept, "✅ Approved"/"❌ Rejected" added); on 403/409 the backend `detail` pops up and the card is unchanged.
- T4: `src:<id>` → `GET /sources/{id}` → type label, title, author, time, body (tasks also show assignee, due date, status). 403 → "You don't have access to this source."
- T5: `brief:audio` → `GET /brief/audio` → `sendVoice`, falls back to `sendAudio`; 503 → "Voice is not configured."
- Backend down: user actions get "The Brain is not reachable right now. Try again in a moment."; the poller logs once and keeps retrying. No crash.
- Verified offline against the live backend: rendering of Giulia's and Luca's threads, source 403 (Giulia → contract doc), audio 503, action 403 (Marco → act_golive), backend down. NOT yet verified with a real Telegram chat (needs a human: T6).
- @BACKEND the update_task effect only carries `task_id`; the bot calls `GET /sources/{task_id}` to show the task title. Fine as is, no change needed.
