---
name: release-check
description: Use when signing off a large, risky release/batch before it ships to production and you need an exhaustive FILE-BY-FILE, TABLE-BY-TABLE, API-BY-API checklist plus a formal release sign-off report and APPROVED / NOT-APPROVED call. Triggers include "release sign-off", "validate the release", "release-check a release", "is this batch safe to ship". Reach for /full-qa for a single story/PR GO/NO-GO; use this when the scope is a whole release that must be ZERO-bug in prod.
argument-hint: "release name or list of changes"
disable-model-invocation: true
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "Agent", "Agent(qa-verdict-auditor)", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(regression-runner)", "Skill(visual-regression)", "Skill(a11y-test)", "Skill(observability-check)", "Skill(ai-output-eval)", "Skill(latent-pattern-sweep)", "Skill(prod-sentinel)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# Release Validation (Full Checklist)

> **Capability gate:** This skill is **always on** (orchestrator — it never hard-stops). Before doing
> anything, read `PROJECT-PROFILE.md` §2 (Capability Map) and skip every checklist section whose
> capability is `off`: no **GitHub** / **LocalRepos** -> the change set comes from the user and
> sections 1-2 (repository / file-by-file review) are skipped; no **DB** -> skip section 3; no
> **API** -> skip section 4; no **Browser** -> skip section 5 (and visual / a11y); no **Jira** -> take
> acceptance criteria from the user; no **Postman** -> enumerate endpoints from the routes;
> no **Prod-DB** -> no pre-deploy prod state check. Every skipped section is stated in the sign-off
> ("Section 5 skipped: Browser capability off") and its Execution Register rows read
> NOT YET VERIFIED — never PASS. If `PROJECT-PROFILE.md` is blank, STOP and tell the user to run
> `/configure-project`.

**Role:** Act as a Release Manager and Full Stack Engineer with 20+ years experience. The release is HUGE and RISKY — ensure ZERO BUGS in production.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which release (name + the PRs/commits/changes in scope) should I sign off? Confirm QA mode = release (full per area + checklist + GO/NO-GO)."

Do NOT guess the release contents from conversation. Enumerate the actual change set from PRs/commits before testing.

---

## Step 0a: Six questions + QA Mode + Scope Lock (REQUIRED — before any tool runs)

**Six questions first** (qa-standards -> The six questions): write them out explicitly (2-6 lines) before the first tool runs —
1. **What is requested?** (the literal ask — here, a release sign-off — and the mode it implies)
2. **What is authoritative?** (each ticket / AC / spec / code contract / ruling — per qa-standards -> Authoritative Source Hierarchy)
3. **What can be verified?** (which layers, with which tools, in which environment — only capabilities that are `on`)
4. **Which assumptions are eliminated?** (name them; each becomes a check)
5. **What evidence is required?** (the ledger rows a GO would need)
6. **What is completion?** (the register rows that must all be non-empty — one per ticket per area)

QA mode for this skill is **release** (qa-standards -> QA Modes): `full` per area + release checklist + GO/NO-GO. Emit the **Scope Lock** table and run nothing until it is filled (ask if a critical field is unknown — do not guess):

| Field | Value |
|---|---|
| Release name / batch | |
| QA mode | release |
| PRs / commits / tickets in scope | (every ticket gets its own register rows) |
| Data / content imports in scope | (an import is a release — escape class E2; list each one) |
| Roles in scope | <roles: PROJECT-PROFILE.md §8> — e.g. Admin / Manager / User / Guest / Other |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | <key tables: PROJECT-PROFILE.md §10> |
| Direct dependents | (Step 0b) |
| Indirect blast radius | (Step 0b) |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only repro) |
| Build under test | `<branch: PROJECT-PROFILE.md §3> @ <short sha>` per repo — capture once, reuse in every Evidence Ledger row |
| Risk level | High (assume) |
| Stop conditions | feature undeployed / migration not applied / wrong branch / auth fails |

## Step 0b: Impact Analysis (REQUIRED — this is the whole point of a release check)

For the WHOLE change set, trace the blast radius per qa-standards -> Impact Analysis before testing: shared FE components (grep imports), shared API endpoints (other features / roles / params), shared DB tables/columns (reports, dashboards, exports, other endpoints), async consumers (cron / serverless functions / queues / storage events / email — `PROJECT-PROFILE.md §11`), caches & snapshots (client-side cache keys, snapshot tables (`PROJECT-PROFILE.md §11`)), downstream reports/exports (CSV columns, dashboards, printed/PDF outputs). Feed results into the Scope Lock "Indirect blast radius" row. **A release is in scope plus everything this surfaces — validate the full flows and the whole blast radius, not just the diffs.**

If Jira is on, pull acceptance criteria for each ticket in the release via `mcp__claude_ai_Atlassian__*` (tracker: `PROJECT-PROFILE.md §15`) — read each whole thread; a clarifying dev/PO comment often overrides a stale AC. Re-read every ticket LIVE this run: a remembered status is not evidence (qa-standards -> Fresh vs Historical).

---

## Run record & resume (`run.json`)
Keep `qa-evidence/<run-folder>/run.json` (`qa-standards/references/run-record.md`): create it at Scope Lock
(one register row per in-scope area, NOT YET VERIFIED until run, plus the Step 1b matrix), update it after
every phase (that update is the checkpoint), and if it already exists with `checkpoint.next_step` set,
RESUME from that step and say so. Before the verdict,
`python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>` must exit 0 - it
recomputes the confidence line and the run verdict; never type them by hand. `--package` then writes the
`package.md` the independent audit reads.

## Environment & Credentials (Embedded for Fork Context)

Identifiers only — passwords live in the env vars named in `PROJECT-PROFILE.md §7` and are never written here.

- **Main Portal (Primary FE — Test, DEFAULT):** <main app URL: PROJECT-PROFILE.md §5>
- **Main Portal (Primary FE — Dev):** <main app URL (dev): PROJECT-PROFILE.md §5>
- **Secondary / legacy FE (if §5 lists one):** <legacy app URL: PROJECT-PROFILE.md §5>
- **FE selection:** default to the primary FE. Use a secondary / legacy surface only when the release scope explicitly touches it. Never navigate to a surface §5 marks as retired.
- **Admin Portal (if Admin is on):** <admin URL: PROJECT-PROFILE.md §5> — <admin account: PROJECT-PROFILE.md §7>
- **Auth method:** per `PROJECT-PROFILE.md §7` — obtain a token (JWT / session cookie / OAuth / identity-provider ID token) and send it the way §7 says.
- **Role accounts:** <role account: PROJECT-PROFILE.md §7> for every role in scope.
- **Database (Test/Dev):** <test DB name: PROJECT-PROFILE.md §6> at <DB host/port: PROJECT-PROFILE.md §6> — `mcp__mcp_server_mysql__mysql_query` (DB tool: `PROJECT-PROFILE.md §6`)
- **Database (Prod, read-only, only if Prod-DB is on):** `mcp__mcp_server_mysql_prod__mysql_query` — confirm a prod repro / pre-deploy state only, via the prod read-only access described in `PROJECT-PROFILE.md §6`. **Never mutate prod.**
- **Repos:** <frontend repo: PROJECT-PROFILE.md §3/§9> (primary FE), <legacy frontend repo: PROJECT-PROFILE.md §3> (if any), <backend repo: PROJECT-PROFILE.md §3/§9>, <admin repo: PROJECT-PROFILE.md §3/§9>, <report repo: PROJECT-PROFILE.md §3>, plus any background-worker / serverless repos listed in §3 (branch: <branch: PROJECT-PROFILE.md §3>, case-sensitive)
- **API tooling:** if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it; otherwise `mcp__http-client__*`. `mcp__postman-api-mcp__*` (Postman on) for existing contracts.

## Critical Requirements

1. Extended thinking enabled — deep analysis for every check.
2. FILE BY FILE — read and verify each changed file.
3. TABLE BY TABLE — check every relevant database table.
4. API BY API — test every affected endpoint via the §14 typed tools, `mcp__http-client__*` or `mcp__postman-api-mcp__*`.
5. No assumptions — verify with actual data and behavior. Code is truth.
6. **Validate the full flow + blast radius (Step 0b), not just the diffs** — the #1 cause of missed bugs.
7. Every finding — bug OR pass — needs an Evidence Ledger row with provenance. **No evidence = no finding.**
8. Zero tolerance — any confirmed bug (any layer, any severity) blocks the release until reported (default policy; see `PROJECT-PROFILE.md §16`).
9. Memory load is ON-DEMAND; memory write at end is MANDATORY (Post-Session).
10. The sign-off is never self-graded — an independent audit runs BEFORE the report is written.

## Mutation Safety Gate (before ANY write — DB or API)

Applies to any DB UPDATE/INSERT/DELETE AND any POST/PUT/PATCH/DELETE API call (qa-standards): (1) target in scope; (2) prefer existing disposable test data; (3) SELECT + log original state first; (4) rollback plan ready; (5) never destructive against shared/prod data — prod is read-only; (6) UPDATE/DELETE needs a WHERE, never hard-DELETE (use status / `deleted_at` where the column exists); (7) after the test verify + restore + re-SELECT, logging the table below. No clean rollback -> STOP and ask the user.

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

---

## Pre-Release Checklist

### 0. Memory cross-check
Grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for each ticket (`APP-nnn`) / `BUG-` ID, file path, and entity in the release; load matches as known regression-risk areas and known-open bugs. Don't re-litigate CONFIRMED+CLOSED items unless the release touches them. Memory is context, never proof: every dated claim in a recalled file (root cause, ticket status, fixture, prevalence) is stale until re-checked this run (qa-standards -> Fresh vs Historical).

### 1. Repository Validation
- **Pre-release preflight -> `Skill(env-health)`**: MCP servers reachable, repos on `<branch: PROJECT-PROFILE.md §3>` (case-sensitive) + current, portals/DB/auth up, and every change in the release actually deployed to the target env. A RED item is a stop condition -> PARTIAL (NOT APPROVED). Record `git rev-parse --short HEAD` per repo in the Scope Lock "Build under test" row.
- **Test data -> `Skill(test-data-manager)`**: locate rich existing records covering each area's scenarios (prefer reuse); prepare + snapshot + restore only if needed, under the Mutation Safety Gate above. Exhaust the data resources — fixtures via the application's own API (`PROJECT-PROFILE.md §14` typed tools, if any), the sample-file library (`§13`, if any), a disposable replica (`§6`, if any) — before recording a coverage gap.
- All repos on correct branches (`<branch: PROJECT-PROFILE.md §3>`, case-sensitive — see PROJECT-PROFILE.md §3).
- All repos pulled to latest; no uncommitted changes.
- Use `mcp__github__list_pull_requests` to find all open/merged PRs for this release (or `git log` on the local repos if LocalRepos is on).
- Use `mcp__github__list_commits` to identify all changed files since the last release.
- Use `mcp__github__pull_request_read` to review PR details, diffs, and review comments.
- All changed files identified and listed — including background-worker / serverless repos (escape class E7: the owner of a bug may be a job, not FE/BE/Admin).
- **Release radar (E11):** list every ticket the tracker says is in this release / ready to deploy; a ticket with no QE touch gets a register row of its own (NOT YET VERIFIED until checked), never silence.

### 2. Code Review (FILE BY FILE)
**Per change/PR -> `Skill(pr-risk-analyzer)`**: run the formal blast-radius risk map for each PR/commit in the release; feed every impact map into the Scope Lock "Indirect blast radius" row so the checklist below covers the whole impact, not just the diffs.

For EACH changed file verify: business logic correct, no hardcoded values/secrets, error handling in place, no stray console.log/debug, no commented-out code, security concerns addressed, consistent with coding standards. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md` for each layer. **For every bug-fix ticket in the release (E6):** `git diff --name-only` of the fix must include the ticket's root-cause file (`path:line` from the bug report / memory); a fix that never touched the root-cause line is a symptom fix — a finding, not a PASS. **Masked errors (E9):** a swallowed / commented-out throw in the changed path is filed as its own finding.

Delegate large areas to sub-agents in parallel (`Agent` tool; `superpowers:dispatching-parallel-agents` describes the pattern if the plugin is installed — `PROJECT-PROFILE.md §17`) **only if `PROJECT-PROFILE.md §16` allows sub-agents**; otherwise review the areas sequentially in-session. Sub-agent reports are leads: reproduce first-hand anything you act on (qa-standards -> Verdict Integrity #7).

### 3. Database Validation (TABLE BY TABLE)
For EACH relevant table verify via `mcp__mcp_server_mysql__mysql_query`: schema correct, migrations applied, data integrity maintained, foreign keys valid, no orphaned records, indexes exist for performance. Read `COLUMN_COMMENT` / the model before judging a value. (Roles may live in a join / membership table rather than on `user`; soft-delete columns are not universal — see `.claude/rules/db-gotchas.md` and `PROJECT-PROFILE.md §10`.)

**Data / content imports in the release (E2 + E3):** treat each import as a change — re-test the code paths its rows can now reach (a mode / type / enum value production never held before arms dormant branches; consider `Skill(latent-pattern-sweep)` when the import adds new content types). **Async writers (E8):** verify the terminal DB state of every job / queue / event the release touches, never the enqueue.

**If any area produces model-generated or computed numbers** (recommendations, scores, KPIs, report figures) -> `Skill(ai-output-eval)`: recompute the stored value from its source rows and check the edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope). Transcription proves transport, not correctness (qa-standards -> Judgement Discipline #8).

### 4. API Validation (API BY API)
For EACH affected endpoint verify via the §14 typed tools, `mcp__http-client__*` or `mcp__postman-api-mcp__getCollectionRequest`: returns expected response, authentication working, authorization correct (RBAC + cross-tenant), validation in place, error responses proper, performance acceptable. Clear stale headers (`set_default_headers` merge:false) before auth. Test against the real wire — the actual response body / file / event shape captured live in the target environment, never a mock (Judgement Discipline #7).

**If an endpoint returns model-generated or computed numbers** -> `Skill(ai-output-eval)`: recompute the value vs source data and check the edge cases (falsy-zero, randomness, snapshot-vs-live scope).

### 5. UI/Browser Validation
For EACH affected page/flow verify via `mcp__playwright__*` the **full** journey (not just the changed screen): page loads correctly, no console errors (via `mcp__chrome-devtools__*`), all elements present, forms work, data displays correctly; capture network requests during every flow. **Path exercised (E5):** a functional PASS is proven by the API call / DB write that actually happened (network capture or DB row), never by a success toast or the presence of a control. **Input class (E4):** every upload / import / file flow names the input class exercised and covers at least two classes from the sample-file library (`PROJECT-PROFILE.md §13`, if any) — a flow that is green with one fixture is not green. Paginated surfaces beyond page 1; sortable columns in both directions (qa-standards -> Completion Gate).

For EACH affected UI area also run: **`Skill(visual-regression)`** (layout / overflow / truncation / responsive across Desktop 1440 / Tablet 768 / Mobile 375) **+ `Skill(a11y-test)`** (keyboard / ARIA / focus / WCAG AA contrast) **+ always `Skill(observability-check)`** (console errors / failed-slow network / backend 5xx the UI hides).

---

## Testing Types (ALL REQUIRED)

> Moved to [`references/testing-types.md`](references/testing-types.md). Every testing type listed there is REQUIRED; each gets register rows.

## Consistency Verification

For each entity, the same value must agree across FE, BE, DB, Browser, API. Compare in a table: `| Field | DB | API | Browser | Match? |`. Verify data value/format, validation, error handling, business logic, soft-delete filtering, aggregation, and security. **No DB/API/Browser comparison = no cross-layer claim.** Mismatch -> classify (FE / BE / Admin / Report / DB / Both) and verify with `Skill(bug-verifier)` before it counts; confirmed -> `Skill(bug-report)`.

*(illustrative — replace with `<key tables: PROJECT-PROFILE.md §10>` and this project's endpoints)*

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

Every finding (bug OR proof-of-correct) maps to >=1 evidence row. **No evidence = no finding. No reproduction = no confirmed bug.** Save proof for PASS too. Stamp provenance on every row (qa-standards -> Evidence provenance) — a result observed on DEV / a replica / PROD is evidence for THAT environment only, never for the target.

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

Attachments under `qa-evidence/<RELEASE-SLUG>-<yyyymmdd>/` (or `qa-evidence/BUG-YYYYMMDD-HHMMSS-<yyyymmdd>/` per bug). Write them via `mcp__filesystem__write_file` (the read-only hook blocks `Write`/`Edit` for `qa-evidence/`); pass `filename: qa-evidence/<RELEASE-SLUG>-<yyyymmdd>/<name>.png` to Playwright screenshots (a bare filename saves to the repo root). Reports stay in the chat.

## Plugins & escalation (optional enhancers — `PROJECT-PROFILE.md §17`)

> Moved to [`references/sign-off-template.md`](references/sign-off-template.md). Optional plugin enhancers (PROJECT-PROFILE.md §17) with their by-hand equivalents.

---

## Independent Verdict Audit (REQUIRED — before the sign-off is written)

A release sign-off is the highest-stakes verdict this harness produces. **It MUST NOT be self-graded.**

Before writing the report, hand over ONLY the package: the Scope Lock, the acceptance criteria / authoritative sources, every finding (bugs AND passes), the Evidence Ledger, the Execution Register, and the proposed GO/NO-GO. **Never hand over your reasoning or transcript** — that is what makes the audit independent.

- **Sub-agents allowed (`PROJECT-PROFILE.md §16`):** dispatch the `qa-verdict-auditor` sub-agent via the `Agent` tool with the path of `qa-evidence/<run-folder>/package.md` (from `verdict_check.py --package`). It runs in a FRESH context as a judge, not a second QA run (its cost discipline is in its definition).
- **Sub-agents disabled (§16):** audit in-session — re-derive the verdict from the package alone, item by item against qa-standards -> Verdict Integrity #1-8 and the Completion Gate, and write `AUDIT_PASSED` / `AUDIT_FAILED` with the challenges.
- **`AUDIT_FAILED`** -> the sign-off is BLOCKED. Resolve every challenge with evidence, then re-audit.
- **`AUDIT_PASSED`** -> proceed, and record in the sign-off that an independent audit ran, with its date and mode (sub-agent / in-session).

Reproduce first-hand anything you act on — an auditor challenge is a lead, not a finding (qa-standards -> Verdict Integrity #7). If the harness's completion-gate hook is switched to enforce (`harness-config.json` -> `gate.enforce`), the Completion Gate is enforced mechanically at stop time rather than from memory; otherwise run the checklist by hand before every verdict.

### Execution Register (REQUIRED — one row per Scope Lock area, no exceptions)

| ID | Area | Requirement / AC | Check performed | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|

`Result` is one of the five canonical values (`qa-standards` -> Verdict Contract: PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED). **Every area named in the Scope Lock — every ticket, every import, every indirect area — gets exactly one row.** A release sign-off with a missing row is the highest-consequence version of a silent omission: nobody downstream can see what was not checked. Never delete a row to make the release look clean — mark it NOT YET VERIFIED and say what is missing. BLOCKED needs the reason and what would unblock it; an operational blocker (port closed, credentials not tried) must be attempted first.

## Release Sign-Off Report

> Moved to [`references/sign-off-template.md`](references/sign-off-template.md). Read it before writing the sign-off: the report sections, the APPROVED / NOT APPROVED alias rule and the confidence line come from there.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for each endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate. If today's evidence DISPROVES a fact in an older memory, mark that older file SUPERSEDED in the same session (qa-standards -> Memory Ritual).
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title> YYYY-MM-DD](<file>.md) — <hook>` (date in the link title — escape class E13).
4. **Content:** release + date + build(s), verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), audit result and mode, bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/accounts), root-cause `path:line`, regression risks for next time, rollback notes, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
