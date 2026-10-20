---
name: visual-regression
description: Use when a page or screen must be checked for layout/responsive defects across screen sizes — horizontal overflow, text truncation cutting real content, element overlap or misalignment, broken wrapping, off-screen/clipped elements, or images not fitting. Triggers include "check responsive layout", "does this look right on mobile/tablet", "test breakpoints", "is anything overflowing/cut off", "verify the layout across screen sizes".
argument-hint: "page or flow to check + which breakpoints (default Desktop 1440 / Tablet 768 / Mobile 375)"
allowed-tools: ["Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "Skill(qa-standards)", "Write"]
---

# Visual Regression — Responsive Layout Validation

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/visual-regression` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Drive a real browser at multiple viewport widths to catch layout and responsive rendering defects on application UI pages.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates inlined below. Vocabulary (Verdict Contract, Execution Register, Evidence provenance) is defined there — this skill cites it and does not restate it.

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
| Breakpoints in scope | Desktop 1440 / Tablet 768 / Mobile 375 (default — or the project's own set from `PROJECT-PROFILE.md §16`, if any) |
| Roles in scope | `<roles: PROJECT-PROFILE.md §8>` (e.g. Admin / Manager / User / Guest) |
| Routes (full journey, not just the changed screen) | |
| Page states to render (empty / single / many / long text / error) | |
| Environment | Test (default) / Dev / Prod (read-only) — URL from `PROJECT-PROFILE.md §5` |
| Branch / commit under test | `<branch: PROJECT-PROFILE.md §3>` @ short sha — captured once, reused on every evidence row |
| Run folder | `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` |
| Expected / design reference (if any) | |
| Out of scope (explicit) | |

Default FE = the main app (`<main app URL: PROJECT-PROFILE.md §5>`). Use a legacy / secondary FE URL (PROJECT-PROFILE.md §5) only when the story explicitly targets it.

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
**Each finding = one screenshot at a specific breakpoint.** Save each screenshot with `filename: qa-evidence/<run-folder>/<breakpoint>-<name>.png` (a BARE filename saves to the repo root, NOT `qa-evidence/`). A claim with no ledger row does not exist. Save proof for PASS (clean at each breakpoint) too, not only defects. Stamp every row with its provenance (qa-standards -> Evidence provenance) — a layout observed on another environment or build is evidence for THAT environment only.

| Evidence ID | Type | Breakpoint | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|---|

### Path exercised
This skill is **validation-only by nature** — it reads layout, it never closes a write case. If the flow under test contains a write step, hand that step to `/browser-test` (its `Path exercised = write` rule applies there); do not report a write as verified from a screenshot.

---

## Tool Selection

- **Primary driver**: `mcp__playwright__*` — `browser_resize`, `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`
- **Computed-style / overflow checks**: `mcp__chrome-devtools__*` (or `mcp__playwright__browser_evaluate`) — read `scrollWidth` vs `clientWidth`, element rects, `overflow`/`text-overflow`
- **Expected behavior**: `Read`, `Grep`, `Glob` — confirm the design intent against component source (NOT Bash cat/grep)
- **Tabs**: `browser_tabs` with `action: "list"` before every probe — the user can open a tab you did not; some applications log the first tab out when a second tab of the same portal opens (verify per project; keep one tab per portal until you have)

---

## Workflow

### Step 1: Scope & login
Fill the Scope Lock. Navigate to the test URL, log in for the role in scope (`<role account: PROJECT-PROFILE.md §7>`), wait for text unique to the target page, confirm you are on the target screen. Cross-check memory first: grep `<memory folder: PROJECT-PROFILE.md §12>` for the page / component / breakpoint in case a layout defect here is already known.

### Step 2: Per breakpoint — repeat for EACH (Desktop 1440 / Tablet 768 / Mobile 375)
1. `mcp__playwright__browser_resize` to the width (e.g. 1440×900, 768×1024, 375×812).
2. `mcp__playwright__browser_navigate` to (or reload) the target route so layout recomputes at the new width.
3. `mcp__playwright__browser_snapshot` — capture the accessibility/DOM tree (element positions, what is rendered).
4. `mcp__playwright__browser_take_screenshot` with `filename: qa-evidence/<run-folder>/<breakpoint>-<name>.png` — full-page capture for the ledger.
5. Where the eye is not enough, **measure**: run a probe via `browser_evaluate` that returns `document.documentElement.scrollWidth` vs `clientWidth`, and for each scrollable container / table wrapper its `scrollWidth`, `clientWidth` and header rects (`getBoundingClientRect()`), e.g.:
   ```js
   (() => { const d = document.documentElement; const wraps = [...document.querySelectorAll('table, [role=table], .scroll, [style*=overflow]')];
     return { page: { scrollWidth: d.scrollWidth, clientWidth: d.clientWidth, overflow: d.scrollWidth > d.clientWidth + 1 },
       containers: wraps.map(w => ({ tag: w.tagName, scrollWidth: w.scrollWidth, clientWidth: w.clientWidth, overflow: w.scrollWidth > w.clientWidth + 1 })) }; })()
   ```
   Record the numbers in the ledger — "looks cut off" is an impression; `scrollWidth 1612 > clientWidth 375` is evidence.
6. Repeat the capture for each **page state** in scope (empty list, one item, many items, long text, error banner) — a layout that holds for the demo data and breaks at 40 rows or a 60-character name is a FAIL.

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
- **Layout shift after load** — the page settles differently after fonts / data / images arrive; capture once immediately and once after the network goes idle.

### Step 4: Compare to expected
Compare each breakpoint's rendering to the design/expected reference (if provided) or to the intended responsive behavior inferred from component source (`<frontend repo: PROJECT-PROFILE.md §3/§9>`). Flag every deviation with the **breakpoint + the screenshot evidence ID**. If the expected behaviour is not specified anywhere (no design, no AC, no code intent), say so and report the observation as a **Remaining Risk**, not as a FAIL — a FAIL needs an authoritative expected (qa-standards -> Verdict Integrity).

### Step 5: Report
Per finding: page, breakpoint(s) affected, defect type (from Step 3 list), expected vs actual (with the measured numbers), severity, screenshot ledger row. Note whether the defect is breakpoint-specific or present at all widths. End with the breakpoint × check matrix as the **Execution Register** (qa-standards):

| ID | Breakpoint | Check (Step 3 item) | Page state | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|

`Result` is one of the canonical area results (qa-standards -> Verdict Contract): **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED**. An unexercised breakpoint or state is NOT YET VERIFIED — never an implied pass. Then the run verdict as the canonical word (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses) and the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`. Record an explicit result per breakpoint — never "looks fine".

---

## Testing emphasis (MANDATORY)
Test **every breakpoint in scope**, not just desktop. A layout that is perfect at 1440 and broken at 375 is a FAIL. Always capture a screenshot at each breakpoint for both PASS and FAIL — the screenshot is the finding. Resembling the design is not a PASS; the measured overflow / rect values are.

---

## Plugins & escalation (only when it adds value)
If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`):
- Before declaring PASS -> `superpowers:verification-before-completion` (evidence before assertions).
- A non-obvious rendering defect (only at one width, intermittent, layout-shift after load) -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify).

Otherwise do the equivalent by hand: before any PASS re-open each breakpoint screenshot and the probe numbers and confirm they show what the register row claims; for a width-specific defect, bisect the width (resize in steps between the passing and failing breakpoints) until the exact breakpoint is found, then grep the component / CSS for that media query.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/route/component/breakpoint/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** page + breakpoints + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), layout defects (ID, severity, breakpoint, layer FE, NEW/DUPLICATE), test data (URLs/role/login — identifiers only), root-cause `path:line` (component/CSS where known), regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
