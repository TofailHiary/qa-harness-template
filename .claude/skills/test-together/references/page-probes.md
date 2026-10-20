# Page probes

Ready-to-run reads for `browser_evaluate` (pass the arrow function as `function`). They read the page and
change nothing. Edit the regex or the selector for the cards in scope.

**Adapting the selectors.** The probes use `h2` for card titles and `.MuiPaper-root` for the card
container (that is Material UI's class). Replace `.MuiPaper-root` with the card container class of your UI
library (`.ant-card`, `.card`, `.chakra-card`, `[data-testid="card"]`, …) and the heading level with
whatever the app uses for card titles. Take one `browser_snapshot` first and read the real structure —
never guess a selector. Keep every probe read-only.

## Read cards: title, subtitle, toggle state, table rows

Cards are usually a container with a heading. Rows drop empty cells (the row-indicator or selection
column), so a row reads `name | group | value`.

```js
() => {
  const want = /Top 10|Summary/;                      // the card titles in scope
  const CARD = '.MuiPaper-root';                      // the card container class of your UI library
  return Array.from(document.querySelectorAll('h2')).filter((h) => want.test(h.innerText)).map((h) => {
    const card = h.closest(CARD) || h.parentElement;
    return {
      title: h.innerText.trim(),
      subtitle: (card.querySelector('p') || {}).innerText,
      pressed: Array.from(card.querySelectorAll('button[aria-pressed]')).map((b) => b.getAttribute('aria-label') + '=' + b.getAttribute('aria-pressed')),
      rows: Array.from(card.querySelectorAll('tbody tr')).map((tr, i) => (i + 1) + '. ' + Array.from(tr.querySelectorAll('td')).map((td) => td.innerText.replace(/\s+/g, ' ').trim()).filter(Boolean).join(' | ')),
    };
  });
}
```

## Page facts: where am I, as whom, which build

```js
() => ({
  url: location.href,
  title: document.title,
  headings: Array.from(document.querySelectorAll('h1, h2')).map((h) => h.innerText.trim()).slice(0, 15),
  user: ((Array.from(document.querySelectorAll('header *, [class*="Header"] *')).filter((e) => /Welcome,?\s+\S/i.test(e.innerText || '')).sort((x, y) => x.innerText.length - y.innerText.length)[0] || {}).innerText || '').replace(/\s+/g, ' '),
  bundle: (document.querySelector('script[src*="/assets/index-"]') || {}).src,
})
```

- `user`: adapt the regex to the way your header greets the signed-in user (or read the avatar's
  `aria-label` / a profile menu instead).
- `bundle`: most SPA bundlers (Vite, webpack) emit a hashed main bundle name; the hash changes per build, so
  it identifies the deployed build. Adapt the `src*=` fragment to your bundler's output path.
- Many SPAs also print a version line to the console at startup — read it with `browser_console_messages`
  right after the page loads, and compare it with the build you expect to be deployed.

## Tooltips

1. Hover the element with `browser_hover`. Useful selectors:
   - a cell: `tr:has-text("<row text>") >> text=<cell text>`
   - a card's info icon: `h2:has-text("<card title>") >> role=button[name="More information"]` (use the
     icon's real accessible name from the snapshot)
2. Wait with `browser_wait_for` for a word you expect in the tooltip, or for a time of up to 4 s. Most UI
   libraries open tooltips after an enter delay.
3. Read it:

```js
() => Array.from(document.querySelectorAll('[role="tooltip"]')).map((t) => t.innerText.trim())
```

## Horizontal overflow (layout fits the card)

PASS when `overflow` is false and every header's right edge is at or inside the card's right edge.

```js
() => {
  const CARD = '.MuiPaper-root';                      // the card container class of your UI library
  const h = Array.from(document.querySelectorAll('h2')).find((x) => /Top 10/.test(x.innerText));
  const card = h.closest(CARD) || h.parentElement; const wrap = card.querySelector('table').parentElement; const cb = card.getBoundingClientRect();
  return {
    viewport: [innerWidth, innerHeight], card: [Math.round(cb.left), Math.round(cb.right)],
    scrollWidth: wrap.scrollWidth, clientWidth: wrap.clientWidth, overflow: wrap.scrollWidth > wrap.clientWidth + 1,
    headers: Array.from(card.querySelectorAll('thead th')).map((th) => { const r = th.getBoundingClientRect(); return [th.innerText.trim(), Math.round(r.left), Math.round(r.right)]; }),
  };
}
```

## Tabs

`browser_tabs` with `action: "list"` shows every tab; `action: "select", index: N` makes probes run there.
The user can open a tab you did not, so list the tabs before every probe.

## Console and network

- Console: `browser_console_messages`, or the newest `.playwright-mcp/console-*.log`. These logs can
  contain tokens (some dev builds log them); quote only the lines that carry the signal and keep the files
  out of tickets and chats.
- Network: `browser_network_requests`, then filter by the endpoint path. A toggle back to an earlier state
  often fires no request, because a client-side query cache serves it (see `known-noise.md`). Judge that
  case by the screen.
- A console error or a failed request (4xx/5xx) during a step is a finding even when the screen looks
  fine — record it, then rule out known noise before calling it a bug.
