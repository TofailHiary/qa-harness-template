---
name: full-qa
description: Use when a feature, user story, PR, bug fix or release needs complete multi-layer QA validation ending in a GO/NO-GO verdict, delegating to the specialist QA skills. Triggers include "full QA", "validate this story/PR", "run the QA cycle", "sign off this story". For a whole release use /release-check.
argument-hint: "user story, feature, PR, or release to fully validate (plus the QA mode if known)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Agent", "Skill(prompt-generator)", "Skill(qa-standards)", "Skill(env-health)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(test-cases-generator)", "Skill(code-review)", "Skill(db-check)", "Skill(api-test)", "Skill(ai-output-eval)", "Skill(latent-pattern-sweep)", "Skill(browser-test)", "Skill(visual-regression)", "Skill(a11y-test)", "Skill(observability-check)", "Skill(security-review)", "Skill(perf-test)", "Skill(regression-runner)", "Skill(bug-verifier)", "Skill(bug-report)", "Skill(qa-report)", "Skill(evidence-manager)", "Write"]
---

# Full QA Cycle — Master Orchestrator

> **Capability gate:** This orchestrator is always on. Read `PROJECT-PROFILE.md` §2 (Capability Map)
> first and **skip every phase whose capability is `off`** (no DB → skip Phase 3 and the DB side of
> cross-layer checks; no Browser → skip Phase 5 UI/visual/a11y; no GitHub/LocalRepos → skip Phase 2
> and pr-risk-analyzer; no Jira/tracker → read the acceptance criteria from the user). **Every skipped
> phase is named in the verdict as a coverage gap** — never an implied PASS. If nothing is configured,
> stop and tell the user to run `/configure-project`.

Complete end-to-end QA validation across all layers, ending in a run verdict under the project's
verdict policy (`PROJECT-PROFILE.md §16`; default strict binary GO / NO-GO / PARTIAL).

**Follows the shared standard.** Read `.claude/skills/qa-standards/SKILL.md` once at the start of the session (Modes, Scope Lock, Impact Analysis, Evidence Ledger, Mutation Gate, MCP routing, Completion Gate, Verdict Contract, Escape classes, Memory ritual). The safety-critical gates are inlined below; the rest lives there.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What feature, user story, PR, or release should I run /full-qa on? (e.g. 'APP-282 breadcrumb truncation' or 'PR #112 order auto-closer'). Which QA mode — smoke / targeted / regression / bugfix / full / release?"

Do NOT guess scope from conversation. Do NOT enumerate the whole platform. Do NOT run any phase until scope is known.

---

## Rules
1. Use extended thinking for every phase in scope.
2. No assumptions — verify with actual data and behavior. Code is truth.
3. **Validate the full user flow and the blast radius, not just the diff** (Step 0b Impact Analysis). This is the #1 cause of missed bugs.
4. **Step 0 first, then Phase 0.** The run starts from the prompt that `prompt-generator` produced (Step 0); test cases are generated BEFORE testing (Phase 0).
5. Every finding — bug OR pass — needs an Evidence Ledger row. No evidence = no finding.
6. Delegate to specialist sub-skills (Phases 0b-8); the orchestrator coordinates and triangulates, it does NOT duplicate their work. Conditional sub-skills (ai-output-eval, latent-pattern-sweep, visual-regression, a11y-test) fire only when the scope calls for them.
7. Each phase completes before the next, EXCEPT a hard blocker (feature undeployed, schema missing, wrong branch, auth fails) -> exit early with a PARTIAL verdict naming the blocker.
8. **Every generated case is executed** unless `PROJECT-PROFILE.md §16` says otherwise. No sampling by priority, no "P1 first and stop", no "time did not allow". Priority only orders the work. Every case ends as a register row with a canonical Result and an evidence id.
9. Track progress with TodoWrite throughout.

---

## Step 0: Prompt Generator (REQUIRED — the very first step, before the six questions)

`Skill(prompt-generator)` with `$ARGUMENTS`. It researches the request against this setup (live ticket from the tracker in `PROJECT-PROFILE.md §15`, memory, prior evidence, code on the target branch, DB shape, fixtures, armed risks from `.claude/references/system-map.md`, hooks) and returns ONE execution-ready prompt. That prompt is the charter of this run; nothing below starts until it exists.

How the rest of the cycle consumes it:
- **Step 0a** takes the Scope Lock from the prompt's Scope section and writes out the six questions from its "Six questions" block (fill gaps; never narrow silently).
- **Step 0b** starts from the prompt's impact map; `pr-risk-analyzer` still runs for a PR and may only widen it.
- **Phase 0** expands the prompt's requirement register and combination matrix into cases; `test-cases-generator` keeps the prompt's IDs and derives `M` from the code (its Step 1b), never from the prompt's row count.
- **Phase 1** turns every Research Register row marked UNKNOWN / RETRIEVE into a check (deploy state, missing fixture, open question); a row that cannot be closed becomes a named coverage gap or a stop condition, never silence.
- **Run with block:** if it recommends `/goal`, give the user the exact line to type before Phase 0 (interactive) or run `claude -p "/goal …"` unattended; if it recommends `/loop`, run the loop exactly as written (what repeats, what each iteration validates, the stop condition); "neither" with a reason is a valid answer. One goal per session; a loop and a goal are not combined.
- The prompt copy lives at `qa-evidence/<run-folder>/00-prompt-<subject>.md`; later attachments sit beside it.

If the generator cannot fill its Research Register (tracker unreachable, repo missing), it says so and Step 0a proceeds with those rows as stop conditions. The generator never runs a test and never changes a ticket.

## Step 0a: QA Mode + Scope Lock (REQUIRED — after Step 0, before any tool runs)

**Six questions first** (qa-standards → *Before the first tool call*): write them out explicitly — what is requested / what is authoritative / what can be verified / which assumptions are eliminated / what evidence is required / what completion means — before running any tool.

Pick the **QA mode** (qa-standards -> QA Modes). If the user didn't state one, infer the smallest mode that covers the request and say which. Then output the **Scope Lock** table and do not run a single query/call/click until it is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Feature / story / bug / PR | |
| QA mode | smoke / targeted / regression / bugfix / full / release |
| Roles in scope | `<roles: PROJECT-PROFILE.md §8>` |
| Pages / routes | |
| APIs / endpoints | |
| DB entities / tables | |
| Direct dependents | (Step 0b) |
| Indirect blast radius | (Step 0b) |
| Out of scope (explicit) | |
| Environment | Test (default) / Dev / Prod (read-only) — `PROJECT-PROFILE.md §5` |
| Branch / commit under test | `<branch: PROJECT-PROFILE.md §3> @ <short sha>` |
| Risk level | Low / Medium / High |
| Stop conditions | |

The Scope Lock's `M` (the denominator of the confidence line) comes from `test-cases-generator` Step 1b (code-derived matrix), never from intuition.

## Step 0b: Impact Analysis (REQUIRED for regression / bugfix / release; recommended always)

Before generating cases, trace the blast radius per qa-standards -> Impact Analysis: shared FE components (grep imports), shared API endpoints, shared DB tables/columns, async consumers (cron / workers / queues / storage events / email — `PROJECT-PROFILE.md §11`, traced to the terminal writer), caches & report snapshots, downstream reports/exports. Feed the results into the Scope Lock "Indirect blast radius" row and into Phase 0 cases. **A change is in scope plus everything this surfaces.**

If the source is a tracker ticket (Jira on), pull acceptance criteria via `mcp__claude_ai_Atlassian__*`; otherwise take them from the user or the linked document.

**If the scope is a PR / commit / branch -> `Skill(pr-risk-analyzer)`** for the formal blast-radius risk map; feed its impact map into the Scope Lock "Indirect blast radius" row and into Phase 0 cases.

---

## Run record & resume (`run.json`)
Keep `qa-evidence/<run-folder>/run.json` (`qa-standards/references/run-record.md`): create it at Scope Lock
(one register row per in-scope area, NOT YET VERIFIED until run, plus the Step 1b matrix), update it after
every phase (that update is the checkpoint), and if it already exists with `checkpoint.next_step` set,
RESUME from that step and say so. Before the verdict,
`python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>` must exit 0 - it
recomputes the confidence line and the run verdict; never type them by hand. `--package` then writes the
`package.md` the independent audit reads.

## Reusable Reference: Cross-Layer Data Consistency

For each entity tested, verify the value agrees across DB -> API -> Browser (full table in qa-standards). On mismatch -> bug. Take the entity → table → endpoint map from `PROJECT-PROFILE.md §10` and `.claude/references/system-map.md`; illustrative shape:

| Entity | DB table(s) | API endpoint(s) |
|--------|------------|------------------|
| User / Manager | `user`, `user_account` | `GET /api/<resource>/users` |
| Account | `account`, `user_account` | `GET /api/accounts/:id` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Computed output / score | snapshot tables (`PROJECT-PROFILE.md §11`) | `GET /api/<resource>/scores` |

Compare in a table: `| Field | DB | API | Browser | Match? |`.

---

## Phase 0: Test Case Generation
0. **Cross-check memory** — Grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for the feature/story, ticket/BUG- IDs, file paths, entity IDs. Load matches as known regression-risk areas (leads, not evidence — qa-standards → Fresh vs Historical). Skip re-verifying bugs already CONFIRMED+CLOSED unless asked.
0b. **Ambiguous or missing AC** -> clarify BEFORE any case is written, per `test-cases-generator` Step 1.4: numbered rounds with a recommended answer each, facts looked up in-session; each answer becomes the cited source for an expected result. If the `mattpocock-skills` plugin is installed (`PROJECT-PROFILE.md §17`) use `Skill(mattpocock-skills:grilling)`; otherwise ask the rounds yourself. Owner absent: open question + code-derived reading labelled INFERRED.
1. Delegate to `Skill(test-cases-generator)` for the scope + the Step 0b blast radius. Cases must cover positive, negative, boundary, DB integrity, API, UI, security, regression, E2E, data-consistency — and every cell of the coverage matrix (roles, states, inputs, input classes, flow, path exercised, cross-tenant).
2. Present the summary table (count/priority per category) and create TodoWrite tasks (P1 first).

## Phase 1: Pre-flight & Test Data
0. If `PROJECT-PROFILE.md §14` lists a project MCP server with session/status tools, call them first: the role profiles bootstrapped on Test = auth GREEN; a failure here is a stop condition.
1. **Pre-flight -> `Skill(env-health)`**: MCP servers reachable, repos on the right branch (case-sensitive) + current, portals/DB/auth up, **and the feature actually deployed** to the target env (bundle grep / version endpoint). Run its release radar (tickets moved to a deploy state with no QA touch) and, when Prod-DB is on, its prod-sentinel step. A RED item is a stop condition -> PARTIAL. (May run first, before Phase 0, to avoid building cases for a dead env.)
2. **Content imported recently?** If content/data was bulk-imported in the last 14 days into anything the story touches, `Skill(latent-pattern-sweep)` runs BEFORE Phase 2 (anomaly-disposition Rule 2).
3. **Test data -> `Skill(test-data-manager)`**: locate rich existing records matching the cases (prefer reuse); load its INPUT-CLASS FIXTURE REGISTRY — every parser/upload surface in scope gets ≥2 input classes, one of them the class production has never held; prepare + snapshot + restore under the **Mutation Safety Gate** only if needed (SELECT + log original, WHERE on every UPDATE, restore + verify, never mutate prod).

## Phase 2: Code Review
Delegate to `Skill(code-review)` for the changed code + the Step 0b blast radius. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md` for the layer.

## Phase 3: Database Validation
Delegate to `Skill(db-check)` for the entities in scope. (Schema vs ORM model, FK integrity, orphans, soft-delete mechanism, consistency, indexes.)

## Phase 4: API Testing
Drive the API through the project's typed tools when `PROJECT-PROFILE.md §14` lists them (`profile` = the role under test → the tool → DB read-back); otherwise `mcp__http-client__*`, and replay a captured FE request verbatim when the exact wire shape matters.
Delegate to `Skill(api-test)` for the enumerated endpoints. (Auth, RBAC, validation, errors, schema, DB-write consistency, mutation safety.)

**If the feature produces computed or model-generated numbers** (scores, recommendation picks, KPIs, report figures, aggregates) -> `Skill(ai-output-eval)`: recompute vs source data + the edge cases (falsy-zero, non-deterministic source-record selection, snapshot-vs-live scope, silent drops, stale recompute trigger).

## Phase 5: UI/E2E + Cross-Layer
- Delegate to `Skill(browser-test)` for the pages/flows — the **full** journey, not just the changed screen; capture console + network during every flow. **Every browser case records `Path exercised = validation-only | write`.** A write case is closed only by the network log AND a DB read-back. A story whose write path was never exercised cannot be GO.
- **Always during the flows -> `Skill(observability-check)`**: surface console errors / failed-slow network / backend 5xx the UI hides (a clean-looking screen can still be failing under the hood).
- **If the change touches UI -> `Skill(visual-regression)`** (layout / overflow / truncation / responsive across breakpoints) **+ `Skill(a11y-test)`** (keyboard / ARIA / focus / WCAG contrast).
- **Orchestrator only:** triangulate DB -> API -> Browser per the reference above (only the orchestrator has all three sets of outputs).

## Phase 6: Security Review
Delegate to `Skill(security-review)` — 10-point audit (auth, RBAC, injection, XSS, CSRF, data exposure, API security, headers, sessions). Its ratings map into the Verdict Contract (SECURE→PASS, AT RISK→FAIL or NOT YET VERIFIED, VULNERABLE→FAIL, could-not-test→BLOCKED/NOT APPLICABLE).

## Phase 7: Performance
Delegate to `Skill(perf-test)`. The thresholds live in ONE place: `perf-test` -> Thresholds (template defaults), overridden by `PROJECT-PROFILE.md §16`. Any threshold FAIL -> bug.

## Phase 7b: Regression (regression / bugfix / release modes)
In those modes -> `Skill(regression-runner)` over the Step 0b indirect blast radius — actively re-test the shared components / endpoints / tables / reports the change touches but is not "about". (In `full` mode this is already covered by the Phase 0 regression cases.)

**bugfix mode additionally:** (1) reproduce with the reporter's ORIGINAL input; (2) `git diff --name-only <base>..<fix>` must include the ticket's root-cause `file:line`, else report "symptom fixed, root cause untouched" and keep the ticket open; (3) the edge that the ORIGINAL bug's fix protected must be re-run as a negative control.

## Phase 8: Verify, then ASSEMBLE (do not publish yet)
1. **Verify every suspected bug** with `Skill(bug-verifier)` BEFORE it counts — no unverified bug enters the verdict. Confirmed bugs -> `Skill(bug-report)`.
2. **Assemble** — build the **Execution Register** (one row per Scope Lock area and per executed case, `Result` from the five canonical values) and the **Evidence Ledger** (every finding AND every PASS maps to a row, with Env / Branch-Commit / Captured-at). Use `Skill(evidence-manager)` to file and name attachments.
3. **STOP.** Do NOT call `Skill(qa-report)` yet and do NOT state a verdict. The audit in Phase 8a comes first — see the ordering note below.

## Phase 8a: Independent Verdict Audit (REQUIRED in full / release / regression / bugfix)

> **Ordering is load-bearing.** The register and ledger are assembled in Phase 8, audited here, and only
> then rendered in Phase 8b. Auditing after the report is written can only correct, never prevent.

**Default (sub-agents allowed, `PROJECT-PROFILE.md §16`):** dispatch the `qa-verdict-auditor` agent with the PATH of `qa-evidence/<run-folder>/package.md` (from `verdict_check.py --package`) - the PACKAGE only — Scope Lock, acceptance criteria / authoritative source, every finding (bugs AND passes), the Evidence Ledger, the Execution Register, the proposed verdict — and never the reasoning that produced them. It returns `AUDIT_PASSED` or `AUDIT_FAILED` + challenges.

**When §16 disables sub-agents:** do the audit in this session under a discipline that removes your own framing:

1. Put the PACKAGE in front of you and nothing else.
2. Re-derive the verdict FROM THE PACKAGE ONLY. If a register row has no ledger row, it is not a PASS.
   If the Scope Lock names an area with no register row, the audit FAILS ("register incomplete: <areas>").
3. Run Verdict Integrity 1-10 (qa-standards) against every finding, item by item, and write the answers
   down - not "checked", the actual answer. For every PASS: what evidence would prove it wrong, and did you
   look. For every FAIL: quote the source that defines the expected behaviour.
4. Check the confidence line arithmetic against the register rows, and that `M` equals the code-derived
   matrix size from test-cases-generator Step 1b (not a guess).
5. Write the result explicitly: `AUDIT_PASSED` or `AUDIT_FAILED` + the challenges.

Either way: AUDIT_FAILED means you may not report the verdict until each challenge is resolved with evidence. A withdrawn or corrected finding is a RESULT - record it, do not hide it. The completion gate hook (advisory, or blocking when enforced) flags a verdict turn that skips any of this.

### `/goal` — decided in Step 0 (the prompt's Run with block); arm it before Phase 0 when recommended

For a long `release` or `full` run, set a `/goal` condition before starting. A separate evaluator
re-checks it after every turn and the session keeps working until it resolves, which turns the
Completion Gate from something you must remember into something the harness enforces. Example (example only):

> `/goal Every row of the Execution Register carries one of the five canonical values (qa-standards -> Verdict Contract), every finding has an Evidence Ledger row, and the verdict audit returned AUDIT_PASSED.`

Claude Code stops the run if it stalls, so keep the condition objective and checkable.

## Phase 8b: Render the report (ONLY after the Phase 8a AUDIT_PASSED)

Now delegate to `Skill(qa-report)`. It renders the **already-audited** register, ledger and
findings into the standard report. It does not re-derive the verdict and it does not introduce
findings the auditor never saw. If the audit changed anything, the corrected material is what
gets rendered.

### Verdict
Print the canonical run verdict exactly as defined in qa-standards -> **Verdict Contract** (the ONLY definition),
with the mandatory confidence line, every coverage gap named (including every phase skipped because its
capability is off), and the escape classes E1–E13 that were actively checked. Any verdict that changes a
tracker status requires the Phase 8a AUDIT_PASSED first and follows the transition rules in `PROJECT-PROFILE.md §15`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate; mark any disproved older fact SUPERSEDED.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer whose link title carries the date.
4. **Content:** feature + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), the audit result, bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/accounts by identifier), the prompt path and its Research Register gaps, root-cause `path:line`, regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.

---

## Wiring for the escape classes (qa-standards → "Escape classes & their gates")

- **Step 0:** the prompt-generator's Research Register rows marked UNKNOWN / RETRIEVE become Phase 1 checks or named coverage gaps, never silence; its Run with block decides `/goal` / `/loop` before Phase 0.
- **Step 0a:** the Scope Lock's `M` comes from `test-cases-generator` Step 1b (code-derived matrix), never from intuition (E12).
- **Phase 1:** `env-health` release radar (E11) and prod sentinel (E10, when Prod-DB is on); a content import in the last 14 days triggers `latent-pattern-sweep` before Phase 2 (E2, E3).
- **Phase 1:** the input-class registry from `test-data-manager`; every parser/upload surface in scope gets ≥2 classes, one of them the class production has never held (E4).
- **Phase 5:** every browser case records `Path exercised = validation-only | write`; a write case is closed only by the network log AND a DB read-back (E5, E8).
- **bugfix mode:** original input re-run; the fix must touch the root-cause file:line; the original fix's edge re-run as a negative control (E6).
- **Any phase:** an anomaly ends as a ticket or as "expected" with a cited source. The words "by design", "workaround", "unresolved", "first-ever" in a report are a gate failure unless a ticket id sits beside them (E1, E9).
