---
name: full-qa
description: Use when a feature, user story, PR, bug fix or release needs complete multi-layer QA validation ending in a GO/NO-GO verdict, delegating to the specialist QA skills. Triggers include "full QA", "validate this story/PR", "run the QA cycle", "sign off this story". For a whole release use /release-check.
argument-hint: "user story, feature, PR, or release to fully validate (plus the QA mode if known)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Agent", "Skill(sync-repos)", "Skill(prompt-generator)", "Skill(qa-standards)", "Skill(env-health)", "Skill(login)", "Skill(pr-risk-analyzer)", "Skill(test-data-manager)", "Skill(test-cases-generator)", "Skill(code-review)", "Skill(db-check)", "Skill(api-test)", "Skill(ai-output-eval)", "Skill(latent-pattern-sweep)", "Skill(browser-test)", "Skill(visual-regression)", "Skill(a11y-test)", "Skill(observability-check)", "Skill(security-review)", "Skill(perf-test)", "Skill(regression-runner)", "Skill(bug-verifier)", "Skill(flaky-race-verifier)", "Skill(bug-report)", "Skill(qa-report)", "Skill(evidence-manager)", "Skill(mattpocock-skills:grilling)", "Write"]
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
1. No assumptions — verify with actual data and behavior. Code is truth.
2. **Validate the full user flow and the blast radius, not just the diff** (Step 0b Impact Analysis). This is the #1 cause of missed bugs.
3. **Step 0 first (any form), then Phase 0.** The run starts from what `prompt-generator` produced (Step 0); the `/goal` / `/loop` decision exists before Phase 0; test cases are generated BEFORE testing (Phase 0).
4. Every finding — bug OR pass — needs an Evidence Ledger row. No evidence = no finding.
5. **Load every phase skill with the Skill tool.** "Delegate to `Skill(<name>)`" means: call the Skill tool for that skill, then run the phase by that skill's own checklist; a phase done from this file's one-line summary has not run. The Phase skill map below says which skills load and when one does not apply. Pass each skill this run's scope; the orchestrator coordinates and triangulates, it never redoes a skill's work from memory.
6. Each phase completes before the next, EXCEPT a hard blocker (feature undeployed, schema missing, wrong branch, auth fails) -> exit early with a PARTIAL verdict naming the blocker.
7. **Every generated case is executed** unless `PROJECT-PROFILE.md §16` says otherwise. No sampling by priority, no "P1 first and stop", no "time did not allow". Priority only orders the work. Every case ends as a register row with a canonical Result and an evidence id; progress is tracked row by row in the Execution Register.
8. **Run end to end, without asking.** Never ask whether to run one of this skill's own steps (Step 1b, a phase, a phase skill) or the cases still open: run them. Ask the user only for decisions that are theirs (filing tickets, a permission the harness refuses, a product ruling). A case ends NOT YET VERIFIED only after it was tried live -> on a local harness or container copy -> through the real code path with test doubles -> by code read, and the row names the structural blocker and what would unblock it (completion gate checks #15–#16).

---

## Step 0: Sync + Prompt Generator (REQUIRED — the very first step, before the six questions)

`Skill(sync-repos)` first (read-only pull), then `Skill(prompt-generator)` with `$ARGUMENTS`: it researches the request (live ticket per `PROJECT-PROFILE.md §15`, memory, prior evidence, code on the target branch, DB shape, fixtures, armed risks, hooks) and returns this run's charter; nothing below starts until it exists. Its form — FULL / LIGHT / Run with only / Reuse — follows the mode (prompt-generator → Forms). **Read [`references/step-0.md`](references/step-0.md) now:** which form, and how each step consumes the prompt. **`/goal` never stops the run:** print the recommended line and continue into Step 0a in the same turn. The prompt copy lives at `qa-evidence/<run-folder>/00-prompt-<subject>.md`.

If the generator cannot fill its Research Register (tracker unreachable, repo missing), it says so and Step 0a proceeds with those rows as stop conditions. The generator never runs a test and never changes a ticket.

## Step 0a: QA Mode + Scope Lock (REQUIRED — after Step 0, before any tool runs)

**Six questions first** (qa-standards → *Before the first tool call*): write them out explicitly — what is requested / what is authoritative / what can be verified / which assumptions are eliminated / what evidence is required / what completion means — before running any tool.

Pick the **QA mode** (qa-standards -> QA Modes): take it from the prompt's Execution shape and change it only with a stated reason; with no Execution shape (Run with only), if the user didn't state one, infer the smallest mode that covers the request and say which. Then output the **Scope Lock** table and do not run a single query/call/click until it is filled (ask if a critical field is unknown):

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

## Step 0b: Impact Analysis (REQUIRED for full / regression / bugfix / release; recommended always)

Before generating cases, trace the blast radius per qa-standards -> Impact Analysis: shared FE components (grep imports), **shared text files** (each changed key in `<shared text files: PROJECT-PROFILE.md §9>` and every page that reads it), item **1b** (declared scope vs the real diff), shared API endpoints, shared DB tables/columns, async consumers (cron / workers / queues / storage events / email — `PROJECT-PROFILE.md §11`, traced to the terminal writer), caches & report snapshots, downstream reports/exports. Feed the results into the Scope Lock "Indirect blast radius" row and into Phase 0 cases. **A change is in scope plus everything this surfaces.**

If the source is a tracker ticket (Jira on), take the acceptance criteria from the prompt's R2 when Step 0 read it live this run; otherwise pull them via `mcp__claude_ai_Atlassian__*`, or take them from the user or the linked document.

**If the scope is a PR / commit / branch -> `Skill(pr-risk-analyzer)`** for the formal blast-radius risk map; feed its impact map into the Scope Lock "Indirect blast radius" row and into Phase 0 cases.

---

## Run record & resume (`run.json`)
Keep `qa-evidence/<run-folder>/run.json` per `qa-standards/references/run-record.md`: create it at Scope Lock (one register row per in-scope area, NOT YET VERIFIED until run, plus the Step 1b matrix), update it after every phase (the checkpoint), and RESUME from `checkpoint.next_step` when it exists, saying so. Before the verdict `python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>` must exit 0 (it recomputes the confidence line and the run verdict; never type them by hand); `--package` writes the `package.md` the audit reads.

## Phase skill map — load each with the Skill tool, or write why it does not apply

A phase whose capability is `off` is n/a with that reason (capability gate above).

| Phase | Skills to load | n/a only when |
|---|---|---|
| Step 0 / 0b | `sync-repos`, `prompt-generator`; `pr-risk-analyzer` | pr-risk-analyzer: the scope is not a PR, commit or branch |
| 0 | `test-cases-generator`; `mattpocock-skills:grilling` (§17) for an unclear AC | grilling: every AC is clear (no plugin: the rounds by hand) |
| 1 | `env-health`, `login`, `test-data-manager`; `latent-pattern-sweep` after a content import in the last 14 days | latent-pattern-sweep: no import |
| 2 · 6 · 7 · 8b | `code-review` · `security-review` · `perf-test` · `qa-report` | never |
| 3 | `db-check` | no table is in scope |
| 4 | `api-test`; `ai-output-eval` for computed numbers | no endpoint is in scope |
| 5 | `browser-test`, `observability-check`; `visual-regression` + `a11y-test` when a screen's output changes | no screen is in scope, or the owner scoped the run to the backend |
| 7b | `regression-runner` | smoke or targeted mode |
| 8 | `bug-verifier` per suspected bug, `bug-report` per confirmed bug, `evidence-manager`; `flaky-race-verifier` for an intermittent bug | no suspected bug |

**Inside this run every loaded skill** uses this run's Scope Lock and case IDs (no new Scope Lock, no "ask then stop"), returns its findings and evidence rows to this run's Execution Register and Evidence Ledger, and skips its own memory write: this run writes one memory file at the end. Load each skill once per run, and again only after a compaction dropped its text.

## Phase 0: Test Case Generation
0. **Cross-check memory** — start from the prompt's R3 (memory) and R4 (prior evidence) rows; Grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` only for what they did not cover: the feature/story, ticket/BUG- IDs, file paths, entity IDs. Load matches as known regression-risk areas (leads, not evidence — qa-standards → Fresh vs Historical). Skip re-verifying bugs already CONFIRMED+CLOSED unless asked.
0b. **Ambiguous or missing AC** not already settled in the prompt's R10 -> clarify BEFORE any case is written (`test-cases-generator` Step 1.4: numbered rounds, a recommended answer each, facts looked up in-session; each answer becomes the cited source of an expected result) — `Skill(mattpocock-skills:grilling)` if installed (§17), otherwise by hand. Owner absent: open question + code-derived reading labelled INFERRED.
1. Delegate to `Skill(test-cases-generator)` for the scope + the Step 0b blast radius. Cases must cover positive, negative, boundary, DB integrity, API, UI, security, regression, E2E, data-consistency — and every cell of the coverage matrix (roles, states, inputs, input classes, flow, path exercised, cross-tenant). Steps 1b, 1c and 1d all run: the code-derived matrix, the break-it cells and the four inventories (role × action grid, branch inventory, UI inventory, story-is-silent list). Phase 1 does not start while the case-completeness line shows a number below its total (E15).
2. Present the summary table (count/priority per category) and list every case as an Execution Register row (P1 first).

## Phase 1: Pre-flight & Test Data
0. If `PROJECT-PROFILE.md §14` lists a project MCP server with session/status tools, call them first: the role profiles bootstrapped on Test = auth GREEN; a failure here is a stop condition.
1. **Pre-flight -> `Skill(env-health)`**: MCP servers reachable, repos on the right branch (case-sensitive) + current, portals/DB/auth up, **and the feature actually deployed** to the target env (bundle grep / version endpoint). Run its release radar (tickets moved to a deploy state with no QA touch) and, when Prod-DB is on, its prod-sentinel step. A RED item is a stop condition -> PARTIAL. (May run first, before Phase 0, to avoid building cases for a dead env.)
2. **Content imported recently?** If content/data was bulk-imported in the last 14 days into anything the story touches, `Skill(latent-pattern-sweep)` runs BEFORE Phase 2 (anomaly-disposition Rule 2).
3. **Test data -> `Skill(test-data-manager)`**: locate rich existing records matching the cases (prefer reuse); load its INPUT-CLASS FIXTURE REGISTRY — every parser/upload surface in scope gets ≥2 input classes, one of them the class production has never held; prepare + snapshot + restore under the **Mutation Safety Gate** only if needed (SELECT + log original, WHERE on every UPDATE, restore + verify, never mutate prod).

## Phase 2: Code Review
Delegate to `Skill(code-review)` for the changed code + the Step 0b blast radius. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md` for the layer.

**Possibly affected** — end the review with this list: every page, endpoint, table, job and report the changed code can reach beyond the story's own screens (callers of a changed function, importers of a changed component, pages that read a changed text key). Each item joins the Scope Lock "Indirect blast radius" row and is tested in Phase 7b.

## Phase 3: Database Validation
Delegate to `Skill(db-check)` for the entities in scope. (Schema vs ORM model, FK integrity, orphans, soft-delete mechanism, consistency, indexes.)

## Phase 4: API Testing
Drive the API through the project's typed tools when `PROJECT-PROFILE.md §14` lists them (`profile` = the role under test → the tool → DB read-back); otherwise `mcp__http-client__*`, and replay a captured FE request verbatim when the exact wire shape matters.
Delegate to `Skill(api-test)` for the enumerated endpoints. (Auth, RBAC, validation, errors, schema, DB-write consistency, mutation safety.)

**If the feature produces computed or model-generated numbers** (scores, recommendation picks, KPIs, report figures, aggregates) -> `Skill(ai-output-eval)`: recompute vs source data + the edge cases (falsy-zero, non-deterministic source-record selection, snapshot-vs-live scope, silent drops, stale recompute trigger).

## Phase 5: UI/E2E + Cross-Layer (every screen, every role, as the user sees it)
- Delegate to `Skill(browser-test)` for every screen of the **full** journey, not just the changed screen: each control checked with its screenshot opened (E14), every screen state, real-user habits (refresh, back, double click, two tabs, deep link, session end), every role and the hand-off between roles, media / downloads / uploads, and a second browser engine. Console + network during every flow. **Every browser case records `Path exercised = validation-only | write`.** A write case is closed only by the network log AND a DB read-back. A story whose write path was never exercised cannot be GO.
- **Always during the flows -> `Skill(observability-check)`**: surface console errors / failed-slow network / backend 5xx the UI hides (a clean-looking screen can still be failing under the hood).
- **`Skill(visual-regression)`** (layout / overflow / truncation / responsive across breakpoints) **+ `Skill(a11y-test)`** (keyboard / ARIA / focus / WCAG contrast / reflow / page language) on every screen whose output the change can alter: new or changed text, message, empty or error state, control or layout — including a backend change that changes what a screen shows. NOT APPLICABLE needs one line saying no screen shows anything the change produces.
- Screens are tested in `<UI languages: PROJECT-PROFILE.md §16>`; text the story itself produces is tested in each language the story names.
- When the owner scoped the run to the backend, the Phase 5 rows are NOT APPLICABLE with that citation, and every screen that shows the changed output is listed as an open UI risk in the report (E14).
- **Orchestrator only:** triangulate DB -> API -> Browser per entity (qa-standards → Cross-Layer Consistency; the entity → table → endpoint map from `PROJECT-PROFILE.md §10` and `.claude/references/system-map.md`), compared as `| Field | DB | API | Browser | Match? |` — only the orchestrator has all three sets of outputs.

## Phase 6: Security Review
Delegate to `Skill(security-review)` — 10-point audit (auth, RBAC, injection, XSS, CSRF, data exposure, API security, headers, sessions). Its ratings map into the Verdict Contract (SECURE→PASS, AT RISK→FAIL or NOT YET VERIFIED, VULNERABLE→FAIL, could-not-test→BLOCKED/NOT APPLICABLE).

## Phase 7: Performance
Delegate to `Skill(perf-test)`. The thresholds live in ONE place: `perf-test` -> Thresholds (template defaults), overridden by `PROJECT-PROFILE.md §16`. Any threshold FAIL -> bug.

## Phase 7b: Regression (full / regression / bugfix / release modes)
In those modes -> `Skill(regression-runner)`; **full mode runs everything regression mode runs**. Scope = the Step 0b indirect blast radius ∪ the Impact Analysis 1b areas (changed outside the declared scope) ∪ the Phase 2 **Possibly affected** list. Test each area through every layer it has and every role that reaches it; the smallest proving check is the floor, not the target. One register row `Regression: <area>` per area with a canonical result and an evidence id (completion gate check #21); Phase 0's same-feature regression cases do not replace this phase.

**bugfix mode additionally:** (1) reproduce with the reporter's ORIGINAL input; (2) `git diff --name-only <base>..<fix>` must include the ticket's root-cause `file:line`, else report "symptom fixed, root cause untouched" and keep the ticket open; (3) the edge that the ORIGINAL bug's fix protected must be re-run as a negative control.

## Phase 7c: Core-page sweep (every mode)
Run qa-standards -> Core-page sweep on the build under test, whatever the story names: the build carries every merged commit, so the story's own screens are not the only ones it can break. One register row `Core-page sweep: <route>` per page of `<core pages: PROJECT-PROFILE.md §8>`, each with its raw-text scan result and an evidence id (completion gate check #20). Browser off -> one NOT APPLICABLE row citing §2.

## Phase 8: Verify, then ASSEMBLE (do not publish yet)
1. **Verify every suspected bug** with `Skill(bug-verifier)` BEFORE it counts — no unverified bug enters the verdict. Confirmed bugs -> `Skill(bug-report)`.
2. **Assemble** — build the **Execution Register** (one row per Scope Lock area and per executed case, `Result` from the five canonical values) and the **Evidence Ledger** (every finding AND every PASS maps to a row, with Env / Branch-Commit / Captured-at). Use `Skill(evidence-manager)` to file and name attachments.
3. **STOP.** Do NOT call `Skill(qa-report)` yet and do NOT state a verdict. The audit in Phase 8a comes first — see the ordering note below.

## Phase 8a: Independent Verdict Audit (REQUIRED in full / release / regression / bugfix)

> **Ordering is load-bearing.** The register and ledger are assembled in Phase 8, audited here, and only
> then rendered in Phase 8b. Auditing after the report is written can only correct, never prevent.

**Default (sub-agents allowed, `PROJECT-PROFILE.md §16`):** dispatch the `qa-verdict-auditor` agent with the PATH of `qa-evidence/<run-folder>/package.md` (from `verdict_check.py --package`) - the PACKAGE only — the Step 0 prompt, Scope Lock, acceptance criteria / authoritative source, every finding (bugs AND passes), the Evidence Ledger, the Execution Register, the proposed verdict — and never the reasoning that produced them. It returns `AUDIT_PASSED` or `AUDIT_FAILED` + challenges.

**When §16 disables sub-agents:** run the same checklist in this session, from the package alone.

**Either path uses [`references/audit.md`](references/audit.md) — read it before auditing:** re-derive the verdict from the package (a register row without a ledger row is not a PASS; an area or check the Scope Lock or the Step 0 prompt names without a row FAILS), Step 1b ran, every NOT YET VERIFIED row was tried, and items 4b–4f: the `Case completeness:` / `Skills loaded:` lines and the `Core-page sweep:` / `Regression:` rows. Write `AUDIT_PASSED` or `AUDIT_FAILED` + the challenges.

Either way: AUDIT_FAILED means you may not report the verdict until each challenge is resolved with evidence. A withdrawn or corrected finding is a RESULT - record it, do not hide it. The completion gate hook (advisory, or blocking when enforced) flags a verdict turn that skips any of this.

**`/goal`** is decided in Step 0 and never waited for — the condition and its example: [`references/step-0.md`](references/step-0.md) → /goal.

## Phase 8b: Render the report (ONLY after the Phase 8a AUDIT_PASSED)

Now delegate to `Skill(qa-report)`. It renders the **already-audited** register, ledger and
findings into the standard report. It does not re-derive the verdict and it does not introduce
findings the Phase 8a audit never saw. If the audit changed anything, the corrected material is what
gets rendered.

### Verdict
Open the verdict with the **Run line** in plain text, `Run: full-qa | QA mode: <mode> | Audit: AUDIT_PASSED` (qa-standards -> Verdict Contract; the completion gate reads it, checks #18–#22). Print the canonical run verdict exactly as defined in qa-standards -> **Verdict Contract** (the ONLY definition),
with the mandatory confidence line, every coverage gap named (including every phase skipped because its
capability is off), and the escape classes E1–E15 that were actively checked. Any verdict that changes a
tracker status requires the Phase 8a AUDIT_PASSED first and follows the transition rules in `PROJECT-PROFILE.md §15`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`. It is the run's only memory file: the skills this run loaded write none of their own.
2. **Cross-reference first** — grep the folder for the endpoint/path/user-ID/symptom; UPDATE an existing entry instead of filing a duplicate; mark any disproved older fact SUPERSEDED.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer whose link title carries the date.
4. **Content:** feature + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), the audit result, bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/accounts by identifier), the prompt path and its Research Register gaps, root-cause `path:line`, regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.

---

## Wiring for the escape classes (qa-standards → "Escape classes & their gates")
Per-phase wiring: [`references/audit.md`](references/audit.md) → Escape-class wiring (each phase above carries its gate; the audit checks every one).
