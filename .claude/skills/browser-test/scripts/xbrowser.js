#!/usr/bin/env node
// xbrowser.js - second-engine pass for browser-test Step 7. Read-only: it only loads pages (and runs an optional --flow
// you wrote). Usage:
//   node .claude/skills/browser-test/scripts/xbrowser.js --out qa-evidence/<run>/xbrowser --base <main app URL: PROJECT-PROFILE.md §5>
//        --urls path1,path2 [--engines chromium,firefox,webkit] [--sizes 1440x900,1366x768,768x1024t,375x812m]
//        [--state <temp>/state.json] [--axe] [--axe-path <axe.min.js>] [--flow flow.js] [--wait 2000]
//        [--login-path /login] [--loading-selector "<css>"]
// --base is required unless every --urls entry is an absolute URL. --urls @file reads one path per line.
// Sizes: WxH, suffix t = touch, m = mobile + touch (Firefox gets touch only).
// --state: a Playwright storageState file saved from the signed-in Playwright MCP browser:
//   await page.context().storageState({ path: '<temp>/state.json', indexedDB: true })
//   (indexedDB: true when the app keeps its session in IndexedDB). The file holds live tokens: keep it in the OS temp folder,
//   never in qa-evidence, and delete it after the run.
// --flow: a module `module.exports = async ({ page, step, engine, base }) => { ...; await step('name'); }`, run once
//   per engine and size; each step() saves a screenshot plus the console / network events since the last step.
// Playwright: it picks a playwright-core whose pinned browser builds are installed on this machine - the project's
//   node_modules (walking up from the working directory), the home node_modules, the global npm root, then the npx cache.
//   None matches -> exit 3 with the install command.
// Known Playwright limit: WebKit on Windows cannot play audio or video (MediaError 4), so Safari playback needs a Mac
//   or an iPad - a named structural blocker, not a pass.
const fs = require('fs'), path = require('path'), os = require('os'), cp = require('child_process');
const A = {};
for (let i = 2; i < process.argv.length; i++) {
  const k = process.argv[i].replace(/^--/, ''); const v = process.argv[i + 1];
  if (v === undefined || v.startsWith('--')) A[k] = true; else { A[k] = v; i++; }
}
if (!A.out || (!A.urls && !A.flow)) { console.error('need --out and --urls or --flow'); process.exit(2); }
const ENGINES = String(A.engines || 'chromium,firefox,webkit').split(',').map(s => s.trim()).filter(Boolean);
const SIZES = String(A.sizes || '1366x768').split(',').map(s => {
  const m = s.trim().match(/^(\d+)x(\d+)([mt]?)$/);
  if (!m) { console.error('bad size ' + s); process.exit(2); }
  return { label: s.trim(), width: +m[1], height: +m[2], touch: !!m[3], mobile: m[3] === 'm' };
});
const WAIT = +(A.wait || 2000);
const LOGIN = new RegExp('^' + String(A['login-path'] || '/login').replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(/|$)');

const urls = A.urls ? (String(A.urls).startsWith('@') ? fs.readFileSync(String(A.urls).slice(1), 'utf8').split(/\r?\n/) : String(A.urls).split(','))
  .map(s => s.trim()).filter(Boolean)
  // Git Bash rewrites a leading /path to C:/Program Files/Git/path: undo that, and accept paths without the slash.
  .map(s => s.replace(/^[A-Za-z]:[\\/]+Program Files[\\/]+Git(?=[\\/])/i, '').replace(/\\/g, '/'))
  .map(s => (/^https?:\/\//.test(s) || s.startsWith('/')) ? s : '/' + s) : [];
if (!A.base && (A.flow || urls.some(u => !/^https?:\/\//.test(u)))) {
  console.error('need --base <main app URL from PROJECT-PROFILE.md §5> (or absolute URLs only in --urls)'); process.exit(2);
}
const BASE = A.base ? String(A.base).replace(/\/$/, '') : '';

function browsersDir() {
  if (process.env.PLAYWRIGHT_BROWSERS_PATH && process.env.PLAYWRIGHT_BROWSERS_PATH !== '0') return process.env.PLAYWRIGHT_BROWSERS_PATH;
  if (process.platform === 'win32') return path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'ms-playwright');
  if (process.platform === 'darwin') return path.join(os.homedir(), 'Library', 'Caches', 'ms-playwright');
  return path.join(process.env.XDG_CACHE_HOME || path.join(os.homedir(), '.cache'), 'ms-playwright');
}
function moduleRoots() {
  const roots = [];
  for (let d = process.cwd(); ; d = path.dirname(d)) {
    roots.push(path.join(d, 'node_modules'));
    if (path.dirname(d) === d) break;
  }
  roots.push(path.join(os.homedir(), 'node_modules'));
  try { roots.push(cp.execSync('npm root -g', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim()); } catch (e) { /* no npm */ }
  const caches = [process.env.npm_config_cache, process.platform === 'win32' && path.join(process.env.LOCALAPPDATA || '', 'npm-cache'),
    path.join(os.homedir(), '.npm')].filter(Boolean);
  for (const c of caches) {
    const npx = path.join(c, '_npx');
    if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) roots.push(path.join(npx, d, 'node_modules'));
  }
  const withNested = [];
  for (const r of roots) withNested.push(r, path.join(r, 'playwright', 'node_modules'), path.join(r, '@playwright', 'test', 'node_modules'));
  return [...new Set(withNested)].filter(r => fs.existsSync(r));
}
const ROOTS = moduleRoots();

// Pick a playwright-core whose pinned browser builds are installed (a project's playwright may pin builds that are not).
function findCore() {
  const pwDir = browsersDir();
  const found = [];
  for (const r of ROOTS) {
    const core = path.join(r, 'playwright-core'); const bj = path.join(core, 'browsers.json');
    if (!fs.existsSync(bj)) continue;
    try {
      const v = JSON.parse(fs.readFileSync(path.join(core, 'package.json'), 'utf8')).version;
      const revs = JSON.parse(fs.readFileSync(bj, 'utf8')).browsers.filter(b => ENGINES.includes(b.name));
      if (revs.length === ENGINES.length && revs.every(b => fs.existsSync(path.join(pwDir, b.name + '-' + b.revision)))) found.push({ core, v });
    } catch (e) { /* unreadable install */ }
  }
  found.sort((a, b) => b.v.localeCompare(a.v, undefined, { numeric: true }));
  if (!found.length) {
    console.error('No playwright-core matches the browsers installed in ' + pwDir + '. Run once: npx playwright install ' + ENGINES.join(' '));
    process.exit(3);
  }
  return found[0];
}
function findAxe() {
  if (typeof A['axe-path'] === 'string') return A['axe-path'];
  for (const r of ROOTS) { const f = path.join(r, 'axe-core', 'axe.min.js'); if (fs.existsSync(f)) return f; }
  return null;
}
const CORE = findCore();
const pw = require(CORE.core);
const AXE = A.axe ? findAxe() : null;

// Text a user should never see: raw text keys (3+ dotted segments, not a domain or file name), template braces,
// undefined / null / NaN. A lead for the opened screenshot, not a verdict - raw-text-scan.js is the full scan.
const SUSPECT = /(^|\s)(undefined|null|NaN|\[object Object\])(\s|$)|\{\{[^}]+\}\}|^[a-z][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*){2,5}$/;
const NOT_KEY_END = /\.(com|org|net|io|dev|app|co|uk|edu|gov|pdf|png|jpe?g|gif|svg|csv|xlsx?|docx?|txt|json|zip|mp[34]|wav|html?|js|css)$/i;
const LOADING = ['[role=progressbar]', '[aria-busy=true]', '.MuiCircularProgress-root', '.MuiLinearProgress-root', '.MuiSkeleton-root',
  '.ant-spin-spinning', '.skeleton', '.spinner'].concat(A['loading-selector'] ? [String(A['loading-selector'])] : []).join(', ');

async function inspect(page, rec, shot) {
  // Wait for the data, not just the shell: network idle (capped), then WAIT ms. A screen still showing a spinner or
  // skeleton is reported as `loading` - its screenshot proves nothing yet (a 2 s wait once reported a blank page as ok).
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => { rec.networkidleTimeout = true; });
  await page.waitForTimeout(WAIT);
  Object.assign(rec, await page.evaluate(([src, notEnd, loadingSel]) => {
    const re = new RegExp(src); const ne = new RegExp(notEnd, 'i'); const sus = [];
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode() && sus.length < 15) {
      const t = w.currentNode.nodeValue.trim(); const el = w.currentNode.parentElement;
      if (t && el && el.offsetParent !== null && re.test(t) && !ne.test(t)) sus.push(t.slice(0, 80));
    }
    let loading = 0;
    try { loading = document.querySelectorAll(loadingSel).length; } catch (e) { loading = -1; }
    return {
      url: location.href, title: document.title, lang: document.documentElement.lang,
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      brokenImages: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.currentSrc).map(i => i.currentSrc.split('/').pop()),
      media: [...document.querySelectorAll('audio,video')].map(m => ({ src: (m.currentSrc || '').split('/').pop().slice(0, 60),
        paused: m.paused, t: +m.currentTime.toFixed(2), d: m.duration, err: m.error && m.error.code, ready: m.readyState })),
      suspectText: sus,
      loading,
      textLength: (document.body.innerText || '').trim().length,
    };
  }, [SUSPECT.source, NOT_KEY_END.source, LOADING]));
  rec.signedOut = LOGIN.test(new URL(rec.url).pathname);
  if (A.axe) {
    // A strict Content-Security-Policy blocks addScriptTag; page.evaluate of the library text works in all three engines.
    if (!AXE) rec.axe = 'ERR axe-core not found (npm i -D axe-core in the project, or --axe-path <axe.min.js>)';
    else {
      try {
        await page.evaluate(fs.readFileSync(AXE, 'utf8') + ';0');
        rec.axe = await page.evaluate(async () => (await axe.run()).violations.map(v => `${v.impact}:${v.id}:${v.nodes.length}`));
      } catch (e) { rec.axe = 'ERR ' + e.message.slice(0, 100); }
    }
  }
  await page.screenshot({ path: shot, fullPage: true });
  rec.screenshot = path.basename(shot);
}

(async () => {
  fs.mkdirSync(A.out, { recursive: true });
  const report = { core: CORE.v, base: BASE, at: new Date().toISOString(), runs: [] };
  const slug = s => s.replace(/^https?:\/\/[^/]+/, '').replace(/[^a-zA-Z0-9]+/g, '_').slice(0, 50) || 'root';
  const strip = s => (BASE ? s.replace(BASE, '') : s).slice(0, 120);
  for (const engine of ENGINES) {
    const browser = await pw[engine].launch({ headless: true }); const ver = browser.version();
    for (const size of SIZES) {
      const opts = { viewport: { width: size.width, height: size.height }, hasTouch: size.touch, acceptDownloads: true };
      if (size.mobile && engine !== 'firefox') opts.isMobile = true;
      if (A.state) opts.storageState = A.state;
      const ctx = await browser.newContext(opts); const page = await ctx.newPage();
      let log = { console: [], failed: [], http: [] };
      page.on('console', m => { if (['error', 'warning'].includes(m.type())) log.console.push(m.type() + ': ' + m.text().slice(0, 200)); });
      page.on('pageerror', e => log.console.push('pageerror: ' + String(e.message).slice(0, 200)));
      page.on('requestfailed', q => log.failed.push(strip(q.url()) + ' -> ' + (q.failure() || {}).errorText));
      page.on('response', r => { if (r.status() >= 400) log.http.push(r.status() + ' ' + r.request().method() + ' ' + strip(r.url())); });
      const take = () => { const l = log; log = { console: [], failed: [], http: [] }; return l; };
      for (const u of urls) {
        const rec = { engine, version: ver, size: size.label, target: u };
        try {
          await page.goto(/^https?:\/\//.test(u) ? u : BASE + u, { waitUntil: 'load', timeout: 60000 });
          await inspect(page, rec, path.join(A.out, `${engine}-${size.label}-${slug(u)}.png`));
        } catch (e) { rec.error = e.message.split('\n')[0].slice(0, 200); }
        Object.assign(rec, take()); report.runs.push(rec);
      }
      if (A.flow) {
        const flow = require(path.resolve(String(A.flow))); let n = 0;
        const step = async (name) => {
          const rec = { engine, version: ver, size: size.label, target: 'flow:' + name };
          try { await inspect(page, rec, path.join(A.out, `${engine}-${size.label}-flow-${++n}-${slug(name)}.png`)); }
          catch (e) { rec.error = e.message.split('\n')[0].slice(0, 200); }
          Object.assign(rec, take()); report.runs.push(rec);
        };
        try { await flow({ page, step, engine, base: BASE }); }
        catch (e) { report.runs.push({ engine, size: size.label, target: 'flow', error: e.message.split('\n')[0].slice(0, 200), ...take() }); }
      }
      await ctx.close();
    }
    await browser.close();
  }
  fs.writeFileSync(path.join(A.out, 'xbrowser-report.json'), JSON.stringify(report, null, 1));
  for (const r of report.runs) {
    console.log([r.engine, r.size, r.target, r.error ? 'ERROR ' + r.error : (r.signedOut ? 'SIGNED-OUT' : (r.loading > 0 ? 'STILL-LOADING' : (r.textLength < 40 ? 'BLANK' : 'rendered'))),
      'text=' + (r.textLength || 0),
      'console=' + (r.console || []).length, 'failed=' + (r.failed || []).length, 'http4xx5xx=' + (r.http || []).length,
      r.overflowX ? 'OVERFLOW-X' : '', (r.brokenImages || []).length ? 'broken-img=' + r.brokenImages.length : '',
      (r.suspectText || []).length ? 'suspect-text=' + r.suspectText.length : '',
      r.axe ? 'axe=' + (Array.isArray(r.axe) ? r.axe.length : r.axe) : ''].filter(Boolean).join(' | '));
  }
  console.log('report:', path.join(A.out, 'xbrowser-report.json'), '| playwright-core', CORE.v);
  console.log('Open every screenshot with Read before calling a screen right: "rendered" only means text is present.');
})().catch(e => { console.error(e); process.exit(1); });
