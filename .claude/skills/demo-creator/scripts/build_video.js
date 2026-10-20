#!/usr/bin/env node
// demo-creator build: recordings + timeline + narration clips -> one MP4 with chapters.
// Usage: node build_video.js --demo <dir> [--name <file.mp4>] [--crf 20]
// 1) cuts each context's WebM into the segments where that context was active (consecutive steps),
// 2) concatenates them in step order, 3) lays every narration clip at its step's offset, 4) muxes.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : def; };
const DEMO = opt('--demo');
if (!DEMO) { console.error('usage: node build_video.js --demo <dir> [--name out.mp4] [--crf 20]'); process.exit(2); }
const DIR = path.resolve(DEMO);
const OUT = path.join(DIR, 'out');
const NAME = opt('--name', path.basename(DIR) + '-demo.mp4');
const CRF = String(opt('--crf', '20'));
const tl = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'));
const ff = (a) => { console.log('ffmpeg', a.join(' ')); execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...a], { stdio: 'inherit' }); };
const PAD = 0.35;

const segs = [];
for (const s of tl.steps) {
  if (!s.end) continue;
  const last = segs[segs.length - 1];
  if (last && last.ctx === s.ctx) { last.steps.push(s); last.endAbs = s.end; }
  else segs.push({ ctx: s.ctx, steps: [s], startAbs: s.start, endAbs: s.end });
}
if (!segs.length) { console.error('timeline has no completed steps'); process.exit(1); }
let finalT = 0;
const stepOffset = {};
segs.forEach((g, i) => {
  const vstart = tl.vstart[g.ctx];
  const file = tl.videos[g.ctx];
  if (!vstart || !file) throw new Error('no video for context ' + g.ctx);
  const firstSeg = i === 0;
  g.from = firstSeg ? 0 : Math.max(0, (g.startAbs - vstart) / 1000 - PAD);
  g.to = (g.endAbs - vstart) / 1000 + PAD;
  g.finalStart = finalT;
  for (const s of g.steps) stepOffset[s.id] = finalT + ((s.start - vstart) / 1000 - g.from);
  g.file = path.join(OUT, `seg${i + 1}.mp4`);
  ff(['-ss', g.from.toFixed(3), '-to', g.to.toFixed(3), '-i', file, '-r', '25', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', CRF, '-pix_fmt', 'yuv420p', '-an', g.file]);
  finalT += g.to - g.from;
});
const listFile = path.join(OUT, 'concat.txt');
fs.writeFileSync(listFile, segs.map((g) => `file '${g.file.replace(/\\/g, '/')}'`).join('\n'));
const silent = path.join(OUT, 'video-silent.mp4');
ff(['-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', silent]);

// narration track (22050 Hz mono 16-bit), each clip at its step offset + 0.25 s
const RATE = 22050;
const total = Math.ceil((finalT + 1) * RATE);
const pcm = new Int16Array(total);
function readWav(f) {
  const b = fs.readFileSync(f);
  let off = 12, dataOff = 0, dataLen = 0, fmt = null;
  while (off + 8 <= b.length) {
    const id = b.toString('ascii', off, off + 4); const sz = b.readUInt32LE(off + 4);
    if (id === 'fmt ') fmt = { ch: b.readUInt16LE(off + 10), rate: b.readUInt32LE(off + 12), bits: b.readUInt16LE(off + 22) };
    if (id === 'data') { dataOff = off + 8; dataLen = sz; break; }
    off += 8 + sz + (sz % 2);
  }
  if (!fmt || fmt.rate !== RATE || fmt.ch !== 1 || fmt.bits !== 16) throw new Error('unexpected wav format in ' + f + ' ' + JSON.stringify(fmt) + ' (run tts.js again)');
  return new Int16Array(b.buffer.slice(b.byteOffset + dataOff, b.byteOffset + dataOff + dataLen - (dataLen % 2)));
}
const chapters = [];
for (const s of tl.steps) {
  if (stepOffset[s.id] === undefined) continue;
  const f = path.join(OUT, 'tts', s.id + '.wav');
  if (fs.existsSync(f)) {
    const clip = readWav(f);
    const at = Math.round((stepOffset[s.id] + 0.25) * RATE);
    for (let i = 0; i < clip.length && at + i < total; i++) pcm[at + i] = clip[i];
  }
  chapters.push({ id: s.id, at: +stepOffset[s.id].toFixed(2) });
}
const wav = Buffer.alloc(44 + pcm.length * 2);
wav.write('RIFF', 0); wav.writeUInt32LE(36 + pcm.length * 2, 4); wav.write('WAVE', 8);
wav.write('fmt ', 12); wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22); wav.writeUInt32LE(RATE, 24); wav.writeUInt32LE(RATE * 2, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34);
wav.write('data', 36); wav.writeUInt32LE(pcm.length * 2, 40);
Buffer.from(pcm.buffer).copy(wav, 44);
const narr = path.join(OUT, 'narration.wav');
fs.writeFileSync(narr, wav);

const final = path.join(DIR, NAME);
ff(['-i', silent, '-i', narr, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', final]);
fs.writeFileSync(path.join(OUT, 'chapters.json'), JSON.stringify({ file: final, durationSec: +finalT.toFixed(1), segments: segs.map((g) => ({ ctx: g.ctx, from: +g.from.toFixed(2), to: +g.to.toFixed(2), finalStart: +g.finalStart.toFixed(2), steps: g.steps.map((s) => s.id) })), chapters }, null, 2));
console.log('DONE', final, 'duration', finalT.toFixed(1) + 's', 'size', (fs.statSync(final).size / 1048576).toFixed(1) + ' MB');
