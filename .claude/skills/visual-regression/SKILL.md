---
name: visual-regression
description: Use when a page or screen must be checked for layout/responsive defects across screen sizes — horizontal overflow, text truncation cutting real content, element overlap or misalignment, broken wrapping, off-screen/clipped elements, or images not fitting. Triggers include "check responsive layout", "does this look right on mobile/tablet", "test breakpoints", "is anything overflowing/cut off", "verify the layout across screen sizes".
argument-hint: "page or flow to check + which breakpoints (default Desktop 1440 / Tablet 768 / Mobile 375)"
allowed-tools: ["Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "Skill(qa-standards)"]
---

# Visual Regression — Responsive Layout Validation

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/visual-regression` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Drive a real browser at multiple viewport widths to catch layout and responsive rendering defects on application UI pages.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates inlined below.

## ARGUMENTS
$ARGUMENTS

If no arguments: ask which page/flow and which breakpoints to check, then STOP. Do not navigate until scope is set.

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any browser action
State the scope before the first navigation. Do not resize/snapshot until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Page / screen / flow | |
| QA mode | smoke / targeted / regression / bugfix |
| Breakpoints in scope | Desktop 1440 / Tablet 768 / Mobile 375 (default) |
| Roles in scope | Admin / Manager / User / Guest |
| Routes (full journey, not just the changed screen) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Expected / design reference (if any) | |
| Out of scope (explicit) | |

Default FE = current application `<the relevant URL: PROJECT-PROFILE.md §5>`. Use the legacy FE URL (PROJECT-PROFILE.md §5) only when the story explicitly targets the legacy FE.

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
**Each finding = one screenshot at a specific breakpoint.** Save each screenshot with `filename: qa-evidence/<finding>/<breakpoint>-<name>.png` (a bare filename saves to the repo root, NOT qa-evidence). A claim with no ledger row does not exist. Save proof for PASS (clean at each breakpoint) too, not only defects.

| Evidence ID | Type | Breakpoint | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|---|

---

## Tool Selection

- **Primary driver**: `mcp__playwright__*` — `browser_resize`, `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`
- **Computed-style / overflow checks**: `mcp__chrome-devtools__*` (or `mcp__playwright__browser_evaluate`) — read `scrollWidth` vs `clientWidth`, element rects, `overflow`/`text-overflow`
- **Expected behavior**: `Read`, `Grep`, `Glob` — confirm the design intent against component source (NOT Bash cat/grep)

---

## Workflow

### Step 1: Scope & login
Fill the Scope Lock. Navigate to the test URL, log in for the role in scope, wait for the page, confirm you are on the target screen.

### Step 2: Per breakpoint — repeat for EACH (Desktop 1440 / Tablet 768 / Mobile 375)
1. `mcp__playwright__browser_resize` to the width (e.g. 1440×900, 768×1024, 375×812).
2. `mcp__playwright__browser_navigate` to (or reload) the target route so layout recomputes at the new width.
3. `mcp__playwright__browser_snapshot` — capture the accessibility/DOM tree (element positions, what is rendered).
4. `mcp__playwright__browser_take_screenshot` with `filename: qa-evidence/<finding>/<breakpoint>.png` — full-page capture for the ledger.

### Step 3: Layout checks at each breakpoint
Inspect snapshot + screenshot (and computed styles where ambiguous) for:
- **Horizontal overflow / unexpected scrollbars** — page or container `scrollWidth > clientWidth`; content forcing sideways scroll.
- **Text truncation cutting real content** — ellipsis/clipping that hides meaningful text (labels, names, values), not just intended single-line truncation.
- **Overlap** — elements rendering on top of each other (text over icons, modal over trigger, sticky header over content).
- **Misalignment** — broken grid/flex alignment, off-baseline labels, uneven spacing vs siblings.
- **Broken wrapping** — buttons/menus/cards wrapping awkwardly, single words breaking mid-character, rows collapsing.
- **Off-screen / clipped elements** — controls pushed outside the viewport, cut at a container edge, or unreachable.
- **Images not fitting** — distorted aspect ratio, overflow past container, not scaling down on mobile, broken/missing render.
- **Mobile specifics (375)** — nav collapses to hamburger as intended, tap targets not crammed, no fixed-width element wider than viewport.

### Step 4: Compare to expected
Compare each breakpoint's rendering to the design/expected reference (if provided) or to the intended responsive behavior inferred from component source. Flag every deviation with the **breakpoint + the screenshot evidence ID**.

### Step 5: Report
Per finding: page, breakpoint(s) affected, defect type (from Step 3 list), expected vs actual, severity, screenshot ledger row. Note whether the defect is breakpoint-specific or present at all widths. End with a breakpoint × check matrix (PASS/FAIL per cell) and overall status. Record an explicit Pass/Fail per breakpoint — never "looks fine".

---

## Testing emphasis (MANDATORY)
Test **every breakpoint in scope**, not just desktop. A layout that is perfect at 1440 and broken at 375 is a FAIL. Always capture a screenshot at each breakpoint for both PASS and FAIL — the screenshot is the finding.

---

## Superpowers escalation (only when it adds value)
- Before declaring PASS -> `superpowers:verification-before-completion` (evidence before assertions).
- A non-obvious rendering defect (only at one width, intermittent, layout-shift after load) -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/route/component/breakpoint/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** page + breakpoints + date, verdict (PASS/FAIL), layout defects (ID, severity, breakpoint, layer FE, NEW/DUPLICATE), test data (URLs/role/login), root-cause `path:line` (component/CSS where known), regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
