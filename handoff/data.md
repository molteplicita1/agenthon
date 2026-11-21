# Handoff log — data agent

Only the data agent writes in this file. The other agents read it.

- Append at the bottom. Never edit or delete older lines.
- One line per message. To address another agent, start the line with `@BACKEND`, `@BOT`, `@FRONTEND` or `@DATA`.
- Write `SEED CORE READY`, then `SEED FULL READY`, here when the seed files can be loaded.

---
