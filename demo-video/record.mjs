// Records the demo-video/demo.md script as a video: control room on the left, Giulia's and Luca's phones on the right.
// Needs the backend (port 8000) and the control room (port 5173) running, freshly started. The bot is not needed.
//   node narrate.mjs           → out/narration/*.mp3 (the narrator, needed first)
//   node record.mjs            → out/frames/*.jpg + out/timeline.json
//   node assemble.mjs          → out/brightloop-demo.mp4
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');
const FRAMES = path.join(OUT, 'frames');
const API = 'http://localhost:8000';
fs.rmSync(FRAMES, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });

const marks = [];
const mark = (name) => { marks.push({ name, t: Date.now() / 1000 }); };

const browser = await chromium.launch({ channel: 'chrome' });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const page = await context.newPage();
page.on('console', (m) => { if (m.type() === 'error') console.log('[page]', m.text()); });

await page.exposeFunction('brainApi', async (method, p, person, body) => {
  const headers = { 'Content-Type': 'application/json' };
  if (person) headers['X-User-Id'] = person;
  const r = await fetch(API + p, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let json = null;
  try { json = await r.json(); } catch {}
  return { status: r.status, json };
});
await page.exposeFunction('brainAudio', async (person) => {
  const r = await fetch(API + '/brief/audio', { headers: { 'X-User-Id': person } });
  if (!r.ok) return null;
  const buf = Buffer.from(await r.arrayBuffer());
  fs.writeFileSync(path.join(OUT, `voice-${person}.mp3`), buf);
  return buf.toString('base64');
});
await page.exposeFunction('brainMark', (name) => mark(name));

await page.goto('file://' + path.join(HERE, 'stage.html'));
const dash = await (async () => {
  for (let i = 0; i < 50; i++) {
    const f = page.frames().find((fr) => fr.url().startsWith('http://localhost:5173'));
    if (f) return f;
    await page.waitForTimeout(200);
  }
  throw new Error('control room iframe not found');
})();
await dash.waitForSelector('text=Start the day');
await dash.waitForSelector('.memory-card');
await page.evaluate(() => stage.start());
await page.evaluate(() => stage.card({ h: '', instant: true }));   // black screen while everything settles
await page.waitForTimeout(2500);

// ---------- screencast ----------
const cdp = await context.newCDPSession(page);
const frames = [];
let n = 0;
cdp.on('Page.screencastFrame', ({ data, metadata, sessionId }) => {
  const file = `f${String(n++).padStart(6, '0')}.jpg`;
  fs.writeFileSync(path.join(FRAMES, file), Buffer.from(data, 'base64'));
  frames.push({ file, t: metadata.timestamp });
  cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
});
await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
mark('start');

// ---------- helpers ----------
const S = (fn, arg) => page.evaluate(fn, arg);
const hold = (ms) => page.waitForTimeout(ms);
const camera = (shot, ms) => S(([s, m]) => stage.camera(s, m), [shot, ms]);
const caption = (h, p) => S(([a, b]) => stage.caption(a, b), [h, p || '']);
const step = (k, checks) => S(([a, b]) => stage.step(a, b), [k, checks]);
const card = (o) => S((x) => stage.card(x), o);
const incoming = (p) => S((x) => stage.phones[x].incoming, p);
const waitIncoming = (p, before, timeout = 90000) =>
  page.waitForFunction(([x, b]) => stage.phones[x].incoming > b, [p, before], { timeout, polling: 200 });
const ask = (p, q) => S(([x, y]) => stage.phones[x].ask(y), [p, q]);
const tap = (p, label) => S(([x, y]) => stage.phones[x].tap(y), [p, label]);

// Finders run inside the control room. Each returns the element's rect in its own CSS pixels.
const FIND = {
  button: (t) => [...document.querySelectorAll('button')].find((b) => b.textContent.includes(t)),
  task: (t) => [...document.querySelectorAll('.task-card')].find((e) => e.textContent.includes(t)),
  outboxPanel: () => document.querySelector('[aria-labelledby="sent-messages-heading"]'),
  lastOutbox: () => [...document.querySelectorAll('.outbox-card')].sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top)[0],
  outboxTo: (t) => [...document.querySelectorAll('.outbox-card')].find((e) => e.textContent.includes(t)),
  memory: (t) => [...document.querySelectorAll('.memory-card')].find((e) => e.textContent.includes(t)),
  caught: () => document.querySelector('.caught-tag'),
};
async function rect(finder, arg) {
  return dash.evaluate(([src, a]) => {
    const el = eval(src)(a);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height };
  }, [FIND[finder].toString(), arg]);
}
async function scrollTo(finder, arg) {
  await dash.evaluate(([src, a]) => {
    const el = eval(src)(a);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [FIND[finder].toString(), arg]);
  await hold(1000);
}
const scrollTop = async () => { await dash.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await hold(900); };
async function highlight(finder, arg, label) {
  const r = await rect(finder, arg);
  if (!r) { console.log('highlight: not found', finder, arg); return null; }
  await S(([a, b]) => stage.highlight(a, b), [r, label]);
  return r;
}
async function focusDash(r, s = 1.32) {
  const c = await S(([x, y]) => stage.dashToStage(x, y), [r.x + r.w / 2, r.y + r.h / 2]);
  await camera({ cx: c.x, cy: c.y, s });
}
async function clickDash(label) {
  const r = await rect('button', label);
  const c = await S(([x, y]) => stage.dashToStage(x, y), [r.x + r.w / 2, r.y + r.h / 2]);
  await S(([x, y]) => stage.pointTo(x, y), [c.x, c.y]);
  await hold(250);
  await S(([x, y]) => stage.clickAt(x, y), [c.x, c.y]);
  await dash.evaluate(([src, t]) => eval(src)(t).click(), [FIND.button.toString(), label]);
  await hold(500);
  await S(() => stage.hidePointer());
}
const T = (s) => s; // marker for on-screen text


// ---------- narration: every line of the narrator sets the pace ----------
const NARR = JSON.parse(fs.readFileSync(path.join(OUT, 'narration', 'index.json'), 'utf8'));
const DUR = Object.fromEntries(Object.entries(NARR).map(([k, f]) => [k,
  parseFloat(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path.join(HERE, f)]).toString())]));
let busyUntil = 0;
// Waits for the narrator to finish the current line, then holds `extra` ms more.
async function idle(extra = 0) { const w = busyUntil - Date.now(); if (w > 0) await hold(w); if (extra) await hold(extra); }
// Starts a line (after the previous one has ended). Returns at once: the action can go on under the voice.
async function say(key) {
  if (!(key in DUR)) throw new Error(`no narration for ${key}`);
  await idle();
  mark('say:' + key);
  busyUntil = Date.now() + DUR[key] * 1000 + 250;
}

// ================================================================ the film
// Intro
await card({ h: 'BrightLoop', p: 'A linter for company decisions.' });
await hold(900);
await say('intro1');
await idle(700);
await card({ k: 'Live demo', h: 'One morning at Brightloop.', p: 'Real backend, real model calls, Telegram on two phones.<br>Waits for the model are shortened.' });
await hold(700);
await say('intro2');
await idle(400);
await camera('all', 10);
await card(null);
await caption(T('Two people. Two empty chats.'), T('Giulia leads Tech. Luca runs Finance. Nothing has been sent.'));
await say('empty');
await idle(500);

// Chapter 1
await card({ light: true, h: 'It speaks <span class="grad">first</span>.', p: 'Where the team already is.' });
await hold(600);
await say('ch1');
await idle(300);
await card(null);

// Step 1 — Start the day
await step(1, ['1 · Speaks first', '7 · Fits the day']);
await caption(T('Start the day.'), T('One press in the control room.'));
await say('s1a');
await hold(1000);
let g = await incoming('giulia'), l = await incoming('luca');
await clickDash('Start the day');
await waitIncoming('giulia', g); await waitIncoming('luca', l);
await idle();
await camera('phones');
await caption(T('Everyone gets a morning brief.'), T('Unasked. As text, then as voice.'));
await say('s1b');
await idle(300);
await S(() => stage.phones.giulia.playVoice());
await hold(800);

// Step 2 — first tech event
await camera('all');
await step(2, ['1 · Speaks first', '4 · Cites', '6 · Only proposes']);
await caption(T('Then, something happens.'), T('Alpilog brings its go-live forward to 4 Dec.'));
await say('s2a');
await hold(1600);
g = await incoming('giulia');
await clickDash('Simulate tech event');
await waitIncoming('giulia', g);
await idle();
await camera('giulia');
await caption(T('One message. The alert and a proposal.'), T('Her task is due 9 Dec. Move it to 2 Dec? With its sources, [1] and [2].'));
await say('s2b');
await idle(900);
await camera('dash');
await caption(T('Nothing has changed yet.'), T('The task is still due 9 Dec. No message has been sent.'));
await highlight('task', 'API migration', 'Due 9 Dec');
await highlight('outboxPanel', null, 'Nothing sent');
await say('s2c');
await idle(900);
await S(() => stage.clearHighlights());

// Step 3 — Approve
await step(3, ['6 · Only proposes']);
await camera('giulia');
await caption(T('Giulia approves.'), T('Only now does anything happen.'));
await say('s3a');
await idle(200);
await tap('giulia', 'Approve');
await hold(1600);
await camera('dash');
await hold(1400);
await caption(T('The task moves to 2 Dec. #tech is told.'), T('Simulated tools, real effects of one approval.'));
await highlight('task', 'API migration', 'Now due 2 Dec');
await highlight('lastOutbox', null, 'Sent to #tech');
await say('s3b');
await idle(1100);
await S(() => stage.clearHighlights());

// Chapter 2
await card({ h: 'It remembers.<br>Only what you <span class="grad">approve</span>.' });
await hold(600);
await say('ch2');
await idle(400);
await camera('giulia', 10);
await card(null);

// Step 4 — unknown
await step(4, ['5 · Admits gaps']);
await caption(T('Giulia asks why.'), T('The reason was agreed in a chat, but nobody approved it as memory.'));
await say('s4a');
await idle(200);
await ask('giulia', 'Why did we choose PostgreSQL for Alpilog?');
await caption(T('It admits the gap.'), T('No guessing. No made-up answer.'));
await say('s4b');
await idle(900);

// Step 5 — memory proposal
await step(5, ['2 · People curate the memory']);
await camera('all');
await caption(T('The Brain noticed that decision.'), T('Before remembering it, it asks the lead of the team.'));
await say('s5a');
await hold(1800);
g = await incoming('giulia');
await clickDash('Simulate tech event');
await waitIncoming('giulia', g);
await camera('giulia');
await idle(700);
await caption(T('Giulia approves it.'), T('PostgreSQL over MongoDB, because reporting needs joins.'));
await hold(900);
await tap('giulia', 'Approve');
await hold(1500);
await scrollTo('memory', 'PostgreSQL');
await hold(900);
let r = await highlight('memory', 'PostgreSQL', 'Approved by Giulia');
if (r) await focusDash(r, 1.3);
await caption(T('Now it is company memory.'), T('Approved by the lead of its team. Visible to Tech.'));
await say('s5b');
await idle(1300);
await S(() => stage.clearHighlights());

// Step 6 — answer with citation
await step(6, ['2 · Curated memory', '4 · Cites']);
await camera('giulia');
await caption(T('Same question, again.'), '');
await say('s6a');
await idle(200);
await ask('giulia', 'Why did we choose PostgreSQL for Alpilog?');
await caption(T('Now it knows. And it cites.'), T('The footnote points to the #tech chat where it was decided.'));
await say('s6b');
await idle(700);
await tap('giulia', '[1]');
await caption(T('Every footnote opens its source.'), '');
await say('s6c');
await idle(1800);

// Chapter 3
await card({ h: 'Memory that <span class="grad">watches</span>.', p: 'An approved decision becomes a rule for new work.' });
await hold(600);
await say('ch3');
await scrollTop();
await idle(400);
await camera('all', 10);
await card(null);

// Step 7 — the conflict
await step(7, ['1 · Speaks first', '2 · Curated memory', '4 · Cites', '6 · Only proposes']);
await caption(T('Marco opens a pull request.'), T('“Add MongoDB store for Alpilog reports.”'));
await say('s7a');
await idle(200);
g = await incoming('giulia');
await clickDash('Simulate tech event');
mark('wait-start');
await waitIncoming('giulia', g);
mark('wait-end');
await camera('giulia');
await caption(T('It goes against what Giulia approved.'), T('Nobody asked. The Brain cites the decision and the pull request.'));
await say('s7b');
await idle(1500);
await scrollTo('memory', 'PostgreSQL');
r = await highlight('caught', null, 'Caught');
if (r) await focusDash(r, 1.3);
await caption(T('The decision caught new work.'), T('On the control room, the approved item now carries the pull request.'));
await say('s7c');
await idle(1300);
await S(() => stage.clearHighlights());
await camera('giulia');
await caption(T('Still, it only proposes.'), T('Giulia approves the note asking Marco to hold.'));
await say('s7d');
await hold(2600);
await tap('giulia', 'Approve');
await hold(1600);
await idle();
await scrollTo('outboxTo', 'Marco');
await hold(600);
r = await highlight('outboxTo', 'Marco', 'Sent to Marco');
if (r) await focusDash(r, 1.25);
await hold(2800);
await S(() => stage.clearHighlights());

// Chapter 4
await card({ light: true, h: 'Same question.<br><span class="grad">Two answers</span>.', p: 'It knows who is asking.' });
await hold(600);
await say('ch4');
await idle(400);
await camera('phones', 10);
await card(null);

// Step 8 — Giulia, restricted
await step(8, ["3 · Knows who's asking", '5 · Admits gaps']);
await caption(T('Giulia asks about the contract.'), '');
await say('s8a');
await idle(200);
await ask('giulia', 'What is the Alpilog contract value?');
await caption(T('Tech cannot see Finance documents.'), T('The Brain does not even reveal that they exist.'));
await say('s8b');
await idle(800);

// Step 9 — Luca, allowed
await step(9, ["3 · Knows who's asking", '4 · Cites']);
await caption(T('Luca asks the same.'), '');
await say('s9a');
await idle(200);
await ask('luca', 'What is the Alpilog contract value?');
await camera('luca');
await caption(T('€84,000.'), T('For Finance, with the contract summary as its source.'));
await say('s9b');
await idle(1800);

// Outro
await card({ h: 'Seven checks.', list: ['It speaks first', 'People curate the memory', "It knows who's asking", 'It cites', 'It admits gaps', 'It only proposes', "It fits the team's day"] });
await hold(500);
await say('outro1');
await S(() => stage.revealList(420));
await idle(900);
await card({ h: 'BrightLoop', p: 'A linter for company decisions.' });
await hold(700);
await say('outro2');
await idle(3200);

mark('end');
await cdp.send('Page.stopScreencast');
await hold(300);
fs.writeFileSync(path.join(OUT, 'timeline.json'), JSON.stringify({ frames, marks }, null, 1));
console.log(`frames: ${frames.length}, length: ${(marks.at(-1).t - marks[0].t).toFixed(1)} s`);
await browser.close();
