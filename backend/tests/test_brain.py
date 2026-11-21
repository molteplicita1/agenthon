"""Rules 4, 5 and 8 are enforced in code, whatever the model says. The model is faked."""
import pytest
from conftest import H

import llm
import store


@pytest.fixture
def fake(monkeypatch):
    calls = []

    def install(**answer):
        def ask_json(prompt, schema):
            calls.append(prompt)
            return schema(**answer)
        monkeypatch.setattr(llm, "ask_json", ask_json)
        return calls
    return install


def ask(c, user, q="Why did we choose PostgreSQL for Alpilog?"):
    return c.post("/ask", headers=H(user), json={"question": q}).json()


def test_ask_only_sees_approved_visible_memory(c, fake):  # rule 4
    calls = fake(answerable=False, answer="", used_memory_ids=[])
    ask(c, "giulia")
    assert "mem_pg" not in calls[0] and "mem_contract" not in calls[0] and "mem_golive" in calls[0]


def test_ask_drops_ids_not_given(c, fake):  # rule 5
    fake(answerable=True, answer="It is worth €84,000.", used_memory_ids=["mem_contract", "mem_pg"])
    r = ask(c, "giulia")
    assert r["answerable"] is False and r["text"] == store.IDK and r["citations"] == []


def test_ask_cites_used_items(c, fake):  # rule 5
    c.post("/memory/mem_pg/approve", headers=H("giulia"))
    fake(answerable=True, answer="Because reporting needs joins [3].", used_memory_ids=["mem_pg"])
    r = ask(c, "giulia")
    assert r["answerable"] is True and r["text"] == "Because reporting needs joins [1]."
    assert [x["source_id"] for x in r["citations"]] == ["src_chat_pg"]
    kinds = [m["kind"] for m in c.get("/state", headers=H("giulia")).json()["thread"]]
    assert kinds == ["brief", "question", "answer"]


def test_ask_model_failure_is_503(c):
    assert c.post("/ask", headers=H("giulia"), json={"question": "x"}).status_code == 503


def press(c, n=1, track="tech"):
    return [c.post(f"/demo/next-event?track={track}").json() for _ in range(n)][-1]


def to_watcher(c, approve_pg=True):
    """Run the two release steps, approving mem_pg if asked, so the next press is the watcher."""
    press(c, 2)
    if approve_pg:
        assert c.post("/memory/mem_pg/approve", headers=H("giulia")).status_code == 200


def test_script_order_and_next_step(c, fake):
    fake(conflict_memory_id=None, conflict_quote=None, alert_text=None, message_to_author=None, facts=[])
    o = c.get("/demo/overview").json()
    assert o["remaining_events"] == {"tech": 3, "finance": 0} and o["last_event"] is None
    assert o["next_step"]["tech"] == "Action for Giulia Ferri: Move 'Alpilog – API migration' to 2 Dec and notify #tech"
    assert o["next_step"]["finance"] is None  # finance track left out of the pitch (section 18)
    r = press(c)
    assert r["event"]["id"] == "src_email_golive" and r["remaining"] == 2
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["text"] == "Alpilog go-live moved to 4 Dec, but this task is due 9 Dec."
    assert [x["source_id"] for x in alert["citations"]] == ["src_email_golive", "task_api_migration"]
    assert c.get("/demo/overview").json()["next_step"]["tech"].startswith("Memory proposal for Giulia Ferri: For Alpilog")
    press(c)
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["text"] == "I noticed this in Chat · #tech · Mon 23 Nov 10:15. Should I remember it?"
    assert c.get("/demo/overview").json()["next_step"]["tech"] == \
        "New pull request by Marco Riva: Add MongoDB store for Alpilog reports"
    press(c)
    whom = {pid: [x["id"] for m in c.get("/state", headers=H(pid)).json()["thread"][1:]
                  for x in m["actions"] + m["memory_items"]] for pid in ("giulia", "marco", "luca", "sara")}
    assert whom == {"giulia": ["act_golive", "mem_pg"], "marco": [], "luca": [], "sara": []}
    o = c.get("/demo/overview").json()
    assert o["remaining_events"] == {"tech": 0, "finance": 0} and o["next_step"] == {"tech": None, "finance": None}
    assert press(c) == {"event": None, "remaining": 0}
    assert press(c, track="finance") == {"event": None, "remaining": 0}
    assert c.post("/demo/next-event?track=sales").status_code == 404


def test_watcher_ignores_conflict_with_item_not_given(c, fake):  # rule 8 and the counter-test
    to_watcher(c, approve_pg=False)
    calls = fake(conflict_memory_id="mem_pg", conflict_quote="adds a MongoDB collection",
                 alert_text="Bad.", message_to_author="Bad.", facts=[])
    r = press(c)
    assert r["event"]["id"] == "src_pr_mongo" and r["remaining"] == 0
    assert "mem_pg" not in calls[0]
    assert len(c.get("/state", headers=H("giulia")).json()["thread"]) == 3  # brief + 2 releases
    assert all(m["caught"] == [] for m in c.get("/demo/overview").json()["memory"])


def test_watcher_uses_model_text_and_marks_caught(c, fake):
    to_watcher(c)
    fake(conflict_memory_id="mem_pg", conflict_quote="not in the body",
         alert_text="Marco's pull request adds a MongoDB store for Alpilog reports, but the team chose PostgreSQL.",
         message_to_author="Hi Marco, this PR adds MongoDB but we chose PostgreSQL. Can we talk before merging?",
         facts=[{"statement": "x", "quote": "pre-aggregated"}])
    press(c)
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["text"] == ("Marco's pull request adds a MongoDB store for Alpilog reports, "
                             "but the team chose PostgreSQL. [1][2]")
    assert [x["source_id"] for x in alert["citations"]] == ["src_chat_pg", "src_pr_mongo"]
    assert alert["citations"][1]["quote"] is None  # invalid quote becomes null
    act = alert["actions"][0]
    assert act["title"] == 'Ask Marco to hold "Add MongoDB store for Alpilog reports"'
    assert act["effects"][0]["text"].startswith("Hi Marco")
    mem = {m["id"]: m for m in c.get("/demo/overview").json()["memory"]}
    assert mem["mem_pg"]["caught"] == ["Pull request · Add MongoDB store for Alpilog reports · Tue 24 Nov 09:00"]
    assert len(mem) == 17  # facts are discarded when there is a conflict
    assert c.post(f"/actions/{act['id']}/approve", headers=H("marco")).status_code == 403
    assert c.post(f"/actions/{act['id']}/approve", headers=H("giulia")).status_code == 200
    out = c.get("/demo/overview").json()["outbox"]
    assert len(out) == 1 and out[0]["to"] == "marco" and out[0]["text"].startswith("Hi Marco")
    mem2 = {m["id"]: m for m in c.get("/demo/overview").json()["memory"]}
    assert mem2["mem_pg"]["status"] == "approved" and mem2["mem_pg"]["caught"] == mem["mem_pg"]["caught"]
    c.post("/demo/reset")
    assert all(m["caught"] == [] for m in c.get("/demo/overview").json()["memory"])


@pytest.mark.parametrize("alert_text,note", [
    (None, None), ("", "  "), ("word " * 61, "word " * 49), ("It clashes [1].", "See [2]."),
])
def test_watcher_falls_back_to_templates(c, fake, alert_text, note):  # B10b
    to_watcher(c)
    fake(conflict_memory_id="mem_pg", conflict_quote=None, alert_text=alert_text,
         message_to_author=note, facts=[])
    press(c)
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["text"] == ('Marco Riva\'s pull request "Add MongoDB store for Alpilog reports" goes against '
                             'a decision the team approved: For Alpilog we chose PostgreSQL over MongoDB because '
                             'reporting needs joins across shipments and invoices. [1][2]')
    assert alert["actions"][0]["effects"][0]["text"] == (
        'Your pull request "Add MongoDB store for Alpilog reports" goes against a team decision: For Alpilog '
        'we chose PostgreSQL over MongoDB because reporting needs joins across shipments and invoices. '
        'Can we talk before it is merged?')


def test_watcher_model_failure_keeps_the_step(c):
    to_watcher(c)
    assert c.post("/demo/next-event").status_code == 503
    assert c.get("/demo/overview").json()["remaining_events"]["tech"] == 1


def test_watcher_facts_become_proposals_for_lead_only(c, fake):
    to_watcher(c, approve_pg=False)
    fake(conflict_memory_id=None, conflict_quote=None, alert_text=None, message_to_author=None,
         facts=[{"statement": "Alpilog reports are pre-aggregated.", "quote": "pre-aggregated shipment"},
                {"statement": "Made up.", "quote": "not in the body"}])
    press(c)
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["kind"] == "alert" and len(alert["memory_items"]) == 1
    m = alert["memory_items"][0]
    assert m["status"] == "proposed" and m["team"] == "tech" and m["visible_to"] == ["tech"] and m["can_decide"]
    for pid in ("marco", "sara", "luca"):
        assert len(c.get("/state", headers=H(pid)).json()["thread"]) == 1


GIULIA = {"id": "giulia", "name": "Giulia Ferri", "title": "Tech Lead"}
ONE_FACT = {"facts": [{"id": "mem_x", "statement": "The office is closed on Friday.",
                       "cites": [{"source_id": "src_x", "quote": None}]}], "actions": [], "proposals": []}


def test_brief_falls_back_on_bad_marker(fake):
    import brief
    fake(text="Good morning, Giulia. Something [9].")
    text = brief.write_text(GIULIA, ONE_FACT, {"mem_x": [1]})
    assert text == "Good morning, Giulia. Since yesterday: The office is closed on Friday [1]."


def test_brief_falls_back_on_below(fake):
    import brief
    fake(text="Good morning, Giulia. Approve the cards below [1].")
    assert "below" not in brief.write_text(GIULIA, ONE_FACT, {"mem_x": [1]})


def test_brief_repeats_nothing_the_script_brings_later(c):  # no repetitions
    for pid in ("sara", "giulia", "marco", "luca"):
        b = c.get("/state", headers=H(pid)).json()["thread"][0]
        assert b["citations"] == []
        first = {"sara": "Sara", "giulia": "Giulia", "marco": "Marco", "luca": "Luca"}[pid]
        assert b["text"] == (f"Good morning, {first}. Nothing needs you right now. "
                             "I will message you as soon as something does.")


def test_startup_is_a_fresh_demo_without_brief(c, tmp_path, monkeypatch):  # change set 4
    monkeypatch.setattr(store, "STATE_PATH", tmp_path / "state.json")
    assert c.post("/actions/act_golive/approve", headers=H("giulia")).status_code == 200
    store.save()  # the end of a demo, on disk
    store.load_or_init()  # restart
    assert all(thread == [] for thread in store.S["threads"].values())
    assert store.S["outbox"] == [] and next(a for a in store.S["actions"] if a["id"] == "act_golive")["status"] == "pending"


def test_template_brief_fits_the_word_limit(c):  # the model is off here, so these are templates
    import brief
    for pid in ("sara", "giulia", "marco", "luca"):
        text = c.get("/state", headers=H(pid)).json()["thread"][0]["text"]
        assert brief.spoken_words(text) <= brief.MAX_WORDS, text
