---
name: qa-report
description: Use when QA testing is complete and you need to compile every result, bug, and verdict into the standardized 9-section QA report with a GO/NO-GO recommendation. Triggers include "write the QA report", "compile the findings", "produce the sign-off report".
argument-hint: "feature or story name"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__filesystem__*", "Write"]
---

# QA Report Generator — 9-Section Report

> **Capability note:** this skill is **always on** (utility — see `docs/capability-matrix.md`). It compiles; it does not test. A section whose capability is `off` in `PROJECT-PROFILE.md` §2 (for example Section 5 with DB off) is recorded as "skipped: <capability> off" and listed as a coverage gap in Section 3a — never as PASS.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Evidence provenance, Execution Register, Verdict Contract, Judgement Discipline, Escape classes & their gates, Memory Ritual).

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
7. **This skill is a RENDERER, not a judge.** Print a run verdict (GO / NO-GO / PARTIAL) only when the caller hands you an **`AUDIT_PASSED`** result for THIS package (findings + ledger + register + proposed verdict) from the independent audit pass — `full-qa` Phase 8a: `Agent(qa-verdict-auditor)` when `PROJECT-PROFILE.md §16` allows sub-agents, otherwise the in-session audit pass the orchestrator ran itself (re-deriving the verdict from the package alone against qa-standards → Verdict Integrity). If the audit result is missing, stop and say "no audit result — run the audit pass (full-qa Phase 8a) first". Render only what was audited; add no findings of your own; if a finding in the package was not in the audited set, flag it as unaudited and keep it out of the verdict count.
8. Use the canonical vocabulary only (qa-standards → Verdict Contract): area results PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED; run verdict GO / NO-GO / PARTIAL (a skill alias may follow in parentheses); finding verdicts CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE. Banned in verdict lines: *seems fine, probably, should work, looks correct, most likely, I assume, apparently*.

---

## Data Sources

- **Evidence files:** read from `qa-evidence/` via `mcp__filesystem__read_file` / `mcp__filesystem__list_directory` — the run folder `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/`.
- **Conversation context:** TodoWrite state and test results from the current session (Scope Lock, the six questions, Evidence Ledgers, Execution Registers, bug reports, cross-layer tables produced by the specialist skills, and the audit result).
- **Memory:** grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for prior runs on this feature to mark bugs NEW vs DUPLICATE. A remembered result is a lead, never evidence (qa-standards → Fresh vs Historical) — only rows captured THIS run count as current.

If a section has no data because that dimension was not tested, record it as a **Coverage Gap** (Section 3a) — do not leave it blank and do not infer a PASS.

---

## Report Structure

### Section 0: Evidence Ledger (REQUIRED — the report's backbone)

Every other section's claims trace back to a row here. Compile the union of the Evidence Ledgers produced by each phase/skill this session.

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

(Provenance columns are mandatory on every row — qa-standards → Evidence provenance. **Env** = TEST / DEV / PROD-readonly, using the surface labels in `PROJECT-PROFILE.md §5/§6`; **Branch / Commit** = `<branch: PROJECT-PROFILE.md §3> @ <short sha>` captured at Scope Lock in the repo that owns the code under test; **Captured at** = timestamp of the observation. A row observed on DEV, on a replica, or on PROD is evidence for THAT environment only — it is never reported as evidence for the target environment; label it and say why if it must be cited.)

**Allowed types:** DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), Postman contract, GitHub diff/commit.

**Hard rules (qa-standards):**
- **No evidence = no finding.** Any bug in Section 8 and any PASS in Section 3 must cite at least one Evidence ID from this table.
- **No reproduction = no confirmed bug.** Suspected findings are listed separately and excluded from the verdict count.
- **No DB / API / Browser comparison = no cross-layer claim.** A "the API is wrong" line needs the DB row beside it.
- Evidence exists for **PASS** too — a green result needs proof it was actually exercised. A PASS proven only by a success toast, with no API call or DB write observed, is not a PASS (escape class E5).

### Section 0b: Execution Register (REQUIRED for full / release / regression, and for ANY run whose verdict will change a ticket status)

One row per in-scope area from the Scope Lock. `Result` ∈ PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED (qa-standards → Verdict Contract). No area may be missing from this table; an empty `Result` is not permitted — write NOT YET VERIFIED. BLOCKED and NOT APPLICABLE each carry a reason (and, for BLOCKED, what would unblock it). A shared component fixed is not every consumer fixed — each named consumer is its own row.

| ID | Area | Requirement / AC | Check performed | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|

### Section 1: Executive Summary
- Feature/Story name, Date, Environment, Verdict: **GO / NO-GO / PARTIAL** (qa-standards → Verdict Contract; policy knob in `PROJECT-PROFILE.md §16`).
- Confidence line (mandatory): `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: <one line or "none">`. Confidence is proportional to evidence — if 8 of 10, say 8 of 10.
- Quick stats: tests run, passed, failed, bugs found (confirmed only).
- Audit: `AUDIT_PASSED` by <in-session pass / qa-verdict-auditor> on <date>.
- Recommendation: **GO / NO-GO** (or **PARTIAL** if a hard blocker stopped a phase).

### Section 2: Scope (echo what was actually run)
- **QA mode** run (smoke / targeted / regression / bugfix / full / release) — echoed from the Scope Lock.
- Repos validated (with branches + short sha), features/pages tested, user roles exercised (`<roles: PROJECT-PROFILE.md §8>`).
- **Direct dependents + indirect blast radius** that were in scope (from Impact Analysis), including async consumers (`PROJECT-PROFILE.md §11`).
- **Out of scope (explicit)** — what was deliberately not covered.
- **Phases skipped** because a capability is off (§2) — named explicitly.

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

The denominator is the code-derived case count from the test plan (origin × mode × type × action), not a guessed one (escape class E12).

### Section 3a: Coverage Gaps (REQUIRED — name every untested dimension)

List every dimension from the coverage matrix (roles / states / inputs / flow / cross-tenant / regression — qa-standards Impact Analysis) that was **not** exercised, and why. Each gap is a known unknown, never an implied PASS. If coverage was complete, state "No coverage gaps — every in-scope dimension exercised (see ledger)."

| Untested dimension | Why not covered | Risk if shipped untested |
|---|---|---|

### Section 4: Code Review Findings
Files reviewed (`path:line`), issues, code quality, security concerns. For a bugfix run: whether the fix diff touched the root-cause `file:line` the ticket names (a fix that did not is a symptom patch — escape class E6).

### Section 5: Database Findings
Schema vs model, FK integrity, orphaned records, data consistency, missing indexes. Terminal state of async writes verified from the DB, not from the enqueue (E8).

### Section 6: API Test Results
Endpoints tested, auth/authz issues, validation gaps, response-schema issues, DB-write consistency. Fixes verified against the real wire shape captured in the target environment, not a mock (Judgement Discipline #7).

### Section 7: UI/Browser Test Results
Pages tested, console errors, network failures, visual/functional issues, cross-layer mismatches.

### Section 8: Bug Summary

Confirmed bugs only — each cites its Evidence ID(s) and its classification (FE / BE / Admin / Report / DB / Both) and NEW/DUPLICATE vs memory. `Status` is the tracker status read live this run (`PROJECT-PROFILE.md §15`), or "not filed".

| Bug ID | Title | Severity | Layer | NEW/DUP | Evidence ID(s) | Status |
|--------|-------|----------|-------|---------|----------------|--------|

(Suspected-but-unverified items, if any, go in a separate "Suspected — not counted in verdict" list below this table. Anomalies closed as "expected" appear here too, each with its cited source — an anomaly with no citation is not closed; it is a finding.)

### Section 9: Recommendation

**Verdict — per the project's verdict policy (`PROJECT-PROFILE.md §16`; default strict binary as defined in qa-standards → Verdict Contract: GO = exactly 0 confirmed bugs across all executed areas and 0 NOT YET VERIFIED rows in mandatory scope; NO-GO = 1+ confirmed bugs, any layer, any severity; PARTIAL = a hard blocker stopped an in-scope area — name it. No "conditional GO" and no severity weighting unless §16 says otherwise). This skill does not restate or re-define the rule.** Print the canonical word first; a skill alias may follow in parentheses. Use the report vocabulary Confirmed / Finding / Blocked / Remaining Risk / Not Applicable.

**Confidence line:** `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`
**Escape classes checked:** [which of E1–E13 (qa-standards → Escape classes & their gates) were actively checked this run; an unchecked class is a NOT YET VERIFIED row, not silence]
**Rationale:** [based on findings + ledger]
**Risks:** [known risks if released, incl. coverage gaps from 3a]
**Conditions:** [what must be fixed first if NO-GO]

**Sign-off:**
- QA: [Date]
- Dev: Pending
- PM: Pending

---

## Post-Report: Save to Filesystem

Save **evidence attachments only** (API responses, screenshots, logs — each prefixed with the bug name) to the run folder `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` (qa-standards → Evidence folder convention). The Write/Edit tool is hook-blocked for `qa-evidence/` — use `mcp__filesystem__write_file` or a Bash heredoc. The report body and bug findings appear in the chat conversation itself (and in the tracker when the user asks), **not** as markdown files in `qa-evidence/` (no index files, no bug-report `.md` in the evidence folder).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report a completed report without persisted memory.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the feature / endpoint / file path / user-ID / symptom; UPDATE an existing entry with today's report instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** feature + date, the final verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses) plus the confidence line, every confirmed bug (ID, severity, layer, NEW/DUPLICATE, tracker key), test data used (IDs / account identifiers — never passwords), root-cause `path:line`, coverage gaps carried forward, escape classes checked, regression risks for next time, and any prior memory this report disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
