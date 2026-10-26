# i18n probes

Snippets for `mcp__playwright__browser_evaluate` (pass the function as written) and one read-only Node script for
the locale files. Every probe returns JSON: save it as a ledger row (`<id>-<page>-<locale>-probe.json` in the run
folder). A probe hit is a lead; the screenshot and a reading of the hit make it a finding.

## §1 Raw keys and broken interpolation

```js
() => {
  const KEY = /^[a-z][a-z0-9_]*(?:\.[a-z0-9_-]+)+$/i;             // orders.empty_state.heading
  const MARK = /\{\{[^}]*\}\}|\{\d+\}|%[sd]|\[missing|missing translation|MISSING_/i;
  const ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];
  const where = el => { const p = []; for (let e = el; e && e.nodeType === 1 && p.length < 4; e = e.parentElement) p.unshift(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '')); return p.join(' > '); };
  const hits = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const t = n.textContent.trim();
    if (!t || n.parentElement.closest('script, style, code, pre')) continue;
    if (KEY.test(t) || MARK.test(t)) hits.push({ where: where(n.parentElement), text: t.slice(0, 120) });
  }
  document.querySelectorAll('*').forEach(el => ATTRS.forEach(a => {
    const v = el.getAttribute(a);
    if (v && (KEY.test(v.trim()) || MARK.test(v))) hits.push({ where: where(el) + ' [' + a + ']', text: v.slice(0, 120) });
  }));
  return { count: hits.length, hits: hits.slice(0, 50) };
}
```

## §2 Untranslated text

Paste the default-locale values from Step 2 (distinct, four characters or more) into `DEFAULT`, and the words the
product keeps in every locale (brand names, "OK") into `KEEP`.

```js
() => {
  const DEFAULT = new Set([ /* default-locale strings */ ]);
  const KEEP = new Set([ /* words kept in every locale */ ]);
  const out = new Set();
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const t = n.textContent.trim();
    if (t.length >= 4 && DEFAULT.has(t) && !KEEP.has(t)) out.add(t);
  }
  return { count: out.size, sample: [...out].slice(0, 50) };
}
```

For a locale written in a non-Latin script (Arabic, Hebrew, Russian, Chinese, Japanese ...), long text nodes made
only of Latin letters are candidates as well: test each trimmed text node against `/^[\x20-\x7E]*[A-Za-z]{4,}[\x20-\x7E]*$/`.

## §3 Overflow and truncation

```js
() => {
  const items = [];
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || !el.textContent.trim()) return;
    const clips = ['hidden', 'clip'].includes(cs.overflowX) || cs.textOverflow === 'ellipsis';
    if (clips && el.scrollWidth > el.clientWidth + 1) {
      items.push({ tag: el.tagName.toLowerCase(), cls: String(el.className).slice(0, 60), text: el.textContent.trim().slice(0, 80), hiddenPx: el.scrollWidth - el.clientWidth });
    }
  });
  return { pageScrollsX: document.documentElement.scrollWidth > window.innerWidth, clipped: items.length, items: items.slice(0, 50) };
}
```

Run it at every breakpoint in scope (`visual-regression` sets the viewport). A clipped element whose full text is
needed to act (a button label, a price, a name) is a FAIL candidate; decorative ellipsis on a long description may
be the design — cite the design source before calling it expected.

## §4 `lang`, `dir` and right-to-left alignment

```js
() => {
  const root = document.documentElement;
  const dir = root.getAttribute('dir') || getComputedStyle(root).direction;
  const rtl = dir === 'rtl';
  const leftAligned = [];
  if (rtl) document.querySelectorAll('body *').forEach(el => {
    if (getComputedStyle(el).textAlign === 'left' && el.textContent.trim()) leftAligned.push(el.tagName.toLowerCase() + ' ' + String(el.className).split(' ')[0]);
  });
  return {
    lang: root.getAttribute('lang'), dir, rtl,
    textAlignLeftInRtl: leftAligned.length, examples: leftAligned.slice(0, 30),
    isolates: document.querySelectorAll('[dir="ltr"], bdi, bdo').length
  };
}
```

`textAlignLeftInRtl` above 0 points at physical CSS (`left` / `margin-left`) where logical CSS (`start`) was
needed. `isolates` = 0 on a page full of phone numbers or codes in RTL text is a hint that bidi isolation is missing
— check the screenshot.

## §5 Simulated text expansion (DOM only — reload afterwards)

```js
() => {
  const factor = 1.35;
  let changed = 0;
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const t = n.textContent;
    if (!t.trim() || n.parentElement.closest('script, style')) continue;
    n.textContent = t.replace(/\s+$/, '') + ' ' + '\u00c5'.repeat(Math.ceil(t.trim().length * (factor - 1)));
    changed++;
  }
  return { changed, note: 'simulation in this tab only; reload to restore; hits are leads, confirm with a real locale' };
}
```

Then run §3. The accented filler also tests line height for scripts with tall glyphs.

## §6 Expected formats for the current locale

```js
() => {
  const loc = document.documentElement.getAttribute('lang') || navigator.language;
  const d = new Date(Date.UTC(2026, 0, 31, 15, 5));
  const nf = (o) => new Intl.NumberFormat(loc, o);
  return {
    locale: loc,
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    date: new Intl.DateTimeFormat(loc, { dateStyle: 'medium' }).format(d),
    dateTime: new Intl.DateTimeFormat(loc, { dateStyle: 'short', timeStyle: 'short' }).format(d),
    number: nf().format(1234567.891),
    percent: nf({ style: 'percent' }).format(0.256),
    currency: nf({ style: 'currency', currency: 'EUR' }).format(1234.5),
    pluralCategories: new Intl.PluralRules(loc).resolvedOptions().pluralCategories,
    plurals: [0, 1, 2, 5, 11, 21, 101].map(n => n + ': ' + new Intl.PluralRules(loc).select(n)),
    sorted: ['Zoe', 'Zo\u00eb', '\u00c9mile', '\u00c5ngstr\u00f6m', 'apple', 'Zebra'].sort(new Intl.Collator(loc).compare)
  };
}
```

Change `EUR` to the currency the page shows. The browser formats dates in the machine's timezone: when the product
shows the user's profile timezone, add `timeZone: '<that zone>'` to the date options before comparing.

## §7 Locale-file key diff (Node, read-only)

Save as `key-diff.js` in the run folder (never inside the product repo) and run
`node key-diff.js <default-locale.json> <other-locale.json>`. It reads two files and prints; it writes nothing.

```js
const fs = require('fs');
const flat = (o, p = '', out = {}) => {
  for (const [k, v] of Object.entries(o)) {
    const key = p ? p + '.' + k : k;
    if (v && typeof v === 'object') flat(v, key, out); else out[key] = String(v);
  }
  return out;
};
const [a, b] = process.argv.slice(2).map(f => flat(JSON.parse(fs.readFileSync(f, 'utf8'))));
const ph = s => (s.match(/\{[^}]+\}|%[sd]/g) || []).sort().join(',');
const keys = Object.keys(a);
console.log(JSON.stringify({
  missing: keys.filter(k => !(k in b)),
  identical: keys.filter(k => k in b && a[k] === b[k] && /[A-Za-z]{4,}/.test(a[k])),
  placeholderMismatch: keys.filter(k => k in b && ph(a[k]) !== ph(b[k])),
  onlyInOther: Object.keys(b).filter(k => !(k in a))
}, null, 2));
```

Gettext `.po`, YAML or server-side resource files need a different reader; the four questions stay the same.
