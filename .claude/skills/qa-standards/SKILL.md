---
name: qa-standards
description: Use when running any QA skill or sub-agent — the shared, mandatory standard for scope locking, full-flow + impact coverage, the evidence ledger, mutation safety, QA modes, cross-layer checks, bug classification, MCP-server routing, Superpowers escalation, and the memory ritual. Read once per QA session.
---

# QA Standards (Shared Module)

The single source of truth every QA skill and sub-agent obeys. **Read this once at the start of a QA session**, then follow the gates inline in each skill. Individual skills inline only the safety-critical gates (Scope Lock, Mutation Safety, Memory) so they survive even when this file is not loaded; everything else lives here to keep skills short.

**Core philosophy (why this exists):** QA misses on projects have come from testing *the changed code only* and declaring PASS. A change is never just its diff — it has direct dependents and indirect blast radius (shared components, shared endpoints, shared tables, cron/Lambda jobs, caches, downstream reports, every role that touches the flow). **You validate the full user flow and the whole blast radius, not the diff.** When in doubt, reproduce it, try to break it, and cover every related case before giving a verdict.

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
- Superpowers & built-in debug — when to escalate
- Memory Ritual — MANDATORY post-session
- Recommended Skill Sequence
- Environments & Layer Rules — pointers

---

## QA Modes — pick the gear before testing

Choosing a mode prevents over-testing (wasting a session) and under-testing (missing the blast radius). If the user did not state a mode, **infer the smallest mode that covers the request and state which you picked** in the Scope Lock; ask only if genuinely ambiguous.

| Mode | When | Runs |
|------|------|------|
| **smoke** | Quick "is it alive" check | Login + one critical path + console/network scan |
| **targeted** | One named feature / field / endpoint | Just that surface, all its roles + negative cases |
| **regression** | After a change, guard nearby behavior | Changed feature **+ indirect blast radius** (see Impact Analysis) |
| **bugfix** | Verify a fix landed | Reproduce original bug (must now fail to reproduce) + regression around the root cause |
| **full** | New/changed feature, full confidence | All phases: cases -> code -> DB -> API -> UI/E2E -> security -> perf -> report |
| **release** | Sign-off on a batch/release | `full` per area + release checklist + GO/NO-GO |

`regression`, `bugfix`, and `release` **must** complete the Impact Analysis below — that is exactly where "obvious" bugs hide.

---

## Scope Lock — REQUIRED before any tool runs

Before the first DB query, API call, or browser action, output this table. It is the contract for the session. **If a critical field is unknown, ask — do not guess.**

| Field | Value |
|---|---|
| Feature / story / bug / PR | |
| QA mode | smoke / targeted / regression / bugfix / full / release |
| Roles in scope | Admin / Manager / User / Guest / Other |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | |
| Direct dependents (see Impact Analysis) | |
| Indirect blast radius | |
| Out of scope (explicit) | |
| Environment | Test / Dev / Prod (read-only) |
| Risk level | Low / Medium / High |
| Stop conditions | feature undeployed / schema missing / wrong branch / auth fails |

A change is in scope **plus** everything the Impact Analysis surfaces. Do not silently narrow scope to make a PASS easier; if you must drop coverage, say so explicitly and why.

---

## Impact Analysis & Coverage — direct + indirect blast radius

For every change under test, enumerate the blast radius **before** writing the verdict. This is the antidote to "we only tested the diff."

**1. Direct** — what the diff literally touches: the changed component, route, query, column.

**2. Indirect (where obvious bugs hide)** — trace each outward:
- **Shared FE components** — is the changed component reused on other pages? Grep imports.
- **Shared API endpoints** — do other features call the same endpoint? Different params/roles?
- **Shared DB tables/columns** — what else reads/writes this table? Reports, dashboards, exports, other endpoints.
- **Async consumers** — cron jobs, Lambda (order processing / parser / report / notification), SQS, S3 events, email.
- **Caches & snapshots** — React Query keys, snapshot tables (PROJECT-PROFILE.md §11), materialized aggregates that drift from live data.
- **Downstream reports/exports** — CSV columns, reports, dashboards (online vs offline scope).

**3. Coverage matrix** — for the in-scope surface, confirm you hit every cell that applies:

| Dimension | Must cover |
|---|---|
| Roles | every role that can reach the flow (Admin / Manager / User / Guest) |
| States | empty / single / many / max; draft vs published; active vs deleted; null vs zero |
| Inputs | valid (positive) **and** invalid/missing/malformed (negative) + boundaries |
| Flow | the **full** user journey end-to-end, not just the changed screen |
| Cross-tenant | other accounts cannot see or act on this data |
| Regression | the indirect areas above still behave |

If a dimension is untested, it is a coverage gap — name it in the report, do not imply it passed.

---

## Evidence Ledger — REQUIRED

Every finding (bug OR proof-of-correct) maps to at least one evidence item. Output this table in every QA result:

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

**Allowed evidence types:** DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), Postman contract, GitHub diff/commit.

**Hard rules — these reduce false positives and false PASSes:**
- **No evidence = no finding.** A claim without a ledger row does not exist.
- **No reproduction = no confirmed bug.** Suspected != confirmed (see `bug-verifier`).
- **No DB / API / Browser comparison = no cross-layer claim.** Don't say "the API is wrong" without the DB row next to it.
- Save proof for **PASS** too, not only bugs — a green result needs evidence it was actually exercised.

**Evidence folder convention** (`qa-evidence/`):
- One folder per finding: `qa-evidence/BUG-YYYYMMDD-HHMMSS/` (bugs) or `qa-evidence/<FEATURE-SLUG>/` (feature runs). `HHMMSS` avoids collisions across parallel sessions.
- Inside: API responses (`<slug>_api-response.json`), screenshots (`<slug>.png`), logs (`<slug>.log`), DB dumps (`<slug>.csv`), notes (`<slug>_evidence.md`), config (`.yml`) where relevant.
- **HOW to write** — the read-only QA hook BLOCKS the `Write`/`Edit` tools for `qa-evidence/`. Use one of: (1) `mcp__filesystem__write_file` with the target path (preferred); (2) Bash heredoc into the folder; (3) **Playwright screenshots — pass an explicit path:** call `mcp__playwright__browser_take_screenshot` with `filename: qa-evidence/<finding>/<name>.png` so the PNG lands in `qa-evidence/`. A BARE filename saves to the repo root, NOT `qa-evidence/`; the PostToolUse copy hook is only a backstop.
- Bug *reports* and findings live in the chat conversation, not as markdown files in `qa-evidence/`. The folder holds attachments only.

---

## Mutation Safety Gate — before any write

Applies to any DB UPDATE/INSERT/DELETE AND any POST/PUT/PATCH/DELETE API call. The environment is read-only by policy; writes are the exception, not the default.

1. Confirm the target is **in scope** (Scope Lock).
2. Prefer **existing disposable test data** over creating new rows.
3. **SELECT and log the original state first** (exact row, all columns you may touch).
4. Have a **rollback plan** before the write.
5. Never run destructive calls against **shared/prod** data. Prod DB is **read-only** — never mutate prod.
6. UPDATE/DELETE **must** have a WHERE. Never hard-DELETE — prefer status / `deleted_at` changes.
7. After the test, **verify** DB state and **restore**, then SELECT again to confirm restoration. Log it:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

If rollback is impossible (no clean restore path) -> **STOP and ask the user** before mutating.

---

## Cross-Layer Consistency — DB / API / Browser

For each entity in scope, the same value must agree across all three layers. Mismatch = bug.

1. **DB** — `mcp__mcp_server_mysql__mysql_query` (test/dev) — the stored truth.
2. **API** — `mcp__http-client__*` or replay the FE's request captured via `mcp__chrome-devtools__*`.
3. **Browser** — `mcp__playwright__*` snapshot / DOM.

Compare in one table: `| Field | DB | API | Browser | Match? |`. Consistency dimensions: value, count, status, date/time format, null handling, soft-delete filtering, FK resolution, aggregation, ordering, pagination.

| Entity | DB table(s) | API endpoint(s) |
|---|---|---|
| User / Manager | `user`, `user_account` | `GET /api/<resource>/users` |
| Account | `account`, `user_account` | `GET /api/accounts/:id` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Subscription | `subscription`, `invoice` | `GET /api/subscriptions/:id` |
| Model output / score | `audit_log`, snapshot tables (PROJECT-PROFILE.md §11) | `GET /api/<resource>/scores` |

(Roles live in `user_account`, not `user`. See `.claude/rules/db-gotchas.md`.)

---

## Bug Classification — FE / BE / Admin / Report / DB / Both

Apply on every confirmed bug so downstream skills don't re-derive it:

1. **Call the API directly.** Correct data but UI wrong -> **FE**. No call when one was expected -> **FE**. Wrong data / unexpected 500/404 -> go to 2.
2. **Query the DB.** DB correct but API wrong -> **BE** (query/logic). DB wrong -> **BE** (write-side) or **DB** (schema/migration).
3. **Edge cases:** Admin panel -> **Admin**. Reporting service (PROJECT-PROFILE.md §3) -> **Report**. API wrong AND UI mishandles the error -> **Both**.

---

## Test-Case Quality Bar

Every test case — generated or executed — is **executable**, never vague. Minimum columns:

`TC ID | Requirement/AC | Scenario | Preconditions | Test Data | Steps | Expected | Layer | Role | Priority | Automation? | Execute With | Evidence Required`

Every executed case records **Expected**, **Actual**, and an explicit **Pass/Fail** (not "looks fine"). A case with no expected result is not a test.

---

## MCP Server Routing — which server for which job

Use **fully-qualified** tool names (`mcp__server__tool`) so the right server is hit.

| Job | Server | Notes |
|---|---|---|
| Query **test/dev** DB | `mcp__mcp_server_mysql__mysql_query` | DB `<test DB name: PROJECT-PROFILE.md §6>` / `<DB name: PROJECT-PROFILE.md §6>` on `<DB host: PROJECT-PROFILE.md §6>:3306` |
| Query **prod** DB (read-only) | `mcp__mcp_server_mysql_prod__mysql_query` | Confirm a prod repro. Needs SSH tunnel on `<prod DB via tunnel: PROJECT-PROFILE.md §6>` first. **Never mutate prod.** |
| Browser UI: clicks/forms/snapshots/screenshots | `mcp__playwright__*` | Primary E2E driver |
| Network/console/perf inspection | `mcp__chrome-devtools__*` | Capture the real FE request + console errors during repro |
| Direct API calls | `mcp__http-client__*` | Clear stale headers (`set_default_headers` merge:false) before auth |
| Existing API contracts | `mcp__postman-api-mcp__*` | Search first — source of truth for URL/headers/body |
| Code/PR/commit/diff (remote) | `mcp__github__*` | `search_code`, `pull_request_read`, `list_commits` |
| Evidence files | `mcp__filesystem__*` | Writes allowed only under `qa-evidence/` |
| Jira / Confluence | `mcp__claude_ai_Atlassian__*` | Pull AC from a ticket; file/annotate issues when asked |

**Default tool choices:** DB -> MySQL MCP (NOT Postgres). UI -> Playwright. API -> http-client (Postman for existing contracts). Code search -> Read/Grep/Glob (NOT Bash cat/grep). Parallel multi-layer work -> Agent sub-agents.

---

## Superpowers & built-in debug — when to escalate

Use the **Superpowers** plugin only when it adds real QA value — never reflexively:

| Situation | Invoke |
|---|---|
| A confirmed bug whose root cause is non-obvious after the standard cross-layer pass | `superpowers:systematic-debugging` (hypothesis -> isolate -> verify) |
| An intermittent/race/timing bug | `superpowers:systematic-debugging` + repeat to get a reproduction rate |
| About to claim DONE/PASS/FIXED | `superpowers:verification-before-completion` — evidence before assertions |
| Designing a new skill or a non-trivial test strategy | `superpowers:brainstorming`, then `superpowers:writing-skills` |
| Large independent fan-out (multi-area regression) | `superpowers:dispatching-parallel-agents` (or the `qa-team` skill) |

The built-in `/debug` (Claude Code) is a lighter alternative to `systematic-debugging` for a quick, single-thread root-cause dig. Prefer `systematic-debugging` when the bug spans layers.

---

## Memory Ritual — MANDATORY post-session

**Every skill and sub-agent updates auto-memory before claiming completion.** Not optional. If memory cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Create/update a memory file** under `~/.claude/projects/c--Users-<user>-<project>/memory/` (the ONLY path the `Write` tool is allowed — use `Write` directly here). Naming: `project_<slug>.md` (QA runs), `feedback_<slug>.md` (guidance), `reference_<slug>.md` (pointers). Frontmatter:
   ```markdown
   ---
   name: <short title>
   description: <one-line searchable hook>
   metadata:
     type: project | feedback | reference | user
   ---
   ```
2. **Cross-reference first.** Grep the memory folder for the endpoint / file path / user ID / symptom. If an entry already covers this root cause, **UPDATE it** with today's reproduction — do not file a duplicate.
3. **Update the index** `MEMORY.md` with one <=200-char line: `- [<title>](<file>.md) — <hook>`.
4. **Required content:** feature/date, verdict (GO/NO-GO/CONFIRMED/DUPLICATE), bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/emails), root-cause location (`path:line`), regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.

---

## Recommended Skill Sequence

A typical full validation flows: **sync-repos -> env-health -> login -> scope-lock (this module) -> test-data-manager -> test-cases-generator -> pr-risk-analyzer -> code-review -> db-check -> api-test -> browser-test -> security-review -> perf-test -> bug-verifier -> bug-report -> qa-report** (memory write at each step). `full-qa` and `qa-team` orchestrate this; `qa-validate` is the lighter cross-layer path. `bug-verifier` precedes `bug-report` — never report an unverified bug.

**Specialized skills — slot in when relevant:** `regression-runner` (drive the blast radius after a change) · `visual-regression` + `a11y-test` (UI depth) · `observability-check` (errors the UI hides) · `flaky-race-verifier` (intermittent/race bugs) · `evidence-manager` (capture + ledger proof) · `automation-writer` (confirmed manual case -> script) · `explainer` (plain-language, per-role change summary — any time, even with no story).

---

## Environments & Layer Rules — pointers

- **Credentials, URLs, DB connections, repos/branches:** `CLAUDE.md` (always loaded) is the source of truth. Default FE = the main app (`<the relevant URL: PROJECT-PROFILE.md §5>`). Branch names are case-sensitive.
- **Layer-specific QA checks** (auto-attach when working in those repos): `.claude/rules/backend.md`, `.claude/rules/frontend.md`, `.claude/rules/admin.md`, `.claude/rules/db-gotchas.md`, `.claude/rules/testing.md`. Read the relevant one before reviewing that layer.
