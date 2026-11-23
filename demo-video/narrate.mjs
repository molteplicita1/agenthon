// Generates the narrator's voice, one MP3 per line of narration.json, with ElevenLabs.
// Reads ELEVENLABS_API_KEY from the project's .env. Clips are cached in out/narration/ by a hash
// of voice, model and text, so only changed lines cost characters.
//   node narrate.mjs
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DIR = path.join(HERE, 'out', 'narration');
fs.mkdirSync(DIR, { recursive: true });

const env = Object.fromEntries(fs.readFileSync(path.join(HERE, '..', '.env'), 'utf8').split('\n')
  .map((l) => l.match(/^\s*([A-Z_]+)\s*=\s*(.*)\s*$/)).filter(Boolean).map((m) => [m[1], m[2]]));
const KEY = env.ELEVENLABS_API_KEY || process.env.ELEVENLABS_API_KEY;
if (!KEY) throw new Error('ELEVENLABS_API_KEY missing in .env');

const { voice, model, lines } = JSON.parse(fs.readFileSync(path.join(HERE, 'narration.json'), 'utf8'));
const keys = Object.keys(lines);
const index = {};
for (let i = 0; i < keys.length; i++) {
  const k = keys[i], text = lines[k];
  const hash = crypto.createHash('sha1').update(`${voice}|${model}|${text}`).digest('hex').slice(0, 10);
  const file = path.join(DIR, `${k}-${hash}.mp3`);
  index[k] = path.relative(HERE, file);
  if (fs.existsSync(file)) continue;
  const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}?output_format=mp3_44100_192`, {
    method: 'POST',
    headers: { 'xi-api-key': KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text, model_id: model,
      previous_text: i > 0 ? lines[keys[i - 1]] : undefined,      // keeps the tone even across clips
      next_text: i + 1 < keys.length ? lines[keys[i + 1]] : undefined,
      voice_settings: { stability: 0.55, similarity_boost: 0.8, style: 0.15, use_speaker_boost: true, speed: 0.95 },
    }),
  });
  if (!r.ok) throw new Error(`${k}: ${r.status} ${(await r.text()).slice(0, 200)}`);
  fs.writeFileSync(file, Buffer.from(await r.arrayBuffer()));
  console.log('generated', k);
}
fs.writeFileSync(path.join(DIR, 'index.json'), JSON.stringify(index, null, 1));
console.log(`${keys.length} lines ready in out/narration/`);
