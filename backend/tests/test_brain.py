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


def test_watcher_ignores_conflict_with_item_not_given(c, fake):  # rule 8
    calls = fake(conflict_memory_id="mem_pg", conflict_quote="adds a MongoDB collection", facts=[])
    r = c.post("/demo/next-event").json()
    assert r["event"]["id"] == "src_pr_mongo" and r["remaining"] == 0
    assert "mem_pg" not in calls[0]
    assert len(c.get("/state", headers=H("giulia")).json()["thread"]) == 1
    assert c.post("/demo/next-event").json() == {"event": None, "remaining": 0}


def test_watcher_conflict_alert_and_action(c, fake):
    c.post("/memory/mem_pg/approve", headers=H("giulia"))
    fake(conflict_memory_id="mem_pg", conflict_quote="not in the body", facts=[])
    c.post("/demo/next-event")
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["kind"] == "alert" and alert["text"].startswith("Marco Riva's pull request")
    assert [x["source_id"] for x in alert["citations"]] == ["src_chat_pg", "src_pr_mongo"]
    assert alert["citations"][1]["quote"] is None  # invalid quote becomes null
    act = alert["actions"][0]
    assert act["title"] == 'Ask Marco to hold "Add MongoDB store for Alpilog reports"'
    assert c.post(f"/actions/{act['id']}/approve", headers=H("marco")).status_code == 403
    assert c.post(f"/actions/{act['id']}/approve", headers=H("giulia")).status_code == 200
    out = c.get("/demo/overview").json()["outbox"]
    assert len(out) == 1 and out[0]["to"] == "marco"
    assert len(c.get("/state", headers=H("marco")).json()["thread"]) == 1  # nothing for Marco


def test_watcher_facts_become_proposals_for_lead_only(c, fake):
    fake(conflict_memory_id=None, conflict_quote=None,
         facts=[{"statement": "Alpilog reports are pre-aggregated.", "quote": "pre-aggregated shipment"},
                {"statement": "Made up.", "quote": "not in the body"}])
    c.post("/demo/next-event")
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["kind"] == "alert" and len(alert["memory_items"]) == 1
    m = alert["memory_items"][0]
    assert m["status"] == "proposed" and m["team"] == "tech" and m["visible_to"] == ["tech"] and m["can_decide"]
    for pid in ("marco", "sara", "luca"):
        assert len(c.get("/state", headers=H(pid)).json()["thread"]) == 1


def test_brief_falls_back_on_bad_marker(c, fake):
    fake(text="Good morning, Giulia. Something [9].")
    c.post("/demo/reset")
    text = c.get("/state", headers=H("giulia")).json()["thread"][0]["text"]
    assert text.startswith("Good morning, Giulia.") and "[9]" not in text and "[5]" in text
