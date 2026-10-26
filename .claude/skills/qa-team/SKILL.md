---
name: qa-team
description: Use when a story or feature should be tested across UI, API and DB at the same time by three parallel agents with one unified report, and fan-out speed matters more than the sequential cycle. Triggers include "parallel testing", "agent team testing", "test this story from all sides at once", "QA team on APP-xxx". Prefer /full-qa for the sequential cycle with code review, security and perf and a strict GO/NO-GO.
argument-hint: "user story or feature to test with agent team"
agent: general-purpose
allowed-tools: ["Agent", "Agent(qa-verdict-auditor)", "Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# QA Agent Team — Parallel Full-Stack Testing

> **Capability gate:** This skill is **always on** (orchestrator — it never hard-stops). Before doing
> anything, read `PROJECT-PROFILE.md` §2 (Capability Map). A lane whose capability is `off` is not
> launched: no **Browser** -> no Agent 1; no **API** -> no Agent 2; no **DB** -> no Agent 3 and no DB
> column in the cross-layer check; no **GitHub** / **LocalRepos** -> skip `pr-risk-analyzer` and code
> comparison; no **Jira** -> take acceptance criteria from the user; no **Postman** -> enumerate
> endpoints from the routes. Every lane not launched is stated in the verdict ("Agent 1 skipped:
> Browser capability off") and its Execution Register rows read NOT YET VERIFIED — never PASS.
> If `PROJECT-PROFILE.md` is blank, STOP and tell the user to run `/configure-project`.

> **Sub-agent policy knob (`PROJECT-PROFILE.md §16`):** this skill's whole win is fan-out. If §16 says
> sub-agents are disabled, say so, then either run the three lanes **sequentially in-session**
> (UI -> API -> DB, using the lane briefs below as your own checklists) or hand the request to
> `/full-qa`. Either way the Execution Register, the audit and the Verdict Contract still apply.

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

The six questions (qa-standards -> The six questions) are recommended before locking scope: what is requested / what is authoritative / what can be verified / which assumptions are eliminated / what evidence is required / what completion means.

Pick the **QA mode** (qa-standards -> QA Modes). If the user didn't state one, infer the smallest mode that covers the request and say which. Then emit the **Scope Lock** table; do not launch an agent or run a single query/call/click until it is filled (ask if a critical field is unknown — do not guess):

| Field | Value |
|---|---|
| Feature / story / bug / PR | |
| QA mode | smoke / targeted / regression / bugfix / full |
| Roles in scope | <roles: PROJECT-PROFILE.md §8> — e.g. Admin / Manager / User / Guest / Other |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | <key tables: PROJECT-PROFILE.md §10> |
| Direct dependents | (Step 0b) |
| Indirect blast radius | (Step 0b) |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Build under test | `<branch: PROJECT-PROFILE.md §3> @ <short sha>` — capture once, hand to every lane for its Evidence Ledger rows |
| Risk level | Low / Medium / High |
| Stop conditions | feature undeployed / schema missing / wrong branch / auth fails |

The Scope Lock is the contract handed to all three agents. Do not silently narrow scope to make a PASS easier.

## Step 0b: Impact Analysis (REQUIRED for regression / bugfix; recommended always)

Before dividing the work, trace the blast radius per qa-standards -> Impact Analysis: shared FE components (grep imports), shared API endpoints (other features / roles / params), shared DB tables/columns (reports, dashboards, exports, other endpoints), async consumers (cron / serverless functions / queues / storage events / email — `PROJECT-PROFILE.md §11`), caches & snapshots (client-side cache keys, snapshot tables (`PROJECT-PROFILE.md §11`)), downstream reports/exports (CSV columns, dashboards, printed/PDF outputs). Feed results into the Scope Lock "Indirect blast radius" row and split them across the agents below. **A change is in scope plus everything this surfaces — validate the full flow and the blast radius, not the diff.**

If the source is a tracker ticket and Jira is on, pull acceptance criteria via `mcp__claude_ai_Atlassian__*` (tracker: `PROJECT-PROFILE.md §15`) and hand them to every agent. Read the whole thread — a clarifying dev/PO comment often overrides a stale AC.

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

Identifiers only — passwords live in the env vars named in `PROJECT-PROFILE.md §7` and are never written here or in a lane brief.

- **Main Portal (Test, DEFAULT):** <main app URL: PROJECT-PROFILE.md §5>
- **Main Portal (Dev):** <main app URL (dev): PROJECT-PROFILE.md §5>
- **Admin Portal (if Admin is on):** <admin URL: PROJECT-PROFILE.md §5> — <admin account: PROJECT-PROFILE.md §7>
- **Surface selection:** if §5 lists more than one frontend surface, default to the primary one; use a secondary / legacy surface only when the story is explicitly about it. Never navigate to a surface §5 marks as retired.
- **Auth method:** per `PROJECT-PROFILE.md §7` — obtain a token (JWT / session cookie / OAuth / identity-provider ID token) and send it the way §7 says (typically `Authorization: Bearer <token>`).
- **Role accounts:** <role account: PROJECT-PROFILE.md §7> for every role in scope.
- **Database (Test/Dev):** <test DB name: PROJECT-PROFILE.md §6> at <DB host/port: PROJECT-PROFILE.md §6> — `mcp__mcp_server_mysql__mysql_query` (DB tool: `PROJECT-PROFILE.md §6`)
- **Database (Prod, read-only, only if Prod-DB is on):** `mcp__mcp_server_mysql_prod__mysql_query` — confirm a prod repro only, via the prod read-only access described in `PROJECT-PROFILE.md §6`. **Never mutate prod.**
- **Repos:** <frontend repo: PROJECT-PROFILE.md §3/§9>, <backend repo: PROJECT-PROFILE.md §3/§9>, <admin repo: PROJECT-PROFILE.md §3/§9>, <report repo: PROJECT-PROFILE.md §3> (branch: <branch: PROJECT-PROFILE.md §3>, case-sensitive)
- **Key paths (§9):** FE API layer: <frontend API layer: PROJECT-PROFILE.md §9> | BE routes: <routes path: PROJECT-PROFILE.md §9> | BE models: <models path: PROJECT-PROFILE.md §9> | Auth middleware: <auth middleware: PROJECT-PROFILE.md §9>
- **API tooling:** if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it (one typed call as the right role replaces token minting + header setup + URL building); otherwise `mcp__http-client__*`. Keep `mcp__http-client__*` for replaying a captured FE request byte-for-byte; `mcp__postman-api-mcp__*` (Postman on) for existing contracts.

## Mutation Safety Gate (hand to every agent that may write)

Any DB UPDATE/INSERT/DELETE AND any POST/PUT/PATCH/DELETE API call follows this gate (qa-standards): (1) target in scope; (2) prefer existing disposable test data; (3) SELECT + log original state first; (4) rollback plan ready; (5) never destructive against shared/prod data — prod is read-only; (6) UPDATE/DELETE needs a WHERE, never hard-DELETE (use status / `deleted_at` where the column exists); (7) after the test verify + restore + re-SELECT, logging `| # | Table | ID | Column | Original | Test value | Restored? |`. No clean rollback -> STOP and ask the user.

## How This Works

You are the **Lead** agent. You will:
1. Lock scope (Step 0a) and run Impact Analysis (Step 0b).
2. Generate test cases (test-cases-generator approach) covering the scope + blast radius.
3. Divide the work across three specialized agents.
4. Launch them in parallel using the `Agent` tool (`Task` in older Claude Code versions) in a single message. If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`), `superpowers:dispatching-parallel-agents` describes the fan-out pattern; otherwise by hand: one message, one self-contained brief per lane (Scope Lock slice, gate, ledger + register requirement), merge only after every lane returns.
5. Collect all results, triangulate cross-layer, audit, and produce a unified report with an Evidence Ledger and an Execution Register.

**Lane reports are leads, not findings.** Agreement between your own lanes is ONE source, not independent confirmation — they inherit your framing (qa-standards -> Verdict Integrity #5). Anything filed externally is reproduced first-hand by the Lead (Verdict Integrity #7).

## Team Structure

```
You (Lead) — Coordinates, synthesizes, audits, reports
├── Agent 1: Browser/UI Tester — Tests all UI flows via Playwright + Chrome DevTools   (Browser on)
├── Agent 2: API Tester — Tests all endpoints via HTTP Client / typed tools + Postman   (API on)
└── Agent 3: DB Validator — Validates all database changes via the DB MCP            (DB on)
```

---

## Step 1: Preparation (Lead Does This)

### 1.0. Preflight, risk, data (BEFORE launching the agents)
- **Preflight -> `Skill(env-health)`**: MCP servers reachable, repos on `<branch: PROJECT-PROFILE.md §3>` (case-sensitive) + current, portals/DB/auth up, and the feature actually deployed. A RED item is a stop condition -> STOP and report PARTIAL; do not launch the agents into a dead env. Record `git rev-parse --short HEAD` of the repo under test in the Scope Lock "Build under test" row.
- **If the scope is a PR / commit / branch -> `Skill(pr-risk-analyzer)`** (GitHub or LocalRepos on) for the formal blast-radius risk map; feed its impact map into the Scope Lock "Indirect blast radius" row and split it across the three agents below.
- **Test data -> `Skill(test-data-manager)`**: locate rich existing records matching the cases (prefer reuse); prepare + snapshot + restore only if needed, under the Mutation Safety Gate above. Exhaust the data resources first — fixtures through the application's own API (`PROJECT-PROFILE.md §14` typed tools, if any), the sample-file library (`§13`, if any), a disposable replica (`§6`, if any) — before any lane is allowed to record a coverage gap. Hand the resolved data IDs to the agents.

### 1a. Analyze the Feature
From the Scope Lock + Impact Analysis, identify:
- Which UI pages/flows are affected (including pages that reuse a shared changed component).
- Which API endpoints are involved — if Postman is on, use `mcp__postman-api-mcp__searchPostmanElements` to enumerate all requests for this feature; otherwise enumerate from <routes path: PROJECT-PROFILE.md §9> and the §14 typed-tool catalog. Pass the full endpoint list to Agent 2 so it tests against the actual contract, not guesses.
- Which database tables are affected (including tables read by downstream reports/dashboards).
- Which user roles need testing (<roles: PROJECT-PROFILE.md §8>).

### 1b. Cross-check memory, then generate test cases
First grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for the feature/story, ticket (`APP-nnn`) / `BUG-` IDs, paths, entity IDs; load matches as known regression-risk areas (context, never proof — qa-standards -> Fresh vs Historical). Then follow the test-cases-generator approach to create executable cases (TC ID | AC | Scenario | Preconditions | Test Data | Steps | Expected | Layer | Role | Priority | Input class | Path exercised) categorized by:
- UI/Browser tests -> Agent 1
- API tests -> Agent 2
- Database tests -> Agent 3
- Cross-layer tests -> Lead handles after agents report back

Cover every cell of the coverage matrix (roles, states, inputs incl. negative/boundary, full flow, cross-tenant). Derive the denominator from the code (origin x mode x type x action), not by guessing (escape class E12). Every Scope Lock area is pre-assigned a register row ID so no area can vanish between lanes.

---

## Step 2: Launch Agents in Parallel

Use the `Agent` tool to launch all enabled agents simultaneously in a SINGLE message (this enables true parallelism). Pass each agent the Scope Lock (including "Build under test"), its slice of the blast radius, its register row IDs, the Mutation Safety Gate, and the Evidence Ledger requirement with provenance (Env / Branch-Commit / Captured at on every row). Each lane returns: PASS/FAIL per case with Expected vs Actual, its ledger rows, and its register rows.

### Agent 1: Browser/UI Tester (Browser on)
```
Launch via Agent with subagent_type: "ui-tester"

Prompt: You are a UI/Browser testing specialist for this application.

Tools: Use mcp__playwright__* for snapshots/clicks/forms, mcp__chrome-devtools__* for console/network inspection.

Test Environment (identifiers only; passwords come from the env vars in PROJECT-PROFILE.md §7):
- Portal (Test, DEFAULT): <main app URL: PROJECT-PROFILE.md §5>
- Portal (Dev): <main app URL (dev): PROJECT-PROFILE.md §5>
- Admin (if Admin is on): <admin URL: PROJECT-PROFILE.md §5> as <admin account: PROJECT-PROFILE.md §7>
- Surface selection: default to the primary frontend in §5; a secondary / legacy surface only when the story is explicitly about it; never a surface §5 marks as retired.
- Auth method: per PROJECT-PROFILE.md §7.
- Role accounts: <role account: PROJECT-PROFILE.md §7> for each role in scope.
- Build under test: [paste the Scope Lock value]

Scope Lock + your test cases + your register row IDs:
[Paste the Scope Lock and the UI test cases here]

For each test:
1. Navigate to the page using Playwright
2. Take a snapshot to understand the page
3. Perform the test actions — exercise the FULL flow, not just the changed screen
4. Check console messages for errors (mcp__chrome-devtools__*)
5. Check network requests for failures (mcp__chrome-devtools__*)
6. Take screenshots for evidence
7. Report PASS or FAIL with Expected vs Actual + evidence. No evidence = no finding. A functional PASS names the API call / write that actually happened (network capture), never a toast or the presence of a control. Paginate beyond page 1; sort both directions.

ALSO, for each affected page, run these three checks using the named skill as the method:
8. Responsive layout (the `visual-regression` method): resize the page to Desktop 1440, Tablet 768, and Mobile 375 (mcp__playwright__browser_resize) and screenshot each; look for horizontal overflow, text truncation cutting real content, element overlap/misalignment, broken wrapping, and off-screen/clipped elements.
9. Accessibility (the `a11y-test` method): keyboard navigation + focus order/visibility (Tab through interactive elements), ARIA labels/roles + semantics, and color-contrast against WCAG AA; flag missing labels and unannounced errors.
10. Hidden errors (the `observability-check` method): console errors + failed/slow 4xx/5xx network calls + backend 5xx — surface what the UI hides even when the screen looks fine.

You ARE that specialist agent — your instructions, tools and preloaded qa-standards are already active. Do NOT re-read your own definition file.
Save all screenshots with an explicit path — pass `filename: qa-evidence/<run folder>/<name>.png` to browser_take_screenshot (a bare filename lands in the repo root, NOT qa-evidence).
Return your Evidence Ledger rows (with Env / Branch-Commit / Captured at) and your Execution Register rows (Result from the five canonical values).
End by updating auto-memory (mandatory) per .claude/agents/qa-ui-tester.md.
```

### Agent 2: API Tester (API on)
```
Launch via Agent with subagent_type: "api-tester"

Prompt: You are an API testing specialist for this application.

Tools: If PROJECT-PROFILE.md §14 lists a project MCP server with typed tools for this surface, prefer it; otherwise mcp__http-client__* for direct API calls. mcp__postman-api-mcp__* for existing contracts (Postman on), mcp__mcp_server_mysql__mysql_query for DB verification after write ops (DB on).

You ARE that specialist agent — your instructions, tools and preloaded qa-standards are already active. Do NOT re-read your own definition file.

Scope Lock + your test cases + your register row IDs:
[Paste the Scope Lock and the API test cases here]

For each endpoint, test: happy path, auth, authorization (RBAC + cross-tenant), validation, not found, error responses, schema, and DB-write consistency. Test against the real wire — the actual response body captured in the target environment, never a mock.
Any write follows the Mutation Safety Gate (SELECT + log original, WHERE on every UPDATE, restore + verify after, never mutate prod).
For async flows, verify the terminal DB state, never the enqueue.
If the feature produces model-generated or computed numbers (scores, recommendation picks, KPIs, report figures), evaluate them with the `ai-output-eval` method: recompute the value from its source data and check the edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope).
Save all requests and responses as evidence under qa-evidence/<run folder>/. Report PASS/FAIL with Expected vs Actual.
Return your Evidence Ledger rows (with Env / Branch-Commit / Captured at) and your Execution Register rows (Result from the five canonical values).
End by updating auto-memory (mandatory) per .claude/agents/qa-api-tester.md.
```

### Agent 3: DB Validator (DB on)
```
Launch via Agent with subagent_type: "db-validator"

Prompt: You are a database validation specialist for this application.

Tools: Use mcp__mcp_server_mysql__mysql_query (DB tool: PROJECT-PROFILE.md §6) for all DB queries, Read/Grep/Glob to compare schema with the ORM models (<models path: PROJECT-PROFILE.md §9>; ORM: PROJECT-PROFILE.md §4).

You ARE that specialist agent — your instructions, tools and preloaded qa-standards are already active. Do NOT re-read your own definition file.
Database: <test DB name: PROJECT-PROFILE.md §6> at <DB host/port: PROJECT-PROFILE.md §6>. Roles may live in a join / membership table rather than on `user`, and soft-delete columns are not universal — see .claude/rules/db-gotchas.md and PROJECT-PROFILE.md §10.

Scope Lock + your test cases + your register row IDs:
[Paste the Scope Lock and the DB test cases here]

Check schema vs ORM model, foreign keys, orphaned records, duplicates, data consistency, indexes — including tables read by downstream reports/dashboards. Read COLUMN_COMMENT / the model before judging a value.
If the feature produces model-generated or computed numbers (scores, recommendation picks, KPIs, report figures), evaluate them with the `ai-output-eval` method: recompute the stored value from its source rows and check the edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope).
Return your Evidence Ledger rows (with Env / Branch-Commit / Captured at) and your Execution Register rows (Result from the five canonical values).
End by updating auto-memory (mandatory) per .claude/agents/qa-db-validator.md.
```

---

## Step 3: Collect Results (Lead Does This)

After all launched agents complete:
1. Gather all results from each agent — cases, ledger rows, register rows.
2. Cross-reference findings (API returns wrong data AND DB has wrong data = same root cause).
3. Identify cross-layer bugs and classify each (FE / BE / Admin / Report / DB / Both per qa-standards).
4. Deduplicate findings. Treat correlated agreement between lanes as ONE source.
5. Merge the register: every pre-assigned row ID must come back with a Result; a row no lane returned is NOT YET VERIFIED, never dropped.

---

## Step 4: Execute Cross-Layer Tests (Lead Does This)

Only the Lead has all three sets of outputs, so the Lead runs the triangulation:
- Create something in UI -> verify it exists in DB.
- Call API -> verify UI reflects the change.
- Change DB data (under the Mutation Safety Gate) -> verify UI shows updated data.

Compare each entity in a table: `| Field | DB | API | Browser | Match? |`. **No DB/API/Browser comparison = no cross-layer claim.** Partially-empty beats empty — `0`, `null`, `""`, `[]`, missing key and Loading are different states (qa-standards -> Judgement Discipline #2). Verify any suspected bug with `Skill(bug-verifier)` before it counts; confirmed bugs -> `Skill(bug-report)`.

---

## Step 5: Unified Report

```
## QA Agent Team Report

> Moved to [`references/report-template.md`](references/report-template.md). Read it before writing the unified report: the section order, the register and ledger tables and the canonical verdict line come from there.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. **Each agent updates memory in its own run; the Lead writes the synthesis.** If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate. If today's evidence DISPROVES a fact in an older memory, mark that older file SUPERSEDED in the same session (qa-standards -> Memory Ritual).
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title> YYYY-MM-DD](<file>.md) — <hook>` (date in the link title — escape class E13).
4. **Content:** feature + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), audit result, lanes launched / skipped, bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/accounts), root-cause `path:line`, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
