// Turns out/frames + out/timeline.json into out/brightloop-demo.mp4.
// Waits for the model (between "wait-start" and "wait-end" marks) are shortened to KEEP seconds.
// Sound: a soft chime when a phone receives a message, and Giulia's real brief voice when it plays.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');
const KEEP = 1.6;
const { frames, marks } = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'));

const t0 = frames[0].t;
const tEnd = marks.find((m) => m.name === 'end').t;
const waits = [];
for (let i = 0; i < marks.length; i++) {
  if (marks[i].name !== 'wait-start') continue;
  const end = marks.slice(i + 1).find((m) => m.name === 'wait-end');
  if (end) waits.push([marks[i].t, end.t]);
}
function map(t) {
  let out = t - t0;
  for (const [a, b] of waits) {
    const L = b - a;
    if (L <= KEEP || t <= a) continue;
    out -= t >= b ? L - KEEP : (t - a) * (1 - KEEP / L);
  }
  return out;
}
console.log('waits shortened:', waits.map(([a, b]) => (b - a).toFixed(1) + 's').join(', ') || 'none');

// ---------- video: concat list with per-frame durations ----------
const lines = [];
for (let i = 0; i < frames.length; i++) {
  const next = i + 1 < frames.length ? frames[i + 1].t : tEnd;
  const d = Math.max(0, map(next) - map(frames[i].t));
  if (d === 0 && i + 1 < frames.length) continue;
  lines.push(`file 'frames/${frames[i].file}'`, `duration ${d.toFixed(4)}`);
}
lines.push(`file 'frames/${frames.at(-1).file}'`);
fs.writeFileSync(path.join(OUT, 'frames.txt'), lines.join('\n'));
const total = map(tEnd);

// ---------- audio ----------
const chime = path.join(OUT, 'chime.wav');
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
  'aevalsrc=0.30*sin(2*PI*1318.5*t)*exp(-9*t)+0.22*sin(2*PI*1975.5*t)*exp(-11*t)*gte(t\\,0.075):s=48000:d=0.7',
  '-af', 'afade=t=in:d=0.004', chime]);

const cues = [];
let last = { giulia: -9, luca: -9 };
for (const m of marks) {
  const [kind, who] = m.name.split(':');
  const at = map(m.t);
  if (kind === 'msg' && at - last[who] > 0.6) { cues.push({ file: chime, at, vol: 0.55 }); last[who] = at; }
  if (kind === 'voice' && fs.existsSync(path.join(OUT, `voice-${who}.mp3`))) cues.push({ file: path.join(OUT, `voice-${who}.mp3`), at, vol: 1.0 });
}

const args = ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(OUT, 'frames.txt')];
for (const c of cues) args.push('-i', c.file);
const parts = cues.map((c, i) => `[${i + 1}:a]aresample=48000,volume=${c.vol},adelay=${Math.round(c.at * 1000)}:all=1[a${i}]`);
const mix = cues.length
  ? `${parts.join(';')};${cues.map((_, i) => `[a${i}]`).join('')}amix=inputs=${cues.length}:normalize=0:dropout_transition=0,apad[aout]`
  : 'anullsrc=r=48000:cl=stereo[aout]';
args.push('-filter_complex', `[0:v]fps=30,scale=1920:1080:flags=lanczos,format=yuv420p[v];${mix}`,
  '-map', '[v]', '-map', '[aout]', '-t', total.toFixed(2),
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-tune', 'stillimage', '-movflags', '+faststart',
  '-c:a', 'aac', '-b:a', '192k', path.join(OUT, 'brightloop-demo.mp4'));
execFileSync('ffmpeg', args, { stdio: 'inherit' });
console.log(`out/brightloop-demo.mp4 · ${total.toFixed(1)} s · ${cues.length} sound cues`);
