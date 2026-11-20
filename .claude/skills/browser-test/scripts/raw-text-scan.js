async () => {
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
}
