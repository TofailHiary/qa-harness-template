#!/usr/bin/env node
// demo-creator one-command setup: installs what is missing and prints a check table.
// Usage: node .claude/skills/demo-creator/scripts/setup.js [--check] [--root <project root>] [--voice <edge-tts voice>]
//   --check  only report, install nothing
//   --root   the folder whose node_modules Playwright must live in (default: the project that holds this .claude/skills folder)
//   --voice  the neural voice to probe (default: en-US-JennyNeural; set the project's default in PROJECT-PROFILE.md §18)
// Needs: node 18+ (you are running it), internet for the installs (npm, Chromium build, Microsoft voices).
// Nothing here is project-specific. Exit 0 = READY, 1 = NOT READY.
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 && args[i + 1] ? args[i + 1] : d; };
const CHECK = args.includes('--check');
const ROOT = path.resolve(opt('--root', path.resolve(__dirname, '..', '..', '..', '..')));
const PW = '1.59.1';            // the Playwright version the recorder was developed against
const VOICE = opt('--voice', 'en-US-JennyNeural');
const WIN = process.platform === 'win32';
const MAC = process.platform === 'darwin';
const PY = WIN ? 'python' : 'python3';
const rows = [];
const add = (item, status, detail) => { rows.push([item, status, detail]); console.log(`${status.padEnd(8)} ${item.padEnd(14)} ${detail}`); };

function sh(cmd, cwd, timeout) {
  const r = spawnSync(cmd, { shell: true, cwd: cwd || ROOT, encoding: 'utf8', timeout: timeout || 600000, stdio: ['ignore', 'pipe', 'pipe'] });
  return { ok: r.status === 0, out: ((r.stdout || '') + (r.stderr || '')).trim() };
}
const first = (s) => (s || '').split(/\r?\n/).find((l) => l.trim()) || '';

// 1. Node
const nodeMajor = Number(process.versions.node.split('.')[0]);
add('node', nodeMajor >= 18 ? 'OK' : 'FAIL', `v${process.versions.node}${nodeMajor >= 18 ? '' : ' (need 18+)'}`);

// 2. Playwright package, resolved the way record.js resolves it (upward from scripts/)
function pwVersion() {
  try { return require(require.resolve('playwright/package.json', { paths: [__dirname, ROOT] })).version; } catch (e) { return null; }
}
let pv = pwVersion();
if (!pv) {
  if (CHECK) add('playwright', 'MISSING', `not installed under ${ROOT} (want ${PW})`);
  else {
    if (!fs.existsSync(path.join(ROOT, 'package.json'))) fs.writeFileSync(path.join(ROOT, 'package.json'), JSON.stringify({ name: path.basename(ROOT).toLowerCase().replace(/[^a-z0-9-]/g, '-') || 'demo-root', private: true }, null, 2));
    console.log(`installing playwright@${PW} in ${ROOT} ...`);
    const r = sh(`npm i -D --no-audit --no-fund playwright@${PW}`, ROOT);
    pv = pwVersion();
    add('playwright', pv ? 'OK' : 'FAIL', pv ? `${pv} installed in ${ROOT}` : first(r.out));
  }
} else add('playwright', 'OK', `${pv} at ${path.dirname(require.resolve('playwright/package.json', { paths: [__dirname, ROOT] }))}${pv !== PW ? ` (developed against ${PW})` : ''}`);

// 3. Chromium build for that Playwright
let exe = null;
try { exe = require(require.resolve('playwright', { paths: [__dirname, ROOT] })).chromium.executablePath(); } catch (e) { exe = null; }
if (exe && fs.existsSync(exe)) add('chromium', 'OK', exe);
else if (CHECK || !pv) add('chromium', 'MISSING', exe ? `expected at ${exe}` : 'playwright not resolvable');
else {
  console.log('installing the Chromium build (npx playwright install chromium) ...');
  const r = sh('npx playwright install chromium', ROOT, 900000);
  const ok = exe && fs.existsSync(exe);
  add('chromium', ok ? 'OK' : 'FAIL', ok ? exe : first(r.out));
}

// 4. ffmpeg
let ff = sh('ffmpeg -version');
if (ff.ok) add('ffmpeg', 'OK', first(ff.out).slice(0, 60));
else if (CHECK || !WIN) add('ffmpeg', 'MISSING', WIN ? 'winget install --id Gyan.FFmpeg -e' : (MAC ? 'brew install ffmpeg' : 'sudo apt install ffmpeg (or your package manager)'));
else {
  console.log('installing ffmpeg with winget ...');
  const r = sh('winget install --id Gyan.FFmpeg -e --silent --accept-source-agreements --accept-package-agreements', ROOT, 900000);
  ff = sh('ffmpeg -version');
  add('ffmpeg', ff.ok ? 'OK' : 'RESTART', ff.ok ? first(ff.out).slice(0, 60) : (r.ok ? 'installed; open a NEW terminal so PATH picks it up, then run --check' : first(r.out)));
}

// 5. Python + edge-tts (the neural voices are streamed from Microsoft at run time; nothing else to download)
const py = sh(`${PY} --version`);
if (!py.ok) add('python', 'MISSING', WIN ? 'install Python 3 (winget install Python.Python.3.12), then re-run' : 'install python3, then re-run');
else {
  add('python', 'OK', first(py.out));
  let et = sh(`${PY} -m edge_tts --version`);
  if (!et.ok && !CHECK) { console.log('installing edge-tts ...'); sh(`${PY} -m pip install --quiet edge-tts`, ROOT, 600000); et = sh(`${PY} -m edge_tts --version`); }
  add('edge-tts', et.ok ? 'OK' : 'MISSING', et.ok ? first(et.out) : `${PY} -m pip install edge-tts`);
  if (et.ok) {
    const lv = sh(`${PY} -m edge_tts --list-voices`, ROOT, 60000);
    add('voice', lv.ok && lv.out.includes(VOICE) ? 'OK' : 'OFFLINE', lv.ok && lv.out.includes(VOICE) ? `${VOICE} reachable (Microsoft online voices)` : 'voice list not reachable now (internet needed at record time; the offline fallback stays available)');
  }
}

// 6. Offline fallback voice - informational
if (WIN) {
  const sapi = sh('powershell -NoProfile -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"', ROOT, 60000);
  add('sapi', sapi.ok && sapi.out ? 'OK' : 'NONE', sapi.ok && sapi.out ? sapi.out.split(/\r?\n/).join(', ') : 'no Windows voices (fallback unavailable)');
} else if (MAC) {
  const say = sh('say -v ? | head -3', ROOT, 30000);
  add('say', say.ok && say.out ? 'OK' : 'NONE', say.ok && say.out ? first(say.out).slice(0, 60) : 'macOS say not available');
} else {
  const esp = sh('espeak-ng --version', ROOT, 30000);
  add('espeak-ng', esp.ok ? 'OK' : 'NONE', esp.ok ? first(esp.out).slice(0, 60) : 'install espeak-ng for an offline fallback (optional)');
}

const bad = rows.filter((r) => r[1] === 'FAIL' || r[1] === 'MISSING' || r[1] === 'RESTART');
console.log(bad.length ? `\nNOT READY: ${bad.map((r) => r[0]).join(', ')}` : `\nREADY: record with node ${path.relative(ROOT, path.join(__dirname, 'record.js')).replace(/\\/g, '/')} --demo <dir>`);
process.exit(bad.length ? 1 : 0);
