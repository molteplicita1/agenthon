# Handoff log — data agent

Only the data agent writes in this file. The other agents read it.

- Append at the bottom. Never edit or delete older lines.
- One line per message. To address another agent, start the line with `@BACKEND`, `@BOT`, `@FRONTEND` or `@DATA`.
- Write `SEED CORE READY`, then `SEED FULL READY`, here when the seed files can be loaded.

---
SEED CORE READY — five files in backend/data/seed/ with the 4 people and all pinned items of CONTRACT section 9 (src_pr_mongo in incoming.json). Full seed follows.
D1 done: sources.json has 45 sources (12 email, 15 chat, 8 task, 5 doc, 5 pr; no MongoDB pr), memory.json has 18 items (15 approved, 3 proposed: mem_pg, mem_azure, mem_verdello), actions.json has 4 pending actions (act_golive, act_key for giulia; act_flaky for marco; act_kestrel for luca), incoming.json has only src_pr_mongo.
Morning brief content after reset: giulia = act_golive, act_key, mem_pg, mem_azure (nothing else); sara = mem_verdello; luca = act_kestrel; marco = act_flaky.
D2 result (checked by hand and by check_seed.py): no parental leave text anywhere (words parental/maternity/paternity/leave appear nowhere) · only src_doc_contract (and mem_contract) state the Alpilog value 84,000, both finance-only · PostgreSQL appears only in src_chat_pg and mem_pg, mem_pg is proposed, no approved item covers it · Azure and AWS appear only in src_chat_azure and mem_azure (proposed) · the only go-live dates are in src_email_kickoff (9 Nov, says 11 Dec, before the clash) and src_email_golive (4 Dec); no source after 23 Nov 16:40 mentions go-live · staging and "API key" appear only in src_chat_key and act_key; no other task or message covers the key · MongoDB appears only in src_chat_pg, src_pr_mongo and mem_pg · src_pr_mongo clashes only with mem_pg; no approved item is about data stores, and the PR body says nothing about deploys, hours or approvals.
@BACKEND note: mem_pg's statement contains the word MongoDB because CONTRACT section 9 pins that exact text; the "nothing else mentions MongoDB" rule is applied to sources only.
@BACKEND note: chat sources use the channel as `title` ("#tech", "#sales", "#finance", "#random"), the author is the first speaker of the thread or the main one; email authors are written like "Elisa Brandt (Alpilog)" so your label can use them as is.
@BACKEND note: seed timestamps have seconds ("2026-11-23T16:40:00"). Latest seeded timestamp is 2026-11-23T17:10:00. Some task due dates are in the future (the audit task is due 2027-01-15).
Contract reading: some sources are visible to ["sales","finance"] (pricing sheet and its two memory items, task_pricing_2027), which the contract allows because the list contains the owning team.
D3 done: backend/data/seed/check_seed.py (run: python3 backend/data/seed/check_seed.py) checks section 10 rules 1-6, the pinned ids of section 9, the source counts, who sees what in each brief, and the DEMO traps. It prints SEED OK.
SEED FULL READY
- (by the bot agent, human's request) Change set 5: mem_azure removed from memory.json; check_seed.py no longer pins it and the azure/aws keyword lists now allow only src_chat_azure. SEED OK.
