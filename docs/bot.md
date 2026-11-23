# Telegram bot

A single file, [`bot/main.py`](../bot/main.py), with `httpx` as its only dependency. It is a thin
adapter over the backend API: it shows what the backend returns and sends back what people do.
It holds no business logic.

```bash
cd bot && uv run python main.py
```

It needs `TELEGRAM_BOT_TOKEN` and reads `BACKEND_URL` (default `http://localhost:8000`) from the
`.env` file at the project root.

## Lifecycle

1. **Start.** Checks the token with `getMe`, drops the updates sent while it was off
   (`deleteWebhook` with `drop_pending_updates`) and deletes from every tied chat the messages
   the previous run sent. Chats stay tied, so each start is a clean demo without a new `/start`.
   Telegram only deletes messages younger than 48 hours.
2. **Updates.** Long polling with `getUpdates` (25-second timeout); each update is handled in a
   pool of 8 threads.
3. **Delivery.** A background thread calls `GET /state` every 2 seconds for each tied chat and
   sends the briefs and alerts not delivered yet. Ids are marked as sent *before* sending, so a
   message is never sent twice. After a brief it fetches `GET /brief/audio` and sends it as a
   voice message (audio file as a fallback, text only if both fail).

## What people can do

| Input | Bot behaviour |
|---|---|
| `/start` | "Who are you?" with one button per person (`who:<id>`). Tying a chat marks everything already in that person's thread as delivered. |
| Any other text | A question: `POST /ask` with the chat's person, shown with "typing…" while waiting. The answer has numbered footnotes and one button per source. |
| Approve / Reject on an action | `POST /actions/{id}/approve` or `/reject` (`act:approve:<id>`). The buttons are replaced by the outcome. |
| Approve / Reject on a memory item | `POST /memory/{id}/approve` or `/reject` (`mem:approve:<id>`). |
| A source button | `GET /sources/{id}` (`src:<id>`): shows the source if the person may see it. |

## Rendering

- Messages use Telegram HTML; long texts are split on line breaks under 4,000 characters.
- An alert with exactly one embedded card (action or memory item) is **one** Telegram message:
  the alert text, what approving would do, the Approve / Reject buttons and the source buttons.
- Other messages are sent as the text with its footnotes, followed by one message per card.
- Errors from the backend are shown as their `detail` text; when the backend is down the bot says
  "The Brain is not reachable right now" and keeps retrying in the background.

## State

`bot/bot_state.json` (ignored by Git) holds, per chat: the tied person, the ids of delivered
messages and the Telegram message ids to delete at the next start. Delete it to untie every chat.

## Moving to another channel

Everything the bot does goes through the public API, so a Slack or Teams adapter would repeat the
same loop: tie a user to a person id, poll `GET /state`, turn texts into `POST /ask` and buttons
into the approve and reject endpoints.
