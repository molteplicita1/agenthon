# Data model and seed

All data is **fictional**. The story follows **Brightloop**, an invented software house in Turin,
and its client **Alpilog**, a logistics company. The seed in `backend/data/seed/` is the only
data source; nothing is fetched from Gmail, Slack, Drive, GitHub or Jira, whose names are labels
only.

## Files

| File | Holds | Count |
|---|---|---|
| `people.json` | The four people. | 4 |
| `sources.json` | The team's work: emails, chat threads, tasks, docs, pull requests. | 45 (15 chats, 12 emails, 8 tasks, 5 docs, 5 PRs) |
| `memory.json` | Facts the Brain remembers, approved or proposed. | 17 (15 approved, 2 proposed) |
| `actions.json` | Proposed actions waiting for a person. | 4 |
| `incoming.json` | Work that arrives during the demo and goes through the watcher. | 1 |
| `check_seed.py` | Standalone check of all the files; prints `SEED OK`. | |

`backend/demo_script.json` decides which seeded items the demo releases and in what order (see
[Backend](backend.md#the-demo-script-and-the-watcher-watcherpy)).

## People

| id | Name | Team | Lead | Title |
|---|---|---|---|---|
| `sara` | Sara Conti | sales | yes | Head of Sales |
| `giulia` | Giulia Ferri | tech | yes | Tech Lead |
| `marco` | Marco Riva | tech | no | Backend Developer |
| `luca` | Luca Moretti | finance | yes | Finance Manager |

The demo uses two Telegram accounts: one plays Giulia, the other Luca.

## Entities

**Source** — one piece of work.

```json
{
  "id": "src_email_golive", "type": "email", "title": "Alpilog go-live date",
  "author": "Elisa Brandt (Alpilog)", "timestamp": "2026-11-23T16:40:00",
  "body": "…", "team": "sales", "visible_to": ["all"]
}
```

Tasks also have `assignee` (person id), `due_date` and `status`. They are what the control room
shows on its task board.

**Memory item** — one fact, with the sources it comes from. Its team and visibility must equal
those of its first cited source; every quote must be an exact substring of the source body.

```json
{
  "id": "mem_golive", "statement": "Alpilog go-live moved from 11 Dec to 4 Dec 2026.",
  "team": "sales", "visible_to": ["all"], "status": "approved",
  "cites": [{"source_id": "src_email_golive", "quote": "bring the go-live forward to 4 December"}],
  "created_at": "2026-11-23T16:55:00", "decided_by": "sara", "decided_at": "2026-11-23T17:05:00"
}
```

**Action** — something the Brain proposes, with the effects that run if the person approves it.

```json
{
  "id": "act_golive", "title": "Move 'Alpilog – API migration' to 2 Dec and notify #tech",
  "reason": "Alpilog go-live moved to 4 Dec, but this task is due 9 Dec.",
  "for_user": "giulia", "status": "pending",
  "effects": [
    {"type": "update_task", "task_id": "task_api_migration", "changes": {"due_date": "2026-12-02"}},
    {"type": "send_message", "to": "#tech", "text": "Heads-up: …"}
  ],
  "cites": [{"source_id": "src_email_golive", "quote": "…"}, {"source_id": "task_api_migration", "quote": null}],
  "created_at": "…", "decided_at": null
}
```

In the seed the field is `cites` (source id + quote); the API renders it as numbered `citations`
with a ready-made label.

## The items the demo depends on

| id | What it is | Visible to | Role in the demo |
|---|---|---|---|
| `act_golive` | Move the API migration task to 2 Dec and notify `#tech`. | Giulia | Step 1 of the script. |
| `mem_pg` | "For Alpilog we chose PostgreSQL over MongoDB…" (proposed) | tech lead | Step 2. Unknown to `/ask` until approved. |
| `src_pr_mongo` | Marco's pull request "Add MongoDB store for Alpilog reports" (incoming). | tech | Step 3: the watcher catches it if `mem_pg` is approved. |
| `mem_contract` | "The Alpilog contract for 2026 is worth €84,000…" | finance | Luca gets the answer, Giulia gets "I don't know". |
| `mem_golive` | The go-live moved to 4 Dec. | all | Background of the go-live alert. |

The other approved items (review rules, Friday freeze, core hours, day rate, invoicing…) make the
memory realistic and give the model something to ignore. `act_key`, `act_flaky`, `act_kestrel`
and `mem_verdello` are left from earlier versions of the script: they exist in the seed but no
step releases them.

## Changing the seed

1. Edit the JSON files, keeping the rules above.
2. Run `python3 backend/data/seed/check_seed.py` until it prints `SEED OK`.
3. Restart the backend, which validates the seed again and refuses to start on errors.
4. If the demo depends on the change, run [`demo-video/demo.md`](../demo-video/demo.md) again.

`BRAIN_SEED_DIR` points the backend to another seed folder; `BRAIN_STATE_PATH` to another state file.
