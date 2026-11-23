// Turns out/frames + out/timeline.json into out/brightloop-demo.mp4.
// Waits for the model (between "wait-start" and "wait-end" marks) are shortened to KEEP seconds.
// Sound: the narrator (narrate.mjs), Giulia's real brief voice, a soft chime per message, and
// background music (music.py) that ducks under the voices. Loudness is normalised to -16 LUFS.
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

const NARR = fs.existsSync(path.join(OUT, 'narration', 'index.json'))
  ? JSON.parse(fs.readFileSync(path.join(OUT, 'narration', 'index.json'), 'utf8')) : {};
const voices = [], fx = [];   // voices: the narrator and the Brain's brief; fx: chimes
let last = { giulia: -9, luca: -9 };
for (const m of marks) {
  const [kind, who] = m.name.split(':');
  const at = map(m.t);
  if (kind === 'msg' && at - last[who] > 0.6) { fx.push({ file: chime, at, vol: 0.45 }); last[who] = at; }
  if (kind === 'voice' && fs.existsSync(path.join(OUT, `voice-${who}.mp3`))) voices.push({ file: path.join(OUT, `voice-${who}.mp3`), at, vol: 0.9 });
  if (kind === 'say' && NARR[who]) voices.push({ file: path.join(HERE, NARR[who]), at, vol: 1.0 });
}

// Background music, as long as the film, from music.py.
const music = path.join(OUT, 'music.wav');
execFileSync('python3', [path.join(HERE, 'music.py'), total.toFixed(2), music]);

const args = ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(OUT, 'frames.txt'), '-i', music];
const cues = [...voices, ...fx];
for (const c of cues) args.push('-i', c.file);
const st = 'aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo';
const parts = cues.map((c, i) => `[${i + 2}:a]${st},volume=${c.vol},adelay=${Math.round(c.at * 1000)}:all=1[c${i}]`);
const bus = (from, to, name) => to - from === 0 ? `anullsrc=r=48000:cl=stereo[${name}]`
  : `${Array.from({ length: to - from }, (_, k) => `[c${from + k}]`).join('')}amix=inputs=${to - from}:normalize=0:dropout_transition=0,apad[${name}]`;
const graph = [
  '[0:v]fps=30,scale=1920:1080:flags=lanczos,format=yuv420p[v]',
  ...parts,
  bus(0, voices.length, 'vbus'),
  bus(voices.length, cues.length, 'fx'),
  '[vbus]asplit=2[vmix][vkey]',
  // the music sits low and ducks a further ~10 dB while someone speaks
  `[1:a]${st},volume=0.30[mus]`,
  '[mus][vkey]sidechaincompress=threshold=0.012:ratio=6:attack=40:release=650:knee=4[mduck]',
  '[vmix][mduck][fx]amix=inputs=3:normalize=0:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]',
].join(';');
args.push('-filter_complex', graph,
  '-map', '[v]', '-map', '[aout]', '-t', total.toFixed(2),
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-tune', 'stillimage', '-movflags', '+faststart',
  '-c:a', 'aac', '-b:a', '192k', path.join(OUT, 'brightloop-demo.mp4'));
execFileSync('ffmpeg', args, { stdio: 'inherit' });
console.log(`out/brightloop-demo.mp4 · ${total.toFixed(1)} s · ${voices.length} voice clips · ${fx.length} chimes · music`);
