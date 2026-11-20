# QA Standards - evidence folder and the run report contract

Part of `qa-standards`. Moved out of SKILL.md to keep the always-loaded file small; the headings are unchanged, so a reference such as "qa-standards -> Verdict Contract" still lands in SKILL.md, which points here.

---

## Evidence folder convention

`qa-evidence/`, root per `PROJECT-PROFILE.md §12`:
- **ONE convention, one folder per run:** `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` (e.g. `qa-evidence/APP-558-20260827/`, `qa-evidence/BUG-20260827-143012/`). `HHMMSS` avoids collisions across parallel sessions.
- Inside: API responses (`<slug>_api-response.json`), screenshots (`<slug>.png`), logs (`<slug>.log`), DB dumps (`<slug>.csv`), notes (`<slug>_evidence.md`), the run's prompt (`00-prompt-<subject>.md`), config (`.yml`) where relevant.
- **HOW to write** — the read-only QA hook BLOCKS the `Write`/`Edit` tools for `qa-evidence/`. Use one of: (1) `mcp__filesystem__write_file` with the target path (preferred); (2) Bash heredoc into the folder; (3) **Playwright screenshots — pass an explicit path:** call `mcp__playwright__browser_take_screenshot` with `filename: qa-evidence/<run-folder>/<name>.png` so the PNG lands in `qa-evidence/`. A BARE filename saves to the repo root, NOT `qa-evidence/`; the PostToolUse copy hook is only a backstop.
- Bug *reports* and findings live in the chat conversation (and the tracker), not as markdown files in `qa-evidence/`. The folder holds attachments only - plus the run record `run.json` and the audit `package.md` (`references/run-record.md`).
- When you hand evidence to the user, give **one full absolute folder path** (the run folder) plus a relative link, then list only the files they need.

---

## Run report contract — the lines the completion gate reads

**Case completeness and skills loaded — with every audit that passes a run verdict:** the line `Case completeness: AC sentences a/A · roles×actions b/B · branches c/C · Step 1c classes d/D · UI controls e/E (screenshots opened s/S) · silent-story questions q` (full-qa Phase 8a; `Case completeness: n/a (<why>)` when the skill writes no cases; gate check #18), and `Skills loaded: <skill> ✓ · <skill> n/a (<why>) …` covering the calling skill's own phase skills (full-qa: its Phase skill map) (`Skills loaded: n/a (<why>)` when the skill loads no other skill; gate check #19 compares every ✓ with the Skill calls in the session transcript).

**Run line — the first line of every run report** (`full-qa`, `qa-validate`, `release-check`, `qa-team`, a standalone `regression-runner`, and a `bug-verifier` verdict that moves a ticket): one plain line, never in backticks: `Run: <skill> | QA mode: <mode> | Audit: AUDIT_PASSED` (or `AUDIT_FAILED`). The completion gate reads the skill, the mode and the audit result from it: every run report covers the core-page sweep route by route (check #20; `bug-verifier` exempt; skipped when Browser is `off` in §2), a full / regression / bugfix / release report needs `Regression: <area>` rows that ran (check #21), and a run report without the line is flagged (check #22). *(Illustrative: a gate that keyed on the bare word AUDIT_PASSED never checked more than half of the past run reports, because they never printed it.)*

**The report passes the gate's own checks:** save the draft verdict message to a file in the OS temp folder (never the evidence folder) and run `python .claude/skills/qa-standards/scripts/gate-audit.py --assume-passed <that file> [<session transcript>]` before AUDIT_PASSED is written — read-only, the same checks the Stop hook runs (checks #15–#22 hold a run report to the Run line, case completeness, skills loaded, core-page sweep and regression rows); exit 0 = the gate would pass it.
