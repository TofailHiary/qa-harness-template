#!/usr/bin/env node
// demo-creator recorder: records a narrated, captioned application demo with Playwright.
// Usage: node record.js --demo <dir> [--fast] [--stop-after <stepId>] [--headed]
//   <dir>/steps.json : [{id, ctx, label, text}]  (ctx = browser context number, 1-based)
//   <dir>/flow.js    : module.exports = async (api) => { ... api.step(page, id, fn) ... }
//   <dir>/out/tts/<id>.wav : narration clips (from tts.js); their length paces each step
//   <dir>/demo.json  : optional {"badge": "text pinned top-centre on every frame"}
// Output: <dir>/out/video/*.webm (one per context) + <dir>/out/timeline.json (for build_video.js)
// Nothing here is project-specific: selectors, URLs and accounts live in flow.js.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true) : def; };
const DEMO = opt('--demo');
if (!DEMO) { console.error('usage: node record.js --demo <dir> [--fast] [--stop-after <id>] [--headed]'); process.exit(2); }
const DIR = path.resolve(DEMO);
const OUT = path.join(DIR, 'out');
const VID = path.join(OUT, 'video');
fs.mkdirSync(VID, { recursive: true });
const FAST = !!opt('--fast', false) || !!process.env.FAST;
const STOP_AFTER = opt('--stop-after', process.env.STOP_AFTER || null);
const HEADED = !!opt('--headed', false);

// A demo folder holds steps.json + flow.js; the bundled templates/ folder ships them as *.example.* so the
// sample can be recorded without copying anything first.
const pick = (name, example) => fs.existsSync(path.join(DIR, name)) ? path.join(DIR, name) : path.join(DIR, example);
const steps = JSON.parse(fs.readFileSync(pick('steps.json', 'steps.example.json'), 'utf8'));
const CONF = fs.existsSync(path.join(DIR, 'demo.json')) ? JSON.parse(fs.readFileSync(path.join(DIR, 'demo.json'), 'utf8')) : {};
const BADGE = CONF.badge || '';
const stepById = Object.fromEntries(steps.map((s) => [s.id, s]));
const flow = require(pick('flow.js', 'flow.example.js'));
const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const T = () => new Date().toISOString().slice(11, 23);
const warn = (where, t0, e) => console.warn(T(), 'SLOW/CAUGHT', where, ((now() - t0) / 1000).toFixed(1) + 's', e && e.message ? e.message.split('\n')[0].slice(0, 140) : '');
const timeline = { fast: FAST, pid: process.pid, startedAt: new Date().toISOString(), vstart: {}, videos: {}, steps: [] };
console.log(T(), 'recorder pid', process.pid, FAST ? '(FAST)' : '');

function wavDur(f) {
  if (!fs.existsSync(f)) return 3;
  const b = fs.readFileSync(f);
  let off = 12, fmt = null, dataLen = 0;
  while (off + 8 <= b.length) {
    const id = b.toString('ascii', off, off + 4);
    const sz = b.readUInt32LE(off + 4);
    if (id === 'fmt ') fmt = { ch: b.readUInt16LE(off + 10), rate: b.readUInt32LE(off + 12), bits: b.readUInt16LE(off + 22) };
    if (id === 'data') { dataLen = sz; break; }
    off += 8 + sz + (sz % 2);
  }
  return fmt ? dataLen / (fmt.rate * fmt.ch * (fmt.bits / 8)) : 3;
}

// Caption bar, step label, badge and a fake cursor, re-created on every navigation (addInitScript).
const OVERLAY_INIT = `(() => {
  function ensure() {
    if (document.getElementById('qaCap')) return;
    const mk = (id, css) => { const d = document.createElement('div'); d.id = id; d.style.cssText = css; document.documentElement.appendChild(d); return d; };
    mk('qaCap', 'position:fixed;left:0;right:0;bottom:0;padding:18px 400px 24px 56px;background:rgba(17,24,39,.93);color:#fff;font:500 30px/1.35 "Segoe UI",Arial,sans-serif;z-index:2147483646;pointer-events:none;min-height:104px;box-shadow:0 -4px 16px rgba(0,0,0,.35)');
    mk('qaStep', 'position:fixed;right:24px;bottom:22px;max-width:340px;padding:8px 16px;background:#1d4ed8;color:#fff;font:600 20px "Segoe UI",Arial,sans-serif;border-radius:8px;z-index:2147483647;pointer-events:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis');
    mk('qaCur', 'position:fixed;left:-60px;top:-60px;width:26px;height:26px;border-radius:50%;background:rgba(255,106,0,.9);border:3px solid #fff;box-shadow:0 0 0 7px rgba(255,106,0,.35);z-index:2147483647;pointer-events:none;transition:left .55s ease,top .55s ease;transform:translate(-50%,-50%)');
    mk('qaBadge', 'position:fixed;left:50%;top:9px;transform:translateX(-50%);padding:6px 16px;background:rgba(180,40,40,.92);color:#fff;font:600 17px "Segoe UI",Arial,sans-serif;border-radius:999px;z-index:2147483646;pointer-events:none;display:none;white-space:nowrap');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ensure); else ensure();
  window.__qaEnsure = ensure;
})();`;

async function overlay(page) { await page.evaluate(() => window.__qaEnsure && window.__qaEnsure()).catch(() => {}); }
async function setCaption(page, label, text) {
  await overlay(page);
  await page.evaluate(([l, t, badge]) => { const a = document.getElementById('qaStep'); const b = document.getElementById('qaCap'); const c = document.getElementById('qaBadge'); if (a) a.textContent = l; if (b) b.textContent = t; if (c) { c.textContent = badge; c.style.display = badge ? 'block' : 'none'; } }, [label, text, BADGE]).catch(() => {});
}
async function moveCursor(page, loc) {
  const tb = now();
  const box = await loc.boundingBox({ timeout: 5000 }).catch((e) => { warn('boundingBox', tb, e); return null; });
  if (!box) return;
  const x = box.x + box.width / 2, y = box.y + box.height / 2;
  await page.evaluate(([x, y]) => { const c = document.getElementById('qaCur'); if (c) { c.style.left = x + 'px'; c.style.top = y + 'px'; } }, [x, y]).catch(() => {});
  await sleep(FAST ? 150 : 650);
}
// Highlight marks the element; un-highlight clears every marked element page-wide (the element is often gone by then).
async function hi(page, loc, on) {
  const tb = now();
  if (on) {
    await loc.evaluate((el) => { el.style.outline = '4px solid #ff6a00'; el.style.outlineOffset = '3px'; el.setAttribute('data-qa-hi', '1'); }, null, { timeout: 3000 }).catch((e) => warn('hi', tb, e));
  } else {
    await page.evaluate(() => { document.querySelectorAll('[data-qa-hi]').forEach((el) => { el.style.outline = ''; el.style.outlineOffset = ''; el.removeAttribute('data-qa-hi'); }); }).catch(() => {});
  }
}
async function clickIt(page, loc, opts = {}) {
  const tb = now();
  if (opts.scrollTop) await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
  await loc.scrollIntoViewIfNeeded({ timeout: 5000 }).catch((e) => warn('scrollIntoView', tb, e));
  if (opts.scrollTop) await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
  await moveCursor(page, loc);
  await hi(page, loc, true);
  await sleep(FAST ? 100 : 450);
  const tc = now();
  await loc.click();
  if (now() - tc > 3000) warn('click', tc, null);
  await sleep(FAST ? 100 : 300);
  await hi(page, loc, false);
}
async function flash(page, loc, ms = 1800) {
  const tb = now();
  await loc.scrollIntoViewIfNeeded({ timeout: 5000 }).catch((e) => warn('flash.scrollIntoView', tb, e));
  await moveCursor(page, loc);
  await hi(page, loc, true);
  await sleep(FAST ? 200 : ms);
  await hi(page, loc, false);
}
// ARIA select: works for MUI, Radix, headless-ui and any native-like role=combobox + role=option widget.
async function select(page, comboRe, optionName) {
  await clickIt(page, page.getByRole('combobox', { name: comboRe }), { scrollTop: true });
  const opt = page.getByRole('option', { name: optionName, exact: true });
  const tw = now();
  await opt.waitFor({ timeout: 15000 });
  if (now() - tw > 3000) warn('option.waitFor', tw, null);
  await moveCursor(page, opt);
  const tc = now();
  await opt.click();
  if (now() - tc > 3000) warn('option.click', tc, null);
  await sleep(FAST ? 200 : 500);
}
// Expand a collapsible section only if it is collapsed. `name` is the expand button's accessible name (string or regex).
async function expandSection(page, name) {
  const b = page.getByRole('button', { name });
  if (!(await b.count())) return;
  const expanded = await b.first().getAttribute('aria-expanded').catch(() => null);
  if (expanded === 'true') return;
  await clickIt(page, b.first());
}
const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
async function card(page, { title, subtitle, foot }) {
  await page.setContent(`<html><body style="margin:0;background:#0f172a;color:#fff;font-family:Segoe UI,Arial,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh"><div style="text-align:center;max-width:1500px"><div style="font-size:64px;font-weight:700">${esc(title)}</div><div style="font-size:30px;margin-top:18px;color:#cbd5e1">${esc(subtitle)}</div><div style="font-size:24px;margin-top:40px;color:#94a3b8">${esc(foot)}</div></div></body></html>`);
  await overlay(page);
}
async function endCard(page, { title, subtitle, foot }) {
  await page.evaluate(([t, s, f]) => {
    const d = document.createElement('div');
    d.style.cssText = 'position:fixed;inset:0;background:#0f172a;color:#fff;font-family:Segoe UI,Arial,sans-serif;display:flex;align-items:center;justify-content:center;z-index:2147483645';
    const e = (x) => String(x || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
    d.innerHTML = '<div style="text-align:center;max-width:1500px"><div style="font-size:56px;font-weight:700">' + e(t) + '</div><div style="font-size:28px;margin-top:18px;color:#cbd5e1">' + e(s) + '</div><div style="font-size:22px;margin-top:40px;color:#94a3b8">' + e(f) + '</div></div>';
    document.documentElement.appendChild(d);
  }, [title, subtitle, foot]);
}
const pageCtx = new WeakMap();
async function step(page, id, fn) {
  const s = stepById[id];
  if (!s) throw new Error('step id not in steps.json: ' + id);
  const dur = wavDur(path.join(OUT, 'tts', id + '.wav'));
  const t0 = now();
  await setCaption(page, s.label || '', s.caption || s.text || '');
  const rec = { id, ctx: pageCtx.get(page) || s.ctx || 1, start: t0, voice: +dur.toFixed(2) };
  timeline.steps.push(rec);
  try {
    await fn();
  } catch (e) {
    rec.error = e.message;
    console.error(T(), 'STEP FAIL', id, e.message.split('\n')[0]);
    await page.screenshot({ path: path.join(OUT, 'fail-' + id + '.png') }).catch(() => {});
    throw e;
  }
  const need = FAST ? 800 : Math.max(dur * 1000 + 1300, 3000);
  const el = now() - t0;
  if (el < need) await sleep(need - el);
  rec.end = now();
  console.log(T(), id, 'ok', ((rec.end - t0) / 1000).toFixed(1) + 's');
  if (STOP_AFTER === id) { console.log('STOP_AFTER reached'); throw new Error('STOP_AFTER'); }
}
const heading = (page, re) => page.getByRole('heading', { name: re });

(async () => {
  const browser = await chromium.launch({ headless: !HEADED });
  const contexts = {};
  const api = {
    FAST, sleep, now, step, clickIt, flash, select, expandSection, moveCursor, hi, setCaption, overlay, card, endCard, heading, warn, OUT, DIR,
    ctx: async (n) => {
      if (contexts[n]) return contexts[n].page;
      const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: VID, size: { width: 1920, height: 1080 } }, locale: 'en-US' });
      ctx.setDefaultTimeout(20000);
      await ctx.addInitScript(OVERLAY_INIT);
      const page = await ctx.newPage();
      timeline.vstart[n] = now();
      pageCtx.set(page, n);
      contexts[n] = { ctx, page };
      return page;
    },
  };
  let failed = null;
  try {
    await flow(api);
  } catch (e) {
    failed = e;
  } finally {
    for (const n of Object.keys(contexts)) {
      const { ctx, page } = contexts[n];
      const v = page.video() ? await page.video().path().catch(() => null) : null;
      timeline.videos[n] = v;
      await ctx.close().catch(() => {});
    }
    await browser.close().catch(() => {});
    timeline.endedAt = new Date().toISOString();
    fs.writeFileSync(path.join(OUT, FAST ? 'timeline-fast.json' : 'timeline.json'), JSON.stringify(timeline, null, 2));
    console.log('videos', JSON.stringify(timeline.videos));
  }
  if (failed && failed.message !== 'STOP_AFTER') { console.error('RUN FAILED', failed.message); process.exit(1); }
})();
