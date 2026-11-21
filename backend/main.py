"""Company Brain API (CONTRACT section 7). Start: cd backend && uv run uvicorn main:app --port 8000"""
import os
from pathlib import Path

from dotenv import dotenv_values

# .env wins over the shell; an empty value counts as missing (CONTRACT section 2).
for _k, _v in dotenv_values(Path(__file__).parent.parent / ".env").items():
    if _v:
        os.environ[_k] = _v

from fastapi import Body, FastAPI, Header, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import Response  # noqa: E402

import access  # noqa: E402
import actions  # noqa: E402
import ask as ask_mod  # noqa: E402
import brief  # noqa: E402
import store  # noqa: E402
import voice  # noqa: E402
import watcher  # noqa: E402
from llm import LLMError  # noqa: E402

app = FastAPI(title="Company Brain")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
store.load_or_init(brief.make_briefs)


def me(x_user_id: str | None) -> dict:
    p = store.person(store.S, x_user_id) if x_user_id else None
    if not p:
        raise HTTPException(401, "Unknown user. Send the X-User-Id header with a person id.")
    return p


def get_or_404(kind, getter, item_id):
    item = getter(store.S, item_id)
    if not item:
        raise HTTPException(404, f"{kind} {item_id} not found")
    return item


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/people")
def people():
    return store.S["people"]


@app.get("/state")
def state(x_user_id: str | None = Header(None)):
    user = me(x_user_id)
    with store.LOCK:
        st = store.S
        return {"me": user, "now": store.now(),
                "thread": [store.render_message(st, m, user) for m in st["threads"][user["id"]]]}


@app.post("/ask")
def ask(body: dict = Body(...), x_user_id: str | None = Header(None)):
    user = me(x_user_id)
    question = str(body.get("question", "")).strip()
    if not question:
        raise HTTPException(422, "question is required")
    try:
        text, answerable, cites = ask_mod.answer(store.snapshot(), user, question)
    except LLMError as e:
        raise HTTPException(503, f"The model is not available: {e}")
    with store.LOCK:
        store.add_message(store.S, user["id"], "user", "question", question)
        msg = store.add_message(store.S, user["id"], "brain", "answer", text,
                                cites=cites, answerable=answerable)
        store.save()
        return store.render_message(store.S, msg, user)


def decide_memory(item_id: str, x_user_id: str | None, status: str):
    user = me(x_user_id)
    with store.LOCK:
        m = get_or_404("Memory item", store.memory, item_id)
        if not access.is_lead_of(user, m["team"]):
            raise HTTPException(403, "Only the lead of this team can decide this item.")
        if m["status"] != "proposed":
            raise HTTPException(409, f"This item was already {m['status']}.")
        m.update(status=status, decided_by=user["id"], decided_at=store.now())
        store.save()
        return store.render_memory(store.S, m, user)


@app.post("/memory/{item_id}/approve")
def memory_approve(item_id: str, x_user_id: str | None = Header(None)):
    return decide_memory(item_id, x_user_id, "approved")


@app.post("/memory/{item_id}/reject")
def memory_reject(item_id: str, x_user_id: str | None = Header(None)):
    return decide_memory(item_id, x_user_id, "rejected")


def decide_action(item_id: str, x_user_id: str | None, status: str):
    user = me(x_user_id)
    with store.LOCK:
        a = get_or_404("Action", store.action, item_id)
        if a["for_user"] != user["id"]:
            raise HTTPException(403, "Only the person this action is for can decide it.")
        if a["status"] != "pending":
            raise HTTPException(409, f"This action was already {a['status']}.")
        if status == "approved":
            actions.run_effects(store.S, a)  # rule 6: effects run only here
        a.update(status=status, decided_at=store.now())
        store.save()
        return store.render_action(store.S, a)


@app.post("/actions/{item_id}/approve")
def action_approve(item_id: str, x_user_id: str | None = Header(None)):
    return decide_action(item_id, x_user_id, "approved")


@app.post("/actions/{item_id}/reject")
def action_reject(item_id: str, x_user_id: str | None = Header(None)):
    return decide_action(item_id, x_user_id, "rejected")


@app.get("/sources/{source_id}")
def get_source(source_id: str, x_user_id: str | None = Header(None)):
    user = me(x_user_id)
    s = get_or_404("Source", store.source, source_id)
    if not access.can_see(user, s):
        raise HTTPException(403, "You don't have access to this source.")
    return s


@app.get("/brief/audio")
def brief_audio(x_user_id: str | None = Header(None)):
    user = me(x_user_id)
    briefs = [m for m in store.S["threads"][user["id"]] if m["kind"] == "brief"]
    if not briefs:
        raise HTTPException(404, "No brief yet. Press Start the day.")
    try:
        mp3 = voice.speak(briefs[-1]["text"])
    except voice.VoiceError as e:
        raise HTTPException(503, f"Voice is not available: {e}")
    return Response(mp3, media_type="audio/mpeg")


@app.get("/demo/overview")
def overview():
    with store.LOCK:
        st = store.S
        return {
            "now": store.now(),
            "tasks": [s for s in st["sources"] if s["type"] == "task"],
            "outbox": st["outbox"],
            "memory": [store.render_memory(st, m, None) for m in st["memory"]],
            "last_event": st["last_event"],
            "remaining_events": len(st["incoming"]),
        }


@app.post("/demo/next-event")
def next_event():
    try:
        return watcher.next_event()
    except LLMError as e:
        raise HTTPException(503, f"The model is not available: {e}")


@app.post("/demo/reset")
def reset():
    st = store.fresh_state()
    brief.make_briefs(st)  # model calls; falls back to the template on any failure
    store.replace(st)
    return {"ok": True}
