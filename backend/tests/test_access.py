"""CONTRACT section 5 rules 1, 2, 3, 6 (task B1)."""
from conftest import H


def overview(c):
    return c.get("/demo/overview").json()


def task(c, tid):
    return next(t for t in overview(c)["tasks"] if t["id"] == tid)


def test_identity_required(c):
    assert c.get("/state").status_code == 401
    assert c.get("/state", headers=H("nobody")).status_code == 401


def test_giulia_cannot_read_contract(c):  # rule 1
    assert c.get("/sources/src_doc_contract", headers=H("giulia")).status_code == 403
    assert c.get("/sources/src_doc_contract", headers=H("luca")).status_code == 200
    assert c.get("/sources/task_api_migration", headers=H("luca")).status_code == 200
    assert c.get("/sources/nope", headers=H("luca")).status_code == 404


def test_marco_cannot_approve_mem_pg(c):  # rule 3
    assert c.post("/memory/mem_pg/approve", headers=H("marco")).status_code == 403
    assert c.post("/memory/mem_pg/approve", headers=H("luca")).status_code == 403
    r = c.post("/memory/mem_pg/approve", headers=H("giulia"))
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["decided_by"] == "giulia"
    assert c.post("/memory/mem_pg/reject", headers=H("giulia")).status_code == 409


def test_luca_cannot_approve_act_golive(c):  # rule 6
    assert c.post("/actions/act_golive/approve", headers=H("luca")).status_code == 403
    assert task(c, "task_api_migration")["due_date"] == "2026-12-09"
    assert overview(c)["outbox"] == []


def test_brief_embeds_no_cards(c):  # section 11
    for pid in ("sara", "giulia", "marco", "luca"):
        thread = c.get("/state", headers=H(pid)).json()["thread"]
        assert len(thread) == 1 and thread[0]["kind"] == "brief"
        assert thread[0]["actions"] == [] and thread[0]["memory_items"] == []
        text = thread[0]["text"]
        assert "below" not in text.lower() and "card" not in text.lower()
        if pid != "giulia":  # rules 2 and 7: proposals only reach their lead
            assert "PostgreSQL" not in text and "Azure" not in text


def test_proposed_item_released_only_to_its_lead(c):  # rules 2 and 7
    for _ in range(2):
        c.post("/demo/next-event")
    for pid in ("sara", "marco", "luca"):
        assert len(c.get("/state", headers=H(pid)).json()["thread"]) == 1
    alerts = c.get("/state", headers=H("giulia")).json()["thread"][1:]
    assert [m["kind"] for m in alerts] == ["alert"] * 2
    assert [x["id"] for m in alerts for x in m["actions"] + m["memory_items"]] == ["act_golive", "mem_pg"]
    assert all(x["can_decide"] for m in alerts for x in m["memory_items"])


def test_approve_golive_changes_task_and_outbox(c):  # rule 6
    r = c.post("/actions/act_golive/approve", headers=H("giulia"))
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert task(c, "task_api_migration")["due_date"] == "2026-12-02"
    out = overview(c)["outbox"]
    assert len(out) == 1 and out[0]["to"] == "#tech" and out[0]["action_id"] == "act_golive"
    assert c.post("/actions/act_golive/approve", headers=H("giulia")).status_code == 409
    # a later release embeds the action with its current status
    c.post("/demo/next-event")
    alert = c.get("/state", headers=H("giulia")).json()["thread"][-1]
    assert alert["actions"][0]["id"] == "act_golive" and alert["actions"][0]["status"] == "approved"


def test_reject_changes_nothing(c):  # rule 6
    before = overview(c)
    r = c.post("/actions/act_golive/reject", headers=H("giulia"))
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    after = overview(c)
    assert after["tasks"] == before["tasks"] and after["outbox"] == []


def test_create_task_effect(c):
    n = len(overview(c)["tasks"])
    assert c.post("/actions/act_key/approve", headers=H("giulia")).status_code == 200
    tasks = overview(c)["tasks"]
    assert len(tasks) == n + 1
    new = tasks[-1]
    assert new["title"] == "Rotate staging API key" and new["assignee"] == "marco"
    assert new["due_date"] == "2026-11-27" and new["status"] == "todo"


def test_message_ids_unique_across_resets(c):
    a = c.get("/state", headers=H("giulia")).json()["thread"][0]["id"]
    c.post("/demo/reset")
    b = c.get("/state", headers=H("giulia")).json()["thread"][0]["id"]
    assert a != b
