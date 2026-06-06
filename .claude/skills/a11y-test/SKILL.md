---
name: a11y-test
description: Use when a page or component must be checked for accessibility — keyboard navigation and focus order/visibility, ARIA labels/roles and semantics, color-contrast against WCAG AA, screen-reader basics, and accessible form labels/error announcements. Triggers include "accessibility check", "a11y audit", "is this keyboard accessible", "check ARIA labels", "check color contrast", "can a screen reader use this", "WCAG compliance".
argument-hint: "page or component to audit for accessibility"
allowed-tools: ["Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "Skill(qa-standards)"]
---

# Accessibility Test — Keyboard, ARIA, Contrast, Screen-Reader Basics

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/a11y-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Drive a real browser to validate that an application UI page or component is usable by keyboard and assistive technology and meets WCAG AA basics.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates inlined below.

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
| Roles in scope | Admin / Manager / User / Guest |
| Routes (full journey, not just the changed screen) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| WCAG checks in scope | keyboard / focus / ARIA / contrast / forms / SR-basics |
| Out of scope (explicit) | |

Default FE = current application `<the relevant URL: PROJECT-PROFILE.md §5>`. Use the legacy FE URL (PROJECT-PROFILE.md §5) only when the story explicitly targets the legacy FE.

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every violation (and every PASS) maps to >=1 row. A11y evidence = accessibility-tree snapshots (`browser_snapshot`), focus screenshots (saved with `filename: qa-evidence/<finding>/<name>.png`), and computed-contrast readouts. A claim with no ledger row does not exist.

| Evidence ID | Type | Source | File / URL / Tool | WCAG criterion | What it proves |
|---|---|---|---|---|---|

---

## Tool Selection

- **Keyboard & snapshots**: `mcp__playwright__*` — `browser_press_key` (Tab/Shift+Tab/Enter/Esc), `browser_snapshot` (exposes the accessibility tree), `browser_take_screenshot` (focus ring evidence)
- **Contrast & computed values**: `mcp__chrome-devtools__evaluate_script` (or `mcp__playwright__browser_evaluate`) — read computed `color`/`background-color`/`font-size`, or run an axe-core snippet
- **Expected behavior**: `Read`, `Grep`, `Glob` — verify labels/roles against component source (NOT Bash cat/grep)

---

## Workflow

### Step 1: Scope & login
Fill the Scope Lock. Navigate to the test URL, log in for the role in scope, land on the target page/component.

### Step 2: Keyboard navigation
Press `Tab` (and `Shift+Tab` to go back) through **every** interactive element; use `Enter`/`Space` to activate and `Esc` to dismiss. Verify:
- **Logical tab order** — focus moves in a sensible reading order, not jumping around.
- **Visible focus ring** — every focused element shows a clear focus indicator (screenshot each non-obvious one).
- **No keyboard trap** — focus can always move forward and backward off any element.
- **All actions reachable** — every control operable by keyboard alone (no mouse-only buttons/menus).
- **Modals/dialogs** — opening a modal moves focus into it, focus is trapped while open, and on close focus returns to the trigger.

### Step 3: ARIA & semantics
`browser_snapshot` to read the accessibility tree, then verify:
- **Accessible names** — every input, button, link, and icon-button has an accessible name/label (not empty, not just an icon).
- **Images** — meaningful images have `alt`; decorative images are hidden from AT.
- **Roles correct** — controls expose the right role (button vs link vs checkbox); custom widgets have proper ARIA roles/states.
- **Heading structure** — headings present and ordered (no skipped levels), page has a clear main heading.
- **Landmarks** — main/nav/header regions identifiable where expected.

### Step 4: Color contrast (WCAG AA)
Use `mcp__chrome-devtools__evaluate_script` to read computed foreground/background colors and font size for text in scope (or run an axe-core contrast snippet). Flag text below:
- **4.5:1** for normal text (WCAG AA 1.4.3).
- **3:1** for large text (>=18.66px bold or >=24px) and for UI component boundaries/focus indicators (1.4.11).
Record the measured ratio and the two colors in the ledger.

### Step 5: Forms
- **Labels associated** — every field has a programmatic label (`<label for>`, `aria-label`, or `aria-labelledby`), not just placeholder text.
- **Required/invalid state** — required and error states exposed to AT (`aria-required`, `aria-invalid`).
- **Errors announced** — validation messages are associated with the field and in a live/announced region, not visual-only.

### Step 6: Report
Per violation: element, WCAG criterion (e.g. 1.4.3 Contrast, 2.1.1 Keyboard, 4.1.2 Name/Role/Value), expected vs actual, severity, evidence ledger row. End with a check × area matrix (PASS/FAIL) and overall status. Record an explicit Pass/Fail per check — never "looks accessible".

---

## Testing emphasis (MANDATORY)
Operate the page **with the keyboard only** for the full flow, and read the **accessibility tree** (not just the visual DOM) — a control that looks fine but has no accessible name or no focus ring is a FAIL. Tie every violation to a specific WCAG criterion.

---

## Superpowers escalation (only when it adds value)
- Before declaring PASS -> `superpowers:verification-before-completion` (evidence before assertions).
- A non-obvious AT/focus defect (intermittent focus loss, dynamic-content not announced) -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/component/WCAG-criterion/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** page/component + date, verdict (PASS/FAIL), violations (ID, severity, WCAG criterion, layer FE, NEW/DUPLICATE), test data (URLs/role/login), root-cause `path:line`, regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
