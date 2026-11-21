# Demo script = acceptance test

On screen, side by side: **Telegram** (left) and the **web page** (right).
Two Telegram accounts: account A plays Giulia (Tech Lead), account B plays Luca (Finance Manager).

## Before the demo

1. Backend, bot and web page are running.
2. In both Telegram accounts: clear the chat with the bot, send `/start`, pick the person.
3. Fictional time: Tuesday 24 Nov 2026, 09:00.

## The seven checks

1. It speaks first · 2. People curate the memory · 3. It knows who's asking ·
4. It cites · 5. It admits gaps · 6. It only proposes · 7. It fits the team's day

| # | Where | Do | Expected | Checks |
|---|---|---|---|---|
| 1 | Web | Press **Start the day**. | On Telegram, without anyone asking, Giulia receives the morning brief: Alpilog go-live moved to 4 Dec and clashes with her task due 9 Dec; Marco promised to rotate the staging API key by Friday and no task exists; two memory proposals wait for her. Right after it: two action cards and two memory cards, each with Approve / Reject. Luca receives his own brief. | 1, 7 |
| 2 | Telegram (Giulia) | Tap **Listen to the brief**. | A voice message arrives and plays. | 1, 7 |
| 3 | Telegram (Giulia) | On the go-live action card, tap the source button `[1]`. | The bot sends the Alpilog email. | 4 |
| 4 | Web | Look at the page. | Task "Alpilog – API migration" is due 9 Dec. "Sent messages" is empty. | 6 |
| 5 | Telegram (Giulia) | Tap **Approve** on "Move 'Alpilog – API migration' to 2 Dec and notify #tech". | The card shows "Approved". On the web page the task moves to 2 Dec and one message to #tech appears in "Sent messages". | 6 |
| 6 | Telegram (Giulia) | Ask: `Why did we choose PostgreSQL for Alpilog?` | `I don't know. I can't find this in the memory you have access to.` | 5 |
| 7 | Telegram (Giulia) | Tap **Approve** on the PostgreSQL memory card and **Reject** on the Azure one. | Both cards show the outcome. On the web page, "Company memory" shows one Approved and one Rejected. | 2 |
| 8 | Telegram (Giulia) | Ask again: `Why did we choose PostgreSQL for Alpilog?` | An answer about joins across shipments and invoices, with a footnote citing the #tech chat. | 2, 4 |
| 9 | Telegram (Giulia) | Ask: `Are we migrating to Azure?` | `I don't know. …` | 2 |
| 10 | Telegram (Giulia) | Ask: `What is the Alpilog contract value?` | `I don't know. …` | 3 |
| 11 | Telegram (Luca) | Ask the same question. | `€84,000`, with a footnote citing the contract summary. | 3, 4 |
| 12 | Telegram (Luca) | Ask: `What is our parental leave policy?` | `I don't know. …` | 5 |
| 13 | Web | Press **Simulate incoming event** (Marco opens a pull request). | Within a few seconds Giulia receives an alert on Telegram, without asking: Marco's pull request "Add MongoDB store for Alpilog reports" goes against the PostgreSQL decision approved in step 7. It cites the #tech chat and the pull request, and comes with the card "Ask Marco to hold …". She taps **Approve**: the message to Marco appears in "Sent messages" on the web page. | 1, 2, 4, 6 |

All thirteen steps are core. Step 13 is the moment that shows what is different:
the memory the team curates is what the Brain uses to watch new work.

**Counter-test for step 13.** Press **Start the day**, skip step 7 (leave the
PostgreSQL item proposed), press **Simulate incoming event**: no conflict alert may arrive.

## What each step proves about the product

- Steps 1–5: the Brain **speaks first**, where the team already is, and **only proposes**.
- Steps 6–9: the Brain **remembers decisions and their reasons**, but only what a lead confirmed.
- Steps 10–12: the Brain **respects who is asking** and **admits gaps**.
- Step 13: the memory is **active**: an approved decision makes the Brain flag work that goes against it.
