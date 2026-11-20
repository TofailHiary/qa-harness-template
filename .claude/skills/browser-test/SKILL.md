---
name: browser-test
description: Use when a UI page, screen, or end-to-end user journey needs browser validation — a feature checked in a real browser for every role and control, every screen state, real user habits (refresh, back, double click, two tabs), Safari/WebKit, media and downloads; a frontend bug fix confirmed; or console/network evidence captured during a flow. Triggers include "test this in the browser", "verify the UI", "walk the flow", "check the page renders", "test it like a user".
argument-hint: "feature, page, or user flow to test in the browser"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__mcp_server_mysql__mysql_query", "mcp__http-client__*", "mcp__filesystem__*", "Skill(qa-standards)", "Skill(observability-check)", "Skill(visual-regression)", "Skill(a11y-test)", "Write"]
---

# Browser Testing — the screen as the user sees it

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/browser-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Drive a real browser through every screen of the journey, as every role in scope, and check each control, state and message a user can meet. A value proven in the DB or the API is not a UI check: a screen you only drove by API or form posts has had no UI check (qa-standards -> Escape classes, E14).

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below. Vocabulary (Verdict Contract, Execution Register, Evidence provenance, Escape classes, Core-page sweep) is defined there — this skill cites it and does not restate it.

## ARGUMENTS
$ARGUMENTS

**Called from a run skill (`/full-qa`, `/qa-validate`, `/release-check`, `/regression-runner`):** use the caller's Scope Lock and case IDs instead of writing new ones, never stop to ask, return your findings and evidence rows to the caller's Execution Register and Evidence Ledger, and skip the Post-Session memory write: the caller writes the run's single memory file (full-qa → Phase skill map).

If no arguments (standalone): ask which feature / page / flow to test and as which role, then STOP. Do not navigate until scope is set.

---

## Rules
1. **Scope Lock before the first navigation** (table below). Inside `/full-qa` it comes from the run's Scope Lock and Phase 0 cases.
2. **Control by control.** Every control in the UI inventory (Step 1) gets a checklist row. "The page works" is not a result.
3. **Open every screenshot you save** with `Read` and write what you see, control by control: drawn once, readable, aligned, in the right state. A screenshot nobody opened is not evidence, and neither is a tool summary such as "ok" or "rendered" *(illustrative: a screen a script reported as "ok" was blank in the picture)*.
4. **Every write is proven twice**: the network request (method, URL, status, body) and a DB read-back (Path exercised, below). A toast is not proof (anomaly-disposition Rule 5). A click that should send a request and sends none is an FE bug.
5. **Console + network on every flow** (`Skill(observability-check)` runs alongside). A console error or a 4xx/5xx is a finding even when the screen looks fine.
6. **Language:** every visible string is in `<UI languages: PROJECT-PROFILE.md §16>` (default: the app's default language only). Test another language only for output the story itself produces, in each language the story names.
7. **Run end to end without asking** (full-qa Rule 8). Ask the user only for decisions that are theirs (filing, a refused permission, a product ruling).
8. **Never paste a snapshot of a filled login form** into a report, ticket or chat: a Playwright snapshot can print the value of a filled password field (browser autofill).

### Scope Lock — REQUIRED before any browser action

| Field | Value |
|---|---|
| Feature / page / flow | |
| QA mode | smoke / targeted / regression / bugfix / full |
| Roles in scope (+ a role that must be refused, the same role in another tenant, signed out) | `<roles: PROJECT-PROFILE.md §8>` |
| Screens / routes (full journey, not just the changed screen) | |
| Write steps in the journey (the actions that MUST reach the network) | |
| Engines and sizes | `<browsers / devices: PROJECT-PROFILE.md §16>` (default: Chromium 1440 / 1366 / 768 / 375 + WebKit; Firefox when forms, media or layout change) |
| Environment | Test (default) / Dev / Prod (read-only) — URL from `PROJECT-PROFILE.md §5` |
| Branch / commit under test | `<branch: PROJECT-PROFILE.md §3>` @ short sha — captured once here, reused on every evidence row |
| Run folder | `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` |
| Out of scope (explicit) | |

Default FE = the main app (`<main app URL: PROJECT-PROFILE.md §5>`). Use a legacy / secondary FE URL (PROJECT-PROFILE.md §5) only when the story explicitly targets it.

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every finding (bug OR PASS) maps to >=1 row. Browser evidence = screenshots saved with `filename: qa-evidence/<run-folder>/<finding>-<name>.png`, the console log, the network log, and the DB read-back for writes. Stamp every row with its provenance (qa-standards -> Evidence provenance): a result observed on another environment or build is evidence for THAT environment only.

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

### Path exercised — REQUIRED on every case (`A PASS by toast is not a PASS`)
Every browser case records `Path exercised = validation-only | write`:

- **validation-only** — the case never reached the network (client-side validation, a disabled button, a local-state change, a cached response). It proves the **form**, not the **outcome**. A green validation-only case never proves the feature.
- **write** — the case fired a request that should change server state. A write case is **closed only by the network log AND a DB read-back** (`<DB tool: PROJECT-PROFILE.md §6>`; if DB is `off` in §2, close it by the network log plus an API read-back and name the missing DB read-back as a coverage gap). A success toast, a counter that moved, or an HTTP 200 alone does not close a write case.

Rules of thumb that catch the usual misses *(illustrative)*:
- a per-card `Save` on an existing record may mutate only local state -> no API call; the real write is often a later step (`Next` / `Assign` / bulk submit) — find it and exercise it.
- a toggle back to an earlier state may fire no request because the client cache serves it; judge that case by the screen AND record it as validation-only.
- for any action handed to an async consumer (`PROJECT-PROFILE.md §11` — queue / job / email / webhook), the toast proves enqueue only; read the terminal state (the row that should exist, its status, its timestamp) before closing the case.

A story whose write path was never exercised cannot be GO (qa-standards -> Escape classes, "validation green ≠ feature green").

---

## Tools

- **Playwright MCP** (`mcp__playwright__*`, Chromium): `browser_navigate`, `browser_snapshot`, `browser_click` (`doubleClick` for double-submit), `browser_type`, `browser_fill_form`, `browser_select_option`, `browser_press_key`, `browser_hover`, `browser_file_upload`, `browser_handle_dialog`, `browser_resize`, `browser_take_screenshot` (explicit `filename`), `browser_evaluate`, `browser_network_requests`, `browser_console_messages`, `browser_tabs` (a second tab; where your Playwright MCP version supports an isolated context, a second user signed in at the same time), `browser_run_code_unsafe` (Playwright code with `page`: route mocks, offline, downloads, storage state; no `require` / `process` inside it).
- **chrome-devtools MCP** (when configured): `emulate` (network conditions Slow 3G / Offline, CPU throttling, viewport with touch / mobile, user agent), `list_console_messages`, `list_network_requests`, performance traces. Without it, use the Playwright console / network tools.
- **Raw-text scan** — `scripts/raw-text-scan.js`: Read it and pass its text as the `function` of `browser_evaluate` (never as `filename`, the tool's output file): raw text keys, `{{…}}` slots and leaked `undefined` / `NaN` / `[object Object]` on the screen. **Core-page sweep** — `scripts/core-page-sweep.js` (qa-standards -> Core-page sweep).
- **Second engine** — `node .claude/skills/browser-test/scripts/xbrowser.js` (Step 7): it finds a Playwright build that matches the browsers installed on this machine, loads each screen in Chromium, Firefox and WebKit at the sizes you give, and writes screenshots plus a JSON report (console, failed requests, 4xx/5xx, sideways overflow, broken images, media state, suspect text, still-loading, optional axe-core).
- **DB read-back**: `<DB tool: PROJECT-PROFILE.md §6>` (DB `on` in §2). **Fixtures and roles**: `test-data-manager`; accounts `<role account: PROJECT-PROFILE.md §7>` (identifiers only — passwords come from their env vars and never go into a report or a script). If `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it for setup and for replaying a captured request; otherwise use `mcp__http-client__*`.
- **Expected behaviour**: `Read` / `Grep` / `Glob` on the component source (`<frontend repo: PROJECT-PROFILE.md §3/§9>`; NOT Bash cat/grep).
- **Evidence saving**: pass `filename: qa-evidence/<run-folder>/<name>.png` to `browser_take_screenshot` — a BARE filename saves to the repo root, NOT `qa-evidence/`; any PostToolUse copy hook is only a backstop. Other attachments go through the filesystem MCP or a Bash heredoc (the Write/Edit tool is hook-blocked for `qa-evidence/`).

---

## Browser-session cautions (verify per project — none of these is a finding until it is reproduced here)

- **One tab per portal at a time.** Some applications log the first tab out when a second tab of the same portal opens. Keep one tab per portal until you have verified this project's behaviour; another site in the same tab is fine. List the tabs before every probe (`browser_tabs` with `action: "list"`) — the user can open a tab you did not.
- **Remembered form values.** The login form may already hold another account (browser autofill). `browser_type` replaces the value; confirm the account that actually logged in from the page, not from what you typed.
- **Browser chrome noise.** An "unsupported command-line flag" bar, a "Save password?" prompt and find-bar highlights come from the automation launch flags and the browser, not the app.
- **Delayed UI.** Tooltips and menus in component libraries often open after a delay (e.g. for a MUI app, hover, wait for a tooltip word, then read) — a read that comes back empty is a timing miss before it is a bug.
- **Tokens in console logs.** DEV builds may print an auth token to the console on purpose. Quote only the lines that carry the signal and keep such logs out of tickets and chats.
- **Known noise needs a source.** Keep a per-project list of "looks like a bug, is not" items, each with the source that makes it expected (a ticket, a code line, a ruling). An item without a cited source is a finding, not noise.

---

## Step 1: Sign in and build the UI inventory (before the first click)

Navigate to the test URL (`PROJECT-PROFILE.md §5`), sign in as the in-scope role, wait for text unique to the landing page, read the signed-in account from the page, then scan the console. Cross-check memory first: grep `<memory folder: PROJECT-PROFILE.md §12>` for the page / route / symptom so a known issue is not re-discovered as new.

For every screen of the journey, list every control and message from the code (the page component and its children) AND from a live `browser_snapshot`:

| Screen | Control / message | Kind | Roles that see it | States it can be in | Source `file:line` |
|---|---|---|---|---|---|

Kinds: button, link, field, select, checkbox, switch, tab, menu, dialog, tooltip, table column, toast / alert, empty-state text, error text. A control in the code but not on screen (or the reverse) is a finding or a scope note. The count is the "UI controls" number of the case-completeness line (test-cases-generator Step 1d).

## Step 2: Each control, each role — the control checklist

Read the **starting state** of the data under test first (snapshot + DB/API read where a write will follow). Then, for every inventory row, per role that can see it:
- **Present or absent** as expected for this role and state (hidden vs disabled matters).
- **Text**: correct for the UI language; no raw text key (`common.save`, `{{name}}`), no `undefined` / `null` / `NaN` / `[object Object]`, nothing cut off, right singular / plural, the same date and number format as the rest of the app. Run the **raw-text scan** (Tools above) on every screen; 2-segment key groups: `<text-key prefixes: PROJECT-PROFILE.md §9>` (`keyPrefixes` in the `qa-core-pages` config).
- **Look** (from the opened screenshot): drawn once, aligned, readable, in the right state (on / off / disabled / selected / error / hover / focus).
- **Behaviour**: click / type / select does what the story says; disabled when it should be; tooltip and help text right.
- **Result is visible**: the screen shows the new state without a manual refresh, and still shows it after one.
- **Write proof**: network request + DB read-back (Rule 4), field by field against what the UI claims.

## Step 3: Every state of each screen

| State | How to produce it |
|---|---|
| Loading | slow network (chrome-devtools `emulate`, or a delayed `page.route`); spinner or skeleton shows, no flash of wrong or empty data |
| Empty | a fixture with no rows; a clear empty message, never a blank area or an error |
| Partly empty | the row that EXISTS with one field absent or in a third state (`0`, `null`, `""`, `[]`, failed request are different states) |
| One / many | page 2, the last page, every sortable column in both directions, filter + clear filter, a search with no result |
| Server error | without touching the backend: `browser_run_code_unsafe` → `await page.route('**/api/<path>**', r => r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }))`, reload, then `page.unroute(...)`. The screen shows an error message and stays usable |
| Network drop | `page.route('**/api/<path>**', r => r.abort('internetdisconnected'))` (works in all three engines), or chrome-devtools offline emulation. `context.setOffline` may not stop routed requests in Chromium — check that requests really failed |
| Long and odd values | very long names, `0`, the maximum, decimals, accents (José, Zoë), special / Unicode characters, as shown on screen |

## Step 4: What real users do

- **Refresh** in the middle of a flow (`page.reload()`): state kept or clearly reset; no silent data loss.
- **Back button** after save / submit: no second submit, no stale screen pretending to be current.
- **Double click** every submit button (`doubleClick: true`): exactly one request in the network log and one DB row.
- **Two tabs** (same context): edit the same record in both; the second save does not silently overwrite the first.
- **Deep link**: open the screen URL directly, signed in and signed out (signed out → login → back to the same screen).
- **Session ends mid-flow** (clear site storage in a throwaway context, or wait out the session guard): a clear message, no silent loss.
- **Zoom** 67 % and 200 %: nothing overlaps, nothing is lost. **Keyboard**: Enter submits forms, Esc closes dialogs.

## Step 5: Every role, and the hand-off between roles

- Keep two users signed in at once (an isolated browser context per role, or a second browser profile).
- Walk the role × action grid from test-cases-generator Step 1d: each role sees only its controls; a direct URL to a screen it must not reach is refused or redirected — never a blank page, a crash or a working screen.
- **Hand-off**: what one role does shows up for the other in the browser (one role creates or assigns → the other sees it; the other responds → the first sees the result), with the DB row in between.

## Step 6: Media, files and story-produced languages (when the screen has them)

- **Audio / video**: the media request returns 200 with `content-type` `audio/*` or `video/*` and a size above 0; after Play, `paused === false`, `currentTime` grows over 2 s, `duration > 0`, `error === null`; the control changes state (Play → Pause; reset at the end). Read it with `browser_evaluate`: `() => [...document.querySelectorAll('audio,video')].map(m => ({ src: m.currentSrc, paused: m.paused, t: m.currentTime, d: m.duration, err: m.error && m.error.code, ready: m.readyState }))`. Whether the right words are spoken needs a person: record a "needs a human listen" row with the file path. WebKit on Windows cannot play media (MediaError 4): Safari playback needs a Mac or an iPad — a named structural blocker, not a pass.
- **Downloads / exports**: `const [d] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Export' }).click()]); await d.saveAs('<absolute path in qa-evidence/<run-folder>/>')`. Open the file: a PDF starts with `%PDF-` and its text matches the screen; CSV / XLSX columns and row count match the screen and the DB.
- **Uploads**: `browser_file_upload` with at least two equivalence classes of the input, not two copies of one fixture (the sample-file library in `PROJECT-PROFILE.md §13`, test-data-manager -> INPUT-CLASS FIXTURE REGISTRY).
- **Language output the story produces** (generated audio, translations): test each language the story names, only for that output; everything else on the screen stays in the UI language.

## Step 7: Second engine and devices

1. Chromium (= Chrome / Edge) is the main pass above.
2. Save the signed-in session from the Playwright MCP browser into `<temp>` (the OS temp folder): `browser_run_code_unsafe` → `async (page) => { await page.context().storageState({ path: '<temp>/state-<role>.json', indexedDB: true }); return page.url(); }` (`indexedDB: true` matters when the app keeps its session in IndexedDB). Save it while the page is signed in (a page sitting on the login screen gives a signed-out state). The file holds live tokens: never copy it into `qa-evidence/`; delete it at the end of the run.
3. Run every screen of the journey in the other engines of `<browsers / devices: PROJECT-PROFILE.md §16>` (default: WebKit = Safari / iPad; Firefox when forms, media or layout change):
   `node .claude/skills/browser-test/scripts/xbrowser.js --out qa-evidence/<run-folder>/xbrowser --base <main app URL: PROJECT-PROFILE.md §5> --urls <path1>,<path2> --engines chromium,firefox,webkit --sizes 1366x768,768x1024t --state <temp>/state-<role>.json --axe`
   Write paths without the leading slash (Git Bash rewrites `/x`). For a journey with clicks, pass `--flow <file.js>` (`module.exports = async ({ page, step }) => { ...; await step('name'); }`).
4. Open every screenshot it saved and compare each engine with Chromium at the same size. A row marked STILL-LOADING or BLANK proves nothing: rerun it with `--wait 8000` before judging. A difference between engines is a finding with both screenshots.
5. Sizes come from `<browsers / devices: PROJECT-PROFILE.md §16>`; default desktop 1440×900, a common small-laptop width 1366×768, tablet 768×1024 (touch), phone 375×812 (mobile). `visual-regression` owns the layout checks at these sizes.
6. In a full-page screenshot a `position: fixed` sidebar stops at the viewport height: that is the capture, not the layout.

## Step 8: Report

Per screen, one UI checklist row:

| Screen | Role | Controls checked n/n | Screenshots opened n/n | States done | User habits done | Roles + hand-off | Media / files | Engines | UI language | Result | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|

Then the **Execution Register** (REQUIRED for full / regression / bugfix; recommended always) — every in-scope case gets a row and a disposition (qa-standards -> Execution Register):

| ID | Area / page | Requirement / AC | Check performed | Path exercised | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|---|

`Result` is exactly one of the canonical area results (qa-standards -> Verdict Contract): **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED**. BLOCKED and NOT APPLICABLE require a reason (and, for BLOCKED, what would unblock it). An empty `Result` is not permitted — silence is never a pass.

Per case: URL, role, preconditions, steps, **Path exercised**, expected vs actual, Result, console errors, network failures, ledger row — never "looks fine". The "controls checked" and "screenshots opened" totals feed the case-completeness line (full-qa Phase 8a). Standalone, end with the Evidence Ledger, a summary of passed / failed / blocked / not-yet-verified, and the run verdict as the canonical word (qa-standards -> Verdict Contract: **GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses) plus the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`. If `PROJECT-PROFILE.md §16` sets a verdict policy other than the strict-binary default, apply that policy and say which one you applied.

---

## Hand-offs in the same flow
- `Skill(observability-check)` during every flow.
- `Skill(visual-regression)` + `Skill(a11y-test)` on every screen whose output the change can alter — new or changed text, message, empty or error state, control or layout — including a backend change that changes what a screen shows. "Does not apply" needs one line saying no screen shows anything the change produces.
- Regression: related features, shared components and navigation flows (the indirect blast radius from qa-standards -> Impact Analysis) are `Regression: <area>` rows of the caller's register.

## Plugins & escalation (only when it adds value)
If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`):
- Before declaring PASS -> `superpowers:verification-before-completion` (evidence before assertions).
- A non-obvious failure (renders wrong, intermittent, cross-layer) -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify).

Otherwise do the equivalent by hand: before any PASS, re-open the ledger row and confirm the screenshot / network entry / DB read-back actually shows the expected value; for a non-obvious failure write one hypothesis, change one variable (role, data, viewport, engine, cache), re-run, and record what changed. An intermittent failure goes to `/flaky-race-verifier`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual (inside a run skill (`/full-qa`, `/qa-validate`, `/release-check`, `/regression-runner`) the caller writes the run's single file instead). If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/route/component/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<YYYY-MM-DD · title>](<file>.md) — <hook>`.
4. **Content:** feature/page + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), bugs (ID, severity, layer FE, NEW/DUPLICATE), the write paths exercised and how each was closed, engines and sizes run, test data (URLs/user IDs/logins — identifiers only, never passwords), root-cause `path:line`, browser-session noise confirmed with its source, regression risks for next time, any prior memory disproved.
5. **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
6. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
