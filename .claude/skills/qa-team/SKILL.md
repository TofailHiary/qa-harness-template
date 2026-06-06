---
name: qa-team
description: Use when a feature or user story should be tested across all layers at once with maximum coverage and speed by running three independent agents in parallel — a browser/UI tester, an API tester, and a DB validator — with the lead synthesizing one unified report. Triggers include "parallel testing", "agent team testing", "test this story from all sides at once", "QA team on APP-xxx". Prefer /full-qa when you want the sequential master cycle with code-review/security/perf phases and a strict GO/NO-GO; use this when the win is fan-out speed.
argument-hint: "user story or feature to test with agent team"
agent: general-purpose
allowed-tools: ["Bash", "Read", "Grep", "Glob", "Task", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)"]
---

# QA Agent Team — Parallel Full-Stack Testing

Launch a coordinated team of specialized agents to test a feature across all layers simultaneously, then synthesize one verdict.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What feature or user story should the QA team test? Which QA mode — smoke / targeted / regression / bugfix / full?"

Do NOT guess scope from conversation. Do NOT launch any agent until scope is known.

---

## Step 0a: QA Mode + Scope Lock (REQUIRED — before any agent launches)

Pick the **QA mode** (qa-standards -> QA Modes). If the user didn't state one, infer the smallest mode that covers the request and say which. Then emit the **Scope Lock** table; do not launch an agent or run a single query/call/click until it is filled (ask if a critical field is unknown — do not guess):

| Field | Value |
|---|---|
| Feature / story / bug / PR | |
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

The Scope Lock is the contract handed to all three agents. Do not silently narrow scope to make a PASS easier.

## Step 0b: Impact Analysis (REQUIRED for regression / bugfix; recommended always)

Before dividing the work, trace the blast radius per qa-standards -> Impact Analysis: shared FE components (grep imports), shared API endpoints (other features / roles / params), shared DB tables/columns (reports, dashboards, exports, other endpoints), async consumers (cron / Lambda / SQS / S3 / email), caches & report snapshots (React Query keys, snapshot tables (PROJECT-PROFILE.md §11)), downstream reports/exports. Feed results into the Scope Lock "Indirect blast radius" row and split them across the agents below. **A change is in scope plus everything this surfaces — validate the full flow and the blast radius, not the diff.**

If the source is a Jira ticket, pull acceptance criteria via `mcp__claude_ai_Atlassian__*` and hand them to every agent.

---

## Environment & Credentials (Embedded for Fork Context)

- **Admin Portal:** <the relevant URL: PROJECT-PROFILE.md §5> — <admin email: PROJECT-PROFILE.md §7> / <admin password env var: PROJECT-PROFILE.md §7>
- **Main Portal (Test, DEFAULT):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Dev):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Auth method:** Authenticate per PROJECT-PROFILE.md §7 to obtain a token — e.g. JWT (POST credentials → Bearer token), session cookie, OAuth, or Firebase ID token — then send `Authorization: Bearer <token>`. See §7 for the login method configured for this project.
- **User password:** <role password env var: PROJECT-PROFILE.md §7>
- **Manager password:** <role password env var: PROJECT-PROFILE.md §7>
- **Database (Test/Dev):** <test DB name: PROJECT-PROFILE.md §6> at <DB host: PROJECT-PROFILE.md §6>:3306 — `mcp__mcp_server_mysql__mysql_query`
- **Database (Prod, read-only):** `mcp__mcp_server_mysql_prod__mysql_query` — confirm a prod repro only; needs SSH tunnel on <prod DB via tunnel: PROJECT-PROFILE.md §6>. **Never mutate prod.**
- **Repos:** <frontend repo: PROJECT-PROFILE.md §3/§9>, <backend repo: PROJECT-PROFILE.md §3/§9>, <admin repo: PROJECT-PROFILE.md §3/§9>, <report repo: PROJECT-PROFILE.md §3> (branch: see PROJECT-PROFILE.md §3)
- **Key paths:** FE API: <frontend repo: PROJECT-PROFILE.md §3/§9>/src/ (see §9) | BE routes: <backend repo: PROJECT-PROFILE.md §3/§9>/routes/ | BE models: <backend repo: PROJECT-PROFILE.md §3/§9>/models/

## Mutation Safety Gate (hand to every agent that may write)

Any DB UPDATE/INSERT/DELETE AND any POST/PUT/PATCH/DELETE API call follows this gate (qa-standards): (1) target in scope; (2) prefer existing disposable test data; (3) SELECT + log original state first; (4) rollback plan ready; (5) never destructive against shared/prod data — prod is read-only; (6) UPDATE/DELETE needs a WHERE, never hard-DELETE (use status / `deleted_at`); (7) after the test verify + restore + re-SELECT, logging `| # | Table | ID | Column | Original | Test value | Restored? |`. No clean rollback -> STOP and ask the user.

## How This Works

You are the **Lead** agent. You will:
1. Lock scope (Step 0a) and run Impact Analysis (Step 0b).
2. Generate test cases (test-cases-generator approach) covering the scope + blast radius.
3. Divide the work across three specialized agents.
4. Launch them in parallel using the Task tool (a single message — see `superpowers:dispatching-parallel-agents` for the fan-out pattern).
5. Collect all results, triangulate cross-layer, and produce a unified report with an Evidence Ledger.

## Team Structure

```
You (Lead) — Coordinates, synthesizes, reports
├── Agent 1: Browser/UI Tester — Tests all UI flows via Playwright + Chrome DevTools
├── Agent 2: API Tester — Tests all endpoints via HTTP Client + Postman
└── Agent 3: DB Validator — Validates all database changes via MySQL MCP
```

---

## Step 1: Preparation (Lead Does This)

### 1.0. Preflight, risk, data (BEFORE launching the agents)
- **Preflight -> `Skill(env-health)`**: MCP servers reachable, repos on the correct branch (case-sensitive) + current, portals/DB/auth up, and the feature actually deployed. A RED item is a stop condition -> STOP and report PARTIAL; do not launch the agents into a dead env.
- **If the scope is a PR / commit / branch -> `Skill(pr-risk-analyzer)`** for the formal blast-radius risk map; feed its impact map into the Scope Lock "Indirect blast radius" row and split it across the three agents below.
- **Test data -> `Skill(test-data-manager)`**: locate rich existing records matching the cases (prefer reuse); prepare + snapshot + restore only if needed, under the Mutation Safety Gate above. Hand the resolved data IDs to the agents.

### 1a. Analyze the Feature
From the Scope Lock + Impact Analysis, identify:
- Which UI pages/flows are affected (including pages that reuse a shared changed component).
- Which API endpoints are involved — use `mcp__postman-api-mcp__searchPostmanElements` to enumerate all Postman requests for this feature. Pass the full endpoint list to Agent 2 so it tests against the actual contract, not guesses.
- Which database tables are affected (including tables read by downstream reports/dashboards).
- Which user roles need testing (Admin, Manager, User, Guest).

### 1b. Cross-check memory, then generate test cases
First grep `~/.claude/projects/c--Users-<user>-<project>/memory/*.md` for the feature/story, ticket/BUG- IDs, paths, entity IDs; load matches as known regression-risk areas. Then follow the test-cases-generator approach to create executable cases (TC ID | AC | Scenario | Preconditions | Test Data | Steps | Expected | Layer | Role | Priority) categorized by:
- UI/Browser tests -> Agent 1
- API tests -> Agent 2
- Database tests -> Agent 3
- Cross-layer tests -> Lead handles after agents report back

Cover every cell of the coverage matrix (roles, states, inputs incl. negative/boundary, full flow, cross-tenant).

---

## Step 2: Launch Agents in Parallel

Use the Task tool to launch all three agents simultaneously in a SINGLE message (this enables true parallelism). Pass each agent the Scope Lock, its slice of the blast radius, the Mutation Safety Gate, and the Evidence Ledger requirement.

### Agent 1: Browser/UI Tester
```
Launch as Task with subagent_type: "general-purpose"

Prompt: You are a UI/Browser testing specialist for this application.

Tools: Use mcp__playwright__* for snapshots/clicks/forms, mcp__chrome-devtools__* for console/network inspection.

Test Environment:
- Admin: <the relevant URL: PROJECT-PROFILE.md §5> (<admin email: PROJECT-PROFILE.md §7> / <admin password env var: PROJECT-PROFILE.md §7>)
- Portal (Test, DEFAULT): <the relevant URL: PROJECT-PROFILE.md §5>
- Portal (Dev): <the relevant URL: PROJECT-PROFILE.md §5>
- Auth method: Authenticate per PROJECT-PROFILE.md §7 (JWT / session / OAuth / Firebase — see §7).
- User password: <role password env var: PROJECT-PROFILE.md §7>
- Manager password: <role password env var: PROJECT-PROFILE.md §7>

Scope Lock + your test cases:
[Paste the Scope Lock and the UI test cases here]

For each test:
1. Navigate to the page using Playwright
2. Take a snapshot to understand the page
3. Perform the test actions — exercise the FULL flow, not just the changed screen
4. Check console messages for errors (mcp__chrome-devtools__*)
5. Check network requests for failures (mcp__chrome-devtools__*)
6. Take screenshots for evidence
7. Report PASS or FAIL with Expected vs Actual + evidence. No evidence = no finding.

ALSO, for each affected page, run these three checks using the named skill as the method:
8. Responsive layout (the `visual-regression` method): resize the page to Desktop 1440, Tablet 768, and Mobile 375 (mcp__playwright__browser_resize) and screenshot each; look for horizontal overflow, text truncation cutting real content, element overlap/misalignment, broken wrapping, and off-screen/clipped elements.
9. Accessibility (the `a11y-test` method): keyboard navigation + focus order/visibility (Tab through interactive elements), ARIA labels/roles + semantics, and color-contrast against WCAG AA; flag missing labels and unannounced errors.
10. Hidden errors (the `observability-check` method): console errors + failed/slow 4xx/5xx network calls + backend 5xx — surface what the UI hides even when the screen looks fine.

Read the agent instructions from: .claude/agents/qa-ui-tester.md
Save all screenshots with an explicit path — pass `filename: qa-evidence/<finding>/<name>.png` to browser_take_screenshot (a bare filename lands in the repo root, NOT qa-evidence).
End by updating auto-memory (mandatory) per .claude/agents/qa-ui-tester.md.
```

### Agent 2: API Tester
```
Launch as Task with subagent_type: "general-purpose"

Prompt: You are an API testing specialist for this application.

Tools: Use mcp__http-client__* for direct API calls, mcp__postman-api-mcp__* for Postman collections, mcp__mcp_server_mysql__mysql_query for DB verification after write ops.

Read the agent instructions from: .claude/agents/qa-api-tester.md

Scope Lock + your test cases:
[Paste the Scope Lock and the API test cases here]

For each endpoint, test: happy path, auth, authorization (RBAC + cross-tenant), validation, not found, error responses, schema, and DB-write consistency.
Any write follows the Mutation Safety Gate (SELECT + log original, WHERE on every UPDATE, restore + verify after, never mutate prod).
If the feature produces AI/ML-generated numbers (scores, recommendation picks, KPIs, report figures), evaluate them by recomputing the value vs its source data and checking for edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope).
Save all requests and responses as evidence. Report PASS/FAIL with Expected vs Actual.
End by updating auto-memory (mandatory) per .claude/agents/qa-api-tester.md.
```

### Agent 3: DB Validator
```
Launch as Task with subagent_type: "general-purpose"

Prompt: You are a database validation specialist for this application.

Tools: Use mcp__mcp_server_mysql__mysql_query for all DB queries, Read/Grep/Glob to compare schema with ORM models.

Read the agent instructions from: .claude/agents/qa-db-validator.md
Database: <test DB name: PROJECT-PROFILE.md §6> at <DB host: PROJECT-PROFILE.md §6> (roles live in user_account, not user — see .claude/rules/db-gotchas.md).

Scope Lock + your test cases:
[Paste the Scope Lock and the DB test cases here]

Check schema vs ORM model, foreign keys, orphaned records, duplicates, data consistency, indexes — including tables read by downstream reports/dashboards.
If the feature produces AI/ML-generated numbers (scores, recommendation picks, KPIs, report figures), evaluate them by recomputing the stored value vs its source rows and checking for edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope).
End by updating auto-memory (mandatory) per .claude/agents/qa-db-validator.md.
```

---

## Step 3: Collect Results (Lead Does This)

After all three agents complete:
1. Gather all results from each agent.
2. Cross-reference findings (API returns wrong data AND DB has wrong data = same root cause).
3. Identify cross-layer bugs and classify each (FE / BE / Admin / Report / DB / Both per qa-standards).
4. Deduplicate findings.

---

## Step 4: Execute Cross-Layer Tests (Lead Does This)

Only the Lead has all three sets of outputs, so the Lead runs the triangulation:
- Create something in UI -> verify it exists in DB.
- Call API -> verify UI reflects the change.
- Change DB data (under the Mutation Safety Gate) -> verify UI shows updated data.

Compare each entity in a table: `| Field | DB | API | Browser | Match? |`. **No DB/API/Browser comparison = no cross-layer claim.** Verify any suspected bug with `Skill(bug-verifier)` before it counts.

---

## Step 5: Unified Report

```
## QA Agent Team Report

**Feature/Story**: [Description]   **QA Mode**: [mode]   **Date**: [Date]
**Team**: Lead + 3 Agents (Browser, API, DB)

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
- **Severity**: [Critical/High/Medium/Low]   **Layer**: [FE/BE/Admin/Report/DB/Both]   **Found by**: [Agent/Lead]
- **Steps / Expected / Actual / Evidence**: [...]

### Cross-Layer Consistency
| Check | FE | API | DB | Status |
|-------|----|-----|----|--------|
| Data value/format | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] |
| Validation | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] |
| Error handling | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] | [OK/ISSUE] |

### Evidence Ledger (REQUIRED — every finding AND every PASS)
| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

### Coverage Gaps
[Any dimension not tested — an untested dimension is never an implied PASS]

### Verdict
[ ] PASS — 0 bugs across all layers
[ ] FAIL — 1+ bugs (any layer, any severity)
**Reason**: [Explanation]
```

Before declaring PASS, run `superpowers:verification-before-completion` (evidence before assertions). For a non-obvious cross-layer root cause, escalate to `superpowers:systematic-debugging`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. **Each agent updates memory in its own run; the Lead writes the synthesis.** If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** feature + date, verdict (PASS/FAIL), bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/emails), root-cause `path:line`, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.
