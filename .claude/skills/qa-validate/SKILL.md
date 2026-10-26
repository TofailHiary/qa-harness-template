---
name: qa-validate
description: Use when a single user story, bug, or feature needs a lighter end-to-end cross-layer validation (DB / API / Browser) than the full /full-qa cycle, ending in a ready / not-ready call. Triggers include "validate this story", "qa-validate APP-xxx", "check this fix end to end", "does this feature work across all layers". Reach for /full-qa instead when the scope is a PR/release needing a strict GO/NO-GO with code review, security and perf phases.
argument-hint: "user-story or bug description"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "Agent", "Agent(qa-verdict-auditor)", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(test-cases-generator)", "Skill(observability-check)", "Skill(ai-output-eval)", "Skill(bug-report)", "Skill(bug-verifier)", "Write"]
---

# QA Validation Workflow

> **Capability gate:** This skill is **always on** (orchestrator — it never hard-stops). Before doing
> anything, read `PROJECT-PROFILE.md` §2 (Capability Map) and skip every step whose capability is
> `off`: no **DB** -> skip Phase 2 Step 2 and the DB column of Phase 3; no **API** -> skip Step 3 and
> the API column; no **Browser** -> skip Step 4 and the Browser column; no **GitHub** / **LocalRepos**
> -> skip code investigation and `pr-risk-analyzer`; no **Jira** -> take acceptance criteria from the
> user; no **Postman** -> enumerate endpoints from the routes. Every skipped step is stated in the
> verdict ("Step 4 skipped: Browser capability off") and its Execution Register rows read
> NOT YET VERIFIED — never PASS. If `PROJECT-PROFILE.md` is blank, STOP and tell the user to run
> `/configure-project`.

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
8. The verdict uses the canonical words of qa-standards -> Verdict Contract, carries an Execution Register, and is independently audited BEFORE it is stated (Deliverables).

---

## Step 0a: Six questions + QA Mode + Scope Lock (REQUIRED — before any tool runs)

**Six questions first** (qa-standards -> The six questions): write them out explicitly (2-6 lines) before the first tool runs —
1. **What is requested?** (the literal ask, and the mode it implies)
2. **What is authoritative?** (ticket / AC / spec / code contract / ruling — per qa-standards -> Authoritative Source Hierarchy)
3. **What can be verified?** (which layers, with which tools, in which environment — only capabilities that are `on`)
4. **Which assumptions are eliminated?** (name them; each becomes a check)
5. **What evidence is required?** (the ledger rows a GO would need)
6. **What is completion?** (the register rows that must all be non-empty)

Pick the **QA mode** (qa-standards -> QA Modes). If the user didn't state one, infer the smallest mode that covers the request and say which. Then emit the **Scope Lock** table and run nothing until it is filled (ask if a critical field is unknown — do not guess):

| Field | Value |
|---|---|
| Feature / story / bug | |
| QA mode | smoke / targeted / regression / bugfix / full |
| Roles in scope | <roles: PROJECT-PROFILE.md §8> — e.g. Admin / Manager / User / Guest / Other |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | <key tables: PROJECT-PROFILE.md §10> |
| Direct dependents | (Step 0b) |
| Indirect blast radius | (Step 0b) |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Build under test | `<branch: PROJECT-PROFILE.md §3> @ <short sha>` — capture once here, reuse in every Evidence Ledger row |
| Risk level | Low / Medium / High |
| Stop conditions | feature undeployed / schema missing / wrong branch / auth fails |

Do not silently narrow scope to make a PASS easier. If you must drop coverage, say so and why.

## Step 0b: Impact Analysis (REQUIRED for regression / bugfix; recommended always)

Before generating cases, trace the blast radius per qa-standards -> Impact Analysis: shared FE components (grep imports), shared API endpoints (other features / roles / params), shared DB tables/columns (reports, dashboards, exports, other endpoints), async consumers (cron / serverless functions / queues / storage events / email — `PROJECT-PROFILE.md §11`), caches & snapshots (client-side cache keys, snapshot tables (`PROJECT-PROFILE.md §11`)), downstream reports/exports (CSV columns, dashboards, printed/PDF outputs). Feed results into the Scope Lock "Indirect blast radius" row and into Phase 0 cases. **A change is in scope plus everything this surfaces.**

**If the scope is a PR / commit / branch -> `Skill(pr-risk-analyzer)`** (GitHub or LocalRepos on) for the formal blast-radius risk map; feed its impact map into the Scope Lock "Indirect blast radius" row and into Phase 0 cases.

If the source is a tracker ticket and Jira is on, pull acceptance criteria via `mcp__claude_ai_Atlassian__*` (tracker and ticket pattern: `PROJECT-PROFILE.md §15`). Read the whole thread — a clarifying dev/PO comment often overrides a stale AC (qa-standards -> Authoritative Source Hierarchy).

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

### Portals
- **Main app (Test, DEFAULT):** <main app URL: PROJECT-PROFILE.md §5>
- **Main app (Dev):** <main app URL (dev): PROJECT-PROFILE.md §5>
- **Admin (if Admin is on):** <admin URL: PROJECT-PROFILE.md §5> — <admin account: PROJECT-PROFILE.md §7>
- **Surface selection:** if §5 lists more than one frontend surface, default to the primary one; use a secondary / legacy surface only when the story is explicitly about it. Never navigate to a surface §5 marks as retired.
- **Auth method:** per `PROJECT-PROFILE.md §7` — obtain a token (JWT / session cookie / OAuth / identity-provider ID token) and send it the way §7 says (typically `Authorization: Bearer <token>`).
- **Role accounts:** <role account: PROJECT-PROFILE.md §7> for every role in scope.

### Database
- Test/Dev: <DB host/port: PROJECT-PROFILE.md §6> | DB <test DB name: PROJECT-PROFILE.md §6> — `mcp__mcp_server_mysql__mysql_query` (DB tool: `PROJECT-PROFILE.md §6`)
- Prod (read-only, confirm a prod repro only, only if Prod-DB is on): `mcp__mcp_server_mysql_prod__mysql_query` via the prod read-only access described in `PROJECT-PROFILE.md §6`. **Never mutate prod.**

### Repos & Branches
| Repo | Branch | Type |
|------|--------|------|
| <frontend repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | Frontend |
| <backend repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | Backend |
| <admin repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | Admin panel (if Admin is on) |
| <report repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | Reporting service (if Reporting is on) |

Branch names are case-sensitive.

### Key Code Paths (`PROJECT-PROFILE.md §9`)
- FE API layer: <frontend API layer: PROJECT-PROFILE.md §9>
- FE pages / components: <frontend pages: PROJECT-PROFILE.md §9>
- BE routes: <routes path: PROJECT-PROFILE.md §9>
- BE models: <models path: PROJECT-PROFILE.md §9>
- Auth middleware: <auth middleware: PROJECT-PROFILE.md §9>
- Admin controllers: <admin controllers: PROJECT-PROFILE.md §9>

### API tooling
If `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it — one typed call as the right role replaces token minting + header setup + URL building. Otherwise use `mcp__http-client__*`. Keep `mcp__http-client__*` for replaying a captured FE request byte-for-byte, and `mcp__postman-api-mcp__*` (if Postman is on) for existing contracts.

---

## Phase 0: Test Case Generation

0. **Cross-check memory** — Grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for the feature/story, ticket (`APP-nnn`) / `BUG-` IDs, file paths, entity IDs. Load matches as known regression-risk areas; skip re-verifying bugs already CONFIRMED+CLOSED unless asked. Memory is context, never proof (qa-standards -> Fresh vs Historical): every dated claim in a recalled file — root cause, ticket status, fixture, prevalence — is stale until re-checked this run.
1. **Analyze input** — extract acceptance criteria, affected roles, pages/routes/APIs, data entities. Pull AC from the tracker via `mcp__claude_ai_Atlassian__*` if the source is a ticket and Jira is on (`PROJECT-PROFILE.md §15`).
2. **Enumerate endpoints** — if Postman is on, use `mcp__postman-api-mcp__searchPostmanElements` to find relevant requests and `mcp__postman-api-mcp__getCollectionFolder` to list endpoints in the affected area; otherwise enumerate from <routes path: PROJECT-PROFILE.md §9> (and the typed-tool catalog in §14, if any). This defines the full API surface to cover.
3. **Investigate code** — search FE components, BE routes/models, Admin controllers, DB schemas. Use `mcp__github__search_code` for cross-repo searches, `mcp__github__list_commits` for recent changes, `mcp__github__pull_request_read` for PR context (GitHub on), or `Read`/`Grep`/`Glob` on the local repos (LocalRepos on).
4. **Generate test cases** via `Skill(test-cases-generator)` by category: Positive, Negative, Boundary, DB Integrity, API, UI, Security, Regression, E2E, Data Consistency — covering every cell of the coverage matrix (roles, states, inputs incl. negative/boundary, full flow, cross-tenant) from Step 0b. Derive the denominator from the code (origin x mode x type x action), never by guessing (qa-standards -> Escape classes, E12). Every case carries an **Input class** column (which kind of file / record / payload it exercises) and a **Path exercised** column (the API call / DB write / job run that proves it did something — not a toast).
5. **Present summary table** with count per category and priority, then create TodoWrite tasks (P1 first). If the user specified scope, only generate for that scope plus its blast radius.

---

## Phase 1: Setup

**Preflight -> `Skill(env-health)`** (run this first): MCP servers reachable, repos on `<branch: PROJECT-PROFILE.md §3>` (case-sensitive) + current, portals/DB/auth up, **and the feature actually deployed** to the target env. A RED item is a stop condition -> STOP and report PARTIAL (not-ready) naming the blocker (do not build cases for a dead env).

Ensure repos are on the correct branches (`<branch: PROJECT-PROFILE.md §3>`, case-sensitive) and up to date; confirm the feature is actually deployed to the target env; record `git rev-parse --short HEAD` of the repo that owns the code under test in the Scope Lock "Build under test" row.

---

## Phase 1.5: Test Data Preparation + Mutation Safety Gate

**Test data -> `Skill(test-data-manager)`**: locate rich existing records matching the cases (prefer reuse); prepare + snapshot + restore only if needed, under the **Mutation Safety Gate** below.

Search the DB for rich existing test data with real relationships before testing; prefer disposable existing rows over creating new ones.

**Data resources — exhaust these before recording a coverage gap:** fixtures created through the application's own API (the typed tools in `PROJECT-PROFILE.md §14`, if any — they write every side table the way the app does; snapshot the returned ids for the restore), the sample-file library in `PROJECT-PROFILE.md §13` (if any) for upload / import cases, and a disposable local replica if `PROJECT-PROFILE.md §6` lists one. A fixture that does not exist is seeded under the gate rather than the case declared untestable. "Not found" is not "not present" (qa-standards -> Judgement Discipline #3): rule out search scope, naming, environment, feature flag and timing before writing BLOCKED.

**Mutation Safety Gate (qa-standards) — applies to ANY DB UPDATE/INSERT/DELETE AND ANY POST/PUT/PATCH/DELETE API call:**
1. Confirm the target is **in scope** (Scope Lock).
2. Prefer **existing disposable test data** over new rows.
3. **SELECT and log the original state first** (exact row, all columns you may touch).
4. Have a **rollback plan** before the write.
5. Never run destructive calls against **shared/prod** data. Prod DB is **read-only** — never mutate prod.
6. UPDATE/DELETE **must** have a WHERE. Never hard-DELETE — prefer status / `deleted_at` changes (confirm the column exists — `.claude/rules/db-gotchas.md`).
7. After the test, **verify** DB state and **restore**, then SELECT again to confirm. Log it:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

If rollback is impossible (no clean restore path) -> **STOP and ask the user** before mutating.

---

## Phase 2: Execute Test Cases

Work through cases by priority (P1 first). For each: PASS or FAIL with **Expected**, **Actual**, and an explicit verdict + evidence. Label the epistemic status when it changes the conclusion — VERIFIED FACT / STRONG INFERENCE / HYPOTHESIS / UNKNOWN (qa-standards -> Judgement Discipline #1).

### Step 1: Code Investigation
Read each related file — business logic, error handling, edge cases, security, cross-layer consistency. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md` for the layer. Investigation scope may be wide; the verdict stays inside the locked scope (Judgement Discipline #5).

### Step 2: Database Investigation
Query relevant tables via `mcp__mcp_server_mysql__mysql_query` — schema, data integrity, relationships, orphaned records. Read `COLUMN_COMMENT` / the model before judging a value. (Roles may live in a join / membership table rather than on `user` — see `.claude/rules/db-gotchas.md` and `PROJECT-PROFILE.md §10`.)

### Step 3: API Investigation
Test each endpoint via the §14 typed tools (if any), `mcp__http-client__*`, or `mcp__postman-api-mcp__*` — request/response, auth, RBAC, validation, error responses, FE consistency. Clear stale headers (`set_default_headers` merge:false) before auth. Test against the real wire, never a mock: the actual response body / file / event shape captured live in the target environment (Judgement Discipline #7).

### Step 4: Browser Validation
Test each UI flow via `mcp__playwright__*` — the **full** journey, not just the changed screen: page load, elements, actions, data display; capture console errors and network requests via `mcp__chrome-devtools__*` during every flow. **During the flow -> `Skill(observability-check)`**: surface console errors / failed-slow network / backend 5xx the UI hides (a clean-looking screen can still be failing under the hood).

**Path exercised (escape class E5):** a functional PASS is proven by the API call / DB write / job run that actually happened (network capture or DB row), never by a success toast or the presence of a control. **Input class (E4):** when the flow takes a file / import / upload, name the input class exercised and cover at least two classes from the sample-file library (`PROJECT-PROFILE.md §13`, if any). **Async flows (E8):** verify the terminal DB state, never the enqueue. Paginated surfaces beyond page 1; sortable columns in both directions (qa-standards -> Completion Gate).

**If the feature produces model-generated or computed numbers** (scores, recommendation picks, KPIs, report figures) -> `Skill(ai-output-eval)`: recompute them from the source records -> expected calculation -> API -> UI and locate any difference; check the edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope). Transcription (API = UI) proves transport, not correctness (Judgement Discipline #8).

**Keep it light:** for deep UI (visual / a11y) or a full regression pass, use `/full-qa`.

---

## Phase 3: Cross-Layer Data Consistency (MANDATORY)

For each entity under test, verify the same value agrees across DB -> API -> Browser. Mismatch = bug.

### Entity Reference *(illustrative — replace with `<key tables: PROJECT-PROFILE.md §10>` and this project's endpoints)*

| Entity | DB Table(s) | API Endpoint(s) |
|--------|------------|-----------------|
| User | `user`, `user_account` | `GET /api/<resource>/users` |
| Manager | `user`, `user_account` | `GET /api/<resource>/managers` |
| Account | `account`, `user_account` | `GET /api/accounts/:id` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Subscription | `subscription`, `invoice` | `GET /api/subscriptions/:id` |
| Model output / score | `audit_log`, snapshot tables (`PROJECT-PROFILE.md §11`) | `GET /api/<resource>/scores` |

### Check Process
For each entity: **A)** Query DB via `mcp__mcp_server_mysql__mysql_query` -> **B)** Call API via the §14 typed tool or `mcp__http-client__*` (or replay the FE request captured via `mcp__chrome-devtools__*`) -> **C)** Check browser via `mcp__playwright__*` -> **D)** Compare in a table:

```
| Field | DB Value | API Value | Browser Value | Match? |
```

### Consistency Types to Check
Value, count, status, date/time format, null handling, soft-delete filtering, FK resolution, aggregation, ordering, pagination. Partially-empty beats empty: `0`, `false`, `null`, `""`, `[]`, missing key, no rows, Loading, 401/403 are DIFFERENT states — the row that exists with one field absent is where defects live (Judgement Discipline #2).

### On Mismatch -> Bug
If actual data mismatch (not just format), classify (FE / BE / Admin / Report / DB / Both per qa-standards), verify with `Skill(bug-verifier)` before it counts, then file via `Skill(bug-report)` with values from each layer and root-cause `path:line`. **No DB/API/Browser comparison = no cross-layer claim.** A shared component fixed is not every consumer fixed — each consumer named in scope is its own register row (Judgement Discipline #4).

---

## Evidence Ledger (REQUIRED in the final report)

Every finding (bug OR proof-of-correct) maps to >=1 evidence row. **No evidence = no finding. No reproduction = no confirmed bug.** Save proof for PASS too. Stamp provenance on every row (qa-standards -> Evidence provenance) — a result observed on DEV / a replica / PROD is evidence for THAT environment only.

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

Attachments live under `qa-evidence/<APP-nnn or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/`. Write them via `mcp__filesystem__write_file` (the read-only hook blocks `Write`/`Edit` for `qa-evidence/`); pass `filename: qa-evidence/<run folder>/<name>.png` to Playwright screenshots (a bare filename saves to the repo root). Findings/reports stay in the chat, not as markdown in `qa-evidence/`.

## Plugins & escalation (optional enhancers — `PROJECT-PROFILE.md §17`)
- Non-obvious root cause after the cross-layer pass -> if the `superpowers` plugin is installed, `superpowers:systematic-debugging`; otherwise by hand: write 3-5 ranked, falsifiable hypotheses, change one variable at a time, and accept a cause only when a reproduction confirms it.
- Before declaring ready / PASS -> if installed, `superpowers:verification-before-completion`; otherwise by hand: re-run the qa-standards Completion Gate checklist and Verdict Integrity #1-8 against your own conclusions, and quote the evidence row behind every PASS.
- Ambiguous or missing acceptance criteria with the owner present -> if the `mattpocock-skills` plugin is installed, `Skill(mattpocock-skills:grilling)` (numbered rounds, each question with a recommended answer; facts are looked up in-session); otherwise by hand: list the ambiguities as numbered questions with your recommended reading, ask, and cite each answer as the source of its expected result. Owner absent: record the ambiguity as an open question, take the code-derived reading, label it INFERRED.

---

## Deliverables

> Moved to [`references/deliverables.md`](references/deliverables.md). Read it before writing the result: the report sections, the register and ledger tables and the ready / not-ready alias rule come from there.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate. If today's evidence DISPROVES a fact in an older memory, mark that older file SUPERSEDED in the same session (qa-standards -> Memory Ritual).
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title> YYYY-MM-DD](<file>.md) — <hook>` (the date in the link title is the knowledge-decay gate, escape class E13).
4. **Content:** feature + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), audit result, bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/accounts), root-cause `path:line`, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
