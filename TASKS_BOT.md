# Bot tasks (Claude Code)

Read `CONTRACT.md` and `DEMO.md` in full first. Section 13 of the contract is your spec.
You own `bot/` and `handoff/bot.md`.

## Rules

- **Simplicity first.** One small Python program. Plain HTTP calls to the Telegram
  Bot API with `httpx` and long polling (`getUpdates`). No bot framework, no webhook,
  no database. If two ways work, pick the one with less code.
- **The bot has no rules of its own.** It shows what the backend returns and sends
  back what people do. No model calls, no permission checks, no memory logic.
- Write only in the files you own. Never touch `backend/`, `frontend/` or `CONTRACT.md`.
- `handoff/bot.md` is the only handoff file you write. If you need a field, an
  endpoint or a change, add a line there.
- Before each task read `handoff/backend.md`: the backend agent announces changes there.
- **No git commands that change the repository** (add, commit, checkout, stash,
  reset). Several agents share this folder; the humans commit.
- Never print or log the bot token. Read `TELEGRAM_BOT_TOKEN` and `BACKEND_URL` from
  the `.env` file at the project root (`CONTRACT.md` section 2). Do not create or edit `.env`.
- Telegram is the only outside service the bot calls. Only text coming from the
  backend goes through it.
- All bot texts in English. Escape text properly for the parse mode you use.

## Setup

Python 3.12 with `uv`, in `bot/`. Start command: `uv run python main.py`.
Check the current Telegram Bot API docs for the methods you use (`getUpdates`,
`sendMessage` with inline keyboards, `answerCallbackQuery`, `editMessageText` or
`editMessageReplyMarkup`, `sendChatAction`, `sendVoice`).

## Tasks, in order

**T0 — Who is who.**
Long-polling loop. `/start` asks "Who are you?" with one button per person and ties
the chat to the chosen person in `bot/bot_state.json`. Until `handoff/backend.md`
says `BACKEND SKELETON READY`, use the four people of `CONTRACT.md` section 4 as a
constant; after that, read them from `GET /people`.

**T1 — Deliver what the Brain says.**
Every 2 seconds, for each tied chat, call `GET /state` and send the new `brief` and
`alert` messages, then one message per embedded action and memory item, as the
table in section 13 describes. Remember which message ids were sent to which chat.
Footnotes for the citations; one button per source.

**T2 — Questions.**
Any text that is not a command: show "typing", call `POST /ask`, reply with the
answer, its footnotes and source buttons.

**T3 — Approve and reject.**
Buttons call the matching endpoint. On success edit the message: buttons removed,
"Approved" or "Rejected" added. On `403` or `409` show the error from the backend
and leave the message as it is.

**T4 — Sources.**
A source button calls `GET /sources/{id}` and sends type label, title, author, time
and body. On `403`: "You don't have access to this source."

**T5 — Listen to the brief.**
The button calls `GET /brief/audio` and sends the result with `sendVoice`. If
Telegram refuses the format, fall back to `sendAudio`. On `503`: "Voice is not
configured."

**T6 — Run `DEMO.md` with a human.**
Ask the humans to run the Telegram steps of `DEMO.md` with you watching the logs.
Fix what is not stable. Report the result in `handoff/bot.md`.

## Done when

Every Telegram step of `DEMO.md` works with two different Telegram accounts tied to
two different people, and the backend being down gives a clear message instead of a crash.

## Only if time is left (ask the humans first)

- A person sends a voice message instead of text: transcribe it and treat it as a question.
