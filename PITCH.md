# Pitch: 3 minutes, demo included

Total budget: **3:00**. About 380 spoken words at a calm pace.

| Part | Time | Length |
|---|---|---|
| 1. The problem | 0:00 – 0:30 | 30 s |
| 2. The solution | 0:30 – 0:55 | 25 s |
| 3. The demo (9 steps) | 0:55 – 2:45 | 1 min 50 s |
| 4. Close | 2:45 – 3:00 | 15 s |

On screen: Telegram on the left (Giulia and Luca), the web page on the right.
Best setup: one person speaks, one person drives the demo.

---

## 1. The problem (0:00 – 0:30)

> In a company, decisions are everywhere.
> They are in emails, in chats, in tasks and in pull requests.
> It is impossible to read all of it.
>
> So things get lost.
> A deadline moves, and the team finds out too late.
> A developer writes code that goes against a decision from two weeks ago.
>
> And AI assistants don't fix this.
> They answer with confidence, even when they are wrong.
> And they often show information to the wrong person.

## 2. The solution (0:30 – 0:55)

> Our answer is **BrightLoop**.
>
> It watches the work of the teams in a company.
> It keeps a shared memory of decisions.
> But people stay in control: a team lead approves every fact.
>
> The agent is proactive and always cites its sources.
> It says "I don't know" when it doesn't have information to reply and if the question is outside the employee's scope.
> And it never acts alone. It only proposes.
>
> We decided to use Telegram since it's a popular app that employees are very likely to already use.
> Let's see it.

## 3. The demo (0:55 – 2:45)

Do the action first, then talk while the message arrives.

**Step 1 · Web: Start the day** (0:55 – 1:05)

> It's morning. Giulia is the Tech Lead. Luca is the Finance Manager.
> Nobody asked anything. But each of them gets a short brief, as text and as voice.

*Don't play the voice message to the end.*

**Step 2 · Web: Simulate tech event** (1:05 – 1:20)

> Now something changes. The client moved the go-live to the 4th of December.
> But Giulia's task is due on the 9th.
> The Brain sees the problem and tells her. With sources.
> And it proposes a fix: move the task, and tell the team.

**Step 3 · Telegram, Giulia: Approve** (1:20 – 1:30)

> Nothing happens until Giulia says yes.
> She taps Approve. The task moves. The message to the team is sent.

**Step 4 · Telegram, Giulia: ask** `Why did we choose PostgreSQL for Alpilog?` (1:30 – 1:40)

> Giulia asks why the team chose PostgreSQL.
> The Brain says: I don't know. It does not make things up.

**Step 5 · Web: Simulate tech event, then Approve in Telegram** (1:40 – 1:50)

> The decision is in a team chat. The Brain asks Giulia: should I remember this?
> She approves. Now it is part of the company memory.

*This Approve is required, or step 7 shows nothing.*

**Step 6 · Telegram, Giulia: ask the same question again** (1:50 – 2:00)

> Same question. Now the Brain answers.
> And it cites the chat where the team decided.

**Step 7 · Web: Simulate tech event, then Approve** (2:00 – 2:25)

> This is the most important part.
> Marco, a developer, opens a pull request. He adds MongoDB.
> But the team chose PostgreSQL.
> The Brain checks new work against the approved decisions.
> It finds the conflict and alerts Giulia, with both sources.
> It also proposes a note to Marco.
> The memory is not only for answers. **It is active.**

*The alert takes a few seconds: keep talking. Point at the "Caught" tag on the web page.*

**Steps 8 and 9 · Telegram: Giulia, then Luca ask** `What is the Alpilog contract value?` (2:25 – 2:45)

> Last thing. Giulia asks for the contract value. The Brain says: I don't know.
> Luca works in Finance. He asks the same question. He gets the answer: 84,000 euros.
> Same question. Two people. Two answers. The Brain knows who is asking.

## 4. Close (2:45 – 3:00)

> That's Company Brain.
> It speaks first. It cites. It admits gaps. And people stay in control.
> These rules are in the code, not in the prompt.
> Thank you!

---

## Tips

- **Paste the questions, don't type them.** Keep the two questions ready to copy.
- **If you are late**, skip step 4. The "I don't know" still appears in step 8.
- **If step 7 is slow**, keep talking about why it matters. Don't wait in silence.
- **Restart backend and bot just before the pitch**, so the chats are clean.
- Practise with a timer at least twice. Most teams run 20–30 seconds over the first time.
