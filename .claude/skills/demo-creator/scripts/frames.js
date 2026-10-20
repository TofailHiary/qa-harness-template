#!/usr/bin/env node
// demo-creator frame check: one JPG per chapter (2.5 s into the step) so the caption/voice/screen alignment can be read.
// Usage: node frames.js --demo <dir> [--ids A,B,C] [--offset 2.5]
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : def; };
const DEMO = opt('--demo');
if (!DEMO) { console.error('usage: node frames.js --demo <dir> [--ids A,B,C] [--offset 2.5]'); process.exit(2); }
const DIR = path.resolve(DEMO);
const OUT = path.join(DIR, 'out');
const ch = JSON.parse(fs.readFileSync(path.join(OUT, 'chapters.json'), 'utf8'));
const ids = opt('--ids', null) ? String(opt('--ids')).split(',') : ch.chapters.map((c) => c.id);
const offset = +opt('--offset', 2.5);
fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
for (const id of ids) {
  const c = ch.chapters.find((x) => x.id === id);
  if (!c) { console.log(id, 'not in chapters'); continue; }
  const t = Math.max(0, Math.min(c.at + offset, ch.durationSec - 0.5)).toFixed(2);
  const f = path.join(OUT, 'frames', id + '.jpg');
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-ss', t, '-i', ch.file, '-frames:v', '1', '-vf', 'scale=960:-1', f]);
  console.log(id.padEnd(8), '@', t + 's', f);
}
