"""Effects of an approved action (rule 6). They change the state only; nothing real is sent."""
import store


def run_effects(st: dict, a: dict) -> None:
    for e in a["effects"]:
        if e["type"] == "update_task":
            task = store.source(st, e["task_id"])
            if task:
                task.update(e["changes"])
        elif e["type"] == "create_task":
            assignee = store.person(st, e["assignee"])
            team = assignee["team"] if assignee else "tech"
            st["sources"].append({
                "id": store.new_id("task"), "type": "task", "title": e["title"],
                "author": store.person(st, a["for_user"])["name"], "timestamp": store.now(st),
                "body": a["reason"], "team": team, "visible_to": [team],
                "assignee": e["assignee"], "due_date": e["due_date"], "status": "todo",
            })
        elif e["type"] == "send_message":
            st["outbox"].append({"id": store.new_id("out"), "to": e["to"], "text": e["text"],
                                 "sent_at": store.now(st), "action_id": a["id"]})
