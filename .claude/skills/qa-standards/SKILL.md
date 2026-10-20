---
name: qa-standards
description: Use when running any QA skill or sub-agent — the shared, mandatory standard for scope locking, full-flow + impact coverage, the evidence ledger, mutation safety, QA modes, cross-layer checks, bug classification, MCP-server routing, plugin escalation, the completion gate, the verdict contract, judgement discipline, escape classes, and the memory ritual. Read once per QA session.
---

# QA Standards (Shared Module)

The single source of truth every QA skill and sub-agent obeys. **Read this once at the start of a QA session**, then follow the gates inline in each skill. Individual skills inline only the safety-critical gates (Scope Lock, Mutation Safety, Memory) so they survive even when this file is not loaded; everything else lives here to keep skills short.

All project specifics (URLs, repos, branches, DB, roles, tracker, policies) come from `.claude/PROJECT-PROFILE.md`. This file never names a project; it names the profile section that does.

**Core philosophy (why this exists):** QA misses come from testing *the changed code only* and declaring PASS. A change is never just its diff — it has direct dependents and indirect blast radius (shared components, shared endpoints, shared tables, cron/worker jobs, caches, downstream reports, every role that touches the flow). **You validate the full user flow and the whole blast radius, not the diff.** When in doubt, reproduce it, try to break it, and cover every related case before giving a verdict.

## Contents
- QA Modes — pick the gear before testing
- Scope Lock — REQUIRED before any tool runs
- Impact Analysis & Coverage — direct + indirect blast radius
- Evidence Ledger — REQUIRED; no evidence = no finding
- Mutation Safety Gate — before any write (DB or API)
- Cross-Layer Consistency — DB / API / Browser
- Bug Classification — FE / BE / Admin / Report / DB / Both
- Test-Case Quality Bar — every case is executable
- MCP Server Routing — which server for which job
- Plugins & escalation — when to escalate (optional plugins)
- Memory Ritual — MANDATORY post-session
- Recommended Skill Sequence
- Environments & Layer Rules — pointers
- Completion Gate · Verdict Integrity · Data resources · Authoritative Source Hierarchy · Fresh vs Historical · Reuse assets · Execution Register · Evidence provenance
- Verdict Contract — the ONLY definition of area results and run verdicts
- Judgement Discipline — fact vs inference, partial-empty rows, negative evidence, coverage quality
- Before the first tool call — the six questions
- Escape classes & their gates (E1–E13)

---

## QA Modes — pick the gear before testing

Choosing a mode prevents over-testing (wasting a session) and under-testing (missing the blast radius). If the user did not state a mode, **infer the smallest mode that covers the request and state which you picked** in the Scope Lock; ask only if genuinely ambiguous.

| Mode | When | Runs |
|------|------|------|
| **smoke** | Quick "is it alive" check | Login + one critical path + console/network scan |
| **targeted** | One named feature / field / endpoint | Just that surface, all its roles + negative cases |
| **regression** | After a change, guard nearby behavior | Changed feature **+ indirect blast radius** (see Impact Analysis) |
| **bugfix** | Verify a fix landed | Reproduce original bug with the reporter's ORIGINAL input (must now fail to reproduce) + the fix must touch the root-cause `file:line` + regression around the root cause |
| **full** | New/changed feature, full confidence | All phases: prompt → cases → code → DB → API → UI/E2E → security → perf → audit → report |
| **release** | Sign-off on a batch/release | `full` per area + release checklist + GO/NO-GO |

`regression`, `bugfix`, and `release` **must** complete the Impact Analysis below — that is exactly where "obvious" bugs hide.

**Scale effort to STAKES, not to prompt length.** A one-line request can carry a release decision. State the mode you picked and why.

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

For every change under test, enumerate the blast radius **before** writing the verdict. This is the antidote to "we only tested the diff."

**1. Direct** — what the diff literally touches: the changed component, route, query, column.

**2. Indirect (where obvious bugs hide)** — trace each outward:
- **Shared FE components** — is the changed component reused on other pages? Grep imports.
- **Shared API endpoints** — do other features call the same endpoint? Different params/roles?
- **Shared DB tables/columns** — what else reads/writes this table? Reports, dashboards, exports, other endpoints.
- **Async consumers** — cron jobs, workers/Lambdas, queues, storage events, email (`PROJECT-PROFILE.md §11`). Trace an async chain to its **terminal writer** — the enqueue proves nothing.
- **Caches & snapshots** — client query caches, snapshot/aggregate tables, materialized aggregates that drift from live data.
- **Downstream reports/exports** — CSV columns, reports, dashboards (online vs offline scope).

**3. Coverage matrix** — for the in-scope surface, confirm you hit every cell that applies:

| Dimension | Must cover |
|---|---|
| Roles | every role that can reach the flow (`PROJECT-PROFILE.md §8`) |
| States | empty / single / many / max; draft vs published; active vs deleted; null vs zero |
| Inputs | valid (positive) **and** invalid/missing/malformed (negative) + boundaries |
| Input class | for any parse/upload surface: every input CLASS (e.g. text-layer PDF vs scanned image-only vs 0-byte) — see `test-data-manager` → INPUT-CLASS FIXTURE REGISTRY |
| Flow | the **full** user journey end-to-end, not just the changed screen |
| Path exercised | `validation-only` vs `write` — a write case is closed only by the network log AND a DB read-back |
| Cross-tenant | other accounts/tenants cannot see or act on this data |
| Regression | the indirect areas above still behave |

If a dimension is untested, it is a coverage gap — name it in the report, do not imply it passed.

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
- Bug *reports* and findings live in the chat conversation (and the tracker), not as markdown files in `qa-evidence/`. The folder holds attachments only.
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

For each entity in scope, the same value must agree across all three layers. Mismatch = bug.

1. **DB** — the DB tool from `PROJECT-PROFILE.md §6` (template default `mcp__mcp_server_mysql__mysql_query`) — the stored truth.
2. **API** — if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for the route, call it as the right role; otherwise `mcp__http-client__*`; or replay the FE's request captured via `mcp__chrome-devtools__*` byte-for-byte.
3. **Browser** — `mcp__playwright__*` snapshot / DOM.

Compare in one table: `| Field | DB | API | Browser | Match? |`. Consistency dimensions: value, count, status, date/time format, null handling, soft-delete filtering, FK resolution, aggregation, ordering, pagination.

**Matching API and UI proves transport, not correctness.** Correctness needs source records → an independent expected calculation → API → UI, and the difference located.

The project's entity → tables → endpoints map lives in `PROJECT-PROFILE.md §10` and `.claude/references/system-map.md`. Illustrative shape:

| Entity | DB table(s) | API endpoint(s) |
|---|---|---|
| User / Manager | `user`, `user_account` | `GET /api/<resource>/users` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Computed output / score | snapshot tables (`PROJECT-PROFILE.md §11`) | `GET /api/<resource>/scores` |

(Roles may live in a membership table, not on `user`. See `.claude/rules/db-gotchas.md`.)

---

## Bug Classification — FE / BE / Admin / Report / DB / Both

Apply on every confirmed bug so downstream skills don't re-derive it:

1. **Call the API directly.** Correct data but UI wrong -> **FE**. No call when one was expected -> **FE**. Wrong data / unexpected 500/404 -> go to 2.
2. **Query the DB.** DB correct but API wrong -> **BE** (query/logic). DB wrong -> **BE** (write-side) or **DB** (schema/migration).
3. **Edge cases:** Admin panel -> **Admin**. Reporting service (`PROJECT-PROFILE.md §3`) -> **Report**. API wrong AND UI mishandles the error -> **Both**. An async worker/Lambda that owns the terminal write -> **BE** with the worker named (the owner is a worker, not the API — escape class E7).

---

## Test-Case Quality Bar

Every test case — generated or executed — is **executable**, never vague. Minimum columns:

`TC ID | Requirement/AC | Scenario | Preconditions | Test Data | Input class | Steps | Expected (with its SOURCE) | Layer | Role | Priority | Automation? | Execute With | Evidence Required`

Every executed case records **Expected**, **Actual**, **Path exercised** and an explicit **Pass/Fail** (not "looks fine"). A case with no expected result is not a test. **An expected value that QA wrote needs a quotable source** (story line, contract, brief, design decision, code comment); if there is none, the case expects "UNKNOWN / ask" — never whatever the UI happens to do.

---

## MCP Server Routing — which server for which job

Use **fully-qualified** tool names (`mcp__server__tool`) so the right server is hit. Use only servers whose capability is `on` in `PROJECT-PROFILE.md §2`.

| Job | Server | Notes |
|---|---|---|
| Query **test/dev** DB | `<DB tool: PROJECT-PROFILE.md §6>` (default `mcp__mcp_server_mysql__mysql_query`) | DB `<test DB name: PROJECT-PROFILE.md §6>` on `<DB host: PROJECT-PROFILE.md §6>` |
| Query **prod** DB (read-only) | `mcp__mcp_server_mysql_prod__mysql_query` (or the engine's equivalent) | Confirm a prod repro. Access path per `PROJECT-PROFILE.md §6` (often an SSH tunnel). **Never mutate prod.** |
| Browser UI: clicks/forms/snapshots/screenshots | `mcp__playwright__*` | Primary E2E driver |
| Network/console/perf inspection | `mcp__chrome-devtools__*` | Capture the real FE request + console errors during repro |
| Direct API calls | `mcp__http-client__*` | Clear stale headers (`set_default_headers` merge:false) before auth |
| Act as a role through typed tools | `PROJECT-PROFILE.md §14` (optional project MCP) | One typed call can replace token minting + headers + URL building; prefer it when present |
| Existing API contracts | `mcp__postman-api-mcp__*` | Search first — source of truth for URL/headers/body (Postman capability) |
| Code/PR/commit/diff (remote) | `mcp__github__*` | `search_code`, `pull_request_read`, `list_commits` (GitHub capability); local repos use read-only `git` verbs |
| Evidence files | `mcp__filesystem__*` | Writes allowed only under `qa-evidence/` |
| Issue tracker | `mcp__claude_ai_Atlassian__*` for Jira (`PROJECT-PROFILE.md §15`) | Pull AC from a ticket; file/annotate issues when authorised |

**Default tool choices:** DB -> the profile's DB MCP (never another engine's). UI -> Playwright. API -> typed project tools if any, else http-client (Postman for contracts). Code search -> Read/Grep/Glob (NOT Bash cat/grep). Parallel multi-layer work -> Agent sub-agents, when `PROJECT-PROFILE.md §16` allows them.

---

## Plugins & escalation — when to escalate (optional plugins)

Plugins are **optional enhancers** (`PROJECT-PROFILE.md §17`). Use them only when they add real QA value — never reflexively. When a plugin is not installed, do the by-hand equivalent in the right-hand column.

| Situation | With the plugin | Without it |
|---|---|---|
| A confirmed bug whose root cause is non-obvious after the standard cross-layer pass | `superpowers:systematic-debugging` | hypothesis → isolate one variable → verify, written down |
| An intermittent/race/timing bug | `superpowers:systematic-debugging` + repeat for a reproduction rate | `flaky-race-verifier` |
| About to claim DONE/PASS/FIXED | `superpowers:verification-before-completion` | run the Completion Gate list below against your own output |
| Designing a new skill or a non-trivial test strategy | `superpowers:brainstorming`, then `superpowers:writing-skills` | write the goal, the failure it prevents, then the steps |
| Large independent fan-out (multi-area regression) | `superpowers:dispatching-parallel-agents` (or `qa-team`) | `qa-team`, or sequential lanes when sub-agents are disabled |
| A hard or intermittent bug that needs a repro harness BEFORE any hypothesis | `mattpocock-skills:diagnosing-bugs` **Phases 1–4 only** (red feedback loop → minimise → 3–5 ranked falsifiable hypotheses → instrument one variable at a time). Never its fix phases — this setup is read-only | the same four steps by hand |
| Ambiguous or missing acceptance criteria, owner present | `mattpocock-skills:grilling` — numbered rounds, each question with a recommended answer; facts looked up in-session; each answer becomes the cited source for an expected result | ask the same numbered questions yourself, one round at a time |
| Owner absent, AC ambiguous | — | record the ambiguity as an open question, take the code-derived reading, label it INFERRED |
| Editing any `.claude/skills/*`, `CLAUDE.md` or a rule file | `mattpocock-skills:writing-for-agents` + `superpowers:writing-skills` | follow `docs/maintainers/generalization-conventions.md` |

The built-in `/debug` (Claude Code) is a lighter alternative for a quick, single-thread root-cause dig. Prefer `systematic-debugging` (or the by-hand steps) when the bug spans layers. Plugin skills that write code or repository files (tdd, implement, to-spec, code-review variants that patch) are never used in a read-only QA session.

---

## Memory Ritual — MANDATORY post-session

**Every skill and sub-agent updates auto-memory before claiming completion.** Not optional. If memory cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Create/update a memory file** under `<memory folder: PROJECT-PROFILE.md §12>` (the ONLY path the `Write` tool is allowed — use `Write` directly here). Naming: `project_<slug>.md` (QA runs), `feedback_<slug>.md` (guidance), `reference_<slug>.md` (pointers). Frontmatter:
   ```markdown
   ---
   name: <short title>
   description: <one-line searchable hook>
   metadata:
     type: project | feedback | reference | user
   ---
   ```
2. **Cross-reference first.** Grep the memory folder for the endpoint / file path / user ID / symptom. If an entry already covers this root cause, **UPDATE it** with today's reproduction — do not file a duplicate.
   **Supersession rule:** when today's evidence DISPROVES a fact in an older memory, you must, in the SAME session, insert directly under that older file's frontmatter: `> ⚠️ SUPERSEDED on <date> by [[<new-file>]] — <what changed>` AND fix its `MEMORY.md` index line. A newer-dated file that repeats a disproven fact is the most dangerous record in the store — never leave the old claim unmarked.
3. **Update the index** `MEMORY.md` with one <=200-char line: `- [<title> YYYY-MM-DD](<file>.md) — <hook>`. The date in the link title is what the rotation hook uses to archive old entries (escape class E13).
4. **Required content:** feature/date, verdict = the canonical run verdict per *Verdict Contract* (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/accounts by identifier), root-cause location (`path:line`), regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.

---

## Recommended Skill Sequence

A typical full validation flows: **prompt-generator (Step 0: the researched, self-contained prompt that decides /goal and /loop) -> sync-repos -> env-health -> login -> scope-lock (this module) -> test-data-manager -> test-cases-generator -> pr-risk-analyzer -> code-review -> db-check -> api-test -> browser-test -> security-review -> perf-test -> bug-verifier -> bug-report -> verdict audit -> qa-report** (memory write at each step). `full-qa` and `qa-team` orchestrate this; `qa-validate` is the lighter cross-layer path; `release-check` is the release-level orchestrator. `bug-verifier` precedes `bug-report` — never report an unverified bug.

**Specialized skills — slot in when relevant:** `regression-runner` (drive the blast radius after a change) · `visual-regression` + `a11y-test` (UI depth) · `observability-check` (errors the UI hides) · `flaky-race-verifier` (intermittent/race bugs) · `ai-output-eval` (computed / model-generated outputs: scores, recommendations, KPIs, report figures) · `latent-pattern-sweep` (code assumptions vs live data distribution; mandatory after a bulk import) · `prod-sentinel` (read-only production anomaly scan, weekly and after deploys/imports) · `test-together` (guided pair-testing in a shared browser) · `evidence-manager` (capture + ledger proof) · `automation-writer` (confirmed manual case -> script) · `explainer` (plain-language, per-role change summary) · `release-note` (customer-facing notes) · `demo-creator` (narrated demo video of a flow — a delivery tool, not a test).

---

## Environments & Layer Rules — pointers

- **Credentials, URLs, DB connections, repos/branches:** `PROJECT-PROFILE.md` (imported by `CLAUDE.md`, always loaded) is the source of truth. Default environment = **Test** (`§5`). Branch names are case-sensitive.
- **Layer-specific QA checks** (auto-attach when working in those repos): `.claude/rules/backend.md`, `.claude/rules/frontend.md`, `.claude/rules/admin.md`, `.claude/rules/db-gotchas.md`, `.claude/rules/testing.md`, plus the always-loaded `.claude/rules/anomaly-disposition.md` and `.claude/rules/pushback-protocol.md`. Read the relevant one before reviewing that layer.
- **System map:** `.claude/references/system-map.md` — the project's verified-from-code map (repos → API mounts → admin controllers → FE pages → DB families → async chains → armed risks). Every QA run verifies and extends one section; a section older than 60 days is treated as unverified.

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

### Failure modes this list catches *(illustrative)*
- Two lanes independently filed the same bug for rows that were **correctly out of scope by design**
  (checked one type column without checking the other).
- A "user-facing" severity claim that was actually **latent** — the columns had no read path.
- A prevalence query returning **0 instead of 2** because it assumed `deleted_at` on a table that
  uses a `status` enum.
- "No prod access" recorded as a gap when a read-only prod path existed the whole time.
- A keyboard-focus bug filed from an accessibility scanner that the real Tab walk disproved.

## Data resources — exhaust these before recording a coverage gap

See `test-data-manager` → "Data resources" and "INPUT-CLASS FIXTURE REGISTRY", and `PROJECT-PROFILE.md §6/§7/§13`. Before you EVER record a coverage gap, a missing fixture, or "no access", confirm the resource table there is exhausted. Prefer fixtures created through the platform itself (its own API or typed project tools, `§14`) over hand-written INSERTs; snapshot the returned ids for the restore. **A closed port or a stopped container is an OPERATIONAL blocker, not a structural one** — start it rather than record a false gap. Only record a gap when the resource cannot be started at all.

## Authoritative Source Hierarchy — what wins when sources disagree

"Is this a bug?" is only answerable against a source that is allowed to define correct. Rank them.
**Higher rank wins. NEVER assume the expected behaviour — name the source you are judging against.**

| # | Source | Notes |
|---|---|---|
| 1 | The ticket / story currently under test | Scope and intent |
| 2 | Acceptance criteria on that ticket | The contract |
| 3 | Clarifying comments from the dev or product owner on that ticket | Often overrides a stale AC — read the whole thread |
| 4 | Official spec / wiki page | Only if not contradicted above |
| 5 | Design (mockups / prototype) | Visual truth only; never functional truth |
| 6 | Related stories / linked bugs | Context, not licence to widen scope |
| 7 | Current implementation (code) | What it DOES, never what it SHOULD do |
| 8 | API / backend contract (collection, route handler, schema) | |
| 9 | Database + column comment semantics | Read the comment before judging any value |
| 10 | Previous evidence / auto-memory | Historical. See the next section |
| 11 | Current reproducible behaviour | Evidence of state, never of correctness |

**Conflict rule.** If two sources disagree, that is a finding in itself — **investigate and report the
conflict**. Do NOT silently pick the one that makes the verdict easier. If nothing ranked 1-6 defines
the behaviour, you are inventing a requirement: say so, and either ask or record it as an ambiguity.
A developer's reply ("keep as is") is a ruling only when the written requirement allows it; a
requirement visible to the user and still unmet stays FAIL until product changes the requirement.

## Fresh vs Historical Evidence

Auto-memory, past reports, old screenshots, prior tracker comments and earlier sessions are
**supporting context, not proof of current correctness.** They are dated snapshots.

**Use them to:** understand context, recover commands and queries, locate the right area, reuse
fixtures and credentials, recall past defects, and avoid repeating discovery.

**NEVER use them to:** close a case, confirm a fix, or justify a PASS.

**Staleness is not selective — it applies to EVERY dated claim in the record, not just the one you
came for.** A memory file typically carries several: the code root cause, the ticket status, the
assignee, the fix version, the fixture credentials, the prevalence numbers, "table X is empty".
Re-checking one of them does NOT license trusting the rest. *(illustrative)* the gate was correctly
applied to the CODE in a record — catching that HEAD already held the fix — while the ticket status
in the SAME file was still read as "To Do" from three days earlier; the ticket had moved on, and a
pointless transition was recommended. Data-state memory ages fastest: code facts stay true, row
counts do not — before writing "secondary" / "out of scope" for any environment, run one `COUNT(*)`.

**The tracker rule is bidirectional.** The Completion Gate says *"a tracker status is NOT evidence"*
of a fix. The reverse is equally true: **a REMEMBERED status is not evidence that a ticket is still
open.** Before recommending ANY transition, or describing a ticket's state, re-read it live (the tracker
tool in `PROJECT-PROFILE.md §15`) — status, assignee, fix version, parent.

Anything entering a verdict MUST be re-executed in THIS run against the target environment.
If a recalled memory names a file, endpoint, table, column or flag — **verify it still exists**
before relying on it. When memory and today's evidence disagree, today's evidence wins, and the
memory file MUST be corrected in the post-session ritual (Supersession rule).

## Reuse assets, not conclusions

Reuse scripts, queries, saved requests, fixtures, logins, tokens and environments freely —
rebuilding them wastes the session. **Reusing a testing asset is not reusing its result.**
An old query is a tool; its old output is not evidence for today. A correction made to a result row
must also be patched INTO the script that produced it; a replayed row is never counted as fresh.

## Execution Register — REQUIRED for full / release / regression

Every in-scope item gets a row and a disposition. No applicable item may disappear silently.
Output this in the result alongside the Evidence Ledger:

| ID | Area | Requirement / AC | Check performed | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|

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

**Confidence line — mandatory with every run verdict:** `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: <one line or "none">`. Confidence is proportional to evidence: if 8 of 10, say 8 of 10. `M` is the code-derived matrix size.

**Ticket-transition rule:** a verdict that will change a tracker status (any mode, including `bug-verifier`) requires (1) a fresh live read of the ticket this run, (2) an audit pass returning AUDIT_PASSED on the package (findings + ledger + register + proposed verdict) — by `qa-verdict-auditor` in a fresh context, or in-session item by item against Verdict Integrity 1-10 when `§16` disables sub-agents, (3) the transition rules in `PROJECT-PROFILE.md §15` (read the available transitions live; never reuse an id from a previous session). A ruling from a developer ("this is intended") is recorded as **a ruling, not a fix** — the verdict says "PASS as ruled" and cites the comment. Never re-file or close tickets to repair a filing mistake without asking.

## Judgement Discipline

1. **Label the epistemic status when it changes the conclusion:** VERIFIED FACT (directly evidenced) · STRONG INFERENCE (evidenced, not proven) · HYPOTHESIS (needs investigation) · UNKNOWN. Never present an inference as a fact. *(illustrative: "code unchanged" was a fact; "therefore still broken" was an inference reported as a verdict and reversed the same day.)*
2. **Partially-empty beats empty.** `0`, `false`, `null`, `undefined`, `""`, `[]`, `{}`, missing key, no rows, Not Applicable, Loading, failed request, 401/403, Unknown are DIFFERENT states — verify what each means in THIS system. Empty pages are handled everywhere; **the row that EXISTS with one field absent or in a third state is where defects live.** Test the enum width: FE union vs API union.
3. **Not found ≠ not present.** Before writing BLOCKED / NOT APPLICABLE on a negative search, rule out: incomplete search scope · different naming · other environment · feature flag / conditional path · different fixture · timing · another code path.
4. **A shared component fixed ≠ every consumer fixed.** If the scope names several consumers, each is a register row: verified, or NOT YET VERIFIED — never "fixed everywhere because they share the code".
5. **Investigation scope ≠ change scope.** Read as widely as the root cause needs; report only inside the locked scope; never let the width of the reading silently widen the verdict.
6. **Coverage quality over count.** Priority: changed code → shared dependencies → calculations/aggregations → permission boundaries → prior regressions → edge states. One deeply verified critical path outranks twenty shallow checks — but mandatory scope is still every row.
7. **Test the fix against the real wire, never the mock.** A detector/parser/mapper is verified against the actual response body / file / event shape captured live in the target environment. *(illustrative: 65/65 unit tests passed against a string body; the backend sends a JSON envelope; the fix never fired.)*
8. **Recompute; do not transcribe.** API = UI proves transport. Correctness needs source records → expected calculation → API → UI, and the difference located.
9. **Current reality overrides memory.** A remembered PASS, FAIL, fixture, password, ticket status or table state is a lead to re-verify, never evidence. Staleness is not selective.
10. **Test the flow the product supports, not just a route that is reachable.** Before filing "X can never happen for user Y", find and execute the flow the product actually provides for Y (read the developers' own path); an API route production does not use carries NOT APPLICABLE, never a FAIL.
11. **Open the artifact in its real consumer.** A CSV/PDF/XLSX export is verified in Excel / a PDF viewer / the Office app, not by `Content-Type` and `content-length`; measure bytes with `arrayBuffer().byteLength`, not `text().length`.
12. **A host string in a bundle is not proof the page contacts it.** For any allow-list or "which hosts does X call" answer, confirm each host with the live CSP header and a real call site.

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
