---
name: browser-test
description: Use when a UI page, screen, or end-to-end user journey needs browser validation — verifying a feature works in a real browser, checking a flow renders/clicks/submits correctly, confirming a frontend bug fix, or capturing console/network evidence during a flow. Triggers include "test this in the browser", "verify the UI", "walk the flow", "check the page renders".
argument-hint: "feature, page, or user flow to test in the browser"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "Skill(qa-standards)", "Write"]
---

# Browser Testing with Playwright MCP

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/browser-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Drive a real browser to validate application UI pages and end-to-end user journeys.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below. Vocabulary (Verdict Contract, Execution Register, Evidence provenance, Escape classes) is defined there — this skill cites it and does not restate it.

## ARGUMENTS
$ARGUMENTS

If no arguments: ask which feature / page / flow to test and as which role, then STOP. Do not navigate until scope is set.

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any browser action
State the scope before the first navigation. Do not click until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Feature / page / flow | |
| QA mode | smoke / targeted / regression / bugfix / full |
| Roles in scope | `<roles: PROJECT-PROFILE.md §8>` (e.g. Admin / Manager / User / Guest) |
| Pages / routes (full journey, not just changed screen) | |
| Write steps in the journey (the actions that MUST reach the network) | |
| Environment | Test (default) / Dev / Prod (read-only) — URL from `PROJECT-PROFILE.md §5` |
| Branch / commit under test | `<branch: PROJECT-PROFILE.md §3>` @ short sha — captured once here, reused on every evidence row |
| Run folder | `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` |
| Out of scope (explicit) | |

Default FE = the main app (`<main app URL: PROJECT-PROFILE.md §5>`). Use a legacy / secondary FE URL (PROJECT-PROFILE.md §5) only when the story explicitly targets it.

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every finding (bug OR PASS) maps to >=1 row. Browser evidence = screenshots (saved with `filename: qa-evidence/<run-folder>/<name>.png`) + console logs + network requests. Stamp every row with its provenance (qa-standards -> Evidence provenance): a result observed on another environment or build is evidence for THAT environment only.

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

A claim with no ledger row does not exist. Save proof for PASS too, not only bugs.

### Path exercised — REQUIRED on every case (`A PASS by toast is not a PASS`)
Every browser case records `Path exercised = validation-only | write`:

- **validation-only** — the case never reached the network (client-side validation, a disabled button, a local-state change, a cached response). It proves the **form**, not the **outcome**. A green validation-only case never proves the feature.
- **write** — the case fired a request that should change server state. A write case is **closed only by the network log AND a DB read-back** (`<DB tool: PROJECT-PROFILE.md §6>`; if DB is `off` in §2, close it by the network log plus an API read-back and name the missing DB read-back as a coverage gap). A success toast, a counter that moved, or an HTTP 200 alone does not close a write case.

Rules of thumb that catch the usual misses *(illustrative)*:
- a per-card `Save` on an existing record may mutate only local state -> no API call; the real write is often a later step (`Next` / `Assign` / bulk submit) — find it and exercise it.
- a toggle back to an earlier state may fire no request because the client cache serves it; judge that case by the screen AND record it as validation-only.
- for any action handed to an async consumer (`PROJECT-PROFILE.md §11` — queue / job / email / webhook), the toast proves enqueue only; read the terminal state (the row that should exist, its status, its timestamp) before closing the case.

A story whose write path was never exercised cannot be GO (qa-standards -> Escape classes, "validation green ≠ feature green").

### Full-flow emphasis (MANDATORY)
Test the **FULL** user journey end-to-end, not just the changed screen. During **EVERY** flow capture console (`mcp__chrome-devtools__list_console_messages`) + network (`mcp__chrome-devtools__list_network_requests`). **A console error or a failed network call (4xx/5xx) is a finding even when the UI "looks fine".**

---

## Tool Selection

- **Primary browser driver**: `mcp__playwright__*` — snapshots, clicks, form fills, navigation, screenshots
- **Network & console inspection**: `mcp__chrome-devtools__*` — console errors, network requests, performance traces (`mcp__playwright__browser_console_messages` / `browser_network_requests` when the devtools server is not configured)
- **Code reading**: `Read`, `Grep`, `Glob` — verify expected behavior against source code (NOT Bash cat/grep)
- **Evidence saving**: pass `filename: qa-evidence/<run-folder>/<name>.png` to `browser_take_screenshot` — a BARE filename saves to the repo root, NOT `qa-evidence/`; any PostToolUse copy hook is only a backstop. For other attachments use the filesystem MCP or a Bash heredoc (the Write/Edit tool is hook-blocked for `qa-evidence/`)
- **DB read-back for write cases**: `<DB tool: PROJECT-PROFILE.md §6>` (only when DB is `on` in §2)
- **Replaying a captured request**: if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it; otherwise use `mcp__http-client__*`

---

## Browser-session cautions (verify per project — none of these is a finding until it is reproduced here)

- **One tab per portal at a time.** Some applications log the first tab out when a second tab of the same portal opens. Keep one tab per portal until you have verified this project's behaviour; another site in the same tab is fine. List the tabs before every probe (`browser_tabs` with `action: "list"`) — the user can open a tab you did not.
- **Remembered form values.** The login form may already hold another account (browser autofill). `browser_type` replaces the value; confirm the account that actually logged in from the page, not from what you typed.
- **Browser chrome noise.** An "unsupported command-line flag" bar, a "Save password?" prompt and find-bar highlights come from the automation launch flags and the browser, not the app.
- **Delayed UI.** Tooltips and menus in component libraries often open after a delay (e.g. for a MUI app, hover, wait for a tooltip word, then read) — a read that comes back empty is a timing miss before it is a bug.
- **Tokens in console logs.** DEV builds may print an auth token to the console on purpose. Quote only the lines that carry the signal and keep such logs out of tickets and chats.
- **Known noise needs a source.** Keep a per-project list of "looks like a bug, is not" items, each with the source that makes it expected (a ticket, a code line, a ruling). An item without a cited source is a finding, not noise.

---

## Testing Workflow

### Step 1: Setup & Login
Navigate to the test URL (`PROJECT-PROFILE.md §5`), take a snapshot, fill the credentials of the in-scope role (`<role account: PROJECT-PROFILE.md §7>` — identifiers only; the password comes from its env var), click login, wait for text unique to the landing page, verify logged in (read the account from the page), then scan the console via `mcp__chrome-devtools__list_console_messages`. Cross-check memory first: grep `<memory folder: PROJECT-PROFILE.md §12>` for the page / route / symptom so a known issue is not re-discovered as new.

### Step 2: Navigate to Feature
Snapshot to see navigation, click the required menu/link, wait for page load, capture the feature page, check console errors and network requests. Read the **starting state** of the data under test (snapshot + DB/API read where a write will follow) so the after-state has something to be compared with.

### Step 3: Test Feature (THOROUGHLY)
For EACH functionality: snapshot before action -> perform action -> wait for response -> snapshot after -> verify expected outcome -> check console errors -> check network requests -> screenshot for evidence -> **record `Path exercised`**. For a write case: find the request in the network log (method, URL, status, body), then read the row back from the DB / API and compare field by field with what the UI claims.

### Step 4: Validation Checks
For EVERY test verify: page loads correctly, all expected elements present, user actions work, data displays correctly, form submissions succeed, error/success messages show appropriately, no JS console errors, all network requests succeed (no 4xx/5xx), API responses contain expected data, UI updates reflect data changes, **and the stored state matches the UI after every write**.

### Step 5: Execution Register (REQUIRED for full / regression / bugfix; recommended always)
Every in-scope case gets a row and a disposition. No applicable case may disappear silently (qa-standards -> Execution Register):

| ID | Area / page | Requirement / AC | Check performed | Path exercised | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|---|

`Result` is exactly one of the canonical area results (qa-standards -> Verdict Contract): **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED**. BLOCKED and NOT APPLICABLE require a reason (and, for BLOCKED, what would unblock it). An empty `Result` is not permitted — write NOT YET VERIFIED; silence is never a pass.

---

## Testing Types

- **Happy Path**: Normal expected user flow with valid inputs
- **Edge Cases**: Boundary values, empty inputs, max length, special/unicode characters; the row that EXISTS with one field absent or in a third state (`0`, `null`, `""`, `[]`, Loading, failed request are different states)
- **Error Scenarios**: Invalid inputs, missing required fields, unauthorized access, expired sessions
- **Input classes**: for any parser / upload / import surface, at least two equivalence classes of the input, not two copies of the same fixture (sample files: the sample-file library in `PROJECT-PROFILE.md §13`, if any)
- **Regression**: Related features, shared components, navigation flows (the indirect blast radius from qa-standards -> Impact Analysis)

---

## Output Format

For each test report: URL, role, pre-conditions, steps, **Path exercised**, expected vs actual, Result (canonical value), console errors, network failures, evidence (ledger row). End with the Execution Register, the Evidence Ledger, a summary of passed / failed / blocked / not-yet-verified, and the run verdict as the canonical word (qa-standards -> Verdict Contract: **GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses) plus the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`. Record an explicit result per case — never "looks fine". If `PROJECT-PROFILE.md §16` sets a verdict policy other than the strict-binary default, apply that policy and say which one you applied.

---

## Plugins & escalation (only when it adds value)
If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`):
- Before declaring PASS -> `superpowers:verification-before-completion` (evidence before assertions).
- A non-obvious failure (renders wrong, intermittent, cross-layer) -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify).

Otherwise do the equivalent by hand: before any PASS, re-open the ledger row and confirm the screenshot / network entry / DB read-back actually shows the expected value; for a non-obvious failure write one hypothesis, change one variable (role, data, viewport, cache), re-run, and record what changed. An intermittent failure goes to `/flaky-race-verifier`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/route/component/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** feature/page + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), bugs (ID, severity, layer FE, NEW/DUPLICATE), the write paths exercised and how each was closed, test data (URLs/user IDs/logins — identifiers only, never passwords), root-cause `path:line`, browser-session noise confirmed with its source, regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
