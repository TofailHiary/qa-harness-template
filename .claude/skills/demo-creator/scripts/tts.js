#!/usr/bin/env node
// demo-creator narration: one WAV per step (22050 Hz, 16-bit, mono) from steps.json.
// Usage: node tts.js --demo <dir> [--engine edge|sapi|say|espeak] [--voice <name>] [--rate +0%] [--only ID] [--dry]
//   edge   = Microsoft neural voices via `python -m edge_tts` (free, needs internet); falls back per clip on failure to
//            the platform's offline engine (sapi on Windows, say on macOS, espeak-ng on Linux).
//   sapi   = Windows System.Speech (e.g. "Microsoft Zira Desktop"), offline.
//   say    = macOS `say`, offline.   espeak = espeak-ng, offline.
// Set the project's default voice/rate in PROJECT-PROFILE.md §18 and pass them here.
const fs = require('fs');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : def; };
const DEMO = opt('--demo');
if (!DEMO) { console.error('usage: node tts.js --demo <dir> [--engine edge|sapi|say|espeak] [--voice V] [--rate +0%] [--only ID] [--dry]'); process.exit(2); }
const DIR = path.resolve(DEMO);
const OUT = path.join(DIR, 'out', 'tts');
fs.mkdirSync(OUT, { recursive: true });
const WIN = process.platform === 'win32';
const MAC = process.platform === 'darwin';
const PY = WIN ? 'python' : 'python3';
const OFFLINE = WIN ? 'sapi' : (MAC ? 'say' : 'espeak');
const ENGINE = opt('--engine', 'edge');
const DEFAULT_VOICE = { edge: 'en-US-JennyNeural', sapi: 'Microsoft Zira Desktop', say: 'Samantha', espeak: 'en-us' };
const VOICE = opt('--voice', DEFAULT_VOICE[ENGINE] || DEFAULT_VOICE.edge);
const RATE = opt('--rate', '+0%');
const ONLY = opt('--only', null);
const DRY = !!opt('--dry', false);
const stepsFile = fs.existsSync(path.join(DIR, 'steps.json')) ? path.join(DIR, 'steps.json') : path.join(DIR, 'steps.example.json');
const steps = JSON.parse(fs.readFileSync(stepsFile, 'utf8'));

function wavSeconds(f) {
  const b = fs.readFileSync(f);
  let off = 12, fmt = null, dataLen = 0;
  while (off + 8 <= b.length) {
    const id = b.toString('ascii', off, off + 4); const sz = b.readUInt32LE(off + 4);
    if (id === 'fmt ') fmt = { ch: b.readUInt16LE(off + 10), rate: b.readUInt32LE(off + 12), bits: b.readUInt16LE(off + 22) };
    if (id === 'data') { dataLen = sz; break; }
    off += 8 + sz + (sz % 2);
  }
  return fmt ? dataLen / (fmt.rate * fmt.ch * (fmt.bits / 8)) : 0;
}
function toWav(src, dst) {
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-ar', '22050', '-ac', '1', '-sample_fmt', 's16', '-f', 'wav', dst], { stdio: 'inherit' });
}
function edge(text, dst, voice) {
  const mp3 = dst.replace(/\.wav$/, '.mp3');
  const r = spawnSync(PY, ['-m', 'edge_tts', '--voice', voice, '--rate=' + RATE, '--text', text, '--write-media', mp3], { encoding: 'utf8', timeout: 120000 });
  if (r.status !== 0 || !fs.existsSync(mp3) || fs.statSync(mp3).size < 1000) throw new Error('edge-tts failed: ' + ((r.stderr || r.stdout || '').trim().split('\n').pop() || 'no output'));
  toWav(mp3, dst);
  fs.unlinkSync(mp3);
}
function sapi(text, dst, voice) {
  const ps = `Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; try { $s.SelectVoice('${voice.replace(/'/g, "''")}') } catch {}; $fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono); $s.SetOutputToWaveFile('${dst.replace(/'/g, "''")}', $fmt); $s.Speak('${text.replace(/'/g, "''")}'); $s.Dispose()`;
  const r = spawnSync('powershell', ['-NoProfile', '-NonInteractive', '-Command', ps], { encoding: 'utf8', timeout: 120000 });
  if (r.status !== 0 || !fs.existsSync(dst)) throw new Error('sapi failed: ' + (r.stderr || '').trim().slice(0, 200));
}
function say(text, dst, voice) {
  const aiff = dst.replace(/\.wav$/, '.aiff');
  const r = spawnSync('say', ['-v', voice, '-o', aiff, text], { encoding: 'utf8', timeout: 120000 });
  if (r.status !== 0 || !fs.existsSync(aiff)) throw new Error('say failed: ' + (r.stderr || '').trim().slice(0, 200));
  toWav(aiff, dst);
  fs.unlinkSync(aiff);
}
function espeak(text, dst, voice) {
  const raw = dst.replace(/\.wav$/, '.raw.wav');
  const r = spawnSync('espeak-ng', ['-v', voice, '-w', raw, text], { encoding: 'utf8', timeout: 120000 });
  if (r.status !== 0 || !fs.existsSync(raw)) throw new Error('espeak-ng failed: ' + (r.stderr || '').trim().slice(0, 200));
  toWav(raw, dst);
  fs.unlinkSync(raw);
}
const ENGINES = { edge, sapi, say, espeak };
if (!ENGINES[ENGINE]) { console.error('unknown --engine', ENGINE); process.exit(2); }

let total = 0;
for (const s of steps) {
  if (ONLY && s.id !== ONLY) continue;
  const text = (s.voice || s.text || '').trim();
  if (!text) { console.log(s.id, 'SKIP (no text)'); continue; }
  const dst = path.join(OUT, s.id + '.wav');
  if (DRY) { console.log(s.id, text.length + ' chars'); continue; }
  let engine = ENGINE, voice = VOICE;
  try {
    ENGINES[ENGINE](text, dst, VOICE);
  } catch (e) {
    if (ENGINE === 'edge') {
      engine = OFFLINE; voice = DEFAULT_VOICE[OFFLINE];
      console.warn(s.id, 'edge-tts failed, using', engine + ':', e.message.slice(0, 120));
      ENGINES[OFFLINE](text, dst, voice);
    } else throw e;
  }
  const sec = wavSeconds(dst);
  total += sec;
  console.log(s.id.padEnd(8), sec.toFixed(1).padStart(5) + 's', engine, voice);
}
if (!DRY) console.log('total narration', (total / 60).toFixed(1), 'min');
