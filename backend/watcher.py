"""POST /demo/next-event (CONTRACT section 12): the demo script and the watcher.

A release step brings a seeded item to the person who must decide (no model call).
The source step is the watcher: one model call, then every check is done in code (rule 8)."""
import re

from pydantic import BaseModel

import access
import llm
import store


class Fact(BaseModel):
    statement: str
    quote: str


class Verdict(BaseModel):
    conflict_memory_id: str | None
    conflict_quote: str | None
    alert_text: str | None
    message_to_author: str | None
    facts: list[Fact]


PROMPT = """You watch the work of Brightloop, a software house. A new piece of work just arrived.
Compare it with the decisions the team approved (listed below).

1. conflict_memory_id: the id of ONE approved decision that this new work clearly goes against
   (it does what the decision rules out). Null if none does. Missing information is not a conflict.
   conflict_quote: the exact words copied from the new work's body that show the conflict, else null.
2. Only if there is a conflict, else null:
   alert_text: a message to {lead}, the {team} lead, at most 50 words, plain English, no [n] markers.
   Say what the new work does, which approved decision it goes against, and why that matters.
   message_to_author: a short, friendly note from {lead} to {author}, at most 40 words, no [n] markers,
   asking to talk before it is merged.
3. facts: at most 2 new, lasting things worth remembering from the new work (decisions, dates,
   commitments). Each with a short statement and an exact quote copied from the body. [] if nothing.

Approved decisions:
{memory}

New work ({type_label}, by {author}, title "{title}"):
{body}"""


def _first(name: str) -> str:
    return name.split()[0]


def usable(text: str | None, max_words: int) -> str | None:
    """Model text is used only if not empty, within its limit (+20%) and free of [n] markers."""
    text = (text or "").strip()
    if not text or len(text.split()) > max_words * 1.2 or re.search(r"\[\d+\]", text):
        return None
    return text


# ---------- what the next step is ----------

def _step(st, track):
    steps, pos = st["script"][track], st["script_pos"][track]
    return steps[pos] if pos < len(steps) else None


def remaining(st, track) -> int:
    return len(st["script"][track]) - st["script_pos"][track]


def describe(st: dict, track: str) -> str | None:
    step = _step(st, track)
    if step is None:
        return None
    if step["step"] == "source":
        s = next(x for x in st["incoming"] if x["id"] == step["id"])
        return f"New {store.TYPE_LABEL[s['type']].lower()} by {s['author']}: {s['title']}"
    a = store.action(st, step["id"])
    if a:
        return f"Action for {store.person(st, a['for_user'])['name']}: {a['title']}"
    m = store.memory(st, step["id"])
    return f"Memory proposal for {store.lead_of(st, m['team'])['name']}: {m['statement']}"


# ---------- running a step ----------

def next_event(track: str) -> dict:
    with store.LOCK:
        st = store.S
        step = _step(st, track)
        if step is None:
            return {"event": None, "remaining": 0}
        if step["step"] == "release":
            return _release(st, track, step["id"])
        src = dict(next(x for x in st["incoming"] if x["id"] == step["id"]), timestamp=store.now())
        lead = store.lead_of(st, src["team"])
        given = [dict(m) for m in access.visible_approved_memory(lead, st["memory"])]
        pos, reset_at = st["script_pos"][track], st["reset_at"]

    # watcher step 2: one model call, outside the lock (LLMError -> 503, the step is not consumed)
    memory = "\n".join(f"- {m['id']}: {m['statement']}" for m in given) or "- none"
    v = llm.ask_json(PROMPT.format(memory=memory, lead=lead["name"], team=lead["team"],
                                   type_label=store.TYPE_LABEL[src["type"]], author=src["author"],
                                   title=src["title"], body=src["body"]), Verdict)

    with store.LOCK:
        st = store.S
        if st["reset_at"] != reset_at or st["script_pos"][track] != pos:  # a reset or another press meanwhile
            return {"event": None, "remaining": remaining(st, track)}
        _watch(st, src, lead, given, v)
        st["script_pos"][track] += 1
        store.save()
        return {"event": src, "remaining": remaining(st, track)}


def _release(st: dict, track: str, item_id: str) -> dict:
    a = store.action(st, item_id)
    if a:
        who, text, cites = a["for_user"], a["reason"], a["cites"]
        store.add_message(st, who, "brain", "alert", text, cites=cites, action_ids=[a["id"]])
    else:
        m = store.memory(st, item_id)
        who, cites = store.lead_of(st, m["team"])["id"], m["cites"]
        first = store.source(st, cites[0]["source_id"])
        text = f"I noticed this in {store.label(first)}. Should I remember it?"
        store.add_message(st, who, "brain", "alert", text, cites=cites, memory_ids=[m["id"]])
    event = store.source(st, cites[0]["source_id"])
    st["last_event"] = event
    st["script_pos"][track] += 1
    store.save()
    return {"event": event, "remaining": remaining(st, track)}


def _watch(st: dict, src: dict, lead: dict, given: list, v: Verdict) -> None:
    """Watcher steps 1, 3, 4, 5 (section 12). Mutates `st`; the caller saves."""
    st["incoming"] = [x for x in st["incoming"] if x["id"] != src["id"]]
    st["sources"].append(src)
    st["last_event"] = src

    by_id = {m["id"]: m for m in given}
    conflict = store.memory(st, v.conflict_memory_id) if v.conflict_memory_id in by_id else None
    quote = v.conflict_quote if v.conflict_quote and v.conflict_quote in src["body"] else None
    facts = [f for f in v.facts[:2] if f.quote and f.quote in src["body"] and f.statement.strip()]
    label = store.TYPE_LABEL[src["type"]].lower()

    if conflict:  # step 4: the model wrote the words, the code decides everything else
        statement = conflict["statement"]
        text = (usable(v.alert_text, 50) or
                f"{src['author']}'s {label} \"{src['title']}\" goes against a decision the team "
                f"approved: {statement}") + " [1][2]"
        cites = [conflict["cites"][0], {"source_id": src["id"], "quote": quote}]
        action_ids = []
        author = store.person_by_name(st, src["author"])
        if author and author["id"] != lead["id"]:
            note = usable(v.message_to_author, 40) or (
                f"Your {label} \"{src['title']}\" goes against a team decision: {statement} "
                f"Can we talk before it is merged?")
            a = {"id": store.new_id("act"), "title": f"Ask {_first(author['name'])} to hold \"{src['title']}\"",
                 "reason": f"It goes against a decision the team approved: {statement}",
                 "for_user": lead["id"], "status": "pending",
                 "effects": [{"type": "send_message", "to": author["id"], "text": note}],
                 "cites": cites, "created_at": store.now(), "decided_at": None}
            st["actions"].append(a)
            action_ids.append(a["id"])
        conflict.setdefault("caught", []).append(store.label(src))
        store.add_message(st, lead["id"], "brain", "alert", text, cites=cites, action_ids=action_ids)
    elif facts:  # step 5: memory proposals for the lead
        ids = []
        for f in facts:
            m = {"id": store.new_id("mem"), "statement": f.statement.strip(), "team": src["team"],
                 "visible_to": list(src["visible_to"]), "status": "proposed",
                 "cites": [{"source_id": src["id"], "quote": f.quote}],
                 "created_at": store.now(), "decided_by": None, "decided_at": None, "caught": []}
            st["memory"].append(m)
            ids.append(m["id"])
        n = "one thing" if len(ids) == 1 else f"{len(ids)} things"
        store.add_message(st, lead["id"], "brain", "alert",
                          f"New {label} from {src['author']}: \"{src['title']}\". I found {n} worth "
                          f"remembering. Should I? [1]",
                          cites=[{"source_id": src["id"], "quote": facts[0].quote}], memory_ids=ids)
