"""Seed loading and validation, live state (state.json), time, ids, and rendering to API shapes."""
import copy
import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).parent / "data"
SEED = Path(os.environ.get("BRAIN_SEED_DIR", DATA / "seed"))
STATE_PATH = Path(os.environ.get("BRAIN_STATE_PATH", DATA / "state.json"))
RESET_NOW = "2026-11-24T09:00:00"
TEAMS = {"sales", "tech", "finance"}
ID_RE = re.compile(r"^[a-z0-9_]{1,40}$")
TYPE_LABEL = {"email": "Email", "chat": "Chat", "doc": "Doc", "task": "Task", "pr": "Pull request"}
IDK = "I don't know. I can't find this in the memory you have access to."

LOCK = threading.RLock()
S: dict = {}  # the live state


# ---------- seed ----------

def load_seed() -> dict:
    load = lambda n: json.loads((SEED / f"{n}.json").read_text(encoding="utf-8"))
    seed = {n: load(n) for n in ("people", "sources", "memory", "actions", "incoming")}
    validate(seed)
    return seed


def validate(seed: dict) -> None:
    """Fail loudly if the seed breaks CONTRACT section 10."""
    errors = []
    people = {p["id"]: p for p in seed["people"]}
    if set(people) != {"sara", "giulia", "marco", "luca"}:
        errors.append("people.json must hold exactly sara, giulia, marco, luca")
    srcs = {s["id"]: s for s in seed["sources"] + seed["incoming"]}
    ids = [x["id"] for k in ("sources", "incoming", "memory", "actions") for x in seed[k]]
    errors += [f"bad id {i!r}" for i in ids if not ID_RE.match(i)]
    errors += [f"duplicate id {i!r}" for i in set(ids) if ids.count(i) > 1]
    for s in srcs.values():
        v = s["visible_to"]
        if s["type"] not in TYPE_LABEL or s["team"] not in TEAMS:
            errors.append(f"{s['id']}: bad type or team")
        if not v or not ("all" in v or s["team"] in v):
            errors.append(f"{s['id']}: bad visible_to")
        if s["type"] == "task" and not all(k in s for k in ("assignee", "due_date", "status")):
            errors.append(f"{s['id']}: task needs assignee, due_date, status")

    def check_cites(owner, cites):
        for c in cites:
            s = srcs.get(c["source_id"])
            if s is None:
                errors.append(f"{owner}: unknown source {c['source_id']}")
            elif c["quote"] is not None and c["quote"] not in s["body"]:
                errors.append(f"{owner}: quote not in {c['source_id']}")

    for m in seed["memory"]:
        if not m["cites"]:
            errors.append(f"{m['id']}: no cites")
        check_cites(m["id"], m["cites"])
        first = srcs.get(m["cites"][0]["source_id"]) if m["cites"] else None
        if first and (first["team"] != m["team"] or first["visible_to"] != m["visible_to"]):
            errors.append(f"{m['id']}: team/visible_to differ from its first source")
        if m["decided_by"] and m["decided_by"] not in people:
            errors.append(f"{m['id']}: unknown decided_by")
    for a in seed["actions"]:
        check_cites(a["id"], a["cites"])
        if a["for_user"] not in people:
            errors.append(f"{a['id']}: unknown for_user")
        for e in a["effects"]:
            if e["type"] == "update_task" and e["task_id"] not in srcs:
                errors.append(f"{a['id']}: unknown task {e['task_id']}")
    if errors:
        raise SystemExit("SEED INVALID:\n  " + "\n  ".join(errors))


# ---------- state ----------

def fresh_state() -> dict:
    seed = load_seed()
    seed["threads"] = {p["id"]: [] for p in seed["people"]}
    seed["outbox"] = []
    seed["last_event"] = None
    seed["reset_at"] = time.time()
    return seed


def save() -> None:
    with LOCK:
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(STATE_PATH)


def load_or_init(make_briefs) -> None:
    """At startup: reuse state.json if present, else build a fresh state (template briefs only)."""
    load_seed()  # validate the seed even when state.json exists
    if STATE_PATH.exists():
        S.clear()
        S.update(json.loads(STATE_PATH.read_text(encoding="utf-8")))
    else:
        st = fresh_state()
        make_briefs(st, use_model=False)
        replace(st)


def replace(new: dict) -> None:
    with LOCK:
        S.clear()
        S.update(new)
        save()


def snapshot() -> dict:
    with LOCK:
        return copy.deepcopy(S)


# ---------- time and ids ----------

def now(st: dict | None = None) -> str:
    st = st or S
    t = datetime.fromisoformat(RESET_NOW) + timedelta(seconds=time.time() - st["reset_at"])
    return t.replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------- lookups ----------

def person(st, pid):
    return next((p for p in st["people"] if p["id"] == pid), None)


def person_by_name(st, name):
    return next((p for p in st["people"] if p["name"] == name), None)


def lead_of(st, team):
    return next((p for p in st["people"] if p["team"] == team and p["is_lead"]), None)


def source(st, sid):
    return next((s for s in st["sources"] if s["id"] == sid), None)


def memory(st, mid):
    return next((m for m in st["memory"] if m["id"] == mid), None)


def action(st, aid):
    return next((a for a in st["actions"] if a["id"] == aid), None)


# ---------- rendering to API shapes ----------

def _short(ts: str) -> str:
    return datetime.fromisoformat(ts).strftime("%a %-d %b %H:%M")


def _day(d: str) -> str:
    return datetime.fromisoformat(d).strftime("%-d %b")


def label(s: dict) -> str:
    t = TYPE_LABEL[s["type"]]
    if s["type"] == "task":
        return f"{t} · {s['title']} · due {_day(s['due_date'])}"
    who = s["author"] if s["type"] == "email" else s["title"]
    return f"{t} · {who} · {_short(s['timestamp'])}"


def citations(st, cites: list) -> list:
    out = []
    for n, c in enumerate(cites, 1):
        s = source(st, c["source_id"])
        out.append({"n": n, "source_id": c["source_id"], "type": s["type"] if s else "doc",
                    "label": label(s) if s else c["source_id"], "quote": c["quote"]})
    return out


def render_memory(st, m: dict, user: dict | None) -> dict:
    from access import can_decide_memory
    out = {k: v for k, v in m.items() if k != "cites"}
    out["citations"] = citations(st, m["cites"])
    out["can_decide"] = bool(user) and can_decide_memory(user, m)
    return out


def render_action(st, a: dict) -> dict:
    out = {k: v for k, v in a.items() if k != "cites"}
    out["citations"] = citations(st, a["cites"])
    return out


def render_message(st, msg: dict, user: dict) -> dict:
    return {
        "id": msg["id"], "from": msg["from"], "kind": msg["kind"], "text": msg["text"],
        "answerable": msg.get("answerable"),
        "citations": citations(st, msg.get("cites", [])),
        "actions": [render_action(st, action(st, i)) for i in msg.get("action_ids", [])],
        "memory_items": [render_memory(st, memory(st, i), user) for i in msg.get("memory_ids", [])],
        "created_at": msg["created_at"],
    }


def add_message(st, pid, frm, kind, text, *, cites=(), action_ids=(), memory_ids=(), answerable=None) -> dict:
    msg = {"id": new_id("msg"), "from": frm, "kind": kind, "text": text, "answerable": answerable,
           "cites": list(cites), "action_ids": list(action_ids), "memory_ids": list(memory_ids),
           "created_at": now(st)}
    st["threads"][pid].append(msg)
    return msg
