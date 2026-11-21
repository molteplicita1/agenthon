# Data tasks (data agent)

Read `CONTRACT.md` and `DEMO.md` in full first.
You own `backend/data/seed/` and `handoff/data.md`, nothing else.

## Goal

Write the synthetic data of Brightloop, a fictional 12-person software house in
Turin, covering Mon 9 Nov – Tue 24 Nov 2026 09:00. It must read like the real
traces of a team at work: short, informal, sometimes messy, never like a brochure.

## Rules

- **Simplicity first.** Plain JSON files and one small check script. Nothing else.
- Write only in the files you own. No code outside the seed folder.
- **No git commands that change the repository** (add, commit, checkout, stash,
  reset). Several agents share this folder; the humans commit.
- **Invent everything.** Do not download, fetch or copy data from Gmail, Slack,
  Google Drive, GitHub, any website or any real repository. Do not use the network
  at all. Emails, chats, tasks, documents and pull requests are all written by you
  (`CONTRACT.md` section 1).
- Follow the file list, shapes and the six rules in `CONTRACT.md` section 10 exactly.
- The pinned items in `CONTRACT.md` section 9 must exist with those exact ids and facts.
- Everything in English. Fictional names only; use the `.example` domain for emails.
- `handoff/data.md` is the only handoff file you write. If something in the
  contract is unclear or impossible, write a line there instead of guessing.
- Before each task read `handoff/backend.md`: the backend agent reports seed problems there.

## Tasks, in order

**D0 — Core seed (target: 15 minutes).**
Write the five files with only: the four people and every pinned item of section 9
(`src_pr_mongo` goes in `incoming.json`, everything else in the other files).
Then append `SEED CORE READY` to `handoff/data.md`. The backend agent is waiting for this.

**D1 — Full seed.**
Grow `sources.json` to about 45 sources:

| Type | How many | Notes |
|---|---|---|
| `email` | 12 | Clients, suppliers, internal. Subject in `title`. |
| `chat` | 15 | One source = one short thread (1–6 lines, `Name: text`) in #tech, #sales, #finance or #random. |
| `task` | 8 | With `assignee`, `due_date`, `status`. Assignees are among the four people. |
| `doc` | 5 | Contract summary, a postmortem, a pricing sheet, onboarding notes, meeting notes. |
| `pr` | 5 | Title like a real pull request; body holds description, state (open or merged), reviewers. `team` tech, `visible_to` tech. None about MongoDB. |

Other colleagues and outside contacts may appear as authors by name. Only the four
people of section 4 have accounts.

Grow `memory.json` to about 15 **approved** items spread across sales, tech and
finance, each with a cite and an exact quote. Include decisions with their reason,
not only plain facts.

So that every morning brief has something real in it: give Sara and Luca one
pending action or one memory proposal each, and give Marco one pending action
(he is not a lead, so memory proposals never go to him).

**D2 — Protect the demo.** Check by hand, then state the result in `handoff/data.md`:

- Nothing mentions a parental leave policy.
- Only `src_doc_contract` states the Alpilog contract value, and it is finance-only.
- Only `src_chat_pg` explains the PostgreSQL choice. No approved item covers it.
- No approved item says anything about Azure.
- No other source gives a different Alpilog go-live date after Mon 23 Nov 16:40.
- No second task or message already handles the staging API key.
- Only `src_chat_pg` and `src_pr_mongo` mention MongoDB.
- The pull request `src_pr_mongo` goes against `mem_pg` and against no other memory item.

**D3 — Self-check.**
Write `backend/data/seed/check_seed.py`: a small standalone script that loads the
five files and verifies the six rules of section 10 plus the pinned ids of
section 9. Run it and fix every error. Append `SEED FULL READY` to `handoff/data.md`.

## Done when

`check_seed.py` passes, and the backend loads the seed without errors.
