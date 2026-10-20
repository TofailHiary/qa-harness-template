---
name: test-cases-generator
description: Use when you need an executable, traceable test plan before testing a user story, feature, PR, API, or bug fix — produces prioritized, categorized cases mapped to the right execution tool, each with steps + expected result + evidence required. Triggers include "generate test cases", planning coverage for a change, and Phase 0 of /full-qa or /qa-validate.
argument-hint: "user story, feature, PR, or API endpoint"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)", "Write"]
---

# Test Cases Generator

> **Capability note:** This skill is **always on** (utility). Read `PROJECT-PROFILE.md` §2 (Capability Map)
> first and skip the investigation steps whose capability is `off` — no DB → no `DESCRIBE`/`SELECT`
> (mark test data "NEEDS PREP / unverified"); no Postman → enumerate the API from the routes file; no Jira →
> the user pastes the story and AC. Say which steps were skipped in the output. If `PROJECT-PROFILE.md` is
> blank, STOP and tell the user to run `/configure-project`.

Generate structured, **executable** test cases in Markdown tables (NOT code blocks).

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Impact Analysis,
Test-Case Quality Bar, Evidence Ledger, Authoritative Source Hierarchy, Execution Register).

## ARGUMENTS
$ARGUMENTS

If input is insufficient, ask for: **what** it does, **who** it affects (roles), **where** it lives
(pages/routes/APIs). If the source is a ticket in the issue tracker (`PROJECT-PROFILE.md` §15), pull the
acceptance criteria with the tracker tool (`mcp__claude_ai_Atlassian__getJiraIssue` when Jira is `on`;
otherwise ask the user to paste the story). Read the ticket **comments** too — the latest developer comment
often supersedes the description and is part of the contract.

---

## Step 1: Understand + Cross-check memory + Impact Analysis
1. Analyze the story / AC / PR diff (`mcp__github__pull_request_read`, `mcp__github__list_commits`, or the
   local diff in `<backend repo: PROJECT-PROFILE.md §3/§9>` / `<frontend repo: PROJECT-PROFILE.md §3/§9>`).
   Extract acceptance criteria — each becomes a Requirement ID for traceability.
2. **Cross-check memory** — Grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for the feature, IDs, file
   paths; fold known regression-risk areas into the plan.
3. **Impact Analysis** (qa-standards) — enumerate the indirect blast radius (shared FE components, shared
   endpoints, shared tables, async consumers in `PROJECT-PROFILE.md` §11, caches, downstream reports).
   **Generate cases for the blast radius, not just the changed surface** — this is where missed bugs live.
4. **Ambiguous or missing AC → grill first.** If a criterion can be read two ways, or the story has no AC,
   resolve it before writing a single case:
   - If the `mattpocock-skills` plugin is installed (`PROJECT-PROFILE.md` §17), run
     `Skill(mattpocock-skills:grilling)` on the story.
   - Otherwise do the equivalent by hand: ask in **numbered rounds**; each round holds every question whose
     prerequisites are already settled; each question carries a **recommended answer** and the fact it rests
     on (code `path:line`, DB row, ticket comment); stop when no open question remains.
   - **Facts the code or DB can answer are looked up in THIS session** — never asked of the user, and never
     handed to a sub-agent when the sub-agent policy (`PROJECT-PROFILE.md` §16) says in-session only, even
     though the plugin's own instructions suggest dispatching one.
   - Record each resolved answer next to its Requirement ID as the **cited source** of the expected result
     (qa-standards → Authoritative Source Hierarchy: nothing is called "expected" without a citation).
   - Product owner absent: log the ambiguity in the Open Questions table (Step 4), take the code-derived
     reading, and label every case that depends on it **INFERRED**.
5. **Sample files** for upload / import / parser cases come from the sample-file library in
   `PROJECT-PROFILE.md` §13 (see `test-data-manager` for the per-input-class fixture rows). **Never test a
   parser with one input class** — one file per equivalence class (text-layer PDF, scanned/image-only PDF,
   empty file, oversized file, wrong type, malformed header, non-ASCII content …).

## Step 1b: Derive the denominator M from the code — never from intuition
Before writing any case, enumerate **from the CODE** the dimensions that select behaviour, and multiply
them: **origin × mode × type × action** at minimum. Examples of dimensions: origin = existing / add-new /
clone / file-import / search-import; mode = online / offline (or mode A / mode B from the enum the code
switches on); type = the entity sub-types the handler branches on; action = per-item save / bulk save /
next-step. Add any further dimension the code branches on (role, feature flag, tenant setting).

- **Print the matrix with its cell count.** The Scope Lock's **M** is that number, not an estimate, and
  every cell is either covered by a TC ID or listed as a named gap.
- *(illustrative)* a plan once declared "7 of 12 covered" from intuition; the code-derived matrix had 24
  cells, and the 5 cells nobody had listed held the data-loss regression that escaped.
- Dimensions come from `switch`/`if` on enum columns, route parameters, request-body discriminators and
  feature flags — Grep the handler and the FE caller, do not infer them from the UI.

## Step 2: Investigate Code, DB, API
- **FE:** components in `<frontend repo: PROJECT-PROFILE.md §3/§9>` (and `<legacy frontend repo:
  PROJECT-PROFILE.md §3>` when the project keeps one); API calls in `<frontend API layer: PROJECT-PROFILE.md §9>`.
- **BE:** routes in `<routes path: PROJECT-PROFILE.md §9>`, models in `<backend models: PROJECT-PROFILE.md §9>`.
- **Admin:** controllers in `<admin controllers: PROJECT-PROFILE.md §9>`. **Verify the path exists** (Glob
  it) before citing it — do not assume a conventional layout; a plan that cites a non-existent path sends
  the executor to the wrong place.
- **DB:** `DESCRIBE` / `SELECT` on relevant tables via `mcp__mcp_server_mysql__mysql_query` (DB tool:
  `PROJECT-PROFILE.md` §6); confirm test data exists for each planned case (note where it's missing).
- **API surface:** `mcp__postman-api-mcp__searchPostmanElements` then `getCollectionFolder` to enumerate
  every endpoint, method, auth, body schema before writing API cases (Postman `on`); otherwise enumerate
  from the routes file. If `PROJECT-PROFILE.md` §14 lists a project MCP server with typed tools for this
  surface, prefer it for probing; otherwise use `mcp__http-client__*`.

## Step 3: Generate Test Cases (ALL IN TABLES)

Cover every applicable category; skip ones that don't apply. **10 categories:** Positive · Negative (incl.
SQLi/XSS) · Boundary · DB Integrity · API (200/400/401/403/404, schema, pagination) · UI/Browser (load,
forms, console, network, loading/empty states) · Security (RBAC, cross-tenant isolation, token expiry) ·
Regression (the Step 1 blast radius still works) · E2E (full journeys across roles) · Data Consistency
(DB=API=Browser).

**Every case uses this executable format** (qa-standards Test-Case Quality Bar, plus the two mandatory
columns from this skill):

| TC ID | Requirement/AC | Scenario | Preconditions | Test Data | Input class | Steps | Expected | Expected source | Path exercised | Layer | Role | Priority | Automation? | Execute With | Evidence Required |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

- **Requirement/AC** — the AC or risk this traces to (traceability; "—" only for exploratory cases).
- **Test Data** — concrete IDs/emails/states the case needs (from Step 2); flag "NEEDS PREP" if absent.
  Identifiers only — passwords are env-var names from `PROJECT-PROFILE.md` §7, never values.
- **Input class** — the equivalence class of the INPUT, not just the input: text-layer PDF vs
  scanned/image-only; partition N=1 vs N>1; mode A vs mode B; field populated vs blank/whitespace; one
  item vs many vs the cap. Mandatory for parser / upload / import surfaces; "—" elsewhere.
- **Expected** — the precise observable result. A case with no expected result is not a test.
- **Expected source** — **every expected value needs a quotable source**: an AC line, a tracker comment, a
  code reference (`path:line`), a DB row, a spec in `PROJECT-PROFILE.md` §13. If no source exists, write
  `Expected: UNKNOWN — ask` and put the question in the Open Questions table. **Never write down what the
  UI happens to do today as the expectation** — that turns the test into a tautology that can only pass.
- **Path exercised** — `validation-only` (no network call fires — the client rejects the input) or `write`
  (request + DB read-back). **A green validation-only case never proves the feature**; every feature needs
  at least one `write` case per matrix cell that writes.
- **Priority** — P1/P2/P3 **with a one-word reason** (e.g. "P1: data-integrity", "P1: auth", "P2: edge").
- **Automation?** — Yes/No candidate for `automation-writer` later.
- **Execute With** — which skill/tool runs it: `db-check` / `api-test` / `browser-test` / `security-review`
  / `perf-test` / `test-together`.
- **Evidence Required** — what proof closes it (DB result / API response / screenshot / console+network).

**Content-import scope.** If the story ships or relies on new content (templates, catalog rows, documents,
sample files, a bulk import), add cases that answer: *what cardinality / mode / format does this introduce
that production has never held?* One case per answer, run FIRST — an import is a release (qa-standards →
Escape classes & their gates; `/latent-pattern-sweep` when the import is large).

---

## Step 4: Output Summary

**Denominator statement** — `M = <N> cells (<dimensions>)`; `covered: <k> cells by TC …`; `uncovered: <list>`.
The Scope Lock copies M from here.

**Counts** — `| Category | Count | P1 | P2 | P3 |`

**Coverage matrix** (qa-standards) — confirm every dimension that applies is covered; a blank cell is a gap
to name, not hide: `| Dimension | Covered? | TC IDs |` for Roles, States, Inputs(+/-), **Input class**,
Flow, **Write path**, Cross-tenant, Regression.

**Risk areas (risk-scored)** — `| Risk | Likelihood (H/M/L) | Impact (H/M/L) | Mitigating TC IDs |`.
Highest Likelihood×Impact first.

**Open questions** — `| # | Question | Recommended answer | Fact it rests on | Status (asked / resolved /
INFERRED) | Affected TC IDs |` — one row per unresolved ambiguity from Step 1.4.

---

## Step 5: Handoff + execution policy

**Default policy (`PROJECT-PROFILE.md` §16): every generated case is executed; priority only orders the
work.** Priority is not permission to skip. A case that is not run is recorded as **NOT YET VERIFIED** in
the Execution Register (qa-standards) and counts against the confidence line — it is never silently
dropped, and a verdict cannot call the plan "covered" while a case is open. Only the profile's QA policy
section can change this default; if it does, say which cases it exempts and why.

If the user proceeds, convert the cases to TodoWrite tasks grouped by priority (P1 first), each tagged with
its **Execute With** skill so the right specialist runs it. The generated table IS the Execution Register
skeleton — executors fill in Actual / result / evidence per row.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot
be persisted -> **HALT and tell the user**.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the
   only path it allows). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the feature/IDs; UPDATE an existing entry instead of
   duplicating.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** feature + date, scope/AC covered, the code-derived matrix and its M, # cases per category,
   highest risk areas, open questions and how they were resolved (or INFERRED), any test data that NEEDS
   PREP, blast-radius areas to regression-test next time.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
