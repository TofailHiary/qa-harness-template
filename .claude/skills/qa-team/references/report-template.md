# QA Agent Team - unified report template

Part of `qa-team`. Moved out of SKILL.md to keep the always-loaded file small; the headings are unchanged, so a reference such as "qa-team -> <heading>" still lands here via the pointer left in SKILL.md.

---

## QA Agent Team Report

**Feature/Story**: [Description]   **QA Mode**: [mode]   **Date**: [Date]   **Build**: [branch @ sha]
**Team**: Lead + [N] Agents (Browser, API, DB) — lanes skipped: [none / "Agent 3: DB capability off"]

### Test Coverage

| Layer | Agent | Tests Run | Passed | Failed | Bugs |
|-------|-------|-----------|--------|--------|------|
| Browser/UI | Agent 1 | [N] | [N] | [N] | [N] |
| API | Agent 2 | [N] | [N] | [N] | [N] |
| Database | Agent 3 | [N] | [N] | [N] | [N] |
| Cross-Layer | Lead | [N] | [N] | [N] | [N] |
| **TOTAL** | — | **[N]** | **[N]** | **[N]** | **[N]** |

### Bugs Found
#### Bug 1: [Title]
- **Severity**: [Critical/High/Medium/Low]   **Layer**: [FE/BE/Admin/Report/DB/Both]   **Found by**: [Agent/Lead]   **Reproduced by Lead**: yes/no
- **Steps / Expected / Actual / Evidence**: [...]

### Cross-Layer Consistency
| Check | FE | API | DB | Status |
|-------|----|-----|----|--------|
| Data value/format | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] |
| Validation | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] |
| Error handling | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] |

### Execution Register (REQUIRED — one row per Scope Lock area, no exceptions)

| ID | Area | Requirement / AC | Check performed | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|

`Result` is one of the five canonical values (`qa-standards` -> Verdict Contract: PASS / FAIL /
BLOCKED / NOT APPLICABLE / NOT YET VERIFIED). **Every area named in the Scope Lock gets exactly one
row.** An area with no row is a silent omission — the single highest cause of a confident wrong
verdict. Never delete a row to make a run look clean: mark it NOT YET VERIFIED and say what is
missing. BLOCKED needs the reason and what would unblock it.

### Evidence Ledger (REQUIRED — every finding AND every PASS, with provenance)
| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

Attachments: qa-evidence/<APP-nnn or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/ (written via mcp__filesystem__write_file; findings stay in chat).

### Coverage Gaps
[Any dimension not tested — an untested dimension is never an implied PASS; include lanes skipped by capability]

### Independent audit (REQUIRED before the verdict is stated)

Hand over ONLY the package — Scope Lock, authoritative source, every finding (bugs AND passes), the
Evidence Ledger, the **Execution Register** and the proposed verdict — never your reasoning or transcript.
- Sub-agents allowed (PROJECT-PROFILE.md §16): dispatch `qa-verdict-auditor` via the `Agent` tool (a judge, not a second QA run).
- Sub-agents disabled (§16): audit in-session — re-derive the verdict from the package alone, item by
  item against qa-standards -> Verdict Integrity #1-8 and the Completion Gate; write AUDIT_PASSED / AUDIT_FAILED.
`AUDIT_FAILED` -> you may NOT state the verdict; resolve each challenge with evidence, then re-audit
if findings moved. Its challenges are leads: reproduce first-hand anything you act on
(qa-standards -> Verdict Integrity #7). Record that the audit ran, and how.

### Verdict — per qa-standards -> Verdict Contract (policy: PROJECT-PROFILE.md §16, default strict binary)
[ ] GO (PASS) — 0 confirmed bugs across all layers, 0 NOT YET VERIFIED in mandatory scope
[ ] NO-GO (FAIL) — 1+ confirmed bugs (any layer, any severity)
[ ] PARTIAL — a hard blocker stopped an in-scope area (name it)
Confidence line: Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …
Escape classes actively checked (qa-standards -> Escape classes & their gates): [list — an unchecked class is a NOT YET VERIFIED row, not silence]
**Reason**: [Explanation — no "seems fine / probably / should work / looks correct"]
```

Before declaring GO: if the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`), run `superpowers:verification-before-completion`; otherwise by hand — re-run the qa-standards Completion Gate checklist and Verdict Integrity #1-8 against your own conclusions and quote the evidence row behind every PASS. For a non-obvious cross-layer root cause: `superpowers:systematic-debugging` if installed; otherwise 3-5 ranked falsifiable hypotheses, one variable at a time, accept only a reproduced cause.

**Ticket transition (only when asked, Jira on):** a verdict that changes a ticket status requires a fresh live read of the ticket this run, the audit pass above, and the transition / assignee rules in `PROJECT-PROFILE.md §15`.
