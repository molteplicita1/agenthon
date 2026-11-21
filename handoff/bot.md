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
- T7 done: after /start and the choice of person, everything already in that person's thread is marked as sent (done at once, or on the first successful poll if the backend is down). Only messages created afterwards arrive.
- T8 done: a brief is the text message (title, text, footnotes, source buttons) followed at once by the voice from `GET /brief/audio` (sendVoice, fallback sendAudio). If the audio fails (503/404/backend down/Telegram refuses) only the text is sent and the reason is logged. "Listen to the brief" button and `brief:audio` handler removed.
- T7/T8 checked offline with a stubbed backend and stubbed Telegram (tie → nothing sent; new alert → alert + card; new brief → text + voice; audio 503 → text only; no repeats). Not yet checked on real Telegram (T9).
- T9 run (Sat 21 Nov, with a human, two real Telegram accounts: Giulia and Luca, backend CHANGE SET 2 READY): /start in both → nothing delivered (old thread marked as sent). Step 1: each got the brief text then the voice (audio 330 KB / 220 KB, ready at reset); human confirmed Giulia's two messages, no cards. Step 2: go-live alert + act_golive card delivered. Step 5: Approve → task_api_migration due 2026-12-02, outbox +1 (#tech). Step 7: mem_pg card delivered, Approve → approved. Step 8: mem_azure card delivered, Reject → rejected. Step 14: model-written conflict alert citing src_chat_pg + src_pr_mongo, card "Ask Marco to hold …", Caught tag on mem_pg; Approve → outbox +1 (to marco). No duplicates, no Telegram refusals seen. Each message reached Telegram within one 2 s poll.
- T9 note: the Approve/Reject outcomes above were checked through the backend; the edited Telegram cards ("✅ Approved" / "❌ Rejected") were seen by the human but not by me.
- Luca's brief mentions the Alpilog go-live move (mem_golive, visible_to all, approved yesterday): expected per CONTRACT section 11, it is backend content.

## Change set 3 (Sat 21 Nov, afternoon)

- An alert with exactly one card is sent as ONE message (`render_alert_with_card`): alert
  text, "Proposed: <title>" + effects or "Remember: <statement>", footnotes, Approve/Reject
  and source buttons. The action's reason is not repeated. Other alerts unchanged.
- Verified offline on sample messages. Not yet tried on real Telegram: the running bot must
  be restarted to pick it up.
- @BACKEND human request (3-minute pitch): the bot agent edited `backend/demo_script.json` with the human's OK, as an exception to the folder rule. Tech track is now act_golive, mem_pg, src_pr_mongo (mem_azure and act_key removed); finance unchanged. Seed check OK. Takes effect at the next Start the day. Side effect: mem_azure (proposed) and act_key (pending) still exist, so Giulia's brief may still mention them although they never arrive. DEMO.md step 8 no longer happens; please update DEMO.md (and the brief, if wanted).
- @BACKEND human request (no repetitions, 3-minute pitch). Three changes, please:
  1. No brief at startup. `store.load_or_init` builds a fresh state with `make_briefs` when state.json is missing or old, so the bot delivers a brief as soon as the system starts. At startup the threads must stay empty; the first brief comes only from Start the day (POST /demo/reset). /brief/audio can return 404 until then.
  2. The brief repeats nothing that arrives later, and announces nothing that never arrives. Today `brief.select` puts in: Giulia act_golive + mem_pg (arrive again as alerts), act_key + mem_azure (removed from the script, never arrive), mem_golive (the go-live alert says it again); Luca act_kestrel (arrives again at the finance event) + mem_golive. Human decision: drop pending actions and proposals from the brief entirely, and drop approved facts whose sources are cited by any item of demo_script.json (so mem_golive goes too). If nothing is left, a short brief with no sources, e.g. "Good morning, Giulia. Nothing needs you right now. I will message you as soon as something does." Voice as usual.
  3. Please update DEMO.md: step 1 brief without sources, step 8 (Azure) gone, tech track = 3 presses.
- Bot: no change needed for this. A brief with no citations is sent as text without buttons, then the voice.
- Change set 4 (CONTRACT section 17) done by the bot agent in backend/ and DEMO.md with the human's OK: see handoff/backend.md. Bot code unchanged.
- Change set 4, bot part: every bot start is a new demo. `remember()` keeps the Telegram id of every message in each chat (ours and the person's) in bot_state.json `tg_messages`; at start `deleteWebhook(drop_pending_updates)` drops taps/texts sent while the bot was off, and `wipe_chats()` calls `deleteMessages` for each chat. Ties and sent ids are kept (so a bot-only restart mid-demo resends nothing, but it does wipe the chats). Messages sent before this change are not tracked: clear those chats by hand once. Checked offline with stubbed Telegram; not yet on real Telegram.
