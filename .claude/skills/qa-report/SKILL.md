---
name: qa-report
description: Use when QA testing is complete and you need to compile every result, bug, and verdict into the standardized 9-section QA report with a GO/NO-GO recommendation. Triggers include "write the QA report", "compile the findings", "produce the sign-off report".
argument-hint: "feature or story name"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__filesystem__*"]
---

# QA Report Generator — 9-Section Report

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session.

Compile all QA findings into a structured report with a GO/NO-GO recommendation. This skill is the **report compiler** — it does not run new tests; it consolidates evidence already produced this session (or stored in `qa-evidence/`) into one factual, sign-off-ready document.

## ARGUMENTS
$ARGUMENTS

---

## Rules

1. Use ultrathink for report compilation.
2. Report must be factual — only include **verified** findings (a suspected bug is not a bug; see `bug-verifier`).
3. **Every finding AND every PASS maps to an Evidence Ledger row (Section 0). No evidence = no finding** — qa-standards. A claim with no ledger row does not enter the report.
4. The report **echoes the QA mode + scope** that was run (Section 2) and **names every coverage gap** (Section 3a). An untested dimension is never reported as PASS — silence is not a pass.
5. Tokens, passwords, and secrets must be `[REDACTED]` in all output.
6. Save evidence attachments to the filesystem and persist memory at the end (Post-Report + Post-Session below).

---

## Data Sources

- **Evidence files:** read from `qa-evidence/` via `mcp__filesystem__read_file` / `mcp__filesystem__list_directory`.
- **Conversation context:** TodoWrite state and test results from the current session (Scope Lock, Evidence Ledgers, bug reports, cross-layer tables produced by the specialist skills).
- **Memory:** grep `~/.claude/projects/c--Users-<user>-<project>/memory/*.md` for prior runs on this feature to mark bugs NEW vs DUPLICATE.

If a section has no data because that dimension was not tested, record it as a **Coverage Gap** (Section 3a) — do not leave it blank and do not infer a PASS.

---

## Report Structure

### Section 0: Evidence Ledger (REQUIRED — the report's backbone)

Every other section's claims trace back to a row here. Compile the union of the Evidence Ledgers produced by each phase/skill this session.

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

**Allowed types:** DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), Postman contract, GitHub diff/commit.

**Hard rules (qa-standards):**
- **No evidence = no finding.** Any bug in Section 8 and any PASS in Section 3 must cite at least one Evidence ID from this table.
- **No reproduction = no confirmed bug.** Suspected findings are listed separately and excluded from the verdict count.
- **No DB / API / Browser comparison = no cross-layer claim.** A "the API is wrong" line needs the DB row beside it.
- Evidence exists for **PASS** too — a green result needs proof it was actually exercised.

### Section 1: Executive Summary
- Feature/Story name, Date, Environment, Overall status: PASS / FAIL / BLOCKED.
- Quick stats: tests run, passed, failed, bugs found (confirmed only).
- Recommendation: **GO / NO-GO** (or **PARTIAL** if a hard blocker stopped a phase).

### Section 2: Scope (echo what was actually run)
- **QA mode** run (smoke / targeted / regression / bugfix / full / release) — echoed from the Scope Lock.
- Repos validated (with branches), features/pages tested, user roles exercised.
- **Direct dependents + indirect blast radius** that were in scope (from Impact Analysis).
- **Out of scope (explicit)** — what was deliberately not covered.

### Section 3: Test Coverage

| Category | Total | Passed | Failed | Blocked |
|----------|-------|--------|--------|---------|
| Positive | | | | |
| Negative | | | | |
| Boundary | | | | |
| DB Integrity | | | | |
| API | | | | |
| UI/Browser | | | | |
| Security | | | | |
| Regression | | | | |
| E2E | | | | |
| Data Consistency | | | | |
| **TOTAL** | | | | |

### Section 3a: Coverage Gaps (REQUIRED — name every untested dimension)

List every dimension from the coverage matrix (roles / states / inputs / flow / cross-tenant / regression — qa-standards Impact Analysis) that was **not** exercised, and why. Each gap is a known unknown, never an implied PASS. If coverage was complete, state "No coverage gaps — every in-scope dimension exercised (see ledger)."

| Untested dimension | Why not covered | Risk if shipped untested |
|---|---|---|

### Section 4: Code Review Findings
Files reviewed (`path:line`), issues, code quality, security concerns.

### Section 5: Database Findings
Schema vs model, FK integrity, orphaned records, data consistency, missing indexes.

### Section 6: API Test Results
Endpoints tested, auth/authz issues, validation gaps, response-schema issues, DB-write consistency.

### Section 7: UI/Browser Test Results
Pages tested, console errors, network failures, visual/functional issues, cross-layer mismatches.

### Section 8: Bug Summary

Confirmed bugs only — each cites its Evidence ID(s) and its classification (FE / BE / Admin / Report / DB / Both) and NEW/DUPLICATE vs memory.

| Bug ID | Title | Severity | Layer | NEW/DUP | Evidence ID(s) | Status |
|--------|-------|----------|-------|---------|----------------|--------|

(Suspected-but-unverified items, if any, go in a separate "Suspected — not counted in verdict" list below this table.)

### Section 9: Recommendation

**Verdict (strict binary — user policy 2026-05-04):**
- **GO** — exactly 0 confirmed bugs across all phases (any layer, any severity).
- **NO-GO** — 1+ confirmed bugs, regardless of severity.
- **PARTIAL** — a hard blocker stopped a phase (name it). No "Conditional GO"; no severity weighting.

**Rationale:** [based on findings + ledger]
**Risks:** [known risks if released, incl. coverage gaps from 3a]
**Conditions:** [what must be fixed first if NO-GO]

**Sign-off:**
- QA: [Date]
- Dev: Pending
- PM: Pending

---

## Post-Report: Save to Filesystem

Save **evidence attachments only** (API responses, screenshots, logs — each prefixed with the bug name) to `qa-evidence/reports/`. The Write/Edit tool is hook-blocked for `qa-evidence/` — use `mcp__filesystem__write_file` or a Bash heredoc. The report body and bug findings appear in the chat conversation itself, **not** as markdown files in `qa-evidence/` (no index files, no bug-report `.md` in the evidence folder).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report a completed report without persisted memory.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the feature / endpoint / file path / user-ID / symptom; UPDATE an existing entry with today's report instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** feature + date, the final verdict (GO/NO-GO/PARTIAL), every confirmed bug (ID, severity, layer, NEW/DUPLICATE), test data used (IDs/emails), root-cause `path:line`, coverage gaps carried forward, regression risks for next time, and any prior memory this report disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.
