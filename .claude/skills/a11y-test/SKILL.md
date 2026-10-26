---
name: a11y-test
description: Use when a page or component must be checked for accessibility — keyboard navigation and focus order/visibility, ARIA labels/roles and semantics, color-contrast against WCAG AA, screen-reader basics, and accessible form labels/error announcements. Triggers include "accessibility check", "a11y audit", "is this keyboard accessible", "check ARIA labels", "check color contrast", "can a screen reader use this", "WCAG compliance".
argument-hint: "page or component to audit for accessibility"
allowed-tools: ["Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "Skill(qa-standards)", "Write"]
---

# Accessibility Test — Keyboard, ARIA, Contrast, Screen-Reader Basics

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/a11y-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Drive a real browser to validate that an application UI page or component is usable by keyboard and assistive technology and meets WCAG AA basics.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates inlined below. Vocabulary (Verdict Contract, Execution Register, Evidence provenance) is defined there — this skill cites it and does not restate it.

## ARGUMENTS
$ARGUMENTS

If no arguments: ask which page/component to audit (and the role to reach it), then STOP. Do not navigate until scope is set.

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any browser action
State the scope before the first navigation. Do not interact until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Page / component / flow | |
| QA mode | smoke / targeted / regression / bugfix |
| Roles in scope | `<roles: PROJECT-PROFILE.md §8>` (e.g. Admin / Manager / User / Guest) |
| Routes (full journey, not just the changed screen) | |
| Environment | Test (default) / Dev / Prod (read-only) — URL from `PROJECT-PROFILE.md §5` |
| Supported browser(s) the project commits to | from `PROJECT-PROFILE.md §16` if listed; otherwise the browser the Playwright MCP launches — name it |
| Branch / commit under test | `<branch: PROJECT-PROFILE.md §3>` @ short sha — captured once, reused on every evidence row |
| Run folder | `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` |
| WCAG checks in scope | keyboard / focus / ARIA / contrast / forms / SR-basics |
| Out of scope (explicit) | |

Default FE = the main app (`<main app URL: PROJECT-PROFILE.md §5>`). Use a legacy / secondary FE URL (PROJECT-PROFILE.md §5) only when the story explicitly targets it.

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every violation (and every PASS) maps to >=1 row. A11y evidence = accessibility-tree snapshots (`browser_snapshot`), focus screenshots (saved with `filename: qa-evidence/<run-folder>/<name>.png` — a BARE filename saves to the repo root, NOT `qa-evidence/`), the recorded Tab walk, and computed-contrast readouts. A claim with no ledger row does not exist. Stamp every row with its provenance (qa-standards -> Evidence provenance).

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | WCAG criterion | What it proves |
|---|---|---|---|---|---|---|---|---|

### An automated rule is a LEAD, not a reproduction
An axe-core / Lighthouse / linter rule hit is where to look, not what to file. **Before filing a keyboard / focus bug, record the actual Tab walk (the active element per Tab press) and the key result in the supported browser; write only what the walk shows.** The same applies to a contrast hit (re-measure the computed colours on the live element) and to a "missing name" hit (read the accessibility tree node yourself). A rule that fires on an element the user can never reach, or on a state the page never shows, is NOT A BUG — say so with the walk as evidence.

Tab-walk record (one row per key press; this table is the reproduction):

| # | Key | Active element (role / accessible name / selector) | Focus visible? | Result of Enter / Space / Esc (if pressed) | Screenshot |
|---|---|---|---|---|---|

Capture the active element after each press with `browser_evaluate` (e.g. `document.activeElement` -> tag, role, accessible name, `id`/`data-testid`) or from `browser_snapshot` (the focused node), not from memory.

### Path exercised
This skill is **validation-only by nature** — it operates and reads the page; it never closes a write case. If a keyboard flow ends in a submit, hand the write step to `/browser-test` (network log AND DB read-back); do not report the write as verified because the focus order was right.

---

## Tool Selection

- **Keyboard & snapshots**: `mcp__playwright__*` — `browser_press_key` (Tab/Shift+Tab/Enter/Space/Esc/Arrow keys), `browser_snapshot` (exposes the accessibility tree), `browser_take_screenshot` (focus ring evidence), `browser_evaluate` (read `document.activeElement`)
- **Contrast & computed values**: `mcp__chrome-devtools__evaluate_script` (or `mcp__playwright__browser_evaluate`) — read computed `color`/`background-color`/`font-size`/`font-weight`, or run an axe-core snippet **as a lead generator**
- **Expected behavior**: `Read`, `Grep`, `Glob` — verify labels/roles against component source (`<frontend repo: PROJECT-PROFILE.md §3/§9>`; NOT Bash cat/grep)
- **Tabs**: `browser_tabs` with `action: "list"` before every probe — some applications log the first tab out when a second tab of the same portal opens (verify per project; keep one tab per portal until you have)

---

## Workflow

### Step 1: Scope & login
Fill the Scope Lock. Navigate to the test URL, log in for the role in scope (`<role account: PROJECT-PROFILE.md §7>`), land on the target page/component. Cross-check memory first: grep `<memory folder: PROJECT-PROFILE.md §12>` for the page / component / WCAG criterion in case a violation here is already known or already ruled expected.

### Step 2: Keyboard navigation
Press `Tab` (and `Shift+Tab` to go back) through **every** interactive element, recording the Tab-walk table as you go; use `Enter`/`Space` to activate, Arrow keys inside composite widgets (menus, tabs, radio groups, grids), and `Esc` to dismiss. Verify:
- **Logical tab order** — focus moves in a sensible reading order, not jumping around.
- **Visible focus ring** — every focused element shows a clear focus indicator (screenshot each non-obvious one).
- **No keyboard trap** — focus can always move forward and backward off any element.
- **All actions reachable** — every control operable by keyboard alone (no mouse-only buttons/menus; hover-only tooltips and menus count as unreachable).
- **Modals/dialogs** — opening a modal moves focus into it, focus is trapped while open, and on close focus returns to the trigger.
- **Dynamic content** — content that appears after an action (toast, error banner, expanded row) is reachable and announced; focus is not lost to `<body>` when an element is removed.

### Step 3: ARIA & semantics
`browser_snapshot` to read the accessibility tree, then verify:
- **Accessible names** — every input, button, link, and icon-button has an accessible name/label (not empty, not just an icon).
- **Images** — meaningful images have `alt`; decorative images are hidden from AT.
- **Roles correct** — controls expose the right role (button vs link vs checkbox); custom widgets have proper ARIA roles/states (`aria-expanded`, `aria-selected`, `aria-checked` change with the state).
- **Heading structure** — headings present and ordered (no skipped levels), page has a clear main heading.
- **Landmarks** — main/nav/header regions identifiable where expected.
- **Page title and language** — the document title names the page; `lang` is set.

### Step 4: Color contrast (WCAG AA)
Use `mcp__chrome-devtools__evaluate_script` to read computed foreground/background colors and font size for text in scope (or run an axe-core contrast snippet as a lead, then re-measure the live element). Flag text below:
- **4.5:1** for normal text (WCAG AA 1.4.3).
- **3:1** for large text (>=18.66px bold or >=24px) and for UI component boundaries/focus indicators (1.4.11).
Record the measured ratio and the two colors in the ledger. When the background is an image or gradient, measure against the darkest and lightest pixel the text sits on and report both.

### Step 5: Forms
- **Labels associated** — every field has a programmatic label (`<label for>`, `aria-label`, or `aria-labelledby`), not just placeholder text.
- **Required/invalid state** — required and error states exposed to AT (`aria-required`, `aria-invalid`).
- **Errors announced** — validation messages are associated with the field (`aria-describedby`) and in a live/announced region, not visual-only; trigger a real validation error and read the tree after it appears.

### Step 6: Report
Per violation: element, WCAG criterion (e.g. 1.4.3 Contrast, 2.1.1 Keyboard, 2.4.3 Focus Order, 2.4.7 Focus Visible, 4.1.2 Name/Role/Value), expected vs actual, severity, the Tab-walk rows or measurement that reproduce it, evidence ledger row. End with the check × area matrix as the **Execution Register** (qa-standards):

| ID | Area / component | Check (keyboard / focus / ARIA / contrast / forms / SR) | WCAG criterion | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|

`Result` is one of the canonical area results (qa-standards -> Verdict Contract): **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED**. A check not exercised is NOT YET VERIFIED — never an implied pass. Then the run verdict as the canonical word (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses) and the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`. Record an explicit result per check — never "looks accessible".

---

## Testing emphasis (MANDATORY)
Operate the page **with the keyboard only** for the full flow, and read the **accessibility tree** (not just the visual DOM) — a control that looks fine but has no accessible name or no focus ring is a FAIL. Tie every violation to a specific WCAG criterion, and to a Tab-walk row or a measured value — an automated rule hit on its own is never the evidence.

---

## Plugins & escalation (only when it adds value)
If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`):
- Before declaring PASS -> `superpowers:verification-before-completion` (evidence before assertions).
- A non-obvious AT/focus defect (intermittent focus loss, dynamic-content not announced) -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify).

Otherwise do the equivalent by hand: before any PASS re-read the Tab-walk table and the tree snapshot and confirm they show what the register row claims; for an intermittent focus loss repeat the walk three times from a fresh load, record which press loses focus each time, and grep the component for the code that moves or removes the focused element.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/component/WCAG-criterion/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** page/component + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), violations (ID, severity, WCAG criterion, layer FE, NEW/DUPLICATE), automated hits ruled NOT A BUG with the walk that showed it, test data (URLs/role/login — identifiers only), root-cause `path:line`, regression risks for next time, any prior memory disproved.
5. **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
6. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
