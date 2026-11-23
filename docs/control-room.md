# Control room

A Vite + React 19 + TypeScript page in `frontend/`, shown next to Telegram during the demo. It
stands in for the team's tools, which the prototype does not connect to: it shows the simulated
task board, the simulated sent messages and the company memory, and it holds the demo buttons.
It is **read-only** for people and **not part of the product**.

```bash
cd frontend && npm install && npm run dev
```

It opens at <http://localhost:5173> (fixed port: the backend's CORS allows only this origin).

## Layout

| Part | Shows |
|---|---|
| Header | **Start the day** (`POST /demo/reset`) and **Simulate tech event** (`POST /demo/next-event?track=tech`), with a "Next: …" line saying what the next press will send, and the fictional clock. |
| Last event | The source behind the latest event. |
| Task board | The task sources in Jira-style columns (To do, In progress, Done) with assignee and due date. |
| Sent messages | The simulated outbox filled by approved actions. |
| Company memory | Every memory item with its status, citations and the **Caught** tag when a decision caught conflicting work. |

The page polls `GET /demo/overview` every 2 seconds and briefly highlights what changed since
the previous poll (a moved task, a new sent message, a decided or caught memory item).

## Files

| File | What it does |
|---|---|
| [`src/App.tsx`](../frontend/src/App.tsx) | The whole page: polling, change highlighting, buttons, sections. |
| [`src/api.ts`](../frontend/src/api.ts) | The three calls, error handling and normalisation of the overview. |
| [`src/types.ts`](../frontend/src/types.ts) | TypeScript versions of the API shapes, the people and the demo tracks. |
| [`src/format.ts`](../frontend/src/format.ts) | Date, time and label formatting. |
| [`src/mockData.ts`](../frontend/src/mockData.ts) | An in-browser copy of the demo for mock mode. |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Where the backend is. |
| `VITE_USE_MOCK` | `false` | `true` runs the page on `mockData.ts`, without a backend. |

```bash
cd frontend && VITE_USE_MOCK=true npm run dev
```

Only the tech track has a button: the finance track of the demo script is empty
(`TRACKS` in `types.ts`).
