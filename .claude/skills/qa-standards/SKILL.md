---
name: qa-standards
description: Use when running any QA skill or sub-agent — the shared, mandatory standard for scope locking, full-flow + impact coverage, the evidence ledger, mutation safety, QA modes, cross-layer checks, bug classification, MCP-server routing, plugin escalation, the completion gate, the verdict contract, judgement discipline, escape classes, and the memory ritual. Read once per QA session.
---

# QA Standards (Shared Module)

The single source of truth every QA skill and sub-agent obeys. **Read this once at the start of a QA session**, then follow the gates inline in each skill. Individual skills inline only the safety-critical gates (Scope Lock, Mutation Safety, Memory) so they survive even when this file is not loaded; everything else lives here to keep skills short.

All project specifics (URLs, repos, branches, DB, roles, tracker, policies) come from `.claude/PROJECT-PROFILE.md`. This file never names a project; it names the profile section that does.

**Core philosophy (why this exists):** QA misses come from testing *the changed code only* and declaring PASS. A change is never just its diff — it has direct dependents and indirect blast radius (shared components, shared endpoints, shared tables, cron/worker jobs, caches, downstream reports, every role that touches the flow). **You validate the full user flow and the whole blast radius, not the diff.** When in doubt, reproduce it, try to break it, and cover every related case before giving a verdict.

## Contents
**Inline (always loaded):** Scope Lock · Evidence Ledger · Mutation Safety Gate · Completion Gate ·
Verdict Integrity · Execution Register · Evidence provenance · Verdict Contract · the six questions ·
Escape classes E1-E13 · the run record (`references/run-record.md`, checked by `scripts/verdict_check.py`).
**References (read when the step needs them; every heading below still points there):**
[`coverage-and-routing.md`](references/coverage-and-routing.md) (modes, impact, cross-layer, classification,
case quality, MCP routing, plugins, skill sequence, environments) ·
[`judgement.md`](references/judgement.md) (data resources, source hierarchy, fresh vs historical, reuse,
judgement discipline) · [`memory-ritual.md`](references/memory-ritual.md).
**Before any verdict or audit, read `references/judgement.md`.**

---

## QA Modes — pick the gear before testing

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Pick smoke / targeted / regression / bugfix / full / release from the table there and state the mode and why before testing.

---

## Scope Lock — REQUIRED before any tool runs

Before the first DB query, API call, or browser action, output this table. It is the contract for the session. **If a critical field is unknown, ask — do not guess.**

| Field | Value |
|---|---|
| Feature / story / bug / PR | |
| QA mode | smoke / targeted / regression / bugfix / full / release |
| Roles in scope | `<roles: PROJECT-PROFILE.md §8>` (e.g. Admin / Manager / User / Guest / Other) |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | |
| Direct dependents (see Impact Analysis) | |
| Indirect blast radius | |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only) — per `PROJECT-PROFILE.md §5` |
| Branch / commit under test | `<branch: PROJECT-PROFILE.md §3> @ <short sha>` (captured once, reused in every evidence row) |
| Risk level | Low / Medium / High |
| Stop conditions | feature undeployed / schema missing / wrong branch / auth fails |

A change is in scope **plus** everything the Impact Analysis surfaces. Do not silently narrow scope to make a PASS easier; if you must drop coverage, say so explicitly and why. The denominator `M` of the confidence line is the code-derived matrix from `test-cases-generator` Step 1b, never intuition.

---

## Impact Analysis & Coverage — direct + indirect blast radius

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Direct + indirect blast radius and the coverage dimensions every case set must span; an untested dimension is a named gap.

---

## Evidence Ledger — REQUIRED

Every finding (bug OR proof-of-correct) maps to at least one evidence item. Output this table in every QA result (with the provenance columns — see *Evidence provenance*):

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

**Allowed evidence types:** DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), API contract (Postman/OpenAPI), Git diff/commit.

**Hard rules — these reduce false positives and false PASSes:**
- **No evidence = no finding.** A claim without a ledger row does not exist.
- **No reproduction = no confirmed bug.** Suspected != confirmed (see `bug-verifier`).
- **No DB / API / Browser comparison = no cross-layer claim.** Don't say "the API is wrong" without the DB row next to it.
- Save proof for **PASS** too, not only bugs — a green result needs evidence it was actually exercised.

**Evidence folder convention** (`qa-evidence/`, root per `PROJECT-PROFILE.md §12`):
- **ONE convention, one folder per run:** `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` (e.g. `qa-evidence/APP-558-20260827/`, `qa-evidence/BUG-20260827-143012/`). `HHMMSS` avoids collisions across parallel sessions.
- Inside: API responses (`<slug>_api-response.json`), screenshots (`<slug>.png`), logs (`<slug>.log`), DB dumps (`<slug>.csv`), notes (`<slug>_evidence.md`), the run's prompt (`00-prompt-<subject>.md`), config (`.yml`) where relevant.
- **HOW to write** — the read-only QA hook BLOCKS the `Write`/`Edit` tools for `qa-evidence/`. Use one of: (1) `mcp__filesystem__write_file` with the target path (preferred); (2) Bash heredoc into the folder; (3) **Playwright screenshots — pass an explicit path:** call `mcp__playwright__browser_take_screenshot` with `filename: qa-evidence/<run-folder>/<name>.png` so the PNG lands in `qa-evidence/`. A BARE filename saves to the repo root, NOT `qa-evidence/`; the PostToolUse copy hook is only a backstop.
- Bug *reports* and findings live in the chat conversation (and the tracker), not as markdown files in `qa-evidence/`. The folder holds attachments only - plus the run record `run.json` and the audit `package.md` (`references/run-record.md`).
- When you hand evidence to the user, give **one full absolute folder path** (the run folder) plus a relative link, then list only the files they need.

---

## Mutation Safety Gate — before any write

Applies to any DB UPDATE/INSERT/DELETE AND any POST/PUT/PATCH/DELETE API call. The environment is read-only by policy; writes are the exception, not the default.

1. Confirm the target is **in scope** (Scope Lock).
2. Prefer **existing disposable test data** over creating new rows.
3. **SELECT and log the original state first** (exact row, all columns you may touch).
4. Have a **rollback plan** before the write.
5. Never run destructive calls against **shared/prod** data. Prod DB is **read-only** — never mutate prod.
6. UPDATE/DELETE **must** have a WHERE. Never hard-DELETE — prefer status / soft-delete changes (confirm the mechanism per `.claude/rules/db-gotchas.md`).
7. After the test, **verify** DB state and **restore**, then SELECT again to confirm restoration (verify by the inserted row id, never by a count that another row could satisfy). Log it:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

If rollback is impossible (no clean restore path) -> **STOP and ask the user** before mutating.

---

## Cross-Layer Consistency — DB / API / Browser

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Compare DB -> API -> Browser per entity in one table; matching API and UI proves transport, not correctness.

---

## Bug Classification — FE / BE / Admin / Report / DB / Both

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Every bug is FE / BE / Admin / Report / DB / Both - never ambiguous.

---

## Test-Case Quality Bar

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Every case is executable: steps, expected result with its source, the tool, the evidence it must leave.

---

## MCP Server Routing — which server for which job

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Which MCP server answers which question, and the fallbacks when one is off.

---

## Plugins & escalation — when to escalate (optional plugins)

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Optional plugins (PROJECT-PROFILE.md §17) and their by-hand equivalents.

---

## Memory Ritual — MANDATORY post-session

> Moved to [`references/memory-ritual.md`](references/memory-ritual.md). Every skill and agent updates memory before claiming completion (each skill's Post-Session block carries the steps); grep first, update instead of duplicating, mark disproved facts SUPERSEDED, verify with ls -la, HALT if it cannot be persisted.

---

## Recommended Skill Sequence

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). The usual order of skills for a story, a bug and a release.

---

## Environments & Layer Rules — pointers

> Moved to [`references/coverage-and-routing.md`](references/coverage-and-routing.md). Where environment URLs, DB connections and layer rules live (PROJECT-PROFILE.md §5/§6, rules/).

---

## Completion Gate — when you are allowed to stop

Deciding "am I done?" is the single biggest source of missed defects. It is not a judgement call
in `full` / `release` / `regression` modes — it is a checklist you must be able to fail.

**Do NOT produce a verdict while ANY of these is true:**

- an in-scope area has no fresh result from THIS run
- a relevant existing bug was not independently retested (a tracker status is NOT evidence of a fix)
- a numeric value was accepted without an independent recomputation from source records
- a chart was checked visually without validating the data behind it
- a functional action was confirmed only by the presence of its control
- a paginated surface was exercised only on page 1
- a sortable column was exercised in only one direction
- an unexplained UI/API/DB contradiction remains
- a defect lacks a layer classification, or FE/BE ownership is unresolved when code or network evidence could settle it
- a write path was never exercised (every case recorded `validation-only`)
- a generated case was not executed ("priority only orders the work" — `PROJECT-PROFILE.md §16`, default: execute every case)
- the parent verdict contradicts an active blocker

**Explicitly NOT valid reasons to stop:** HTTP 200 · UI value equals API value · the page renders ·
it passed last time · it resembles the design · a sub-agent reported it fine · the request was short.

**Disposition rule.** Every in-scope area ends at one of the canonical values defined ONCE in **Verdict Contract** below. Do not restate them anywhere else — a second copy is where drift starts.
Silence is not a result, and **an untested dimension is never an implied pass** — name it as a gap
with the reason and what would unblock it.

The `completion-gate.py` hook (Stop / SubagentStop) is the mechanical backstop for this section: advisory by default, blocking when `QA_GATE_ENFORCE=1` or `harness-config.json → gate.enforce` is set.
- **The run record agrees with itself:** `verdict_check.py qa-evidence/<run-folder>` exits 0 (the completion gate runs the same check when a verdict names the run folder).

## Verdict Integrity — challenge yourself before the user has to

Run this against your own conclusions before reporting. The goal is that a wrong verdict is caught
here, by you, rather than later by the user pushing back.

1. **Every PASS:** what evidence would prove this wrong? Go look for it.
2. **Every FAIL:** is the expected behaviour actually specified in the ticket / AC / design / code
   contract, or am I inventing a requirement? Quote the source or withdraw the finding.
3. **Before claiming something is missing, check the scope predicate.** "Absent from X" is only a
   defect if it was ever in scope for X.
4. **Read the semantic contract before judging a value** — the column comment, the AC, the code
   comment. A surprising number is not automatically a wrong number.
5. **Agreement between your own sub-agents is NOT independent confirmation.** They inherit your
   framing and fail the same way. Treat correlated agreement as ONE source. The independent audit is
   `qa-verdict-auditor` in a fresh context (or the in-session audit discipline when `PROJECT-PROFILE.md §16` disables sub-agents).
6. **Operational vs structural blockers.** "Port closed", "container stopped", "credentials not
   tried" is a setup step you skipped — not proof the test is impossible. Try to unblock first.
7. **Anything filed externally must be reproduced first-hand by the orchestrator.** A sub-agent's
   report is a lead, not a finding.
8. **Report confidence and what would change it.** Never state an inference in the same voice as a
   reproduced fact.
9. **A UI FAIL needs proof the element was on screen.** Collapsed accordion, virtualised list, other
   tab, tooltip not open yet: suspect the reader first, cross-check the captured API body, then decide.
10. **An automated rule (axe, Lighthouse, a linter) is a lead, not a reproduction.** Reproduce it by
    hand in the supported browser before filing.

If this pass changes a conclusion, **say so explicitly** in the report. A withdrawn finding is a
result worth recording — inside the row, never a silent flip.

*Illustrative failure modes this list catches: [`references/judgement.md`](references/judgement.md).*

## Data resources — exhaust these before recording a coverage gap

> Moved to [`references/judgement.md`](references/judgement.md). Exhaust fixtures, sample libraries, replicas and read-only prod before recording a coverage gap.

## Authoritative Source Hierarchy — what wins when sources disagree

> Moved to [`references/judgement.md`](references/judgement.md). What wins when the ticket, the contract, the code and the docs disagree. Read it before any FAIL.

## Fresh vs Historical Evidence

> Moved to [`references/judgement.md`](references/judgement.md). Only evidence captured in THIS run counts; remembered results and ticket states are leads, both ways.

## Reuse assets, not conclusions

> Moved to [`references/judgement.md`](references/judgement.md). Reuse scripts and queries, never their old results.

## Execution Register — REQUIRED for full / release / regression

Every in-scope item gets a row and a disposition. No applicable item may disappear silently.
Output this in the result alongside the Evidence Ledger:

| ID | Area | Requirement / AC | Expected source | Check performed | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|---|

`Result` is exactly one of the canonical values defined in **Verdict Contract** below — that section is the ONLY place they are enumerated.
BLOCKED and NOT APPLICABLE both REQUIRE a reason and, for BLOCKED, what would unblock it.
An empty `Result` is not permitted: if you cannot fill it, write NOT YET VERIFIED — silence is never a pass.
Also REQUIRED (any mode) whenever the verdict will change a tracker status.

## Evidence provenance — stamp every row

A finding that cannot be tied to a build and an environment cannot be retested or handed over.
Every Evidence Ledger row carries:

- **Env** — TEST / DEV / PROD-readonly / local replica (the environments in `PROJECT-PROFILE.md §5/§6`). Record it on EVERY row.
- **Branch / Commit** — `<branch> @ <short sha>` from `git rev-parse --short HEAD` in the repo that owns the code under test. Capture it once at Scope Lock time and reuse.
- **Captured at** — timestamp of the observation.

**Environment attribution rule.** A result observed on DEV, on a local replica, or on PROD is
evidence for THAT environment only. It may NEVER be reported as evidence for the target
environment. If you must cross environments, label the row and say why.

## Verdict Contract — the ONLY definition

Every skill, agent and report uses THESE words and THESE meanings. No skill may restate or
re-define them; it references this section. (Independent copies drift — "0 bugs" vs "0 confirmed
bugs" — and incompatible enums appear; one definition prevents that.)

**Area result** (one per Execution Register row):
| Result | Meaning | Requires |
|---|---|---|
| **PASS** | current, reproduced evidence supports the expected behaviour | ≥1 Evidence Ledger row with provenance |
| **FAIL** | expected behaviour established from an authoritative source AND actual behaviour reproduced AND they differ | expected-source citation + reproduction evidence |
| **BLOCKED** | could not be executed for a concrete reason | the reason + what would unblock it (operational blockers must be attempted first) |
| **NOT APPLICABLE** | provably outside the behaviour under test | the scope predicate that excludes it |
| **NOT YET VERIFIED** | in scope, not executed in THIS run | listed explicitly — never omitted |

**Run verdict** (one per run) — under the project's verdict policy (`PROJECT-PROFILE.md §16`; default **strict binary**):
- **GO** — exactly 0 confirmed bugs (confirmed = reproduced + ledger row) across all executed areas, and 0 rows NOT YET VERIFIED in mandatory scope.
- **NO-GO** — 1+ confirmed bugs, any layer, any severity. No "conditional GO", no severity weighting (unless §16 selects a severity-weighted policy, in which case the policy text defines the threshold and the verdict names it).
- **PARTIAL** — a hard blocker stopped an in-scope area; name it.
Skill aliases are permitted ONLY in parentheses after the canonical word: `qa-validate` ready/not-ready, `regression-runner` no-regression/regression-found, `release-check` APPROVED/NOT APPROVED, `qa-team` PASS/FAIL — the canonical word always prints first.

**Finding verdict** (`bug-verifier`): **CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE** — these describe one finding, never a run.

**Report vocabulary** (every final report/comment): **Confirmed** (supported by current evidence) · **Finding** (confirmed incorrect behaviour) · **Blocked** (concrete limitation, stated) · **Remaining Risk** (not fully proven, could change the conclusion) · **Not Applicable** (explicitly outside scope). Banned in verdict lines: *seems fine, probably, should work, looks correct, most likely, I assume, apparently*.

**Confidence line — mandatory with every run verdict:** `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: <one line or "none">`. Confidence is proportional to evidence: if 8 of 10, say 8 of 10. `M` is the code-derived matrix size. Recompute it with `scripts/verdict_check.py` from `run.json`; never type it by hand.

**Ticket-transition rule:** a verdict that will change a tracker status (any mode, including `bug-verifier`) requires (1) a fresh live read of the ticket this run, (2) an audit pass returning AUDIT_PASSED on the package (findings + ledger + register + proposed verdict) — by `qa-verdict-auditor` in a fresh context, or in-session item by item against Verdict Integrity 1-10 when `§16` disables sub-agents, (3) the transition rules in `PROJECT-PROFILE.md §15` (read the available transitions live; never reuse an id from a previous session). A ruling from a developer ("this is intended") is recorded as **a ruling, not a fix** — the verdict says "PASS as ruled" and cites the comment. Never re-file or close tickets to repair a filing mistake without asking.

## Judgement Discipline

> Moved to [`references/judgement.md`](references/judgement.md). Fact vs inference labels, partially-empty rows, negative evidence, shared components, coverage quality. Read it before any verdict.

## Before the first tool call — the six questions

Write these out explicitly (2-6 lines) in `full-qa`, `qa-validate`, `bug-verifier`, `release-check` before the first tool runs:
1. **What is requested?** (the literal ask, and the mode it implies)
2. **What is authoritative?** (ticket / AC / spec / code contract / ruling — per Source Hierarchy)
3. **What can be verified?** (which layers, with which tools, in which environment)
4. **Which assumptions are eliminated?** (name them; each becomes a check)
5. **What evidence is required?** (the ledger rows a GO would need)
6. **What is completion?** (the register rows that must all be non-empty)

## Escape classes & their gates

Every agent preloads this file, so this is where these gates become binding for sub-agents too.
The full text of Rules 1-5 lives in `.claude/rules/anomaly-disposition.md` (always loaded in the main session).

A bug reaches production through one of these doors. Each has a gate now. **Name the door in the verdict
when you close one.**

| # | Escape class | What it looks like *(illustrative)* | Gate |
|---|---|---|---|
| E1 | **Dissolved anomaly** — seen, then closed as "by design" / "workaround" / "unresolved" | an unexpected merge called by-design in a note; a masked error "parked" | Rule 1: ticket, or "expected" WITH A CITED SOURCE. Gate check #10 flags the phrases. |
| E2 | **Data release without QA** — content import changes reachable code paths | a bulk import that made two latent bugs live the same day | Rule 2 pre-flight question + post-import re-test; `prod-sentinel` S5 detects imports |
| E3 | **Latent assumption** — code assumes 1 / one branch / populated field; data grows past it | `[firstRow]` · an `else` arm never run · "the parser always returns text" | `Skill(latent-pattern-sweep)` crosses code vs PROD distribution |
| E4 | **Same input every time** — the flow is green with one file/fixture | three runs, one text-layer PDF | Input-class column in every case; fixture registry in `test-data-manager` |
| E5 | **Validation green ≠ feature green** — PASS proven by a toast, no write ever happened | five green cases, zero API calls; the write path had data loss | Path-exercised column; Rule 5; gate check #11 |
| E6 | **Symptom fix** — the fix never touched the root-cause line | a PR that changed the component but left the root-cause line untouched | `git diff --name-only` must include the ticket's root-cause file; gate check #12 |
| E7 | **Wrong repo** — the owner is a worker/Lambda, not FE/BE/Admin | the terminal writer lived in an integration repo | `bug-verifier`: trace the async chain to its terminal writer |
| E8 | **Silent async no-op** — success flash, nothing created | an early `return` when a matching draft exists | verify the terminal DB state, never the enqueue |
| E9 | **Masked error** — real failure reported as an unrelated exception | a `throw` commented out years ago | Rule 4: file it separately |
| E10 | **Unwatched production** — damage accrues for weeks in one table | error rate tripled for a month, visible in one log table | `Skill(prod-sentinel)` weekly + after every deploy/import |
| E11 | **Untested ship** — a ticket moves to a deploy state with no QA touch | a ticket at "ready to deploy" nobody tested | `env-health` release radar every session |
| E12 | **Guessed denominator** — "7 of 12" where the code has 24 cells | the matrix was counted from intuition | `test-cases-generator` Step 1b: derive origin × mode × type × action from code |
| E13 | **Knowledge decay** — the harness forgets; rotation silently broken | undated index entries never archived | `MEMORY.md` entries carry `YYYY-MM-DD` in the link title; archives pointer in the header |

**Verdict-line rule:** when a run finds nothing, state which of E1–E13 were actively checked. An escape
class not checked is a NOT YET VERIFIED row, not silence.
