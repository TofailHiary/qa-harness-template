# QA Validate - deliverables (report template)

Part of `qa-validate`. Moved out of SKILL.md to keep the always-loaded file small; the headings are unchanged, so a reference such as "qa-validate -> <heading>" still lands here via the pointer left in SKILL.md.

---

## Deliverables

1. **Validation Summary** — story, date, QA mode, build under test, files reviewed, tables checked, APIs tested, UI flows tested, cross-layer consistency results, findings, coverage gaps (an untested dimension is never an implied PASS), skipped capabilities.
2. **Evidence Ledger** — the table above.
3. **Execution Register** (REQUIRED for EVERY verdict, not only ticket transitions) — one row per Scope Lock area; `Result` is one of the five canonical values (`qa-standards` -> Verdict Contract: PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED). BLOCKED and NOT APPLICABLE require a reason (and, for BLOCKED, what would unblock it). Never delete a row to make a run look clean.

   | ID | Area | Requirement / AC | Check performed | Result | Evidence ID | Finding |
   |---|---|---|---|---|---|---|

4. **Bug Reports** — verified bugs only, via `Skill(bug-report)`.
5. **Independent audit (REQUIRED before the verdict is stated).** Hand the package — Scope Lock, authoritative source, every finding (bugs AND passes), Evidence Ledger, Execution Register, proposed verdict — and never your reasoning or transcript:
   - If `PROJECT-PROFILE.md §16` allows sub-agents: dispatch `Agent(qa-verdict-auditor)` (a judge, not a second QA run; it runs under its own cost discipline).
   - If §16 says sub-agents are disabled: run the audit in-session — re-derive the verdict from the package alone, item by item against qa-standards -> Verdict Integrity #1-8 and the Completion Gate, and write the result as `AUDIT_PASSED` / `AUDIT_FAILED` with the challenges.
   - `AUDIT_FAILED` -> you may NOT state the verdict; resolve each challenge with evidence, then re-audit if findings moved. Its challenges are leads: reproduce first-hand anything you act on (Verdict Integrity #7). Record that the audit ran, and how.
6. **Verdict** — per the project's verdict policy (`PROJECT-PROFILE.md §16`; default strict binary) using the canonical words of qa-standards -> Verdict Contract: **GO** ("ready" may follow in parentheses) = exactly 0 confirmed bugs and 0 NOT YET VERIFIED rows in mandatory scope; **NO-GO** ("not-ready") = 1+ confirmed bugs, any layer, any severity; **PARTIAL** = a hard blocker stopped an in-scope area (name it). Then the mandatory confidence line — `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: <one line or "none">` — and, when the run finds nothing, which escape classes (qa-standards -> Escape classes & their gates) were actively checked; an unchecked class is a NOT YET VERIFIED row, not silence. Banned in verdict lines: *seems fine, probably, should work, looks correct, most likely, I assume, apparently*.
7. **Ticket transition (only when asked, Jira on).** A verdict that will change a ticket status requires a fresh live read of the ticket this run, an audit pass on the package, and the transition / assignee rules in `PROJECT-PROFILE.md §15`. A developer ruling ("this is intended") is recorded as a ruling, not a fix — "PASS as ruled", citing the comment.
