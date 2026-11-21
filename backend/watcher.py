"""POST /demo/next-event (CONTRACT section 12): the active memory.

One model call, then every check and every text is done in code (rule 8)."""
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
    facts: list[Fact]


PROMPT = """You watch the work of Brightloop, a software house. A new piece of work just arrived.
Compare it with the decisions the team approved (listed below).

1. conflict_memory_id: the id of ONE approved decision that this new work clearly goes against
   (it does what the decision rules out). Null if none does. Missing information is not a conflict.
   conflict_quote: the exact words copied from the new work's body that show the conflict, else null.
2. facts: at most 2 new, lasting things worth remembering from the new work (decisions, dates,
   commitments). Each with a short statement and an exact quote copied from the body. [] if nothing.

Approved decisions:
{memory}

New work ({type_label}, by {author}, title "{title}"):
{body}"""


def _first(name: str) -> str:
    return name.split()[0]


def next_event() -> dict:
    with store.LOCK:
        if not store.S["incoming"]:
            return {"event": None, "remaining": 0}
        src = dict(store.S["incoming"][0], timestamp=store.now())
        lead = store.lead_of(store.S, src["team"])
        given = access.visible_approved_memory(lead, store.S["memory"])
        given = [dict(m) for m in given]

    # step 2: one model call, outside the lock (raises LLMError -> 503, queue untouched)
    memory = "\n".join(f"- {m['id']}: {m['statement']}" for m in given) or "- none"
    v = llm.ask_json(PROMPT.format(memory=memory, type_label=store.TYPE_LABEL[src["type"]],
                                   author=src["author"], title=src["title"], body=src["body"]), Verdict)

    # step 3: checks in code
    by_id = {m["id"]: m for m in given}
    conflict = by_id.get(v.conflict_memory_id or "")
    quote = v.conflict_quote if v.conflict_quote and v.conflict_quote in src["body"] else None
    facts = [f for f in v.facts[:2] if f.quote and f.quote in src["body"] and f.statement.strip()]

    with store.LOCK:
        st = store.S
        if not st["incoming"] or st["incoming"][0]["id"] != src["id"]:
            return {"event": None, "remaining": len(st["incoming"])}  # a reset happened meanwhile
        st["incoming"].pop(0)
        st["sources"].append(src)
        st["last_event"] = src
        label = store.TYPE_LABEL[src["type"]].lower()
        if conflict:  # step 4: alert to the lead, built from templates
            text = (f"{src['author']}'s {label} \"{src['title']}\" goes against a decision the team "
                    f"approved: {conflict['statement']} [1][2]")
            mem_cite = conflict["cites"][0]
            cites = [mem_cite, {"source_id": src["id"], "quote": quote}]
            action_ids = []
            author = store.person_by_name(st, src["author"])
            if author and author["id"] != lead["id"]:
                a = {
                    "id": store.new_id("act"),
                    "title": f"Ask {_first(author['name'])} to hold \"{src['title']}\"",
                    "reason": f"It goes against a decision the team approved: {conflict['statement']}",
                    "for_user": lead["id"], "status": "pending",
                    "effects": [{"type": "send_message", "to": author["id"],
                                 "text": (f"Your {label} \"{src['title']}\" goes against a team decision: "
                                          f"{conflict['statement']} Can we talk before it is merged?")}],
                    "cites": cites, "created_at": store.now(), "decided_at": None,
                }
                st["actions"].append(a)
                action_ids.append(a["id"])
            store.add_message(st, lead["id"], "brain", "alert", text, cites=cites, action_ids=action_ids)
        elif facts:  # step 5: memory proposals for the lead
            ids = []
            for f in facts:
                m = {"id": store.new_id("mem"), "statement": f.statement.strip(), "team": src["team"],
                     "visible_to": list(src["visible_to"]), "status": "proposed",
                     "cites": [{"source_id": src["id"], "quote": f.quote}],
                     "created_at": store.now(), "decided_by": None, "decided_at": None}
                st["memory"].append(m)
                ids.append(m["id"])
            n = "one thing" if len(ids) == 1 else f"{len(ids)} things"
            store.add_message(st, lead["id"], "brain", "alert",
                              f"New {label} from {src['author']}: \"{src['title']}\". I found {n} worth "
                              f"remembering. Should I? [1]",
                              cites=[{"source_id": src["id"], "quote": facts[0].quote}], memory_ids=ids)
        store.save()
        return {"event": src, "remaining": len(st["incoming"])}
