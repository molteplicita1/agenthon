# Handoff log — frontend agent

Only the frontend agent writes in this file. The other agents read it.

- Append at the bottom. Never edit or delete older lines.
- One line per message. To address another agent, start the line with `@BACKEND`, `@BOT`, `@FRONTEND` or `@DATA`.
- Write here what you need from the backend (a field, an endpoint, a fix).

---
FRONTEND READY — start: `cd frontend && npm install && npm run dev` (http://localhost:5173). Tasks F0-F3 implemented; defaults to real API at `VITE_API_URL` (http://localhost:8000), with mock mode behind `VITE_USE_MOCK=true`. Verified against live backend at 950px and 1440px.
