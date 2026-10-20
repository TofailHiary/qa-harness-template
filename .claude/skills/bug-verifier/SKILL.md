---
name: bug-verifier
description: Use when a suspected bug must be confirmed 100% real before it is reported or counted in a verdict — eliminates false positives from stale data, caching, env, or wrong assumptions. Triggers include "verify this bug", "is this actually a bug", a suspected issue from testing, or the gate before /bug-report.
argument-hint: "bug description or bug ID"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(flaky-race-verifier)", "Skill(evidence-manager)", "Skill(bug-report)", "Agent(qa-verdict-auditor)", "Write"]
---

# Bug Verifier — Confirm 100% Valid Issues

Verify a suspected bug is REAL before a report is written or it enters a GO/NO-GO verdict.

> **Capability note:** this skill is **always on** (utility — see `docs/capability-matrix.md`). It never hard-stops, but it only touches the layers enabled in `PROJECT-PROFILE.md` §2. When a layer's capability is `off`, skip that layer's tools and record the layer as **BLOCKED** (reason: capability off) in the cross-layer table — never as verified. Prod-DB, Postman and Jira are optional enhancers used only when `on`.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Evidence provenance, Bug Classification, Cross-Layer Consistency, Authoritative Source Hierarchy, Fresh vs Historical, Verdict Contract, Judgement Discipline, The six questions, Escape classes & their gates, Memory Ritual).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which bug should I verify? Give the description, bug ID, or the suspected issue." Do not guess from conversation; do not run queries/tests until the target is known.

---

## Rules
1. Use ultrathink for every verification.
2. Run DB queries ONE AT A TIME (sequentially) to avoid cascading MCP errors.
3. Verify ONE bug at a time — if several, ask which first.
4. Memory is ON-DEMAND for loading; the Memory ritual at the end is MANDATORY.
5. Every step that supports the verdict gets an Evidence Ledger row, stamped with **Env / Branch-Commit / Captured-at** (qa-standards → Evidence provenance). **No reproduction = no confirmed bug.**
6. **Six questions first** (qa-standards → The six questions) — written out in 2–6 lines before the first tool runs: what is requested · what is authoritative · what can be verified · which assumptions are eliminated · what evidence is required · what is completion.
7. **Ticket-transition rule** (qa-standards → Verdict Contract). If this verdict will move a ticket status in the issue tracker (`PROJECT-PROFILE.md §15`): (a) re-read the ticket live THIS run (`mcp__claude_ai_Atlassian__getJiraIssue` for Jira, or the tracker read tool named in §15); (b) produce a mini Execution Register — one row each for *expected source*, *reproduction*, *code at HEAD*, *fixture*; (c) get an independent audit of the package (findings + ledger + register + proposed verdict): if `PROJECT-PROFILE.md §16` allows sub-agents, dispatch `Agent(qa-verdict-auditor)`; if §16 says sub-agents are disabled, run the in-session audit pass yourself — re-derive the verdict from the package alone, item by item against qa-standards → Verdict Integrity, and write the result. **AUDIT_PASSED before any transition.** Transition ids, status names and assignee rules come from §15, never from this skill. A developer ruling ("this is intended") is recorded as a ruling — "PASS as ruled", citing the comment — never as a fix.
8. **Fix verification = real wire shape.** Capture the actual response body / file / event in the target environment and test the fix against THAT, not against the unit-test mock (qa-standards → Judgement Discipline #7). *(illustrative)* every unit test of a response parser passed against a plain-string body while the backend actually sent a JSON envelope — the fix never fired in the real flow.

---

## Verification Checklist (ALL MUST PASS)
1. **Understanding** — Do I fully understand expected behavior? Could this be intentional? Can I cite the source of the expectation?
2. **Reproduction** — Confidence ≥ 90%? Deterministic: 1–2 attempts; intermittent (race): ≥ 5 attempts + compute a reproduction rate; default if unclear: 3. Consistent across data/users? Reproduced with the reporter's original input class?
3. **Data** — Test data valid, not stale/corrupt?
4. **Code** — Read the actual implementation, including the async component that is the terminal writer; does logic match expectation?
5. **Environment** — Correct env (Test default)? Code current on `<branch: PROJECT-PROFILE.md §3>`? Caching ruled out?
6. **Assumptions** — Every assumption verified, not assumed? Epistemic status labelled (VERIFIED FACT / STRONG INFERENCE / HYPOTHESIS / UNKNOWN) wherever it changes the conclusion?

---

## Verification Steps

### Pre-Step: Environment (always) + API Contract (if the bug touches an API)
1. **Environment** — correct test env (`<main app URL: PROJECT-PROFILE.md §5>`), session authenticated as `<role account: PROJECT-PROFILE.md §7>`, repos on `<branch: PROJECT-PROFILE.md §3>` + current. Run `git rev-parse --short HEAD` once in the repo that owns the code under test — that value stamps the **Branch / Commit** column of every ledger row this run.
2. **API Contract** (only if API-related) — `mcp__postman-api-mcp__*` (when Postman is `on` in §2) to confirm endpoint/method/headers/auth/body/response schema; otherwise read the route in `<routes path: PROJECT-PROFILE.md §9>`. **Skip** for purely UI/CSS, i18n/typo, static-asset, a11y, or browser-only (no network) bugs.

### Step 1: Clarify Expected Behavior + Cross-Check Memory
Read code/comments/docs; check how similar functionality behaves elsewhere. Establish the expected behavior from an authoritative source (qa-standards → Authoritative Source Hierarchy: ticket AC / spec / code contract / ruling) and cite it — an expectation you cannot cite is a HYPOTHESIS, not a rule. **Grep memory** (`<memory folder: PROJECT-PROFILE.md §12>/*.md`) for the endpoint, file path, user IDs, ticket / BUG- IDs, symptom keywords. If a prior entry covers this root cause -> mark **DUPLICATE-CHECK**, verify whether the prior fix regressed or holds (current reality overrides memory — a remembered PASS/FAIL is a lead to re-verify, never evidence), and UPDATE that entry (not a new one) in the post-session.

### Step 2: Reproduce Consistently
Reproduce 3+ times with exact steps. Run `mcp__playwright__*` + `mcp__chrome-devtools__*` together every attempt: drive the UI + screenshot, capture `list_network_requests` and `list_console_messages` at the moment of failure (the network/console layer often shows the failure before the UI does).

**Reproduce with the reporter's ORIGINAL input class.** If the report came with a file, an upload, a specific template, a specific record or a specific account, reproduce with THAT first — not with the fixture you usually use. *(illustrative)* a bug stayed "not reproduced first-hand" for three runs because every run used the same clean fixture file; the customer's own file reproduced it on the first attempt. Record the input class on the ledger row (escape class E4 — same input every time).

**If it does NOT reproduce every time (intermittent)** -> hand off to `Skill(flaky-race-verifier)` to get a reproduction rate + the race/timing/ordering cause.

**Red loop before hypotheses (hard bugs only).** For a bug that does not fall out of the 3 repros plus the cross-layer pass:
- If the `mattpocock-skills` plugin is installed (`PROJECT-PROFILE.md §17`), run `Skill(mattpocock-skills:diagnosing-bugs)` **Phases 1–4 only** and **stop before Phase 5**.
- Otherwise do the equivalent by hand: (1) write ONE command that goes red on THIS symptom — a failing test, a curl script, a Playwright script, or a replay of the captured payload; (2) minimise it until every remaining element is load-bearing (remove a step; if it still goes red, that step was noise); (3) write 3–5 ranked, falsifiable hypotheses and show them to the owner; (4) instrument ONE variable at a time and re-run the red command after each change.
- Either way: no fix, no regression test, no source edit (read-only QA). The red command and its red output are Evidence Ledger rows. Sample inputs (files, uploads, media) come from the sample-file library in `PROJECT-PROFILE.md §13`, if any.

### Step 3: Verify Test Data
`mcp__mcp_server_mysql__mysql_query` (DB tool: `PROJECT-PROFILE.md §6`) — confirm test data valid, relationships in place (`<key tables: PROJECT-PROFILE.md §10>`; check soft-delete columns and enum values per `.claude/rules/db-gotchas.md`). To check whether the same bug exists in prod: only when Prod-DB is `on` (§2), query read-only via `mcp__mcp_server_mysql_prod__mysql_query` using the prod read-only access described in §6. **Never mutate prod.** A prod observation is evidence for PROD only — label the row (environment attribution rule).

### Step 4: Verify API Behavior
If `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this route, prefer it — call the route as the affected role (`<roles: PROJECT-PROFILE.md §8>`, e.g. Admin / Manager / User / Guest) in one call with the correct headers and claims, no manual token minting. Otherwise hit the endpoint directly with `mcp__http-client__*` (or `mcp__postman-api-mcp__*` for an existing contract) as `<role account: PROJECT-PROFILE.md §7>`. Repeat it 3× like the UI repro. Capture the FE's real request with `mcp__chrome-devtools__*` and compare — response, auth, format.

### Step 5: Read the Code
FE components, BE routes/models, Admin controllers (`PROJECT-PROFILE.md §9`). Business logic, error handling, edge cases. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md`.

**The code is in more than three repos.** "FE / BE / Admin" is not the whole system. The symptom's owner is often an async consumer — a Lambda/worker, a cron job, a queue consumer, an integration/sync service, a report builder (`PROJECT-PROFILE.md §11`; repos in §3). *(illustrative)* a bug showed in the user-facing portal; the cause was one line in a separate integration service that writes the row the portal reads. **Trace the async chain to its terminal writer** — the component that last writes the row / file / event the user sees — and read THAT code (escape class E7 — wrong repo).

**For a FIX, check it touched the root cause.** `git diff --name-only <base>..<fix>` (or the files list from `mcp__github__pull_request_read`) must include the `file:line` the ticket names as the root cause. If it does not, the fix is a symptom patch: say so in the verdict and keep the ticket open (escape class E6 — symptom fix). *(illustrative)* a fix PR changed the upload component's error message but never touched the id-parsing line the ticket identified; the bug reproduced unchanged.

### Step 6: Cross-Reference Layers
| Layer | Check | Tool | Status |
|-------|-------|------|--------|
| Frontend | Component behavior correct? | `mcp__playwright__*` | [ ] |
| API | Endpoint returns expected data? | `mcp__http-client__*` / `mcp__postman-api-mcp__*` / §14 typed tool | [ ] |
| Backend | Business logic correct? | `Read`, `Grep`, `Glob` | [ ] |
| Database | Data state correct? | `mcp__mcp_server_mysql__mysql_query` | [ ] |
| Browser | UI displays correctly? | `mcp__playwright__*` + `mcp__chrome-devtools__*` | [ ] |
| Async / terminal writer | Terminal row / file / event present and correct? | `Read` + DB query (`PROJECT-PROFILE.md §11`) | [ ] |

A layer whose capability is `off` (§2) is marked BLOCKED with the reason, not left blank and not ticked.

### Step 7: Eliminate Alternatives
Rule out: expected behavior, user error, test-data issue, env issue, caching, timing/race, missing prerequisite.

**Three "alternatives" that are NOT dispositions** (qa-standards → Escape classes & their gates, E1 — dissolved anomaly): "by design" without a cited source · "workaround adopted" · "unresolved without <tool/log/access>". An anomaly ends as exactly one of: a filed ticket / explicit finding in the verdict, or "expected" WITH A CITED SOURCE (acceptance criteria, a schema constraint, a code comment, a named product decision, a written spec). Run the by-design test before typing those words: does the **schema** allow it? does the **UI** promise it? is there an **AC, code comment or named decision** that says so? If all three are no, you invented the requirement — the verdict is CONFIRMED BUG. A **masked error** (a real failure surfacing as an unrelated exception) is a second, separate CONFIRMED BUG (E9).

**Async actions — verify the terminal state, not the enqueue** (E8 — silent async no-op). A success flash on a queue-dispatched action proves only that the message was sent. The verdict needs the row / file it should have created, read from the DB or store, or the explicit absence of it plus the reason. *(illustrative)* a deploy action returned early when a draft already existed — success toast shown, nothing created.

### Step 8: Classify the Layer
Apply qa-standards -> Bug Classification (FE / BE / Admin / Report / DB / Both). Output the layer in the verdict so `/bug-report` doesn't re-derive it.

---

## Decision Matrix
| Scenario | Verdict | Action |
|----------|---------|--------|
| Reproducible + code defect + valid data | **CONFIRMED BUG** | Build the Evidence Ledger -> `Skill(bug-report)` |
| Reproducible + a prior memory entry or an open ticket already covers this root cause | **DUPLICATE** | Update the existing entry; link the ticket per `PROJECT-PROFILE.md §15`; do not file a new report |
| Reproducible but expected behavior (source cited) | **NOT A BUG** | Document as expected, with the citation |
| Not reproducible | **CANNOT CONFIRM** | Escalation path below |
| Data issue causing behavior | **NOT A BUG** | Fix test data |
| Environment/deployment issue | **NOT A BUG** | Note env issue |

Finding verdicts are exactly **CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE** (qa-standards → Verdict Contract); they describe one finding, never a run. In the verdict line, name the escape classes you actively checked (E1–E13); an unchecked class is a NOT YET VERIFIED row, not silence.

## CANNOT CONFIRM — Escalation Path
Run in order; stop as soon as reproduction succeeds.
- **Round 1 — Different user** (same role; then a 2nd account of that role — `<role account: PROJECT-PROFILE.md §7>`).
- **Round 2 — Different test data** (other valid records / states: draft vs published, active vs inactive; and the reporter's original input class if not yet tried).
- **Round 3 — Clean session** (clear cookies, re-auth — rules out stale token/UI).
- **Round 4 — Direct API** (bypass UI via `mcp__http-client__*` or the §14 typed tool using the Pre-Step contract; fails without UI = backend, passes = FE-specific).
- **Intermittent signal (fails only sometimes)?** Before declaring Unverifiable -> `Skill(flaky-race-verifier)` to quantify the reproduction rate and find the race/timing cause.
- **Root cause non-obvious after the rounds?** If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`), escalate to `Skill(superpowers:systematic-debugging)` (hypothesis -> isolate -> verify); otherwise do it by hand: state ONE hypothesis, design the single observation that would falsify it, run it, record the result in the ledger, then move to the next hypothesis. Do this before declaring unverifiable.
- **All rounds fail -> Declare Unverifiable.** Document exact steps per round, users/data tried, network captured, and what would be needed to reproduce. Do NOT loop the same approach. "Not found ≠ not present" (Judgement Discipline #3): state which search scopes, environments, fixtures and code paths were ruled out.

---

## Evidence (Confirmed bugs only)
Build the **Evidence Ledger** with provenance (qa-standards): `| Evidence ID | Type | Source | File/URL/Tool | Env | Branch / Commit | Captured at | What it proves |`. Save attachments to the run folder `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` (HHMMSS avoids parallel-session collisions) — `Skill(evidence-manager)` files them and returns the ledger. Write them via `mcp__filesystem__write_file` or Bash heredoc (the Write/Edit tool is blocked for `qa-evidence/`); Playwright screenshots: pass `filename: qa-evidence/<run folder>/<name>.png` to `browser_take_screenshot` (a bare filename saves to the repo root, NOT qa-evidence). On CONFIRMED, hand the ledger + layer + input class to `Skill(bug-report)`.

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never claim success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it allows). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep for the endpoint/path/user-ID/symptom; UPDATE an existing entry (esp. on DUPLICATE-CHECK) instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** bug + date, verdict (CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE), layer, reproduction rate, input class used, test data (IDs / account identifiers — never passwords), root-cause `path:line`, escape classes checked, any prior memory confirmed/disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
