# Development plans

BrightLoop was built in one day by four AI coding agents (backend, bot, frontend, data), each
working in its own folder, coordinated by two people. These files are the plans and logs of that
build. They are kept as a record: the current behaviour is described in the
[documentation](../README.md), and where the two disagree, the code and the documentation win.

| File | What it is |
|---|---|
| [`contract.md`](contract.md) | The specification every agent built against: types, endpoints, rules, pinned scenario data, bot and page behaviour. Sections 15–18 are the change sets made after the first tests. |
| [`handover.md`](handover.md) | Context, decisions with their reasons and status, written mid-hackathon for whoever took over. |
| [`tasks/`](tasks/) | The task list given to each agent (`backend.md`, `bot.md`, `data.md`, `frontend.md`). All tasks are done. |
| [`handoff/`](handoff/) | The work log each agent kept: what it did, verified and left open. The most detailed record of the build. |

## Paths in these files

The files were written before the repository was reorganised and still use the old paths:

| Old path | Now |
|---|---|
| `CONTRACT.md` | `docs/plans/contract.md` |
| `HANDOVER.md` | `docs/plans/handover.md` |
| `TASKS_BACKEND.md`, `TASKS_BOT.md`, `TASKS_DATA.md`, `TASKS_FRONTEND.md` | `docs/plans/tasks/*.md` |
| `handoff/*.md` | `docs/plans/handoff/*.md` |
| `DEMO.md` | `demo-video/demo.md` |
| `PITCH.md` | `demo-video/pitch.md` |
