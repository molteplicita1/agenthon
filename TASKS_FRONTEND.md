# Frontend tasks (Antigravity)

Read `CONTRACT.md` and `DEMO.md` in full first. Section 14 of the contract is your spec.
You own `frontend/` and `handoff/frontend.md`.

## What this page is

One web page: the **control room** of the demo. It sits next to a Telegram window
on a projector and shows the audience what happens in the simulated tools when
someone taps a button on Telegram.

It is **not** where people talk to the Brain: that happens on Telegram, built by
another agent. So there is no chat, no login, no user switcher and no approve
buttons here.

## Rules

- **Simplicity first.** One page. Few dependencies, no state library, no router.
  If two ways work, pick the one with less code.
- Write only in the files you own. Never touch `backend/`, `bot/` or `CONTRACT.md`.
- `handoff/frontend.md` is the only handoff file you write. If you need a field,
  an endpoint or a change, add a line there.
- Before each task read `handoff/backend.md`: the backend agent announces changes there.
- **No git commands that change the repository** (add, commit, checkout, stash,
  reset). Several agents share this folder; the humans commit.
- Vite + React + TypeScript on port 5173. All text in English.
- The page talks only to our backend, and only to these three endpoints:
  `GET /demo/overview`, `POST /demo/reset`, `POST /demo/next-event`.
  No calls to any other service. No real logos: generic icons and the labels of
  `CONTRACT.md` section 6.
- Read-only: no way to create or edit tasks, messages or memory items.

## Before the backend is ready

Until `handoff/backend.md` contains `BACKEND SKELETON READY`, work on local mock
data that matches the `Overview` type (`CONTRACT.md` section 6, pinned items in
section 9). Put it behind `VITE_USE_MOCK=true` so switching to the real API is one setting.

## Layout

The page is shown at about half a screen (around 950 px wide) and read from far
away: large text, strong contrast, little decoration.

```
┌───────────────────────────────────────────────────────────────┐
│ Brightloop · simulated tools                 Tue 24 Nov 2026  │
│ Demo control room. Not part of the product.                   │
├───────────────────────────────────────────────────────────────┤
│ [ Start the day ]  [ Simulate incoming event ]                │
│ Last event: Pull request · Marco Riva · Add MongoDB store…    │
├───────────────────────────────────────────────────────────────┤
│ TASK BOARD                                                    │
│  To do            In progress            Done                 │
│ ┌─────────────┐  ┌──────────────────┐   ┌─────────────┐       │
│ │ Reporting UI│  │ API migration    │   │ …           │       │
│ │ Marco·1 Dec │  │ Giulia · 9 Dec   │   │             │       │
│ └─────────────┘  └──────────────────┘   └─────────────┘       │
├──────────────────────────────┬────────────────────────────────┤
│ SENT MESSAGES                │ COMPANY MEMORY                 │
│ Nothing has been sent.       │ [Proposed] PostgreSQL over…    │
│                              │ [Approved] Go-live moved to…   │
└──────────────────────────────┴────────────────────────────────┘
```

## Tasks, in order

**F0 — Scaffold.**
Project, a small typed API client for the three endpoints, the types copied from
`CONTRACT.md` section 6, mock mode.

**F1 — The page.**
- Header with the fixed line "Demo control room. Not part of the product." and the
  fictional date from `now`.
- Demo controls: **Start the day** and **Simulate incoming event**. Each shows a
  spinner while the backend works (a few seconds). "Simulate incoming event" is
  disabled when `remaining_events` is 0. Below them, a card with `last_event`.
- Task board: one column per status, one card per task with title, assignee name
  and due date.
- Sent messages: recipient and text, newest first. Empty state: "Nothing has been sent."
- Company memory: each item with a status tag (Proposed / Approved / Rejected), the
  statement, a "visible to" tag (All, Tech, Finance, Sales) and who decided.
  Proposed items first.

**F2 — Live updates.**
Poll `GET /demo/overview` every 2 seconds. When something changes (a due date, a
new sent message, a memory status), highlight it clearly for about three seconds,
so the audience notices the effect of a tap on Telegram.

**F3 — Errors and polish.**
Backend unreachable shows one clear banner. Check the page at 950 px and 1440 px wide.

## Done when

During a run of `DEMO.md`, every change expected "on the web page" shows up within
two seconds, with no reload.
