---
name: regression-runner
description: Use when a change has just landed and you need to guard its INDIRECT blast radius — the shared components, endpoints, tables, cron/Lambda jobs, caches, and downstream reports the change touches but is not "about". Triggers include "run a regression after this PR", "did this change break anything nearby", "regression-runner on APP-xxx", "check the blast radius still works", or Phase-8 regression coverage. NOT for testing the changed feature itself — reach for /full-qa or /qa-validate for that.
argument-hint: "the change/PR/feature whose blast radius to regression-test (+ its indirect areas if known)"
allowed-tools: ["Agent", "Agent(qa-verdict-auditor)", "Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__http-client__*", "mcp__postman-api-mcp__*", "mcp__github__*", "Skill(qa-standards)", "Skill(pr-risk-analyzer)", "Skill(browser-test)", "Skill(api-test)", "Skill(db-check)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# Regression Runner — Guard the Indirect Blast Radius

> **Capability gate:** This skill is **always on** (orchestrator — it never hard-stops). Before doing
> anything, read `PROJECT-PROFILE.md` §2 (Capability Map) and pick only checks whose capability is
> `on`: no **Browser** -> no `browser-test` checks; no **API** -> no `api-test` checks; no **DB** ->
> no `db-check` checks; no **GitHub** / **LocalRepos** -> the blast radius comes from the user or a
> prior `pr-risk-analyzer` run, not from grepping code. An indirect area whose only proving check
> needs an `off` capability is stated in the verdict ("area X not checked: DB capability off") and
> its Execution Register row reads NOT YET VERIFIED — never PASS. If `PROJECT-PROFILE.md` is blank,
> STOP and tell the user to run `/configure-project`.

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
5. A difference from the expected baseline is a **regression candidate** — confirm it with `Skill(bug-verifier)` BEFORE it counts as a bug (rules out stale data / cache / env / wrong baseline).
6. This skill is read-only by default. If a check needs a write, the Mutation Safety Gate applies (below).
7. Track each indirect area as a TodoWrite task; close it only when its matrix row has a Pass/Fail + evidence and its register row has a Result.
8. The verdict uses the canonical words of qa-standards -> Verdict Contract and is independently audited BEFORE it is stated.

---

## Scope Lock (REQUIRED — before any tool runs)

Output this contract first. The "Indirect blast radius" row IS the scope here — fill it from Step 1. Ask if the change/baseline is unknown; do not guess. (The six questions in qa-standards are recommended before locking: what is requested / authoritative / verifiable / assumed / required as evidence / completion.)

| Field | Value |
|---|---|
| Change / PR / feature that landed | |
| QA mode | regression (default) / bugfix |
| Direct area (the changed feature — OUT of scope here, validated elsewhere) | |
| **Indirect blast radius (THE scope)** | shared FE components / shared endpoints / shared tables / async consumers / caches & snapshots / downstream reports |
| Roles touched by the indirect areas | <roles: PROJECT-PROFILE.md §8> — e.g. Admin / Manager / User / Guest |
| Baseline source (expected values) | prod (read-only, if Prod-DB is on) / pre-change snapshot / spec / known-good run |
| Environment | Test (default) / Dev / Prod (read-only) |
| Build under test | `<branch: PROJECT-PROFILE.md §3> @ <short sha>` — capture once, reuse in every Evidence Ledger row |
| Risk level | Low / Medium / High |
| Stop conditions | change not deployed / baseline unknowable / wrong branch / auth fails |

Do not silently narrow the blast radius to make a PASS easier; if you drop an indirect area, say so and why.

---

## Run record & resume (`run.json`)
Keep `qa-evidence/<run-folder>/run.json` (`qa-standards/references/run-record.md`): create it at Scope Lock
(one register row per in-scope area, NOT YET VERIFIED until run, plus the Step 1b matrix), update it after
every phase (that update is the checkpoint), and if it already exists with `checkpoint.next_step` set,
RESUME from that step and say so. Before the verdict,
`python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>` must exit 0 - it
recomputes the confidence line and the run verdict; never type them by hand. `--package` then writes the
`package.md` the independent audit reads.

## Step 1: Enumerate the indirect blast radius

Take the blast radius from `Skill(pr-risk-analyzer)` output if it ran this session; otherwise derive it via qa-standards -> Impact Analysis. Trace each outward and list concrete targets (file / endpoint / table / job / report):

- **Shared FE components** — is the changed component imported on other pages? `Grep` its imports / `mcp__github__search_code`. Each other page that renders it is an indirect area.
- **Shared API endpoints** — do other features call the same route (different params/roles)? List each caller.
- **Shared DB tables/columns** — what else reads/writes this table? Other endpoints, dashboards, exports, aggregates.
- **Async consumers** — cron, serverless functions, queues, storage events, email triggered off the same data (`PROJECT-PROFILE.md §11`). Trace the chain to its terminal writer — the owner of a regression may be a job, not FE/BE/Admin (escape class E7).
- **Caches & snapshots** — client-side cache keys, snapshot tables (`PROJECT-PROFILE.md §11`), materialized aggregates that can drift from live data.
- **Downstream reports/exports** — CSV columns, dashboards (online vs offline scope), printed/PDF outputs.

Feed every concrete target into the Scope Lock "Indirect blast radius" row and into the matrix below, and give each one a register row ID now so none can vanish later. **A change is in scope plus everything this surfaces.** A shared component fixed is not every consumer fixed — each consumer is its own row (qa-standards -> Judgement Discipline #4).

## Step 2: Pick the smallest proving check per area

For each indirect area, run the *smallest* check that proves it still works — delegate to the specialist:
- A UI flow renders/clicks/submits -> `Skill(browser-test)` (capture console + network during the flow).
- An endpoint still returns the right shape/data for the right role -> `Skill(api-test)` (prefer the typed tools in `PROJECT-PROFILE.md §14` if any; otherwise `mcp__http-client__*`).
- A row count / aggregate / FK still reconciles -> `Skill(db-check)`.
- An async consumer still produces its output -> trigger (or wait for) the job and verify the **terminal DB state**, never the enqueue (E8).

Prefer the cheapest layer that detects breakage (a DB count beats a full UI walk when the risk is data). **The check must exercise the path (E5):** a functional "still works" names the API call / write / job run observed, never the presence of a control or a success toast. Run independent area-checks in parallel where they share no state — via sub-agents only if `PROJECT-PROFILE.md §16` allows them (then `superpowers:dispatching-parallel-agents` describes the fan-out if the plugin is installed, `§17`; otherwise one message, one self-contained brief per lane); otherwise sequentially in-session. Sub-agent reports are leads, and agreement between your own lanes is ONE source (qa-standards -> Verdict Integrity #5, #7).

## Step 3: Compare to baseline

Each check has an **Expected** value from the baseline source (prod value via the read-only access in `PROJECT-PROFILE.md §6`, pre-change snapshot, spec, or known-good run). Run the check, record the **Actual**, and diff:
- Actual == Expected -> **Pass** (still capture evidence — a green needs proof it ran).
- Actual != Expected -> **regression candidate**. Do NOT count it yet — hand to `Skill(bug-verifier)` to rule out stale data, caching, env, or a wrong baseline. Only a CONFIRMED candidate becomes a Fail/bug.
- A baseline from memory or an old run is a lead, not evidence (qa-standards -> Fresh vs Historical): re-derive it this run where the source allows, and label it when you cannot.

Partially-empty beats empty: `0`, `null`, `""`, `[]`, missing key, no rows and Loading are different states — the row that exists with one field absent is where regressions hide (Judgement Discipline #2).

## Step 4: Output the regression matrix + register + ledger

### Regression matrix (the core deliverable)

| Indirect area | Check (path exercised) | Expected (baseline + source) | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|---|

One row per concrete target from Step 1. Every Fail row links to its `bug-verifier` verdict and an Evidence ID. An area with no row is an untested area — name it as a coverage gap, never an implied pass.

### Execution Register (REQUIRED — one row per Scope Lock area, no exceptions)

| ID | Area | Requirement / AC | Check performed | Result | Evidence ID | Finding |
|---|---|---|---|---|---|---|

`Result` is one of the five canonical values (`qa-standards` -> Verdict Contract: PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED). **Every area named in the Scope Lock gets exactly one row.** An area with no row is a silent omission — the single highest cause of a confident wrong verdict. Never delete a row to make a run look clean: mark it NOT YET VERIFIED and say what is missing. BLOCKED needs the reason and what would unblock it; an operational blocker (port closed, credentials not tried) must be attempted first.

### Evidence Ledger (REQUIRED — `No evidence = no finding`)

Every matrix row (Pass and Fail) maps to >=1 ledger row, stamped with provenance (qa-standards -> Evidence provenance) — a result observed on DEV / a replica / PROD is evidence for THAT environment only.

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

Allowed types: DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), Postman contract, GitHub diff/commit. Save attachments under `qa-evidence/<APP-nnn or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` via `mcp__filesystem__write_file` or Bash heredoc (the Write/Edit tool is hook-blocked for `qa-evidence/`); pass `filename: qa-evidence/<run folder>/<name>.png` to Playwright screenshots (a bare filename saves to the repo root). Findings stay in chat, not as markdown in `qa-evidence/`.

### Independent audit (REQUIRED before the verdict is stated)

Hand over ONLY the package — Scope Lock, baseline sources, every finding (fails AND passes), the Evidence Ledger, the **Execution Register** and the proposed verdict — never your reasoning or transcript.
- Sub-agents allowed (`PROJECT-PROFILE.md §16`): dispatch `qa-verdict-auditor` via the `Agent` tool with the path of `qa-evidence/<run-folder>/package.md` (from `verdict_check.py --package`) - a judge, not a second QA run.
- Sub-agents disabled (§16): audit in-session — re-derive the verdict from the package alone, item by item against qa-standards -> Verdict Integrity #1-8 and the Completion Gate; write `AUDIT_PASSED` / `AUDIT_FAILED`.
`AUDIT_FAILED` -> you may NOT state the verdict; resolve each challenge with evidence, then re-audit if findings moved. Its challenges are leads: reproduce first-hand anything you act on (qa-standards -> Verdict Integrity #7). Record that the audit ran, and how.

### Verdict — per qa-standards -> Verdict Contract (policy: `PROJECT-PROFILE.md §16`, default strict binary)
**GO** ("no regression" may follow in parentheses: every in-scope indirect area matched baseline, 0 confirmed regression bugs, 0 NOT YET VERIFIED rows in mandatory scope) / **NO-GO** ("regression found": 1+ confirmed regression bugs, any area, any severity — each to `Skill(bug-report)` with its layer classification) / **PARTIAL** (a stop condition halted an area — name it). No "conditional pass"; an untested area is NOT YET VERIFIED, never a pass. Confidence line mandatory: `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: <one line or "none">`. When the run finds nothing, state which escape classes (qa-standards -> Escape classes & their gates) were actively checked — an unchecked class is a NOT YET VERIFIED row, not silence. Banned in verdict lines: *seems fine, probably, should work, looks correct, most likely, I assume, apparently*.

---

## Mutation Safety Gate — before any write
Read-only by default. If an area-check genuinely needs a write, the full 7-step gate applies (qa-standards -> Mutation Safety Gate): in-scope -> prefer disposable test data -> **SELECT + log original first** -> rollback plan -> never mutate prod -> WHERE on every UPDATE/DELETE, never hard-DELETE -> restore + SELECT again to confirm. No clean restore path -> STOP and ask. Log it:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

---

## Plugins & escalation (optional enhancers — `PROJECT-PROFILE.md §17`)
- A large independent fan-out across many indirect areas -> `superpowers:dispatching-parallel-agents` if the `superpowers` plugin is installed (or the `qa-team` skill) — only when `PROJECT-PROFILE.md §16` allows sub-agents; otherwise sequential in-session.
- A confirmed regression whose root cause is non-obvious after the cross-layer pass -> `superpowers:systematic-debugging` if installed; otherwise by hand: 3-5 ranked falsifiable hypotheses, one variable at a time, accept only a reproduced cause.
- Before declaring GO / no-regression -> `superpowers:verification-before-completion` if installed; otherwise by hand: re-run the qa-standards Completion Gate checklist and Verdict Integrity #1-8 against your own conclusions and quote the evidence row behind every PASS.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the change / component / endpoint / table / report; UPDATE an existing entry instead of filing a duplicate. If today's evidence DISPROVES a fact in an older memory, mark that older file SUPERSEDED in the same session (qa-standards -> Memory Ritual).
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title> YYYY-MM-DD](<file>.md) — <hook>` (date in the link title — escape class E13).
4. **Content:** change + date + build, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), audit result, **which indirect blast-radius areas were regression-tested and each area's result** (so the next session knows what was already guarded), confirmed regression bugs (ID, severity, layer, NEW/DUPLICATE), baseline source + test data (IDs/accounts), root-cause `path:line`, indirect areas left untested (carried-forward gaps), any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
