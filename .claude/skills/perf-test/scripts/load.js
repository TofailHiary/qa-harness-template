#!/usr/bin/env node
/*
 * Light concurrency probe for perf-test - Node 18+ (global fetch), no dependencies.
 *
 *   node load.js --url https://test.example.com/api/health --concurrency 10 --duration 20 --out qa-evidence/<run>/E7-load.json
 *   node load.js --url ... --header "Authorization: Bearer $TOKEN"            (repeatable; never logged)
 *   node load.js --url ... --method POST --body '{"x":1}' --i-passed-the-mutation-gate
 *   node load.js --self-test                                                    (local server, proves the tool works)
 *
 * It is NOT a load-testing product: it tells you whether p95 / error rate move when N users act at once.
 * Guard rails: GET/HEAD only unless --i-passed-the-mutation-gate (qa-standards -> Mutation Safety Gate);
 * any host listed in the Prod column of PROJECT-PROFILE.md §5 is refused outright; concurrency <= 50 and
 * duration <= 120 s unless --force-bigger. Output: p50 / p95 / p99 / max ms, error rate, status counts, req/s.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');

function args(argv) {
  const a = { header: [] };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (!k.startsWith('--')) continue;
    const key = k.slice(2);
    const flag = ['self-test', 'i-passed-the-mutation-gate', 'force-bigger'].includes(key);
    const v = flag ? true : argv[++i];
    if (key === 'header') a.header.push(v); else a[key] = v;
  }
  return a;
}

function prodHosts() {
  const root = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, '..', '..', '..', '..');
  const p = path.join(root, '.claude', 'PROJECT-PROFILE.md');
  if (!fs.existsSync(p)) return [];
  const t = fs.readFileSync(p, 'utf8');
  const sec = (t.split(/^## §5/m)[1] || '').split(/^## /m)[0];
  const hosts = [];
  for (const line of sec.split('\n')) {
    const cells = line.split('|').map((c) => c.trim());
    if (cells.length < 6 || /^-+$/.test(cells[1]) || cells[1] === 'Surface') continue;
    const prod = cells[4];
    const m = prod && prod.match(/https?:\/\/([^/\s)]+)/);
    if (m) hosts.push(m[1].toLowerCase());
  }
  return hosts;
}

function pct(sorted, p) {
  if (!sorted.length) return null;
  const i = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return Math.round(sorted[Math.max(0, i)]);
}

async function run(opt) {
  const url = new URL(opt.url);
  const method = (opt.method || 'GET').toUpperCase();
  const conc = parseInt(opt.concurrency || '5', 10);
  const dur = parseInt(opt.duration || '10', 10);
  if (!['GET', 'HEAD'].includes(method) && !opt['i-passed-the-mutation-gate']) {
    throw new Error(method + ' changes data: pass --i-passed-the-mutation-gate only after the Mutation Safety Gate (snapshot + restore plan).');
  }
  if ((conc > 50 || dur > 120) && !opt['force-bigger']) throw new Error('concurrency > 50 or duration > 120 s needs --force-bigger (and the owner\'s agreement).');
  if (prodHosts().includes(url.host.toLowerCase())) throw new Error(url.host + ' is a PROD host in PROJECT-PROFILE.md §5 - load is never generated against production.');
  const headers = {};
  for (const h of opt.header) { const i = h.indexOf(':'); if (i > 0) headers[h.slice(0, i).trim()] = h.slice(i + 1).trim(); }
  if (opt.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  const times = []; const status = {}; let errors = 0; let total = 0;
  const end = Date.now() + dur * 1000;
  async function worker() {
    while (Date.now() < end) {
      const t0 = performance.now();
      try {
        const r = await fetch(url, { method, headers, body: opt.body, signal: AbortSignal.timeout(30000) });
        await r.arrayBuffer();
        status[r.status] = (status[r.status] || 0) + 1;
        if (r.status >= 500) errors++;
      } catch (e) { errors++; status[e.name || 'error'] = (status[e.name || 'error'] || 0) + 1; }
      times.push(performance.now() - t0); total++;
    }
  }
  const started = new Date().toISOString();
  await Promise.all(Array.from({ length: conc }, worker));
  const s = times.slice().sort((x, y) => x - y);
  return {
    tool: 'perf-test/scripts/load.js', target: url.origin + url.pathname, method, concurrency: conc, duration_s: dur,
    started_at: started, requests: total, req_per_s: +(total / dur).toFixed(1),
    p50_ms: pct(s, 50), p95_ms: pct(s, 95), p99_ms: pct(s, 99), max_ms: s.length ? Math.round(s[s.length - 1]) : null,
    error_rate: total ? +(errors / total).toFixed(4) : null, status_counts: status,
    note: 'headers are not recorded; compare p95 / error rate with a single-user baseline from the same env and build',
  };
}

async function selfTest() {
  const srv = http.createServer((req, res) => {
    const slow = Math.random() < 0.1;
    setTimeout(() => { res.writeHead(req.url === '/boom' ? 500 : 200); res.end('ok'); }, slow ? 40 : 5);
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const port = srv.address().port;
  const ok = await run({ url: 'http://127.0.0.1:' + port + '/ok', concurrency: '4', duration: '2', header: [] });
  const bad = await run({ url: 'http://127.0.0.1:' + port + '/boom', concurrency: '2', duration: '1', header: [] });
  let refused = false;
  try { await run({ url: 'http://127.0.0.1:' + port + '/ok', method: 'POST', header: [] }); } catch (e) { refused = true; }
  srv.close();
  const checks = [
    ['requests were made', ok.requests > 20],
    ['p50 <= p95 <= p99 <= max', ok.p50_ms <= ok.p95_ms && ok.p95_ms <= ok.p99_ms && ok.p99_ms <= ok.max_ms],
    ['healthy endpoint error rate is 0', ok.error_rate === 0],
    ['500s are counted as errors', bad.error_rate === 1],
    ['POST without the mutation gate is refused', refused],
  ];
  for (const [label, pass] of checks) console.log((pass ? 'OK   ' : 'FAIL ') + label);
  console.log(JSON.stringify({ p50_ms: ok.p50_ms, p95_ms: ok.p95_ms, p99_ms: ok.p99_ms, req_per_s: ok.req_per_s }));
  return checks.every((c) => c[1]) ? 0 : 1;
}

(async () => {
  const opt = args(process.argv.slice(2));
  try {
    if (opt['self-test']) process.exit(await selfTest());
    if (!opt.url) { console.error('usage: node load.js --url <url> [--concurrency N] [--duration S] [--out file] | --self-test'); process.exit(2); }
    const out = await run(opt);
    const text = JSON.stringify(out, null, 2);
    if (opt.out) { fs.mkdirSync(path.dirname(opt.out), { recursive: true }); fs.writeFileSync(opt.out, text + '\n'); console.log('wrote ' + opt.out); }
    console.log(text);
  } catch (e) { console.error('load.js: ' + e.message); process.exit(1); }
})();