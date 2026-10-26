# QA Standards - modes, coverage, routing, classification

Part of `qa-standards`. Moved out of SKILL.md to keep the always-loaded file small; the headings are unchanged, so a reference such as "qa-standards -> <heading>" still lands here via the pointer left in SKILL.md.

---

## QA Modes — pick the gear before testing

Choosing a mode prevents over-testing (wasting a session) and under-testing (missing the blast radius). If the user did not state a mode, **infer the smallest mode that covers the request and state which you picked** in the Scope Lock; ask only if genuinely ambiguous.

| Mode | When | Runs |
|------|------|------|
| **smoke** | Quick "is it alive" check | Login + one critical path + console/network scan |
| **targeted** | One named feature / field / endpoint | Just that surface, all its roles + negative cases |
| **regression** | After a change, guard nearby behavior | Changed feature **+ indirect blast radius** (see Impact Analysis) |
| **bugfix** | Verify a fix landed | Reproduce original bug with the reporter's ORIGINAL input (must now fail to reproduce) + the fix must touch the root-cause `file:line` + regression around the root cause |
| **full** | New/changed feature, full confidence | All phases: prompt → cases → code → DB → API → UI/E2E → security → perf → audit → report |
| **release** | Sign-off on a batch/release | `full` per area + release checklist + GO/NO-GO |

`regression`, `bugfix`, and `release` **must** complete the Impact Analysis below — that is exactly where "obvious" bugs hide.

**Scale effort to STAKES, not to prompt length.** A one-line request can carry a release decision. State the mode you picked and why.

---

## Impact Analysis & Coverage — direct + indirect blast radius

For every change under test, enumerate the blast radius **before** writing the verdict. This is the antidote to "we only tested the diff."

**1. Direct** — what the diff literally touches: the changed component, route, query, column.

**2. Indirect (where obvious bugs hide)** — trace each outward:
- **Shared FE components** — is the changed component reused on other pages? Grep imports.
- **Shared API endpoints** — do other features call the same endpoint? Different params/roles?
- **Shared DB tables/columns** — what else reads/writes this table? Reports, dashboards, exports, other endpoints.
- **Async consumers** — cron jobs, workers/Lambdas, queues, storage events, email (`PROJECT-PROFILE.md §11`). Trace an async chain to its **terminal writer** — the enqueue proves nothing.
- **Caches & snapshots** — client query caches, snapshot/aggregate tables, materialized aggregates that drift from live data.
- **Downstream reports/exports** — CSV columns, reports, dashboards (online vs offline scope).

**3. Coverage matrix** — for the in-scope surface, confirm you hit every cell that applies:

| Dimension | Must cover |
|---|---|
| Roles | every role that can reach the flow (`PROJECT-PROFILE.md §8`) |
| States | empty / single / many / max; draft vs published; active vs deleted; null vs zero |
| Inputs | valid (positive) **and** invalid/missing/malformed (negative) + boundaries |
| Input class | for any parse/upload surface: every input CLASS (e.g. text-layer PDF vs scanned image-only vs 0-byte) — see `test-data-manager` → INPUT-CLASS FIXTURE REGISTRY |
| Flow | the **full** user journey end-to-end, not just the changed screen |
| Path exercised | `validation-only` vs `write` — a write case is closed only by the network log AND a DB read-back |
| Cross-tenant | other accounts/tenants cannot see or act on this data |
| Regression | the indirect areas above still behave |

If a dimension is untested, it is a coverage gap — name it in the report, do not imply it passed.

---

## Cross-Layer Consistency — DB / API / Browser

For each entity in scope, the same value must agree across all three layers. Mismatch = bug.

1. **DB** — the DB tool from `PROJECT-PROFILE.md §6` (template default `mcp__mcp_server_mysql__mysql_query`) — the stored truth.
2. **API** — if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for the route, call it as the right role; otherwise `mcp__http-client__*`; or replay the FE's request captured via `mcp__chrome-devtools__*` byte-for-byte.
3. **Browser** — `mcp__playwright__*` snapshot / DOM.

Compare in one table: `| Field | DB | API | Browser | Match? |`. Consistency dimensions: value, count, status, date/time format, null handling, soft-delete filtering, FK resolution, aggregation, ordering, pagination.

**Matching API and UI proves transport, not correctness.** Correctness needs source records → an independent expected calculation → API → UI, and the difference located.

The project's entity → tables → endpoints map lives in `PROJECT-PROFILE.md §10` and `.claude/references/system-map.md`. Illustrative shape:

| Entity | DB table(s) | API endpoint(s) |
|---|---|---|
| User / Manager | `user`, `user_account` | `GET /api/<resource>/users` |
| Order | `order`, `order_item` | `GET /api/orders/:id` |
| Computed output / score | snapshot tables (`PROJECT-PROFILE.md §11`) | `GET /api/<resource>/scores` |

(Roles may live in a membership table, not on `user`. See `.claude/rules/db-gotchas.md`.)

---

## Bug Classification — FE / BE / Admin / Report / DB / Both

Apply on every confirmed bug so downstream skills don't re-derive it:

1. **Call the API directly.** Correct data but UI wrong -> **FE**. No call when one was expected -> **FE**. Wrong data / unexpected 500/404 -> go to 2.
2. **Query the DB.** DB correct but API wrong -> **BE** (query/logic). DB wrong -> **BE** (write-side) or **DB** (schema/migration).
3. **Edge cases:** Admin panel -> **Admin**. Reporting service (`PROJECT-PROFILE.md §3`) -> **Report**. API wrong AND UI mishandles the error -> **Both**. An async worker/Lambda that owns the terminal write -> **BE** with the worker named (the owner is a worker, not the API — escape class E7).

---

## Test-Case Quality Bar

Every test case — generated or executed — is **executable**, never vague. Minimum columns:

`TC ID | Requirement/AC | Scenario | Preconditions | Test Data | Input class | Steps | Expected (with its SOURCE) | Layer | Role | Priority | Automation? | Execute With | Evidence Required`

Every executed case records **Expected**, **Actual**, **Path exercised** and an explicit **Pass/Fail** (not "looks fine"). A case with no expected result is not a test. **An expected value that QA wrote needs a quotable source** (story line, contract, brief, design decision, code comment); if there is none, the case expects "UNKNOWN / ask" — never whatever the UI happens to do.

---

## MCP Server Routing — which server for which job

Use **fully-qualified** tool names (`mcp__server__tool`) so the right server is hit. Use only servers whose capability is `on` in `PROJECT-PROFILE.md §2`.

| Job | Server | Notes |
|---|---|---|
| Query **test/dev** DB | `<DB tool: PROJECT-PROFILE.md §6>` (default `mcp__mcp_server_mysql__mysql_query`) | DB `<test DB name: PROJECT-PROFILE.md §6>` on `<DB host: PROJECT-PROFILE.md §6>` |
| Query **prod** DB (read-only) | `mcp__mcp_server_mysql_prod__mysql_query` (or the engine's equivalent) | Confirm a prod repro. Access path per `PROJECT-PROFILE.md §6` (often an SSH tunnel). **Never mutate prod.** |
| Browser UI: clicks/forms/snapshots/screenshots | `mcp__playwright__*` | Primary E2E driver |
| Network/console/perf inspection | `mcp__chrome-devtools__*` | Capture the real FE request + console errors during repro |
| Direct API calls | `mcp__http-client__*` | Clear stale headers (`set_default_headers` merge:false) before auth |
| Act as a role through typed tools | `PROJECT-PROFILE.md §14` (optional project MCP) | One typed call can replace token minting + headers + URL building; prefer it when present |
| Existing API contracts | `mcp__postman-api-mcp__*` | Search first — source of truth for URL/headers/body (Postman capability) |
| Code/PR/commit/diff (remote) | `mcp__github__*` | `search_code`, `pull_request_read`, `list_commits` (GitHub capability); local repos use read-only `git` verbs |
| Evidence files | `mcp__filesystem__*` | Writes allowed only under `qa-evidence/` |
| Issue tracker | `mcp__claude_ai_Atlassian__*` for Jira (`PROJECT-PROFILE.md §15`) | Pull AC from a ticket; file/annotate issues when authorised |

**Default tool choices:** DB -> the profile's DB MCP (never another engine's). UI -> Playwright. API -> typed project tools if any, else http-client (Postman for contracts). Code search -> Read/Grep/Glob (NOT Bash cat/grep). Parallel multi-layer work -> Agent sub-agents, when `PROJECT-PROFILE.md §16` allows them.

---

## Plugins & escalation — when to escalate (optional plugins)

Plugins are **optional enhancers** (`PROJECT-PROFILE.md §17`). Use them only when they add real QA value — never reflexively. When a plugin is not installed, do the by-hand equivalent in the right-hand column.

| Situation | With the plugin | Without it |
|---|---|---|
| A confirmed bug whose root cause is non-obvious after the standard cross-layer pass | `superpowers:systematic-debugging` | hypothesis → isolate one variable → verify, written down |
| An intermittent/race/timing bug | `superpowers:systematic-debugging` + repeat for a reproduction rate | `flaky-race-verifier` |
| About to claim DONE/PASS/FIXED | `superpowers:verification-before-completion` | run the Completion Gate list below against your own output |
| Designing a new skill or a non-trivial test strategy | `superpowers:brainstorming`, then `superpowers:writing-skills` | write the goal, the failure it prevents, then the steps |
| Large independent fan-out (multi-area regression) | `superpowers:dispatching-parallel-agents` (or `qa-team`) | `qa-team`, or sequential lanes when sub-agents are disabled |
| A hard or intermittent bug that needs a repro harness BEFORE any hypothesis | `mattpocock-skills:diagnosing-bugs` **Phases 1–4 only** (red feedback loop → minimise → 3–5 ranked falsifiable hypotheses → instrument one variable at a time). Never its fix phases — this setup is read-only | the same four steps by hand |
| Ambiguous or missing acceptance criteria, owner present | `mattpocock-skills:grilling` — numbered rounds, each question with a recommended answer; facts looked up in-session; each answer becomes the cited source for an expected result | ask the same numbered questions yourself, one round at a time |
| Owner absent, AC ambiguous | — | record the ambiguity as an open question, take the code-derived reading, label it INFERRED |
| Editing any `.claude/skills/*`, `CLAUDE.md` or a rule file | `mattpocock-skills:writing-for-agents` + `superpowers:writing-skills` | follow `docs/maintainers/generalization-conventions.md` |

The built-in `/debug` (Claude Code) is a lighter alternative for a quick, single-thread root-cause dig. Prefer `systematic-debugging` (or the by-hand steps) when the bug spans layers. Plugin skills that write code or repository files (tdd, implement, to-spec, code-review variants that patch) are never used in a read-only QA session.

---

## Recommended Skill Sequence

A typical full validation flows: **prompt-generator (Step 0: the researched, self-contained prompt that decides /goal and /loop) -> sync-repos -> env-health -> login -> scope-lock (this module) -> test-data-manager -> test-cases-generator -> pr-risk-analyzer -> code-review -> db-check -> api-test -> browser-test -> security-review -> perf-test -> bug-verifier -> bug-report -> verdict audit -> qa-report** (memory write at each step). `full-qa` and `qa-team` orchestrate this; `qa-validate` is the lighter cross-layer path; `release-check` is the release-level orchestrator. `bug-verifier` precedes `bug-report` — never report an unverified bug.

**Specialized skills — slot in when relevant:** `regression-runner` (drive the blast radius after a change) · `visual-regression` + `a11y-test` (UI depth) · `observability-check` (errors the UI hides) · `flaky-race-verifier` (intermittent/race bugs) · `ai-output-eval` (computed / model-generated outputs: scores, recommendations, KPIs, report figures) · `latent-pattern-sweep` (code assumptions vs live data distribution; mandatory after a bulk import) · `prod-sentinel` (read-only production anomaly scan, weekly and after deploys/imports) · `test-together` (guided pair-testing in a shared browser) · `evidence-manager` (capture + ledger proof) · `automation-writer` (confirmed manual case -> script) · `explainer` (plain-language, per-role change summary) · `release-note` (customer-facing notes) · `demo-creator` (narrated demo video of a flow — a delivery tool, not a test).

---

## Environments & Layer Rules — pointers

- **Credentials, URLs, DB connections, repos/branches:** `PROJECT-PROFILE.md` (imported by `CLAUDE.md`, always loaded) is the source of truth. Default environment = **Test** (`§5`). Branch names are case-sensitive.
- **Layer-specific QA checks** (auto-attach when working in those repos): `.claude/rules/backend.md`, `.claude/rules/frontend.md`, `.claude/rules/admin.md`, `.claude/rules/db-gotchas.md`, `.claude/rules/testing.md`, plus the always-loaded `.claude/rules/anomaly-disposition.md` and `.claude/rules/pushback-protocol.md`. Read the relevant one before reviewing that layer.
- **System map:** `.claude/references/system-map.md` — the project's verified-from-code map (repos → API mounts → admin controllers → FE pages → DB families → async chains → armed risks). Every QA run verifies and extends one section; a section older than 60 days is treated as unverified.
