---
name: full-qa
description: Use when a feature, user story, PR, bug fix, or release needs complete multi-layer QA validation ending in a GO/NO-GO verdict. The master orchestrator — runs the full cross-layer cycle and delegates to the specialist QA skills. Triggers include "full QA", "validate this story/PR", "run the QA cycle", "sign off this release".
argument-hint: "user story, feature, PR, or release to fully validate"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Agent", "Skill(qa-standards)", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(test-cases-generator)", "Skill(code-review)", "Skill(db-check)", "Skill(api-test)", "Skill(browser-test)", "Skill(visual-regression)", "Skill(a11y-test)", "Skill(observability-check)", "Skill(security-review)", "Skill(perf-test)", "Skill(regression-runner)", "Skill(bug-verifier)", "Skill(bug-report)", "Skill(qa-report)"]
---

# Full QA Cycle — Master Orchestrator

Complete end-to-end QA validation across all layers, ending in a binary GO/NO-GO verdict.

**Follows the shared standard.** Read `.claude/skills/qa-standards/SKILL.md` once at the start of the session (Modes, Scope Lock, Impact Analysis, Evidence Ledger, Mutation Gate, MCP routing, Memory ritual). The safety-critical gates are inlined below; the rest lives there.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What feature, user story, PR, or release should I run /full-qa on? (e.g. 'APP-282 breadcrumb truncation' or 'PR #112 Auto-Closer'). Which QA mode — smoke / targeted / regression / bugfix / full / release?"

Do NOT guess scope from conversation. Do NOT enumerate the whole platform. Do NOT run any phase until scope is known.

---

## Rules
1. Use extended thinking for every phase in scope.
2. No assumptions — verify with actual data and behavior. Code is truth.
3. **Validate the full user flow and the blast radius, not just the diff** (Step 0b Impact Analysis). This is the #1 cause of missed bugs.
4. Generate test cases BEFORE testing (Phase 0).
5. Every finding — bug OR pass — needs an Evidence Ledger row. No evidence = no finding.
6. Delegate to specialist sub-skills (Phases 0b-8); the orchestrator coordinates and triangulates, it does NOT duplicate their work. Conditional sub-skills (visual-regression, a11y-test) fire only when the scope calls for them.
7. Each phase completes before the next, EXCEPT a hard blocker (feature undeployed, schema missing, wrong branch, auth fails) -> exit early with a PARTIAL verdict naming the blocker.
8. Track progress with TodoWrite throughout.

---

## Step 0a: QA Mode + Scope Lock (REQUIRED — before any tool runs)

Pick the **QA mode** (qa-standards -> QA Modes). If the user didn't state one, infer the smallest mode that covers the request and say which. Then output the **Scope Lock** table and do not run a single query/call/click until it is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Feature / story / bug / PR | |
| QA mode | smoke / targeted / regression / bugfix / full / release |
| Roles in scope | Admin / Manager / User / Guest / Other |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | |
| Direct dependents | (Step 0b) |
| Indirect blast radius | (Step 0b) |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Risk level | Low / Medium / High |
| Stop conditions | |

## Step 0b: Impact Analysis (REQUIRED for regression / bugfix / release; recommended always)

Before generating cases, trace the blast radius per qa-standards -> Impact Analysis: shared FE components (grep imports), shared API endpoints, shared DB tables/columns, async consumers (cron/Lambda/SQS/S3/email), caches & report snapshots, downstream reports/exports. Feed the results into the Scope Lock "Indirect blast radius" row and into Phase 0 cases. **A change is in scope plus everything this surfaces.**

If the source is a Jira ticket, pull acceptance criteria via `mcp__claude_ai_Atlassian__*`.

**If the scope is a PR / commit / branch -> `Skill(pr-risk-analyzer)`** for the formal blast-radius risk map; feed its impact map into the Scope Lock "Indirect blast radius" row and into Phase 0 cases.

---

## Reusable Reference: Cross-Layer Data Consistency

For each entity tested, verify the value agrees across DB -> API -> Browser (full table in qa-standards). On mismatch -> bug.

| Entity | DB table(s) | API endpoint(s) |
|--------|------------|------------------|
| User / Manager | `user`, `user_account` | `GET /api/<resource>/users` |
| Account | `account`, `user_account` | `GET /api/accounts/:id` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Subscription | `subscription`, `invoice` | `GET /api/subscriptions/:id` |
| Model output / score | `audit_log`, snapshot tables (PROJECT-PROFILE.md §11) | `GET /api/<resource>/scores` |

Compare in a table: `| Field | DB | API | Browser | Match? |`.

---

## Phase 0: Test Case Generation
0. **Cross-check memory** — Grep `~/.claude/projects/c--Users-<user>-<project>/memory/*.md` for the feature/story, ticket/BUG- IDs, file paths, entity IDs. Load matches as known regression-risk areas. Skip re-verifying bugs already CONFIRMED+CLOSED unless asked.
1. Delegate to `Skill(test-cases-generator)` for the scope + the Step 0b blast radius. Cases must cover positive, negative, boundary, DB integrity, API, UI, security, regression, E2E, data-consistency — and every cell of the coverage matrix (roles, states, inputs, flow, cross-tenant).
2. Present the summary table (count/priority per category) and create TodoWrite tasks (P1 first).

## Phase 1: Pre-flight & Test Data
1. **Pre-flight -> `Skill(env-health)`**: MCP servers reachable, repos on the correct branch (case-sensitive) + current, portals/DB/auth up, **and the feature actually deployed** to the target env. A RED item is a stop condition -> PARTIAL. (May run first, before Phase 0, to avoid building cases for a dead env.)
2. **Test data -> `Skill(test-data-manager)`**: locate rich existing records matching the cases (prefer reuse); prepare + snapshot + restore under the **Mutation Safety Gate** only if needed (SELECT + log original, WHERE on every UPDATE, restore + verify, never mutate prod).

## Phase 2: Code Review
Delegate to `Skill(code-review)` for the changed code + the Step 0b blast radius. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md` for the layer.

## Phase 3: Database Validation
Delegate to `Skill(db-check)` for the entities in scope. (Schema vs ORM model, FK integrity, orphans, consistency, indexes.)

## Phase 4: API Testing
Delegate to `Skill(api-test)` for the enumerated endpoints. (Auth, RBAC, validation, errors, schema, DB-write consistency, mutation safety.)

**If the feature produces AI/ML-generated numbers** (scores, recommendation picks, KPIs, report figures): recompute them vs their source data and check for edge cases (falsy-zero, randomness in source-record selection, snapshot-vs-live scope).

## Phase 5: UI/E2E + Cross-Layer
- Delegate to `Skill(browser-test)` for the pages/flows — the **full** journey, not just the changed screen; capture console + network during every flow.
- **Always during the flows -> `Skill(observability-check)`**: surface console errors / failed-slow network / backend 5xx the UI hides (a clean-looking screen can still be failing under the hood).
- **If the change touches UI -> `Skill(visual-regression)`** (layout / overflow / truncation / responsive across breakpoints) **+ `Skill(a11y-test)`** (keyboard / ARIA / focus / WCAG contrast).
- **Orchestrator only:** triangulate DB -> API -> Browser per the reference above (only the orchestrator has all three sets of outputs).

## Phase 6: Security Review
Delegate to `Skill(security-review)` — 10-point audit (auth, RBAC, injection, XSS, CSRF, data exposure, API security, headers, sessions).

## Phase 7: Performance
Delegate to `Skill(perf-test)`. Thresholds: page load <3s PASS / 3-5s WARN / >5s FAIL; API P95 <500ms PASS / <1s WARN / >1s FAIL; payload/page <500KB / <2MB / over; console errors 0 = PASS else FAIL. Any FAIL -> bug.

## Phase 7b: Regression (regression / bugfix / release modes)
In those modes -> `Skill(regression-runner)` over the Step 0b indirect blast radius — actively re-test the shared components / endpoints / tables / reports the change touches but is not "about". (In `full` mode this is already covered by the Phase 0 regression cases.)

## Phase 8: Verify, Report
1. **Verify every suspected bug** with `Skill(bug-verifier)` BEFORE it counts — no unverified bug enters the verdict. Confirmed bugs -> `Skill(bug-report)`.
2. Delegate to `Skill(qa-report)` to compile the standardized report. It MUST include the **Evidence Ledger** (qa-standards) — every finding and every PASS maps to an evidence row. Use `Skill(evidence-manager)` to file + name the attachments and assemble the ledger.

### Verdict (MANDATORY — strict binary)
- **GO** — exactly 0 bugs found across all phases (any layer, any severity).
- **NO-GO** — 1+ bugs found, regardless of severity.
- **PARTIAL** — a hard blocker stopped a phase (name it).

No "Conditional GO". No severity weighting. Bugs exist or they don't (user policy 2026-05-04 — severity/release calls are downstream). State any coverage gaps explicitly; an untested dimension is never an implied PASS.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** feature + date, verdict (GO/NO-GO/PARTIAL), bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/emails), root-cause `path:line`, regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
