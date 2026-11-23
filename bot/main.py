"""Company Brain — Telegram bot.

A thin adapter over the backend API (docs/plans/contract.md section 13).
It shows what the backend returns and sends back what people do. No logic of its own.
"""

import html
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import httpx

HERE = Path(__file__).parent
STATE_FILE = HERE / "bot_state.json"
DOWN_TEXT = "The Brain is not reachable right now. Try again in a moment."


# ---------- configuration (.env at the project root wins over the shell) ----------

def load_env() -> dict:
    env = {}
    path = HERE.parent / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                if value:  # an empty value counts as missing
                    env[key.strip()] = value
    return env


ENV = load_env()
TOKEN = ENV.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
BACKEND_URL = (ENV.get("BACKEND_URL") or os.environ.get("BACKEND_URL") or "http://localhost:8000").rstrip("/")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")
TG = f"https://api.telegram.org/bot{TOKEN}"

tg_http = httpx.Client(timeout=40)
api_http = httpx.Client(base_url=BACKEND_URL, timeout=60)


def log(*parts):
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


# ---------- Telegram ----------

def tg(method: str, **params):
    """Call a Telegram Bot API method. Returns `result`, or None on failure (never logs the token)."""
    files = params.pop("files", None)
    try:
        if files:
            r = tg_http.post(f"{TG}/{method}", data=params, files=files, timeout=120)
        else:
            r = tg_http.post(f"{TG}/{method}", json=params)
        body = r.json()
    except (httpx.HTTPError, ValueError) as e:
        log(f"telegram {method} failed: {type(e).__name__}")
        return None
    if not body.get("ok"):
        log(f"telegram {method} refused: {body.get('description')}")
        return None
    return body["result"]


def keyboard(rows):
    rows = [row for row in rows if row]
    return {"inline_keyboard": rows} if rows else None


def chunks(text, size=4000):
    """Split on line breaks so HTML tags (always within one line) stay whole."""
    parts, current = [], ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > size:
            parts.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    parts.append(current)
    return [p[:4096] for p in parts]


def send(chat_id, text, rows=None):
    """Send HTML text; buttons go under the last piece."""
    parts = chunks(text)
    for i, part in enumerate(parts):
        params = {"chat_id": chat_id, "text": part, "parse_mode": "HTML",
                  "link_preview_options": {"is_disabled": True}}
        markup = keyboard(rows or []) if i == len(parts) - 1 else None
        if markup:
            params["reply_markup"] = markup
        remember(chat_id, tg("sendMessage", **params))


def esc(text) -> str:
    return html.escape(str(text or ""), quote=False)


# ---------- backend ----------

class BackendDown(Exception):
    pass


def api(method, path, person=None, **kwargs) -> httpx.Response:
    headers = {"X-User-Id": person} if person else {}
    try:
        return api_http.request(method, path, headers=headers, **kwargs)
    except httpx.HTTPError as e:
        raise BackendDown() from e


def detail(r: httpx.Response) -> str:
    try:
        return str(r.json().get("detail") or f"Error {r.status_code}")
    except ValueError:
        return f"Error {r.status_code}"


# ---------- bot state: which chat is which person, what was sent ----------

lock = threading.Lock()


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except ValueError:
            log("bot_state.json is broken, starting empty")
    return {"chats": {}}


def save_state():
    STATE_FILE.write_text(json.dumps(state, indent=2))


state = load_state()


def person_of(chat_id):
    with lock:
        chat = state["chats"].get(str(chat_id))
        return chat["person"] if chat else None


def remember(chat_id, message):
    """Note every Telegram message of a chat (ours and the person's), so the next start can wipe it."""
    if message and "message_id" in message:
        with lock:
            state.setdefault("tg_messages", {}).setdefault(str(chat_id), []).append(message["message_id"])
            save_state()


def wipe_chats():
    """Every start is a new demo (CONTRACT section 17): delete what the last run left in the chats.
    Ties are kept, so nobody has to /start again. Telegram only deletes messages younger than 48 h."""
    with lock:
        chats = state.pop("tg_messages", {})
        save_state()
    for chat_id, ids in chats.items():
        for i in range(0, len(ids), 100):
            tg("deleteMessages", chat_id=chat_id, message_ids=ids[i:i + 100])
        log(f"chat {chat_id}: {len(ids)} messages of the last run deleted")


# ---------- people ----------

# Fallback only, if the backend is down when someone sends /start (docs/plans/contract.md section 4).
PEOPLE = [
    {"id": "sara", "name": "Sara Conti", "team": "sales", "is_lead": True, "title": "Head of Sales"},
    {"id": "giulia", "name": "Giulia Ferri", "team": "tech", "is_lead": True, "title": "Tech Lead"},
    {"id": "marco", "name": "Marco Riva", "team": "tech", "is_lead": False, "title": "Backend Developer"},
    {"id": "luca", "name": "Luca Moretti", "team": "finance", "is_lead": True, "title": "Finance Manager"},
]


def get_people():
    global PEOPLE
    try:
        r = api("GET", "/people")
        if r.status_code == 200:
            PEOPLE = r.json()
    except BackendDown:
        log("backend down: using the last known people")
    return PEOPLE


def name_of(person_id):
    return next((p["name"] for p in PEOPLE if p["id"] == person_id), person_id)


# ---------- formatting ----------

TYPE_LABELS = {"email": "Email", "chat": "Chat", "doc": "Doc", "task": "Task", "pr": "Pull request"}
STATUS_LABELS = {"todo": "To do", "in_progress": "In progress", "done": "Done"}
APPROVED, REJECTED = "✅ Approved", "❌ Rejected"


def fmt_time(ts):
    try:
        d = datetime.fromisoformat(ts)
        return f"{d:%a} {d.day} {d:%b %H:%M}"
    except (TypeError, ValueError):
        return str(ts or "")


def fmt_date(day):
    try:
        d = datetime.fromisoformat(day)
        return f"{d.day} {d:%b %Y}"
    except (TypeError, ValueError):
        return str(day or "")


def footnotes(citations) -> str:
    lines = []
    for c in citations:
        line = f"[{c['n']}] {esc(c['label'])}"
        if c.get("quote"):
            line += f" — “{esc(c['quote'])}”"
        lines.append(line)
    return "\n".join(lines)


def source_rows(citations):
    buttons = [{"text": f"[{c['n']}]", "callback_data": f"src:{c['source_id']}"} for c in citations]
    return [buttons[i:i + 5] for i in range(0, len(buttons), 5)]


def body(*blocks) -> str:
    return "\n\n".join(b for b in blocks if b)


def task_title(task_id, person):
    try:
        r = api("GET", f"/sources/{task_id}", person)
        if r.status_code == 200:
            return r.json().get("title") or task_id
    except BackendDown:
        pass
    return task_id


def effect_line(effect, person) -> str:
    kind = effect.get("type")
    if kind == "update_task":
        changes = effect.get("changes", {})
        what = []
        if "due_date" in changes:
            what.append(f"due date → {fmt_date(changes['due_date'])}")
        if "status" in changes:
            what.append(f"status → {STATUS_LABELS.get(changes['status'], changes['status'])}")
        return f"• Change task “{esc(task_title(effect.get('task_id'), person))}”: {esc(', '.join(what))}"
    if kind == "create_task":
        return (f"• Create task “{esc(effect.get('title'))}” for {esc(name_of(effect.get('assignee')))}, "
                f"due {esc(fmt_date(effect.get('due_date')))}")
    if kind == "send_message":
        to = effect.get("to", "")
        to = to if to.startswith("#") else name_of(to)
        return f"• Send to {esc(to)}: “{esc(effect.get('text'))}”"
    return f"• {esc(kind)}"


def render_action(action, person):
    effects = "\n".join(effect_line(e, person) for e in action.get("effects", []))
    status = {"approved": APPROVED, "rejected": REJECTED}.get(action["status"])
    text = body(f"<b>{esc(action['title'])}</b>", esc(action.get("reason")),
                f"If you approve:\n{effects}" if effects else "", footnotes(action["citations"]), status)
    rows = []
    if action["status"] == "pending":
        rows.append([{"text": "Approve", "callback_data": f"act:approve:{action['id']}"},
                     {"text": "Reject", "callback_data": f"act:reject:{action['id']}"}])
    return text, rows + source_rows(action["citations"])


def render_memory(item):
    status = {"approved": APPROVED, "rejected": REJECTED}.get(item["status"])
    text = body("<b>Should I remember this?</b>", esc(item["statement"]), footnotes(item["citations"]), status)
    rows = []
    if item["status"] == "proposed" and item.get("can_decide"):
        rows.append([{"text": "Approve", "callback_data": f"mem:approve:{item['id']}"},
                     {"text": "Reject", "callback_data": f"mem:reject:{item['id']}"}])
    return text, rows + source_rows(item["citations"])


def render_alert_with_card(msg, person):
    """An alert with exactly one card → ONE Telegram message: the alert text, then what the card
    asks, with its buttons. The alert text already says why, so the card's reason is not repeated."""
    status_word = lambda s: {"approved": APPROVED, "rejected": REJECTED}.get(s)
    rows = []
    if msg.get("actions"):
        a = msg["actions"][0]
        effects = "\n".join(effect_line(e, person) for e in a.get("effects", []))
        card = body(f"<b>Proposed: {esc(a['title'])}</b>", f"If you approve:\n{effects}" if effects else "")
        status = status_word(a["status"])
        if a["status"] == "pending":
            rows.append([{"text": "Approve", "callback_data": f"act:approve:{a['id']}"},
                         {"text": "Reject", "callback_data": f"act:reject:{a['id']}"}])
    else:
        m = msg["memory_items"][0]
        card = f"<b>Remember:</b> {esc(m['statement'])}"
        status = status_word(m["status"])
        if m["status"] == "proposed" and m.get("can_decide"):
            rows.append([{"text": "Approve", "callback_data": f"mem:approve:{m['id']}"},
                         {"text": "Reject", "callback_data": f"mem:reject:{m['id']}"}])
    text = body("<b>Alert</b>", esc(msg["text"]), card, footnotes(msg["citations"]), status)
    return text, rows + source_rows(msg["citations"])


def render(msg, person):
    """One Brain message → list of (html_text, button_rows) Telegram messages."""
    if msg["kind"] == "alert" and len(msg.get("actions", [])) + len(msg.get("memory_items", [])) == 1:
        return [render_alert_with_card(msg, person)]
    header = {"brief": "<b>Morning brief</b>", "alert": "<b>Alert</b>"}.get(msg["kind"])
    rows = source_rows(msg["citations"])
    parts = [(body(header, esc(msg["text"]), footnotes(msg["citations"])), rows)]
    parts += [render_action(a, person) for a in msg.get("actions", [])]
    parts += [render_memory(m) for m in msg.get("memory_items", [])]
    return parts


def render_source(src) -> str:
    head = f"<b>{esc(TYPE_LABELS.get(src['type'], src['type']))}</b> · {esc(src['title'])}"
    meta = f"{esc(src.get('author'))} · {esc(fmt_time(src.get('timestamp')))}"
    if src["type"] == "task":
        bits = []
        if src.get("assignee"):
            bits.append(f"Assignee: {name_of(src['assignee'])}")
        if src.get("due_date"):
            bits.append(f"Due {fmt_date(src['due_date'])}")
        if src.get("status"):
            bits.append(STATUS_LABELS.get(src["status"], src["status"]))
        meta += "\n" + esc(" · ".join(bits))
    return body(head, meta, esc(src.get("body")))


# ---------- T1: deliver what the Brain says ----------

def deliver(chat_id, person):
    r = api("GET", "/state", person)
    if r.status_code != 200:
        log(f"GET /state for {person}: {r.status_code} {detail(r)}")
        return
    brain = [m for m in r.json().get("thread", [])
             if m.get("from") == "brain" and m.get("kind") in ("brief", "alert")]
    with lock:
        chat = state["chats"].get(chat_id)
        if not chat or chat["person"] != person:
            return
        if chat.get("fresh"):
            # T7: a chat that has just been tied gets nothing already in the thread.
            chat["sent"], chat["fresh"] = [m["id"] for m in brain], False
            save_state()
            log(f"chat {chat_id}: {len(brain)} existing messages of {person} marked as sent")
            return
        new = [m for m in brain if m["id"] not in chat["sent"]]
        if new:
            chat["sent"] += [m["id"] for m in new]  # mark first: never send the same message twice
            save_state()
    for msg in new:
        log(f"sending {msg['kind']} {msg['id']} to {person}")
        for text, rows in render(msg, person):
            send(chat_id, text, rows)
        if msg["kind"] == "brief":
            send_brief_voice(chat_id, person)


def poll_forever():
    down = False
    while True:
        with lock:
            chats = [(cid, c["person"]) for cid, c in state["chats"].items()]
        try:
            for chat_id, person in chats:
                deliver(chat_id, person)
            if down:
                log("backend is back")
            down = False
        except BackendDown:
            if not down:
                log(f"backend unreachable at {BACKEND_URL}, retrying every 2 s")
            down = True
        except Exception as e:  # keep polling whatever happens
            log(f"poll error: {type(e).__name__}: {e}")
        time.sleep(2)


# ---------- handlers ----------

def on_start(chat_id):
    rows = [[{"text": f"{p['name']} · {p['title']}", "callback_data": f"who:{p['id']}"}] for p in get_people()]
    send(chat_id, "Who are you?", rows)


def on_who(chat_id, message, person_id):
    person = next((p for p in PEOPLE if p["id"] == person_id), None)
    if not person:
        return "Unknown person."
    with lock:
        # "fresh": the next look at the thread marks everything in it as sent (T7).
        state["chats"][str(chat_id)] = {"person": person_id, "sent": [], "fresh": True}
        save_state()
    tg("editMessageText", chat_id=chat_id, message_id=message["message_id"],
       text=f"You are {person['name']} ({person['title']}). Send /start to change.")
    log(f"chat {chat_id} tied to {person_id}")
    try:
        deliver(str(chat_id), person_id)  # mark the thread now; if the backend is down, the poller does it
    except BackendDown:
        pass
    return None


# T2: questions
def on_text(chat_id, text):
    person = person_of(chat_id)
    if not person:
        send(chat_id, "Send /start first and tell me who you are.")
        return
    stop = threading.Event()

    def typing():
        while not stop.is_set():
            tg("sendChatAction", chat_id=chat_id, action="typing")
            stop.wait(4)

    threading.Thread(target=typing, daemon=True).start()
    try:
        r = api("POST", "/ask", person, json={"question": text})
    finally:
        stop.set()
    if r.status_code == 401:
        send(chat_id, "I don't know who you are. Send /start.")
    elif r.status_code != 200:
        send(chat_id, esc(detail(r)))
    else:
        for part_text, rows in render(r.json(), person):
            send(chat_id, part_text, rows)


# T3: approve and reject
def on_decide(chat_id, message, person, data):
    kind, verb, item_id = data.split(":", 2)
    if verb not in ("approve", "reject"):
        return "Unknown button."
    path = f"/{'actions' if kind == 'act' else 'memory'}/{item_id}/{verb}"
    r = api("POST", path, person)
    if r.status_code != 200:
        return detail(r)  # 403 / 409 / …: shown, message left as it is
    word = APPROVED if verb == "approve" else REJECTED
    old_rows = (message.get("reply_markup") or {}).get("inline_keyboard", [])
    rows = [row for row in old_rows
            if not any(b.get("callback_data", "").startswith(("act:", "mem:")) for b in row)]
    params = {"chat_id": chat_id, "message_id": message["message_id"],
              "text": f"{message.get('text', '')}\n\n{word}", "entities": message.get("entities", [])}
    if rows:
        params["reply_markup"] = {"inline_keyboard": rows}
    tg("editMessageText", **params)
    log(f"{person} {verb}d {item_id}")
    return word


# T4: sources
def on_source(chat_id, person, source_id):
    r = api("GET", f"/sources/{source_id}", person)
    if r.status_code == 403:
        send(chat_id, "You don't have access to this source.")
    elif r.status_code != 200:
        send(chat_id, esc(detail(r)))
    else:
        send(chat_id, render_source(r.json()))


# T8: the brief's voice follows its text at once. If the audio fails, the text alone stays.
def send_brief_voice(chat_id, person):
    tg("sendChatAction", chat_id=chat_id, action="upload_voice")
    try:
        r = api("GET", "/brief/audio", person)
    except BackendDown:
        log(f"brief audio for {person}: backend unreachable, text only")
        return
    if r.status_code != 200:
        log(f"brief audio for {person}: {r.status_code} {detail(r)}, text only")
        return
    audio = ("brief.mp3", r.content, r.headers.get("content-type", "audio/mpeg"))
    sent = tg("sendVoice", chat_id=chat_id, files={"voice": audio})
    if sent is None:
        sent = tg("sendAudio", chat_id=chat_id, title="Morning brief", files={"audio": audio})
    if sent is None:
        log(f"brief audio for {person}: Telegram refused it, text only")
    remember(chat_id, sent)


def on_message(message):
    chat_id = message["chat"]["id"]
    remember(chat_id, message)
    text = (message.get("text") or "").strip()
    try:
        if text.split("@")[0] == "/start" or text.startswith("/start "):
            on_start(chat_id)
        elif text.startswith("/"):
            send(chat_id, "Commands: /start to pick who you are. Any other text is a question for the Brain.")
        elif text:
            on_text(chat_id, text)
        else:
            send(chat_id, "I only understand text messages.")
    except BackendDown:
        send(chat_id, DOWN_TEXT)


def on_callback(query):
    data = query.get("data", "")
    message = query.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    notice = None
    try:
        if chat_id is None:
            notice = "This button is too old."
        elif data.startswith("who:"):
            notice = on_who(chat_id, message, data[4:])
        elif not (person := person_of(chat_id)):
            notice = "Send /start first and tell me who you are."
        elif data.startswith(("act:", "mem:")):
            notice = on_decide(chat_id, message, person, data)
        elif data.startswith("src:"):
            on_source(chat_id, person, data[4:])
        else:
            notice = "Unknown button."
    except BackendDown:
        notice = DOWN_TEXT
    params = {"callback_query_id": query["id"]}
    if notice:
        params.update(text=notice[:200], show_alert=notice not in (APPROVED, REJECTED))
    tg("answerCallbackQuery", **params)


def handle(update):
    try:
        if "message" in update:
            on_message(update["message"])
        elif "callback_query" in update:
            on_callback(update["callback_query"])
    except Exception as e:  # one bad update must never stop the bot
        log(f"error handling update: {type(e).__name__}: {e}")


# ---------- main loop ----------

def main():
    me = tg("getMe")
    if not me:
        raise SystemExit("Telegram refused the token (or is unreachable).")
    log(f"bot @{me['username']} running, backend {BACKEND_URL}")
    # A new demo: drop taps and texts sent while the bot was off, and wipe the old chats.
    tg("deleteWebhook", drop_pending_updates=True)
    wipe_chats()
    threading.Thread(target=poll_forever, daemon=True).start()
    pool = ThreadPoolExecutor(max_workers=8)
    offset = None
    while True:
        params = {"timeout": 25, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            params["offset"] = offset
        updates = tg("getUpdates", **params)
        if updates is None:
            time.sleep(2)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            pool.submit(handle, update)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("bye")
