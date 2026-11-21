# Handoff log — frontend agent

Only the frontend agent writes in this file. The other agents read it.

- Append at the bottom. Never edit or delete older lines.
- One line per message. To address another agent, start the line with `@BACKEND`, `@BOT`, `@FRONTEND` or `@DATA`.
- Write here what you need from the backend (a field, an endpoint, a fix).

---
FRONTEND READY — start: `cd frontend && npm install && npm run dev` (http://localhost:5173). Tasks F0-F3 implemented; defaults to real API at `VITE_API_URL` (http://localhost:8000), with mock mode behind `VITE_USE_MOCK=true`. Verified against live backend at 950px and 1440px.
F4 & F5 done — added `Next: <next_step>` / `No more steps` under Simulate incoming event and `Caught: <label>` tag + highlight in Company memory (missing `next_step` / `caught` normalized safely to undefined / `[]`). Verified at 950px in mock mode (`VITE_USE_MOCK=true`) and against `http://localhost:8000`.

## Change set 3 (Sat 21 Nov, afternoon)

- Two buttons, "Simulate tech event" and "Simulate finance event", each with its own
  "Next: …" line and "(n left)" count. `triggerNextEvent(track)` calls
  `/demo/next-event?track=…`. Overview types: `next_step` and `remaining_events` per track.
  Mock data updated to match.
- Verified: `tsc --noEmit` and `npm run build` pass. Not yet looked at in the browser.
