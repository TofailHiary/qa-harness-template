---
name: browser-test
description: Use when a UI page, screen, or end-to-end user journey needs browser validation — verifying a feature works in a real browser, checking a flow renders/clicks/submits correctly, confirming a frontend bug fix, or capturing console/network evidence during a flow. Triggers include "test this in the browser", "verify the UI", "walk the flow", "check the page renders".
argument-hint: "feature, page, or user flow to test in the browser"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*"]
---

# Browser Testing with Playwright MCP

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/browser-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Drive a real browser to validate project UI pages and end-to-end user journeys.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any browser action
State the scope before the first navigation. Do not click until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Feature / page / flow | |
| QA mode | smoke / targeted / regression / bugfix / full |
| Roles in scope | Admin / Manager / User / Guest |
| Pages / routes (full journey, not just changed screen) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Out of scope (explicit) | |

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every finding (bug OR PASS) maps to >=1 row. Browser evidence = screenshots (saved with `filename: qa-evidence/<finding>/<name>.png`) + console logs + network requests.

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

A claim with no ledger row does not exist. Save proof for PASS too, not only bugs.

### Full-flow emphasis (MANDATORY)
Test the **FULL** user journey end-to-end, not just the changed screen. During **EVERY** flow capture console (`mcp__chrome-devtools__list_console_messages`) + network (`mcp__chrome-devtools__list_network_requests`). **A console error or a failed network call (4xx/5xx) is a finding even when the UI "looks fine".**

---

## Tool Selection

- **Primary browser driver**: `mcp__playwright__*` — snapshots, clicks, form fills, navigation, screenshots
- **Network & console inspection**: `mcp__chrome-devtools__*` — console errors, network requests, performance traces
- **Code reading**: `Read`, `Grep`, `Glob` — verify expected behavior against source code (NOT Bash cat/grep)
- **Evidence saving**: pass `filename: qa-evidence/<finding>/<name>.png` to `browser_take_screenshot` (a bare filename saves to the repo root, NOT qa-evidence); for other attachments use the filesystem MCP or Bash heredoc (the Write/Edit tool is hook-blocked for `qa-evidence/`)

---

## Testing Workflow

### Step 1: Setup & Login
Navigate to the test URL, take a snapshot, fill login credentials, click login, wait for the dashboard, verify logged in, then scan console for errors via `mcp__chrome-devtools__list_console_messages`.

### Step 2: Navigate to Feature
Snapshot to see navigation, click the required menu/link, wait for page load, capture the feature page, check console errors and network requests.

### Step 3: Test Feature (THOROUGHLY)
For EACH functionality: snapshot before action -> perform action -> wait for response -> snapshot after -> verify expected outcome -> check console errors -> check network requests -> screenshot for evidence.

### Step 4: Validation Checks
For EVERY test verify: page loads correctly, all expected elements present, user actions work, data displays correctly, form submissions succeed, error/success messages show appropriately, no JS console errors, all network requests succeed (no 4xx/5xx), API responses contain expected data, UI updates reflect data changes.

---

## Testing Types

- **Happy Path**: Normal expected user flow with valid inputs
- **Edge Cases**: Boundary values, empty inputs, max length, special/unicode characters
- **Error Scenarios**: Invalid inputs, missing required fields, unauthorized access, expired sessions
- **Regression**: Related features, shared components, navigation flows (the indirect blast radius from qa-standards -> Impact Analysis)

---

## Output Format

For each test report: URL, user type, pre-conditions, steps with PASS/FAIL, expected vs actual result, console errors, network failures, evidence (ledger row). End with a summary table of all tests, total passed/failed, and overall status. Record an explicit Pass/Fail per case — never "looks fine".

---

## Superpowers escalation (only when it adds value)
- Before declaring PASS -> `superpowers:verification-before-completion` (evidence before assertions).
- A non-obvious failure (renders wrong, intermittent, cross-layer) -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/route/component/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** feature/page + date, verdict (PASS/FAIL), bugs (ID, severity, layer FE, NEW/DUPLICATE), test data (URLs/user IDs/logins), root-cause `path:line`, regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
