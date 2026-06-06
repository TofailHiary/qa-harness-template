---
name: qa-validate
description: Use when a single user story, bug, or feature needs a lighter end-to-end cross-layer validation (DB / API / Browser) than the full /full-qa cycle, ending in a ready / not-ready call. Triggers include "validate this story", "qa-validate APP-xxx", "check this fix end to end", "does this feature work across all layers". Reach for /full-qa instead when the scope is a PR/release needing a strict GO/NO-GO with code review, security and perf phases.
argument-hint: "user-story or bug description"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "Agent", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(test-cases-generator)", "Skill(observability-check)", "Skill(bug-report)", "Skill(bug-verifier)"]
---

# QA Validation Workflow

Lighter cross-layer validation for one story/bug/feature — generate cases, execute them, prove the same value agrees across DB -> API -> Browser, then give a ready / not-ready call.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What story, bug, or feature should I qa-validate? Which QA mode — smoke / targeted / regression / bugfix / full?"

Do NOT guess scope from conversation. Do NOT run any query/call/click until scope is known.

## Rules
1. Use ultrathink for every step.
2. No assumptions — verify with actual data and behavior. Code is truth.
3. **Validate the full user flow and the blast radius, not just the diff** (Step 0b). This is the #1 cause of missed bugs.
4. Generate test cases BEFORE testing (Phase 0).
5. Cross-layer data consistency (Phase 3) is MANDATORY — DB vs API vs Browser, every entity in scope.
6. Every finding — bug OR pass — needs an Evidence Ledger row. **No evidence = no finding.**
7. Memory load is ON-DEMAND; memory write at end is MANDATORY (Post-Session).

---

## Step 0a: QA Mode + Scope Lock (REQUIRED — before any tool runs)

Pick the **QA mode** (qa-standards -> QA Modes). If the user didn't state one, infer the smallest mode that covers the request and say which. Then emit the **Scope Lock** table and run nothing until it is filled (ask if a critical field is unknown — do not guess):

| Field | Value |
|---|---|
| Feature / story / bug | |
| QA mode | smoke / targeted / regression / bugfix / full |
| Roles in scope | Admin / Manager / User / Guest / Other |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | |
| Direct dependents | (Step 0b) |
| Indirect blast radius | (Step 0b) |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Risk level | Low / Medium / High |
| Stop conditions | feature undeployed / schema missing / wrong branch / auth fails |

Do not silently narrow scope to make a PASS easier. If you must drop coverage, say so and why.

## Step 0b: Impact Analysis (REQUIRED for regression / bugfix; recommended always)

Before generating cases, trace the blast radius per qa-standards -> Impact Analysis: shared FE components (grep imports), shared API endpoints (other features / roles / params), shared DB tables/columns (reports, dashboards, exports, other endpoints), async consumers (cron / Lambda / SQS / S3 / email), caches & report snapshots (React Query keys, snapshot tables (PROJECT-PROFILE.md §11)), downstream reports/exports. Feed results into the Scope Lock "Indirect blast radius" row and into Phase 0 cases. **A change is in scope plus everything this surfaces.**

**If the scope is a PR / commit / branch -> `Skill(pr-risk-analyzer)`** for the formal blast-radius risk map; feed its impact map into the Scope Lock "Indirect blast radius" row and into Phase 0 cases.

If the source is a Jira ticket, pull acceptance criteria via `mcp__claude_ai_Atlassian__*`.

---

## Environment & Credentials (Embedded for Fork Context)

### Portals
- **Admin:** <the relevant URL: PROJECT-PROFILE.md §5> — <admin email: PROJECT-PROFILE.md §7> / <admin password env var: PROJECT-PROFILE.md §7>
- **Main app (Test, DEFAULT):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main app (Dev):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Auth method:** Authenticate per PROJECT-PROFILE.md §7 to obtain a token — e.g. JWT (POST credentials → Bearer token), session cookie, OAuth, or Firebase ID token — then send `Authorization: Bearer <token>`. See §7 for the login method configured for this project.
- **User password:** <role password env var: PROJECT-PROFILE.md §7>
- **Manager password:** <role password env var: PROJECT-PROFILE.md §7>

### Database
- Test/Dev: Host <DB host: PROJECT-PROFILE.md §6> | Port 3306 | DB <test DB name: PROJECT-PROFILE.md §6> — `mcp__mcp_server_mysql__mysql_query`
- Prod (read-only, confirm a prod repro only): `mcp__mcp_server_mysql_prod__mysql_query` — needs SSH tunnel on <prod DB via tunnel: PROJECT-PROFILE.md §6> first. **Never mutate prod.**

### Repos & Branches
| Repo | Branch | Type |
|------|--------|------|
| <frontend repo: PROJECT-PROFILE.md §3/§9> | <default branch: PROJECT-PROFILE.md §3> | Frontend |
| <backend repo: PROJECT-PROFILE.md §3/§9> | <default branch: PROJECT-PROFILE.md §3> | Backend |
| <admin repo: PROJECT-PROFILE.md §3/§9> | <default branch: PROJECT-PROFILE.md §3> | Admin panel |
| <report repo: PROJECT-PROFILE.md §3> | <default branch: PROJECT-PROFILE.md §3> | Reporting service |

### Key Code Paths
- FE API calls: <frontend repo: PROJECT-PROFILE.md §3/§9>/src/ (see §9)
- BE routes: <backend repo: PROJECT-PROFILE.md §3/§9>/routes/
- BE models: <backend repo: PROJECT-PROFILE.md §3/§9>/models/
- Auth middleware: <backend repo: PROJECT-PROFILE.md §3/§9>/middleware/auth.js
- Admin controllers: <admin repo: PROJECT-PROFILE.md §3/§9>/controllers/

---

## Phase 0: Test Case Generation

0. **Cross-check memory** — Grep `~/.claude/projects/c--Users-<user>-<project>/memory/*.md` for the feature/story, ticket/BUG- IDs, file paths, entity IDs. Load matches as known regression-risk areas; skip re-verifying bugs already CONFIRMED+CLOSED unless asked.
1. **Analyze input** — extract acceptance criteria, affected roles, pages/routes/APIs, data entities. Pull AC from Jira via `mcp__claude_ai_Atlassian__*` if the source is a ticket.
2. **Enumerate endpoints** — use `mcp__postman-api-mcp__searchPostmanElements` to find relevant Postman requests; `mcp__postman-api-mcp__getCollectionFolder` to list endpoints in the affected area. This defines the full API surface to cover.
3. **Investigate code** — search FE components, BE routes/models, Admin controllers, DB schemas. Use `mcp__github__search_code` for cross-repo searches, `mcp__github__list_commits` for recent changes, `mcp__github__pull_request_read` for PR context.
4. **Generate test cases** via `Skill(test-cases-generator)` by category: Positive, Negative, Boundary, DB Integrity, API, UI, Security, Regression, E2E, Data Consistency — covering every cell of the coverage matrix (roles, states, inputs incl. negative/boundary, full flow, cross-tenant) from Step 0b.
5. **Present summary table** with count per category and priority, then create TodoWrite tasks (P1 first). If the user specified scope, only generate for that scope plus its blast radius.

---

## Phase 1: Setup

**Preflight -> `Skill(env-health)`** (run this first): MCP servers reachable, repos on the correct branch (case-sensitive) + current, portals/DB/auth up, **and the feature actually deployed** to the target env. A RED item is a stop condition -> STOP and report not-ready (do not build cases for a dead env).

Ensure repos are on the correct branches (case-sensitive — see embedded credentials above) and up to date; confirm the feature is actually deployed to the target env.

---

## Phase 1.5: Test Data Preparation + Mutation Safety Gate

**Test data -> `Skill(test-data-manager)`**: locate rich existing records matching the cases (prefer reuse); prepare + snapshot + restore only if needed, under the **Mutation Safety Gate** below.

Search the DB for rich existing test data with real relationships before testing; prefer disposable existing rows over creating new ones.

**Mutation Safety Gate (qa-standards) — applies to ANY DB UPDATE/INSERT/DELETE AND ANY POST/PUT/PATCH/DELETE API call:**
1. Confirm the target is **in scope** (Scope Lock).
2. Prefer **existing disposable test data** over new rows.
3. **SELECT and log the original state first** (exact row, all columns you may touch).
4. Have a **rollback plan** before the write.
5. Never run destructive calls against **shared/prod** data. Prod DB is **read-only** — never mutate prod.
6. UPDATE/DELETE **must** have a WHERE. Never hard-DELETE — prefer status / `deleted_at` changes.
7. After the test, **verify** DB state and **restore**, then SELECT again to confirm. Log it:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

If rollback is impossible (no clean restore path) -> **STOP and ask the user** before mutating.

---

## Phase 2: Execute Test Cases

Work through cases by priority (P1 first). For each: PASS or FAIL with **Expected**, **Actual**, and an explicit verdict + evidence.

### Step 1: Code Investigation
Read each related file — business logic, error handling, edge cases, security, cross-layer consistency. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md` for the layer.

### Step 2: Database Investigation
Query relevant tables via `mcp__mcp_server_mysql__mysql_query` — schema, data integrity, relationships, orphaned records. (Roles live in `user_account`, not `user` — see `.claude/rules/db-gotchas.md`.)

### Step 3: API Investigation
Test each endpoint via `mcp__http-client__*` or `mcp__postman-api-mcp__*` — request/response, auth, RBAC, validation, error responses, FE consistency. Clear stale headers (`set_default_headers` merge:false) before auth.

### Step 4: Browser Validation
Test each UI flow via `mcp__playwright__*` — the **full** journey, not just the changed screen: page load, elements, actions, data display; capture console errors and network requests via `mcp__chrome-devtools__*` during every flow. **During the flow -> `Skill(observability-check)`**: surface console errors / failed-slow network / backend 5xx the UI hides (a clean-looking screen can still be failing under the hood).

**If the feature produces AI/ML-generated numbers** (scores, recommendation picks, KPIs, report figures): recompute them vs their source data and check for edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope).

**Keep it light:** for deep UI (visual / a11y) or a full regression pass, use `/full-qa`.

---

## Phase 3: Cross-Layer Data Consistency (MANDATORY)

For each entity under test, verify the same value agrees across DB -> API -> Browser. Mismatch = bug.

### Entity Reference

| Entity | DB Table(s) | API Endpoint(s) |
|--------|------------|-----------------|
| User | `user`, `user_account` | `GET /api/<resource>/users` |
| Manager | `user`, `user_account` | `GET /api/<resource>/managers` |
| Account | `account`, `user_account` | `GET /api/accounts/:id` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Subscription | `subscription`, `invoice` | `GET /api/subscriptions/:id` |
| Model output / score | `audit_log`, snapshot tables (PROJECT-PROFILE.md §11) | `GET /api/<resource>/scores` |

### Check Process
For each entity: **A)** Query DB via `mcp__mcp_server_mysql__mysql_query` -> **B)** Call API via `mcp__http-client__*` (or replay the FE request captured via `mcp__chrome-devtools__*`) -> **C)** Check browser via `mcp__playwright__*` -> **D)** Compare in a table:

```
| Field | DB Value | API Value | Browser Value | Match? |
```

### Consistency Types to Check
Value, count, status, date/time format, null handling, soft-delete filtering, FK resolution, aggregation, ordering, pagination.

### On Mismatch -> Bug
If actual data mismatch (not just format), classify (FE / BE / Admin / Report / DB / Both per qa-standards), verify with `Skill(bug-verifier)` before it counts, then file via `Skill(bug-report)` with values from each layer and root-cause `path:line`. **No DB/API/Browser comparison = no cross-layer claim.**

---

## Evidence Ledger (REQUIRED in the final report)

Every finding (bug OR proof-of-correct) maps to >=1 evidence row. **No evidence = no finding. No reproduction = no confirmed bug.** Save proof for PASS too.

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

Attachments live under `qa-evidence/<FEATURE-SLUG>/` or `qa-evidence/BUG-YYYYMMDD-HHMMSS/`. Write them via `mcp__filesystem__write_file` (the read-only hook blocks `Write`/`Edit` for `qa-evidence/`); Pass `filename: qa-evidence/<finding>/<name>.png` to Playwright screenshots (a bare filename saves to the repo root). Findings/reports stay in the chat, not as markdown in `qa-evidence/`.

## Superpowers escalation
Non-obvious root cause after the cross-layer pass -> `superpowers:systematic-debugging`. Before declaring ready / PASS -> `superpowers:verification-before-completion` (evidence before assertions).

---

## Deliverables

1. **Validation Summary** — story, date, QA mode, files reviewed, tables checked, APIs tested, UI flows tested, cross-layer consistency results, findings, coverage gaps (an untested dimension is never an implied PASS).
2. **Evidence Ledger** — the table above.
3. **Bug Reports** — verified bugs only, via `Skill(bug-report)`.
4. **Recommendation** — ready / not-ready with reason. Strict policy: any confirmed bug (any layer, any severity) = not ready.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** feature + date, verdict (ready / not-ready / CONFIRMED / DUPLICATE), bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/emails), root-cause `path:line`, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.
