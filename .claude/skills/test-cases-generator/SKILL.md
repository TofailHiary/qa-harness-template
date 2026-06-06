---
name: test-cases-generator
description: Use when you need an executable, traceable test plan before testing a user story, feature, PR, API, or bug fix — produces prioritized, categorized cases mapped to the right execution tool, each with steps + expected result + evidence required. Triggers include "generate test cases", planning coverage for a change, and Phase 0 of /full-qa or /qa-validate.
argument-hint: "user story, feature, PR, or API endpoint"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)"]
---

# Test Cases Generator

Generate structured, **executable** test cases in Markdown tables (NOT code blocks).

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Impact Analysis, Test-Case Quality Bar, Evidence Ledger).

## ARGUMENTS
$ARGUMENTS

If input is insufficient, ask for: **what** it does, **who** it affects (roles), **where** it lives (pages/routes/APIs). If the source is a Jira ticket, pull acceptance criteria via `mcp__claude_ai_Atlassian__getJiraIssue`.

---

## Step 1: Understand + Cross-check memory + Impact Analysis
1. Analyze the story / AC / PR diff (`mcp__github__pull_request_read`, `mcp__github__list_commits`). Extract acceptance criteria — each becomes a Requirement ID for traceability.
2. **Cross-check memory** — Grep `~/.claude/projects/c--Users-<user>-<project>/memory/*.md` for the feature, IDs, file paths; fold known regression-risk areas into the plan.
3. **Impact Analysis** (qa-standards) — enumerate the indirect blast radius (shared FE components, shared endpoints, shared tables, async consumers, caches, downstream reports). **Generate cases for the blast radius, not just the changed surface** — this is where missed bugs live.

## Step 2: Investigate Code, DB, API
- **FE:** components in `<frontend repo: PROJECT-PROFILE.md §3/§9>/src/` (current, default) and `<legacy frontend repo: PROJECT-PROFILE.md §3>/src/` (legacy); API calls in `<frontend repo: PROJECT-PROFILE.md §3/§9>/src/libs/` / `<api-layer: PROJECT-PROFILE.md §9>`.
- **BE:** routes in `<backend repo: PROJECT-PROFILE.md §3/§9>/routes/`, models in `<backend repo: PROJECT-PROFILE.md §3/§9>/models/`.
- **Admin:** controllers in `<admin repo: PROJECT-PROFILE.md §3/§9>/controllers/`.
- **DB:** `DESCRIBE` / `SELECT` on relevant tables via `mcp__mcp_server_mysql__mysql_query`; confirm test data exists for each planned case (note where it's missing).
- **API surface:** `mcp__postman-api-mcp__searchPostmanElements` then `getCollectionFolder` to enumerate every endpoint, method, auth, body schema before writing API cases.

## Step 3: Generate Test Cases (ALL IN TABLES)

Cover every applicable category; skip ones that don't apply. **10 categories:** Positive · Negative (incl. SQLi/XSS) · Boundary · DB Integrity · API (200/400/401/403/404, schema, pagination) · UI/Browser (load, forms, console, network, loading/empty states) · Security (RBAC, cross-tenant isolation, token expiry) · Regression (the Step 1 blast radius still works) · E2E (full journeys across roles) · Data Consistency (DB=API=Browser).

**Every case uses this executable format** (qa-standards Test-Case Quality Bar):

| TC ID | Requirement/AC | Scenario | Preconditions | Test Data | Steps | Expected | Layer | Role | Priority | Automation? | Execute With | Evidence Required |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

- **Requirement/AC** — the AC or risk this traces to (traceability; "—" only for exploratory cases).
- **Test Data** — concrete IDs/emails/states the case needs (from Step 2); flag "NEEDS PREP" if absent.
- **Expected** — the precise observable result. A case with no expected result is not a test.
- **Priority** — P1/P2/P3 **with a one-word reason** (e.g. "P1: data-integrity", "P1: auth", "P2: edge").
- **Automation?** — Yes/No candidate for `automation-writer` later.
- **Execute With** — which skill/tool runs it: `db-check` / `api-test` / `browser-test` / `security-review` / `perf-test`.
- **Evidence Required** — what proof closes it (DB result / API response / screenshot / console+network).

---

## Step 4: Output Summary

**Counts** — `| Category | Count | P1 | P2 | P3 |`

**Coverage matrix** (qa-standards) — confirm every dimension that applies is covered; a blank cell is a gap to name, not hide:
`| Dimension | Covered? | TC IDs |` for Roles, States, Inputs(+/-), Flow, Cross-tenant, Regression.

**Risk areas (risk-scored)** — `| Risk | Likelihood (H/M/L) | Impact (H/M/L) | Mitigating TC IDs |`. Highest Likelihood×Impact first.

---

## Step 5: Handoff (optional)
If the user proceeds, convert to TodoWrite tasks grouped by priority (P1 first), each tagged with its **Execute With** skill so the right specialist runs it.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it allows). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the feature/IDs; UPDATE an existing entry instead of duplicating.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** feature + date, scope/AC covered, # cases per category, highest risk areas, any test data that NEEDS PREP, blast-radius areas to regression-test next time.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
