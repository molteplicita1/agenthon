#!/usr/bin/env python3
"""Standalone check of the seed files (CONTRACT.md sections 9 and 10, DEMO.md traps).
Usage: python3 check_seed.py      (run from anywhere)"""
import json, re, sys
from pathlib import Path

D = Path(__file__).parent
load = lambda n: json.load(open(D / n, encoding="utf-8"))
people, sources, memory, actions, incoming = (load(f + ".json") for f in
                                              ("people", "sources", "memory", "actions", "incoming"))
errors = []
err = lambda m: errors.append(m)

NOW = "2026-11-24T09:00:00"
TEAMS = {"sales", "tech", "finance"}
ID_RE = re.compile(r"^[a-z0-9_]{1,40}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ---- people: exactly the four of section 4
want = {"sara": ("Sara Conti", "sales", True, "Head of Sales"), "giulia": ("Giulia Ferri", "tech", True, "Tech Lead"),
        "marco": ("Marco Riva", "tech", False, "Backend Developer"), "luca": ("Luca Moretti", "finance", True, "Finance Manager")}
got = {p["id"]: (p["name"], p["team"], p["is_lead"], p["title"]) for p in people}
if got != want:
    err("people.json must be exactly the four people of CONTRACT section 4")

# ---- rule 4 (part 1): unique, well-formed ids
all_src = sources + incoming
src = {s["id"]: s for s in all_src}
ids = [x["id"] for x in all_src + memory + actions]
for i in ids:
    if not ID_RE.match(i):
        err(f"bad id '{i}' (only a-z 0-9 _, max 40 chars)")
for i in {i for i in ids if ids.count(i) > 1}:
    err(f"duplicate id '{i}'")

# ---- sources: shape, rules 3 and 5
for s in all_src:
    i = s["id"]
    if s["type"] not in ("email", "chat", "doc", "task", "pr"):
        err(f"{i}: bad type")
    if s["team"] not in TEAMS:
        err(f"{i}: bad team")
    if not TS_RE.match(s["timestamp"]):
        err(f"{i}: bad timestamp")
    if not s["body"].strip() or not s["title"].strip() or not s["author"].strip():
        err(f"{i}: empty title/author/body")
    v = s["visible_to"]
    if not v or not all(x in TEAMS | {"all"} for x in v) or not ("all" in v or s["team"] in v):
        err(f"{i}: visible_to must be ['all'] or contain its team")
    if s in sources and s["timestamp"] > NOW:
        err(f"{i}: timestamp after {NOW}")                      # rule 5
    if (s["type"] == "task") != ("assignee" in s):
        err(f"{i}: assignee/due_date/status only for tasks")
    if s["type"] == "task":
        if s["assignee"] not in got: err(f"{i}: unknown assignee")
        if not DATE_RE.match(s.get("due_date", "")): err(f"{i}: bad due_date")
        if s.get("status") not in ("todo", "in_progress", "done"): err(f"{i}: bad status")
    if s["type"] == "chat":
        lines = s["body"].split("\n")
        if not (1 <= len(lines) <= 6) or not all(re.match(r"^[A-Z][a-z]+: .+", l) for l in lines):
            err(f"{i}: chat must be 1-6 lines 'Name: text'")
        if s["title"] not in ("#tech", "#sales", "#finance", "#random"):
            err(f"{i}: chat title must be a channel")

# ---- cites: rules 1 and 4
def check_cites(owner, cites):
    for c in cites:
        s = src.get(c["source_id"])
        if s is None:
            err(f"{owner}: unknown source {c['source_id']}")                 # rule 4
        elif c["quote"] is not None and c["quote"] not in s["body"]:
            err(f"{owner}: quote not found in {c['source_id']}: {c['quote']!r}")  # rule 1
        elif c["quote"] is None and s["type"] != "task":
            err(f"{owner}: quote is null on non-task {c['source_id']}")

for m in memory:
    i = m["id"]
    if not m["cites"]: err(f"{i}: needs at least one cite")
    check_cites(i, m["cites"])
    first = src.get(m["cites"][0]["source_id"])
    if first and (m["team"] != first["team"] or m["visible_to"] != first["visible_to"]):
        err(f"{i}: team/visible_to differ from its first source")             # rule 2
    v = m["visible_to"]
    if not ("all" in v or m["team"] in v): err(f"{i}: visible_to must include its team")   # rule 3
    if m["status"] not in ("proposed", "approved", "rejected"): err(f"{i}: bad status")
    if m["created_at"] > NOW or (m["decided_at"] or "") > NOW: err(f"{i}: timestamp after now")
    if first and m["created_at"] < first["timestamp"]: err(f"{i}: created before its source")
    if m["status"] == "proposed" and (m["decided_by"] or m["decided_at"]): err(f"{i}: proposed but decided")
    if m["status"] != "proposed":
        lead = next((p for p in people if p["id"] == m["decided_by"]), None)
        if not lead or not lead["is_lead"] or lead["team"] != m["team"] or not m["decided_at"]:
            err(f"{i}: must be decided by the lead of its team")

TEAM_OF_ASSIGNEE = {p["id"]: p["team"] for p in people}
for a in actions:
    i = a["id"]
    if a["for_user"] not in got: err(f"{i}: unknown for_user")
    if a["status"] not in ("pending", "approved", "rejected"): err(f"{i}: bad status")
    if a["created_at"] > NOW: err(f"{i}: timestamp after now")
    check_cites(i, a["cites"])
    if not a["cites"]: err(f"{i}: needs at least one cite")
    for c in a["cites"]:                       # the person must be allowed to see what is cited
        s = src.get(c["source_id"])
        if s and "all" not in s["visible_to"] and got[a["for_user"]][1] not in s["visible_to"]:
            err(f"{i}: {a['for_user']} cannot see cited source {s['id']}")
    for e in a["effects"]:
        t = e["type"]
        if t == "update_task" and (src.get(e["task_id"], {}).get("type") != "task"): err(f"{i}: update_task on unknown task")
        if t == "create_task" and (e["assignee"] not in got or not DATE_RE.match(e["due_date"])): err(f"{i}: bad create_task")
        # target: a person id, a channel, or an outside contact written as "Name (Company)"
        if t == "send_message" and e["to"] not in got and e["to"] not in ("#tech", "#sales", "#finance", "#random") \
                and not re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+ \([A-Z][A-Za-z ]+\)$", e["to"]):
            err(f"{i}: bad send_message target {e['to']}")
        if t not in ("update_task", "create_task", "send_message"): err(f"{i}: unknown effect {t}")

# ---- section 9: pinned items
def need(cond, msg):
    if not cond: err("pinned: " + msg)
mem = {m["id"]: m for m in memory}
act = {a["id"]: a for a in actions}
S = lambda i: src.get(i, {})
need(S("src_email_golive").get("timestamp") == "2026-11-23T16:40:00" and "bring the go-live forward to 4 December" in S("src_email_golive").get("body", "")
     and S("src_email_golive").get("visible_to") == ["all"] and S("src_email_golive").get("team") == "sales", "src_email_golive")
need(mem.get("mem_golive", {}).get("status") == "approved" and mem["mem_golive"]["decided_by"] == "sara"
     and mem["mem_golive"]["decided_at"] == "2026-11-23T17:05:00", "mem_golive approved by sara 23 Nov 17:05")
t = S("task_api_migration")
need(t.get("assignee") == "giulia" and t.get("due_date") == "2026-12-09" and t.get("status") == "in_progress"
     and t.get("title") == "Alpilog – API migration" and t.get("team") == "tech" and t.get("visible_to") == ["all"], "task_api_migration")
need(act.get("act_golive", {}).get("for_user") == "giulia" and act["act_golive"]["status"] == "pending", "act_golive pending for giulia")
need(S("src_chat_key").get("timestamp") == "2026-11-23T11:12:00" and S("src_chat_key").get("visible_to") == ["tech"]
     and S("src_chat_key").get("title") == "#tech", "src_chat_key")
ak = act.get("act_key", {})
need(ak.get("for_user") == "giulia" and ak.get("status") == "pending" and ak.get("effects") == [
    {"type": "create_task", "title": "Rotate staging API key", "assignee": "marco", "due_date": "2026-11-27"}], "act_key")
need(S("src_chat_pg").get("timestamp") == "2026-11-23T10:15:00" and S("src_chat_pg").get("visible_to") == ["tech"], "src_chat_pg")
need(mem.get("mem_pg", {}).get("status") == "proposed" and mem["mem_pg"]["visible_to"] == ["tech"], "mem_pg proposed, tech only")
need(S("src_chat_azure").get("timestamp") == "2026-11-23T13:30:00" and S("src_chat_azure").get("title") == "#random"
     and S("src_chat_azure").get("visible_to") == ["all"] and S("src_chat_azure").get("team") == "tech", "src_chat_azure")
need("mem_azure" not in mem, "mem_azure is out of the seed (CONTRACT section 18)")
need("€84,000" in S("src_doc_contract").get("body", "") and S("src_doc_contract").get("visible_to") == ["finance"]
     and S("src_doc_contract").get("team") == "finance", "src_doc_contract")
need(mem.get("mem_contract", {}).get("status") == "approved" and mem["mem_contract"]["decided_by"] == "luca"
     and mem["mem_contract"]["visible_to"] == ["finance"], "mem_contract approved by luca, finance only")
need([s["id"] for s in incoming] == ["src_pr_mongo"] and incoming[0]["type"] == "pr", "incoming.json holds only src_pr_mongo")
need("src_pr_mongo" not in {s["id"] for s in sources}, "src_pr_mongo must not be in sources.json")
need(incoming and incoming[0]["team"] == "tech" and incoming[0]["visible_to"] == ["tech"]
     and incoming[0]["author"] == "Marco Riva" and "Giulia Ferri" in incoming[0]["body"], "src_pr_mongo fields")

# ---- counts asked by TASKS_DATA (D1)
cnt = {k: sum(1 for s in sources if s["type"] == k) for k in ("email", "chat", "task", "doc", "pr")}
if cnt != {"email": 12, "chat": 15, "task": 8, "doc": 5, "pr": 5}: err(f"source counts differ from plan: {cnt}")
n_app = sum(1 for m in memory if m["status"] == "approved")
if n_app < 13: err(f"only {n_app} approved memory items (aim for about 15)")
# one brief item per person
pend = {p: [a["id"] for a in actions if a["for_user"] == p and a["status"] == "pending"] for p in got}
prop = {p["id"]: [m["id"] for m in memory if m["status"] == "proposed" and m["team"] == p["team"]] for p in people if p["is_lead"]}
for p in got:
    if not pend[p] and not prop.get(p): err(f"{p}: nothing waiting for their morning brief")
if sorted(pend["giulia"] + prop["giulia"]) != ["act_golive", "act_key", "mem_pg"]:
    err("giulia must have exactly act_golive, act_key, mem_pg waiting")

# ---- DEMO traps (D2): where each keyword may appear
text = lambda x: json.dumps(x, ensure_ascii=False).lower()
def only_in(word, allowed, pools):
    hits = sorted(x["id"] for pool in pools for x in pool if word in text(x))
    if sorted(allowed) != hits: err(f"keyword '{word}' appears in {hits}, expected {sorted(allowed)}")
everything = [sources, incoming, memory, actions]
only_in("mongo", ["src_chat_pg", "src_pr_mongo", "mem_pg"], everything)          # mem_pg is pinned by the contract
only_in("postgres", ["src_chat_pg", "mem_pg"], everything)
only_in("azure", ["src_chat_azure"], everything)
only_in("aws", ["src_chat_azure"], everything)
only_in("84,000", ["src_doc_contract", "mem_contract"], everything)
only_in("staging", ["src_chat_key", "act_key"], everything)
only_in("api key", ["src_chat_key", "act_key"], everything)
for w in ("parental", "maternity", "paternity", "leave"):
    only_in(w, [], everything)
late = [s["id"] for s in sources if "go-live" in text(s) and s["timestamp"] > "2026-11-23T16:40:00"]
if late: err(f"go-live mentioned after the clash email: {late}")
if [s["id"] for s in sources if re.search(r"\b1[0-9] dec|\b[0-9] dec", text(s)) and "go-live" in text(s)
        and s["timestamp"] >= "2026-11-23T16:40:00" and s["id"] != "src_email_golive"]:
    err("another source gives a go-live date after the clash email")
if [s["id"] for s in sources + incoming if s["id"] != "src_doc_contract" and "alpilog" in text(s) and "€" in s["body"]]:
    err("an Alpilog source states an amount other than the contract summary")
# the pull request must clash only with mem_pg: no approved item may talk about stores, databases or reports
for m in memory:
    if m["status"] == "approved" and re.search(r"database|mongo|postgres|collection|report", m["statement"].lower()) \
            and "expense" not in m["statement"].lower():
        err(f"approved {m['id']} may clash with src_pr_mongo")

if errors:
    print("SEED CHECK FAILED")
    for e in errors: print(" -", e)
    sys.exit(1)
print(f"SEED OK: {len(people)} people, {len(sources)} sources {cnt}, {len(memory)} memory items "
      f"({n_app} approved), {len(actions)} actions, {len(incoming)} incoming")
