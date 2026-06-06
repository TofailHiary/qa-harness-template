---
name: regression-runner
description: Use when a change has just landed and you need to guard its INDIRECT blast radius — the shared components, endpoints, tables, cron/Lambda jobs, caches, and downstream reports the change touches but is not "about". Triggers include "run a regression after this PR", "did this change break anything nearby", "regression-runner on APP-xxx", "check the blast radius still works", or Phase-8 regression coverage. NOT for testing the changed feature itself — reach for /full-qa or /qa-validate for that.
argument-hint: "the change/PR/feature whose blast radius to regression-test (+ its indirect areas if known)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__http-client__*", "mcp__postman-api-mcp__*", "mcp__github__*", "Skill(qa-standards)", "Skill(pr-risk-analyzer)", "Skill(browser-test)", "Skill(api-test)", "Skill(db-check)", "Skill(bug-verifier)"]
---

# Regression Runner — Guard the Indirect Blast Radius

After a change lands, run a FOCUSED regression over what the change touches *indirectly* — the shared FE components, shared API endpoints, shared DB tables, async consumers, caches, and downstream reports — NOT the changed feature itself. This is exactly where "obvious" bugs hide: the diff was reviewed, the feature works, and a sibling that quietly reuses the same component/endpoint/table breaks unnoticed.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What change/PR/feature should I run a regression around, and what does it touch (changed component / endpoint / table / report)? I regression-test the INDIRECT blast radius — the shared things the change reuses — not the changed feature itself."

Do NOT guess the change from conversation. Do NOT regression-test the whole platform. Do NOT run a single query/call/click until the blast radius is locked.

---

## Rules
1. Use extended thinking proportional to blast-radius size.
2. **Scope = the INDIRECT blast radius, not the diff.** The changed feature is assumed already validated (by /full-qa or its PR review); this skill guards everything *downstream and adjacent*.
3. No assumptions — every "still works" needs a baseline and an actual. Code is truth.
4. Every cell of the regression matrix maps to >=1 Evidence Ledger row. No evidence = no finding; capture proof for PASS too.
5. A difference from the expected baseline is a **regression candidate** — confirm it with `Skill(bug-verifier)` BEFORE it counts as a bug (rules out stale data / cache / env).
6. This skill is read-only by default. If a check needs a write, the Mutation Safety Gate applies (below).
7. Track each indirect area as a TodoWrite task; close it only when its matrix row has a Pass/Fail + evidence.

---

## Scope Lock (REQUIRED — before any tool runs)

Output this contract first. The "Indirect blast radius" row IS the scope here — fill it from Step 1. Ask if the change/baseline is unknown; do not guess.

| Field | Value |
|---|---|
| Change / PR / feature that landed | |
| QA mode | regression (default) / bugfix |
| Direct area (the changed feature — OUT of scope here, validated elsewhere) | |
| **Indirect blast radius (THE scope)** | shared FE components / shared endpoints / shared tables / async consumers / caches & snapshots / downstream reports |
| Roles touched by the indirect areas | Admin / Manager / User / Guest |
| Baseline source (expected values) | prod / pre-change snapshot / spec / known-good run |
| Environment | Test (default) / Dev / Prod (read-only) |
| Risk level | Low / Medium / High |
| Stop conditions | change not deployed / baseline unknowable / wrong branch / auth fails |

Do not silently narrow the blast radius to make a PASS easier; if you drop an indirect area, say so and why.

---

## Step 1: Enumerate the indirect blast radius

Take the blast radius from `Skill(pr-risk-analyzer)` output if it ran this session; otherwise derive it via qa-standards -> Impact Analysis. Trace each outward and list concrete targets (file / endpoint / table / job / report):

- **Shared FE components** — is the changed component imported on other pages? `Grep` its imports / `mcp__github__search_code`. Each other page that renders it is an indirect area.
- **Shared API endpoints** — do other features call the same route (different params/roles)? List each caller.
- **Shared DB tables/columns** — what else reads/writes this table? Other endpoints, dashboards, exports, aggregates.
- **Async consumers** — cron, Lambda (order processing / report / recommendation), SQS, S3 events, email triggered off the same data.
- **Caches & snapshots** — React Query keys, snapshot tables (`PROJECT-PROFILE.md §11`) snapshots, materialized aggregates that can drift from live data.
- **Downstream reports/exports** — CSV columns, dashboards (online vs offline scope), printed/PDF outputs.

Feed every concrete target into the Scope Lock "Indirect blast radius" row and into the matrix below. **A change is in scope plus everything this surfaces.**

## Step 2: Pick the smallest proving check per area

For each indirect area, run the *smallest* check that proves it still works — delegate to the specialist:
- A UI flow renders/clicks/submits -> `Skill(browser-test)` (capture console + network during the flow).
- An endpoint still returns the right shape/data for the right role -> `Skill(api-test)`.
- A row count / aggregate / FK still reconciles -> `Skill(db-check)`.

Prefer the cheapest layer that detects breakage (a DB count beats a full UI walk when the risk is data). Run independent area-checks in parallel where they share no state.

## Step 3: Compare to baseline

Each check has an **Expected** value from the baseline source (prod value, pre-change snapshot, spec, or known-good run). Run the check, record the **Actual**, and diff:
- Actual == Expected -> **Pass** (still capture evidence — a green needs proof it ran).
- Actual != Expected -> **regression candidate**. Do NOT count it yet — hand to `Skill(bug-verifier)` to rule out stale data, caching, env, or a wrong baseline. Only a CONFIRMED candidate becomes a Fail/bug.

## Step 4: Output the regression matrix + ledger

### Regression matrix (the core deliverable)

| Indirect area | Check | Expected (baseline) | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|---|

One row per concrete target from Step 1. Every Fail row links to its `bug-verifier` verdict and an Evidence ID. An area with no row is an untested area — name it as a coverage gap, never an implied pass.

### Evidence Ledger (REQUIRED — `No evidence = no finding`)

Every matrix row (Pass and Fail) maps to >=1 ledger row.

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

Allowed types: DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), Postman contract, GitHub diff/commit. Save attachments under `qa-evidence/<CHANGE-SLUG>-regression/` via `mcp__filesystem__write_file` or Bash heredoc (the Write/Edit tool is hook-blocked for `qa-evidence/`); Pass `filename: qa-evidence/<CHANGE-SLUG>-regression/<name>.png` to Playwright screenshots (a bare filename saves to the repo root). Findings stay in chat, not as markdown in `qa-evidence/`.

### Verdict (strict binary — user policy 2026-05-04)
- **PASS (no regression)** — every in-scope indirect area matched its baseline; 0 confirmed regression bugs.
- **REGRESSION FOUND** — 1+ confirmed regression bugs (any area, any severity). Each goes to `Skill(bug-report)` with its layer classification.
- **PARTIAL** — a stop condition halted an area before it could be checked (name it). No "conditional pass"; an untested area is a coverage gap, not a pass.

---

## Mutation Safety Gate — before any write
Read-only by default. If an area-check genuinely needs a write, the full 7-step gate applies (qa-standards -> Mutation Safety Gate): in-scope -> prefer disposable test data -> **SELECT + log original first** -> rollback plan -> never mutate prod -> WHERE on every UPDATE/DELETE, never hard-DELETE -> restore + SELECT again to confirm. No clean restore path -> STOP and ask. Log it:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

---

## Superpowers escalation
A large independent fan-out across many indirect areas -> `superpowers:dispatching-parallel-agents` (or the `qa-team` skill). A confirmed regression whose root cause is non-obvious after the cross-layer pass -> `superpowers:systematic-debugging`. Before declaring PASS/no-regression -> `superpowers:verification-before-completion` (evidence before assertions).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the change / component / endpoint / table / report; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** change + date, verdict (PASS / REGRESSION FOUND / PARTIAL), **which indirect blast-radius areas were regression-tested and each area's result** (so the next session knows what was already guarded), confirmed regression bugs (ID, severity, layer, NEW/DUPLICATE), baseline source + test data (IDs/emails), root-cause `path:line`, indirect areas left untested (carried-forward gaps), any prior memory this run disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.
