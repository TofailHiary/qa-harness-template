---
name: release-check
description: Use when signing off a large, risky release/batch before it ships to production and you need an exhaustive FILE-BY-FILE, TABLE-BY-TABLE, API-BY-API checklist plus a formal release sign-off report and APPROVED / NOT-APPROVED call. Triggers include "release sign-off", "validate the release", "release-check a release", "is this batch safe to ship". Reach for /full-qa for a single story/PR GO/NO-GO; use this when the scope is a whole release that must be ZERO-bug in prod.
argument-hint: "release name or list of changes"
disable-model-invocation: true
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "Task", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(regression-runner)", "Skill(visual-regression)", "Skill(a11y-test)", "Skill(observability-check)", "Skill(bug-verifier)"]
---

# Release Validation (Full Checklist)

**Role:** Act as a Release Manager and Full Stack Engineer with 20+ years experience. The release is HUGE and RISKY — ensure ZERO BUGS in production.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which release (name + the PRs/commits/changes in scope) should I sign off? Confirm QA mode = release (full per area + checklist + GO/NO-GO)."

Do NOT guess the release contents from conversation. Enumerate the actual change set from PRs/commits before testing.

---

## Step 0a: QA Mode + Scope Lock (REQUIRED — before any tool runs)

QA mode for this skill is **release** (qa-standards -> QA Modes): `full` per area + release checklist + GO/NO-GO. Emit the **Scope Lock** table and run nothing until it is filled (ask if a critical field is unknown — do not guess):

| Field | Value |
|---|---|
| Release name / batch | |
| QA mode | release |
| PRs / commits in scope | |
| Roles in scope | Admin / Manager / User / Guest / Other |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | |
| Direct dependents | (Step 0b) |
| Indirect blast radius | (Step 0b) |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only repro) |
| Risk level | High (assume) |
| Stop conditions | feature undeployed / migration not applied / wrong branch / auth fails |

## Step 0b: Impact Analysis (REQUIRED — this is the whole point of a release check)

For the WHOLE change set, trace the blast radius per qa-standards -> Impact Analysis before testing: shared FE components (grep imports), shared API endpoints (other features / roles / params), shared DB tables/columns (reports, dashboards, exports, other endpoints), async consumers (cron / Lambda / SQS / S3 / email), caches & report snapshots (React Query keys, snapshot tables (`PROJECT-PROFILE.md §11`)), downstream reports/exports (CSV columns, online vs offline scope). Feed results into the Scope Lock "Indirect blast radius" row. **A release is in scope plus everything this surfaces — validate the full flows and the whole blast radius, not just the diffs.**

Pull acceptance criteria for each ticket in the release via `mcp__claude_ai_Atlassian__*`.

---

## Environment & Credentials (Embedded for Fork Context)

- **Admin Portal:** <the relevant URL: PROJECT-PROFILE.md §5> — <admin email: PROJECT-PROFILE.md §7> / <admin password env var: PROJECT-PROFILE.md §7>
- **Main Portal (Primary FE — Test, DEFAULT):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Primary FE — Dev):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Legacy FE — Test, opt-in):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Legacy FE — Dev, opt-in):** <the relevant URL: PROJECT-PROFILE.md §5>
- **FE selection:** default to the primary FE. Use the legacy FE URL (PROJECT-PROFILE.md §5) only when the release scope is explicitly about the legacy frontend. Same auth on both.
- **User password:** <role password env var: PROJECT-PROFILE.md §7>
- **Manager password:** <role password env var: PROJECT-PROFILE.md §7>
- **Database (Test/Dev):** <test DB name: PROJECT-PROFILE.md §6> at <DB host: PROJECT-PROFILE.md §6>:3306 — `mcp__mcp_server_mysql__mysql_query`
- **Database (Prod, read-only):** `mcp__mcp_server_mysql_prod__mysql_query` — confirm a prod repro / pre-deploy state only; needs SSH tunnel on <prod DB via tunnel: PROJECT-PROFILE.md §6>. **Never mutate prod.**
- **Repos:** <legacy frontend repo: PROJECT-PROFILE.md §3> (legacy FE), <frontend repo: PROJECT-PROFILE.md §3/§9> (primary FE), <backend repo: PROJECT-PROFILE.md §3/§9>, <admin repo: PROJECT-PROFILE.md §3/§9>, <report repo: PROJECT-PROFILE.md §3> (branch: <branch: PROJECT-PROFILE.md §3>)

## Critical Requirements

1. Extended thinking enabled — deep analysis for every check.
2. FILE BY FILE — read and verify each changed file.
3. TABLE BY TABLE — check every relevant database table.
4. API BY API — test every affected endpoint via `mcp__http-client__*` or `mcp__postman-api-mcp__*`.
5. No assumptions — verify with actual data and behavior. Code is truth.
6. **Validate the full flow + blast radius (Step 0b), not just the diffs** — the #1 cause of missed bugs.
7. Every finding — bug OR pass — needs an Evidence Ledger row. **No evidence = no finding.**
8. Zero tolerance — any confirmed bug (any layer, any severity) blocks the release until reported.
9. Memory load is ON-DEMAND; memory write at end is MANDATORY (Post-Session).

## Mutation Safety Gate (before ANY write — DB or API)

Applies to any DB UPDATE/INSERT/DELETE AND any POST/PUT/PATCH/DELETE API call (qa-standards): (1) target in scope; (2) prefer existing disposable test data; (3) SELECT + log original state first; (4) rollback plan ready; (5) never destructive against shared/prod data — prod is read-only; (6) UPDATE/DELETE needs a WHERE, never hard-DELETE (use status / `deleted_at`); (7) after the test verify + restore + re-SELECT, logging the table below. No clean rollback -> STOP and ask the user.

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

---

## Pre-Release Checklist

### 0. Memory cross-check
Grep `~/.claude/projects/c--Users-<user>-<project>/memory/*.md` for each BUG- ID, file path, and entity in the release; load matches as known regression-risk areas and known-open bugs. Don't re-litigate CONFIRMED+CLOSED items unless the release touches them.

### 1. Repository Validation
- **Pre-release preflight -> `Skill(env-health)`**: MCP servers reachable, repos on `<branch: PROJECT-PROFILE.md §3>` (branch names can be case-sensitive) + current, portals/DB/auth up, and every change in the release actually deployed to the target env. A RED item is a stop condition -> NOT APPROVED / PARTIAL.
- **Test data -> `Skill(test-data-manager)`**: locate rich existing records covering each area's scenarios (prefer reuse); prepare + snapshot + restore only if needed, under the Mutation Safety Gate above.
- All repos on correct branches (see PROJECT-PROFILE.md §3).
- All repos pulled to latest; no uncommitted changes.
- Use `mcp__github__list_pull_requests` to find all open/merged PRs for this release.
- Use `mcp__github__list_commits` to identify all changed files since the last release.
- Use `mcp__github__pull_request_read` to review PR details, diffs, and review comments.
- All changed files identified and listed.

### 2. Code Review (FILE BY FILE)
**Per change/PR -> `Skill(pr-risk-analyzer)`**: run the formal blast-radius risk map for each PR/commit in the release; feed every impact map into the Scope Lock "Indirect blast radius" row so the checklist below covers the whole impact, not just the diffs.

For EACH changed file verify: business logic correct, no hardcoded values/secrets, error handling in place, no stray console.log/debug, no commented-out code, security concerns addressed, consistent with coding standards. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md` for each layer. Delegate large areas to `Task` sub-agents in parallel (`superpowers:dispatching-parallel-agents`).

### 3. Database Validation (TABLE BY TABLE)
For EACH relevant table verify via `mcp__mcp_server_mysql__mysql_query`: schema correct, migrations applied, data integrity maintained, foreign keys valid, no orphaned records, indexes exist for performance. (Roles and account membership live in join tables — see `.claude/rules/db-gotchas.md`.)

**If any area produces model-generated scores** (recommendations, scores, report figures, source-record processing): recompute the stored value vs its source rows and check application edge cases (falsy-zero, randomness, snapshot-vs-live scope).

### 4. API Validation (API BY API)
For EACH affected endpoint verify via `mcp__http-client__*` or `mcp__postman-api-mcp__getCollectionRequest`: returns expected response, authentication working, authorization correct (RBAC + cross-tenant), validation in place, error responses proper, performance acceptable. Clear stale headers (`set_default_headers` merge:false) before auth.

**If an endpoint returns model-generated scores:** recompute the value vs source data and check application edge cases (falsy-zero, randomness, snapshot-vs-live scope).

### 5. UI/Browser Validation
For EACH affected page/flow verify via `mcp__playwright__*` the **full** journey (not just the changed screen): page loads correctly, no console errors (via `mcp__chrome-devtools__*`), all elements present, forms work, data displays correctly; capture network requests during every flow.

For EACH affected UI area also run: **`Skill(visual-regression)`** (layout / overflow / truncation / responsive across Desktop 1440 / Tablet 768 / Mobile 375) **+ `Skill(a11y-test)`** (keyboard / ARIA / focus / WCAG AA contrast) **+ always `Skill(observability-check)`** (console errors / failed-slow network / backend 5xx the UI hides).

---

## Testing Types (ALL REQUIRED)

Smoke, Sanity, Regression, End-to-End, Positive, Negative, Edge Case, Full Cycle — all must pass for every area in scope. Cover every cell of the coverage matrix (roles, states incl. empty/single/many/null-vs-zero, inputs incl. negative/boundary, full flow, cross-tenant).

**A release is always a regression -> `Skill(regression-runner)`** over the Step 0b indirect blast radius — actively re-test the shared components / endpoints / tables / async jobs / caches / downstream reports each change touches but is not "about".

---

## Consistency Verification

For each entity, the same value must agree across FE, BE, DB, Browser, API. Compare in a table: `| Field | DB | API | Browser | Match? |`. Verify data value/format, validation, error handling, business logic, soft-delete filtering, aggregation, and security. **No DB/API/Browser comparison = no cross-layer claim.** Mismatch -> classify (FE / BE / Admin / Report / DB / Both) and verify with `Skill(bug-verifier)` before it counts.

| Entity | DB table(s) | API endpoint(s) |
|---|---|---|
| User/Manager | `user`, `user_account` | `GET /api/v2/accounts/{users,managers}` |
| Account | `account`, `user_account` | `GET /api/v2/accounts` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Order Processing | `order_item`, `order_log` | `GET /api/orders/:id/items` |
| Subscription | `subscription`, `audit_log` | `GET /api/subscriptions/:id` |
| Dashboard | snapshot tables (`PROJECT-PROFILE.md §11`) | `GET /api/dashboard/*` |

---

## Evidence Ledger (REQUIRED in the sign-off)

Every finding (bug OR proof-of-correct) maps to >=1 evidence row. **No evidence = no finding. No reproduction = no confirmed bug.** Save proof for PASS too.

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

Attachments under `qa-evidence/<RELEASE-SLUG>/` (or `qa-evidence/BUG-YYYYMMDD-HHMMSS/`). Write them via `mcp__filesystem__write_file` (the read-only hook blocks `Write`/`Edit` for `qa-evidence/`); Pass `filename: qa-evidence/<RELEASE-SLUG>/<name>.png` to Playwright screenshots (a bare filename saves to the repo root). Reports stay in the chat.

## Superpowers escalation
Non-obvious root cause -> `superpowers:systematic-debugging`. Large independent fan-out across release areas -> `superpowers:dispatching-parallel-agents` (or the `qa-team` skill). Before declaring APPROVED -> `superpowers:verification-before-completion` (evidence before assertions).

---

## Release Sign-Off Report

Generate a report containing:

1. **Header** — release name, date, environment, validated by, QA mode (release).
2. **Summary** — total items validated, passed, failed, blocked, release status (APPROVED / NOT APPROVED). Strict policy: any confirmed bug (any layer, any severity) = NOT APPROVED.
3. **Repository Status** — table of all repos with branch, sync status, last commit.
4. **Files Reviewed** — table with file, status, issues.
5. **Tables Checked** — table with table name, schema, data, integrity, status.
6. **APIs Tested** — table with endpoint, method, auth, response, status.
7. **UI Flows Tested** — table with flow, status, console errors, network issues.
8. **Test Results** — table with test type, total, passed, failed.
9. **Bugs Found** — list each with title, severity, layer (FE/BE/Admin/Report/DB/Both), NEW/DUPLICATE, status.
10. **Evidence Ledger** — the table above (every finding AND every PASS).
11. **Coverage Gaps** — any dimension not tested (an untested dimension is never an implied PASS).
12. **Recommendation** — APPROVED or NOT APPROVED with reason, risks, mitigation.
13. **Rollback Plan** — steps to revert if production issues.
14. **Sign-Off** — QA, Dev, PM sign-off lines with dates.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for each endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** release + date, verdict (APPROVED / NOT APPROVED), bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/emails), root-cause `path:line`, regression risks for next time, rollback notes, any prior memory this run disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.
