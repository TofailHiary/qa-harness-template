# Release Check - sign-off report template and optional enhancers

Part of `release-check`. Moved out of SKILL.md to keep the always-loaded file small; the headings are unchanged, so a reference such as "release-check -> <heading>" still lands here via the pointer left in SKILL.md.

---

## Plugins & escalation (optional enhancers — `PROJECT-PROFILE.md §17`)
- Non-obvious root cause -> `superpowers:systematic-debugging` if the `superpowers` plugin is installed; otherwise by hand: 3-5 ranked falsifiable hypotheses, one variable at a time, accept only a reproduced cause.
- Large independent fan-out across release areas -> `superpowers:dispatching-parallel-agents` if installed (or the `qa-team` skill) — only when `PROJECT-PROFILE.md §16` allows sub-agents; otherwise sequential in-session.
- Before declaring APPROVED -> `superpowers:verification-before-completion` if installed; otherwise by hand: re-run the qa-standards Completion Gate checklist and Verdict Integrity #1-8 against your own conclusions and quote the evidence row behind every PASS.
- Ambiguous AC with the owner present -> `Skill(mattpocock-skills:grilling)` if the `mattpocock-skills` plugin is installed (numbered rounds, recommended answer per question, facts looked up in-session); otherwise by hand: numbered questions with your recommended reading, each answer cited as the source of its expected result. Owner absent: record the ambiguity, take the code-derived reading, label it INFERRED.

---

## Release Sign-Off Report

Generate a report containing:

1. **Header** — release name, date, environment, build(s) under test, validated by, QA mode (release), capabilities skipped.
2. **Summary** — total items validated, passed, failed, blocked, verdict **GO / NO-GO / PARTIAL** per qa-standards -> Verdict Contract and the project's verdict policy (`PROJECT-PROFILE.md §16`; default strict binary — "APPROVED / NOT APPROVED" in parentheses) + the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …` + the Execution Register + the audit result + which escape classes (qa-standards -> Escape classes & their gates) were actively checked.
3. **Repository Status** — table of all repos with branch, sync status, last commit.
4. **Files Reviewed** — table with file, status, issues.
5. **Tables Checked** — table with table name, schema, data, integrity, status.
6. **APIs Tested** — table with endpoint, method, auth, response, status.
7. **UI Flows Tested** — table with flow, path exercised, input class, status, console errors, network issues.
8. **Test Results** — table with test type, total, passed, failed.
9. **Bugs Found** — list each with title, severity, layer (FE/BE/Admin/Report/DB/Both), NEW/DUPLICATE, status.
10. **Evidence Ledger** — the table above (every finding AND every PASS, with provenance).
11. **Coverage Gaps** — any dimension not tested (an untested dimension is never an implied PASS), including sections skipped by capability.
12. **Recommendation** — GO (APPROVED) or NO-GO (NOT APPROVED) with reason, risks, mitigation. No "conditional" approval unless `PROJECT-PROFILE.md §16` defines one. Banned: *seems fine, probably, should work, looks correct, most likely, I assume, apparently*.
13. **Rollback Plan** — steps to revert if production issues, plus the post-deploy watch (escape class E10): if Prod-DB is on, run `Skill(prod-sentinel)` after the deploy and after every import in the release, against a named baseline.
14. **Sign-Off** — QA, Dev, PM sign-off lines with dates.

**Ticket transitions (only when asked, Jira on):** a sign-off that will change ticket statuses requires a fresh live read of each ticket this run, the audit pass above, and the transition / assignee rules in `PROJECT-PROFILE.md §15`. A developer ruling ("this is intended") is recorded as a ruling, not a fix — "PASS as ruled", citing the comment.
