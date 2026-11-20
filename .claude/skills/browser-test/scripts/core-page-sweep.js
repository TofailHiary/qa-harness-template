async (page) => {
  // core-page-sweep.js - qa-standards -> Core-page sweep in ONE call per role. Read-only: it only moves between pages.
  // Use (once per role in <core pages: PROJECT-PROFILE.md §8>), signed in as that role in the Playwright MCP browser:
  //   1. mcp__playwright__browser_evaluate with
  //      () => sessionStorage.setItem('qa-core-pages', JSON.stringify({ role: '<role>', routes: ['/a', '/b'],
  //            carry: ['<query params to keep on every page>'], navigation: 'spa',
  //            keyPrefixes: ['<text-key prefixes: PROJECT-PROFILE.md §9>'] }))
  //   2. mcp__playwright__browser_run_code_unsafe with filename = .claude/skills/browser-test/scripts/core-page-sweep.js
  // navigation 'spa' (default) moves INSIDE the app (history.pushState + popstate), so a session the app keeps in memory
  // survives; 'goto' loads each page (page.goto) for an app that is not a single-page app. `carry` copies those query
  // parameters from the current URL onto every route (so tables load with the same scope / filters).
  // Per page it waits for the network to settle, runs the raw-text scan and collects console errors and failed requests.
  // Returns { role, startedFrom, pages, rows }: rows are ready Execution Register rows 'Core-page sweep: <route>' (the role is in the row id);
  // put your evidence id in the last cell and screenshot each page with a hit.
  // Result per page: PASS = rendered, no scan hit, no console error, no failed request; FAIL = any of those;
  // BLOCKED = the page redirected (e.g. to the login page) or rendered no text.
  // SCAN below is a copy of browser-test/scripts/raw-text-scan.js (the run_code sandbox cannot read files) - change both.
  const SCAN = async () => {
    // raw-text-scan.js - pass the TEXT of this file (never its path as `filename`) as the `function` of mcp__playwright__browser_evaluate (or to page.evaluate)
    // on every screen browser-test checks and on every page of the core-page sweep (qa-standards -> Core-page sweep).
    // It lists text a user must never see, in visible text and in aria-label / title / placeholder / alt:
    //   placeholder  - a raw interpolation slot such as {{name}}, or a stray {{ / }}
    //   text key     - a raw translation key: 3+ dotted segments starting lowercase (pages.home.title), a namespaced key
    //                  (common:buttons.save), a PascalCase.Pascal key, or a 2-segment key whose first segment is listed in
    //                  KEY_PREFIXES below. Domains, e-mail addresses, URLs, versions and file names are not keys.
    //   leaked value - undefined, NaN, [object Object], or a lone null
    // Result: { url, checked, hits: [{ kind, where, text }] }. hits = [] is a clean page; every hit is an FE finding until a
    // cited source shows the text is meant to be there (anomaly-disposition Rule 1).
    // The same scan is copied inside core-page-sweep.js (the run_code sandbox cannot read files) - change both.
    const KEY_PREFIXES = (() => { try { return (JSON.parse(sessionStorage.getItem("qa-core-pages") || "{}").keyPrefixes || []).map(String); } catch (e) { return []; } })(); // 2-segment key groups: keyPrefixes in the qa-core-pages config (PROJECT-PROFILE.md §9)
    await new Promise((resolve) => setTimeout(resolve, 1500)); // let late data render
    const NOT_KEY_END = new Set(("com org net io dev app co uk edu gov info biz me ai us eu de fr es it nl sa ae in au ca " +
      "pdf png jpg jpeg gif svg webp ico csv tsv xlsx xls docx doc pptx txt json xml zip gz mp3 mp4 wav webm mov html htm js mjs ts css md").split(" "));
    const isKey = (token) => {
      let tok = token.replace(/^[("'\[{<\u201c\u2018]+|[)"'\]}>.,;:!?\u201d\u2019]+$/g, "");
      let namespaced = false;
      const ns = tok.match(/^([a-z][\w-]*):([A-Za-z_][\w.]*)$/);
      if (ns) { tok = ns[2]; namespaced = true; }
      if (/[\/@:]/.test(tok)) return false;
      if (/^[A-Z][a-z]+[A-Z][A-Za-z]*\.[A-Z][A-Za-z]+$/.test(tok)) return true;
      if (!/^[a-z][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$/.test(tok)) return false;
      const segs = tok.split(".");
      if (NOT_KEY_END.has(segs[segs.length - 1].toLowerCase())) return false;
      return segs.length >= 3 || namespaced || KEY_PREFIXES.includes(segs[0]);
    };
    const RULES = [
      ["placeholder", (t) => /\{\{[^{}]*\}\}|\{\{|\}\}/.test(t)],
      ["text key", (t) => t.split(/\s+/).some(isKey)],
      ["leaked value", (t) => /\bundefined\b|\bNaN\b|\[object Object\]|^\s*null\s*$/.test(t)],
    ];
    const visible = (el) => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
    const describe = (el) => el.tagName.toLowerCase() + (el.getAttribute("role") ? `[role=${el.getAttribute("role")}]` : "");
    const hits = [];
    const seen = new Set();
    const add = (kind, where, text) => {
      const id = `${kind}|${where}|${text}`;
      if (seen.has(id)) return;
      seen.add(id);
      hits.push({ kind, where, text: text.slice(0, 160) });
    };
    let checked = 0;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const el = node.parentElement;
      if (!el || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(el.tagName) || !visible(el)) continue;
      const text = node.nodeValue.trim();
      if (!text) continue;
      checked += 1;
      for (const [kind, test] of RULES) if (test(text)) add(kind, describe(el), text);
    }
    for (const el of document.querySelectorAll("[aria-label],[title],[placeholder],img[alt]")) {
      for (const attr of ["aria-label", "title", "placeholder", "alt"]) {
        const value = el.getAttribute(attr);
        if (!value) continue;
        checked += 1;
        for (const [kind, test] of RULES) if (test(value)) add(kind, `${describe(el)}@${attr}`, value);
      }
    }
    return { url: location.href, checked, hits };
  };
  const cfg = await page.evaluate(() => {
    try { return JSON.parse(sessionStorage.getItem("qa-core-pages") || "null"); } catch (e) { return { bad: String(e) }; }
  });
  const usage = "First call mcp__playwright__browser_evaluate with () => sessionStorage.setItem('qa-core-pages', " +
    "JSON.stringify({ role: '<role>', routes: ['/a', '/b'], carry: [], navigation: 'spa' })) - the role's routes come from " +
    "PROJECT-PROFILE.md §8 (Core pages per role) - then run this file again.";
  if (!cfg || cfg.bad) return { error: `No sweep configuration in sessionStorage['qa-core-pages']. ${usage}` };
  const routes = Array.isArray(cfg.routes) ? cfg.routes.filter((r) => typeof r === "string" && r.startsWith("/")) : [];
  if (!routes.length) return { error: `sessionStorage['qa-core-pages'] has no routes starting with '/'. ${usage}` };
  const role = String(cfg.role || "role").replace(/\s+/g, "-");
  const carryKeys = Array.isArray(cfg.carry) ? cfg.carry.map(String) : [];
  const navigation = cfg.navigation === "goto" ? "goto" : "spa";

  const start = new URL(page.url());
  const carry = new URLSearchParams();
  for (const k of carryKeys) if (start.searchParams.get(k)) carry.set(k, start.searchParams.get(k));
  const target = (route) => {
    const u = new URL(route, start.origin);
    for (const [k, v] of carry) if (!u.searchParams.has(k)) u.searchParams.set(k, v);
    return u.pathname + u.search;
  };
  const go = async (to) => {
    if (navigation === "goto") {
      await page.goto(new URL(to, start.origin).href, { waitUntil: "load", timeout: 60000 }).catch(() => {});
      return;
    }
    await page.evaluate((dest) => {
      window.history.pushState({}, "", dest);
      window.dispatchEvent(new PopStateEvent("popstate", { state: {} }));
    }, to);
  };

  const pages = [];
  for (const route of routes) {
    const consoleErrors = [];
    const failedRequests = [];
    let inflight = 0;
    let lastActivity = Date.now();
    const onConsole = (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200)); };
    const onPageError = (e) => consoleErrors.push(String(e).slice(0, 200));
    const onRequest = () => { inflight += 1; lastActivity = Date.now(); };
    const onDone = () => { inflight = Math.max(0, inflight - 1); lastActivity = Date.now(); };
    const onFailed = (r) => { onDone(); failedRequests.push({ url: r.url().split("?")[0], error: (r.failure() || {}).errorText || "failed" }); };
    const onResponse = (r) => { if (r.status() >= 400) failedRequests.push({ url: r.url().split("?")[0], status: r.status() }); };
    const listeners = [["console", onConsole], ["pageerror", onPageError], ["request", onRequest],
      ["requestfinished", onDone], ["requestfailed", onFailed], ["response", onResponse]];
    for (const [ev, fn] of listeners) page.on(ev, fn);
    const t0 = Date.now();
    await go(target(route));
    // Settle: 1.2 s with no request in flight, or 6 s with at most one (a heartbeat / long poll); never more than 20 s.
    while (Date.now() - t0 < 20000) {
      await page.waitForTimeout(300);
      const quiet = Date.now() - lastActivity;
      if ((inflight === 0 && quiet > 1200) || (Date.now() - t0 > 6000 && inflight <= 1 && quiet > 1200)) break;
    }
    let scan;
    try { scan = await page.evaluate(SCAN); } catch (e) { scan = { checked: 0, hits: [], error: String(e).slice(0, 200) }; }
    for (const [ev, fn] of listeners) page.off(ev, fn);
    const now = new URL(page.url());
    const wanted = new URL(route, start.origin).pathname;
    pages.push({
      route, url: now.pathname + now.search, redirected: !now.pathname.startsWith(wanted), ms: Date.now() - t0,
      checked: scan.checked, hits: scan.hits, scanError: scan.error, consoleErrors, failedRequests,
    });
  }
  await go(start.pathname + start.search);

  const rows = pages.map((p, i) => {
    const result = p.redirected || p.checked === 0 ? "BLOCKED"
      : p.hits.length || p.consoleErrors.length || p.failedRequests.length ? "FAIL" : "PASS";
    const why = p.redirected ? `redirected to ${p.url}` : p.checked === 0 ? "no text rendered"
      : `${p.hits.length} hit(s), ${p.consoleErrors.length} console error(s), ${p.failedRequests.length} failed request(s)`;
    return `| CP-${role}-${i + 1} | Core-page sweep: ${p.route} | raw-text scan + console + network: ${why} | ${result} | <evidence id> |`;
  });
  return { role, startedFrom: start.pathname + start.search, navigation, pages, rows };
}
