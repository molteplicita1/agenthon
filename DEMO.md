# Demo script = acceptance test

On screen, side by side: **Telegram** (left) and the **web page** (right).
Two Telegram accounts: account A plays Giulia (Tech Lead), account B plays Luca (Finance Manager).

One rule keeps the demo readable: **one message at a time, never twice.** Starting the
system sends nothing. "Start the day" sends only the morning brief, and the brief never
announces what an event will bring later. Every other message arrives when the presenter
presses **Simulate tech event** (messages for Giulia) or **Simulate finance event**
(messages for Luca). An alert and its card arrive together as one Telegram message.
The line "Next: …" under each button says what the press will send.

## Before the demo

Restarting is the way to start a new demo: the backend starts from the seed (task due
9 Dec, nothing sent, nothing approved) and the bot deletes from both chats what the last
run left there. Chats stay tied to their person.

1. Start backend, bot and web page. Nothing arrives on Telegram; the web page shows the start of the day.
2. Only the first time, or after a new account: in each Telegram account send `/start`
   and pick the person, then clear the chat history once by hand. Nothing else arrives.

## The seven checks

1. It speaks first · 2. People curate the memory · 3. It knows who's asking ·
4. It cites · 5. It admits gaps · 6. It only proposes · 7. It fits the team's day

| # | Where | Do | Expected | Checks |
|---|---|---|---|---|
| 1 | Web | Press **Start the day**. | Giulia receives, without asking, exactly two messages: a short morning brief as text ("Good morning, Giulia. Nothing needs you right now. I will message you as soon as something does."), then the same brief as a voice message. No cards, no sources. Luca receives his own brief and voice. | 1, 7 |
| 2 | Web | Press **Simulate tech event** (1st press). | Giulia receives one message, alert and card together: Alpilog go-live moved to 4 Dec but her task is due 9 Dec, with "Proposed: Move 'Alpilog – API migration' to 2 Dec and notify #tech" and the Approve / Reject buttons. | 1, 6 |
| 3 | Telegram (Giulia) | On that message, tap the source button `[1]`. | The bot sends the Alpilog email. | 4 |
| 4 | Web | Look at the page. | Task "Alpilog – API migration" is due 9 Dec. "Sent messages" is empty. | 6 |
| 5 | Telegram (Giulia) | Tap **Approve**. | The message shows "Approved". On the web page the task moves to 2 Dec and one message to #tech appears in "Sent messages". | 6 |
| 6 | Telegram (Giulia) | Ask: `Why did we choose PostgreSQL for Alpilog?` | `I don't know. I can't find this in the memory you have access to.` | 5 |
| 7 | Web, then Telegram (Giulia) | Press **Simulate tech event** (2nd press). Tap **Approve** on the message that arrives. | The message asks whether to remember the PostgreSQL decision. After the tap it shows "Approved", and "Company memory" on the web page shows the item as Approved. | 2 |
| 8 | Telegram (Giulia) | Ask again: `Why did we choose PostgreSQL for Alpilog?` | An answer about joins across shipments and invoices, with a footnote citing the #tech chat. | 2, 4 |
| 9 | Telegram (Giulia) | Ask: `Are we migrating to Azure?` | `I don't know. …` (the Azure proposal was never approved). | 2 |
| 10 | Telegram (Giulia) | Ask: `What is the Alpilog contract value?` | `I don't know. …` | 3 |
| 11 | Telegram (Luca) | Ask the same question. | `€84,000`, with a footnote citing the contract summary. | 3, 4 |
| 12 | Telegram (Luca) | Ask: `What is our parental leave policy?` | `I don't know. …` | 5 |
| 13 | Web, then Telegram (Luca) | Press **Simulate finance event**. Tap **Approve** on the message that arrives. | Luca receives one message: Kestrel Freight has not paid invoice 2026-031, promised by 16 Nov, now 8 days late, with "Proposed: Send the first payment reminder to Kestrel Freight". After Approve, the reminder to Martina Gallo appears in "Sent messages" and a follow-up task for Luca appears on the board. | 1, 4, 6 |
| 14 | Web, then Telegram (Giulia) | Press **Simulate tech event** (3rd and last press: Marco opens a pull request). Then tap **Approve**. | Within a few seconds Giulia receives one message: Marco's pull request "Add MongoDB store for Alpilog reports" goes against the PostgreSQL decision approved in step 7, citing the #tech chat and the pull request, with "Proposed: Ask Marco to hold …". On the web page the PostgreSQL item in "Company memory" shows the tag "Caught: Pull request …". After Approve, the message to Marco appears in "Sent messages". | 1, 2, 4, 6 |

Step 14 is the moment that shows what is different: the memory the team curates
is what the Brain uses to watch new work.

Note on step 14: Approve and Reject on "Ask Marco to hold …" never change a memory
item. Approve adds a line to "Sent messages"; Reject changes nothing. What changes
in "Company memory" is the "Caught" tag, and it appears when the alert arrives.

**Counter-test for step 14.** Press **Start the day**, then press **Simulate
tech event** three times without approving the PostgreSQL card: no conflict
alert may arrive and no "Caught" tag may appear.

## What each step proves about the product

- Steps 1–5: the Brain **speaks first**, where the team already is, and **only proposes**.
- Steps 6–9: the Brain **remembers decisions and their reasons**, but only what a lead confirmed.
- Steps 10–12: the Brain **respects who is asking** and **admits gaps**.
- Step 13: the Brain **speaks first for finance too**: it notices a client that has not paid.
- Step 14: the memory is **active**: an approved decision makes the Brain flag work that goes against it.
