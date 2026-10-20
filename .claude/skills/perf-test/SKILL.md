---
name: perf-test
description: Use when a page, endpoint, or feature needs performance measurement — checking page load / Core Web Vitals, API response times, slow DB queries, payload sizes, or resource usage; or confirming a change did not regress performance. Triggers include "measure page load", "is this endpoint slow", "check the query plan", "perf test this", "did this regress performance".
argument-hint: "page URL, endpoint, or feature to test"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__http-client__http_get", "mcp__http-client__http_post", "mcp__http-client__http_request", "mcp__http-client__set_default_headers", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "Skill(qa-standards)", "Write"]
---

# Performance Testing

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/perf-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.
> Run only the categories whose capability is `on`: Browser `off` -> skip categories 1, 4, 5;
> API `off` -> skip category 2; DB `off` -> skip category 3. Name every skipped category in the report.


Measure and analyze performance across all layers of the application.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below. Vocabulary (Verdict Contract, Execution Register, Evidence provenance) is defined there — this skill cites it and does not restate it.

## ARGUMENTS
$ARGUMENTS

If no arguments: ask which page / endpoint / feature to measure, against which dataset size, and whether a baseline exists to compare with, then STOP.

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any measurement
State the scope before the first trace/request. Do not measure until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Pages / endpoints under test | |
| QA mode | targeted / regression / full |
| Roles in scope | `<roles: PROJECT-PROFILE.md §8>` (e.g. Admin / Manager / User / Guest) |
| DB entities / tables | `<key tables: PROJECT-PROFILE.md §10>` |
| Dataset sizes to test (empty / small / large) | |
| Baseline to compare with (same env + build, or none) | |
| Environment | Test (default) / Dev / Prod (read-only) — URL from `PROJECT-PROFILE.md §5` |
| Branch / commit under test | `<branch: PROJECT-PROFILE.md §3>` @ short sha — captured once, reused on every evidence row |
| Thresholds in force | template defaults below, unless `PROJECT-PROFILE.md §16` sets others — state which |
| Run folder | `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` |
| Out of scope (explicit) | |

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every finding (bottleneck OR PASS) maps to >=1 row carrying the **actual timing / network numbers** (trace metric, response ms, query time, payload bytes, request count). A threshold claim with no measured number does not exist. Stamp every row with its provenance (qa-standards -> Evidence provenance) — performance numbers are environment- and build-bound more than any other evidence: a number measured on DEV, on a local replica, or on PROD is evidence for THAT environment only and is never reported as the target environment's number.

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves (number) |
|---|---|---|---|---|---|---|---|

### Measurement discipline
- Measure each target **at least 3 times** and report the median (and the spread); a single sample is a lead, not a result.
- State **cold vs warm** (first load vs cached; first query vs buffer-pool warm) — report both when they differ materially.
- Record the **dataset size** behind the number (row counts for the tables in scope); a fast page on an empty tenant proves nothing about a full one.
- A regression claim needs a baseline from the **same environment and comparable build**; otherwise report the number without the word "regression".
- Save the raw trace / response timing / `EXPLAIN` output under `qa-evidence/<run-folder>/` (filesystem MCP or Bash heredoc — Write/Edit are hook-blocked there).

---

## Environment

- **Admin surface:** `<admin URL: PROJECT-PROFILE.md §5>`
- **Main app (primary FE — Test, DEFAULT):** `<main app URL: PROJECT-PROFILE.md §5>`
- **Main app (primary FE — Dev):** `<main app URL: PROJECT-PROFILE.md §5>`
- **Legacy / secondary FE (opt-in):** the legacy FE URL in `PROJECT-PROFILE.md §5`, if the project has one
- **FE selection:** benchmark the primary FE by default. Benchmark the legacy FE only when the scope is explicitly about it. Compare both when measuring a primary-vs-legacy regression — on the same environment, same data, same session.
- **API base:** `<API base URL: PROJECT-PROFILE.md §5>`
- **Database:** `<test DB name: PROJECT-PROFILE.md §6>` at `<DB host: PROJECT-PROFILE.md §6>` via `<DB tool: PROJECT-PROFILE.md §6>`

---

## Performance Test Categories

### 1. Page Load Performance
Using `mcp__chrome-devtools__performance_start_trace` and `mcp__chrome-devtools__performance_stop_trace`:
1. Start performance trace
2. Navigate to page via `mcp__playwright__browser_navigate`
3. Wait for page to fully load (network idle, not just DOMContentLoaded)
4. Stop trace and analyze with `mcp__chrome-devtools__performance_analyze_insight`

**Thresholds (template defaults, unless `PROJECT-PROFILE.md §16` sets others):**
| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| First Contentful Paint | < 1.5s | < 3s | > 3s |
| Largest Contentful Paint | < 2.5s | < 4s | > 4s |
| Time to Interactive | < 3s | < 5s | > 5s |
| Total Blocking Time | < 200ms | < 500ms | > 500ms |
| Cumulative Layout Shift | < 0.1 | < 0.25 | > 0.25 |

### 2. API Response Times
Using `mcp__http-client__*` (if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it for auth and request shape; the timing still comes from the raw HTTP call), measure response time for each endpoint. Clear stale headers (`set_default_headers` with `merge: false`) before setting auth.

**Thresholds (template defaults, unless `PROJECT-PROFILE.md §16` sets others):**
- GET requests: should respond < 500ms
- POST/PUT requests: should respond < 1000ms
- List/search with pagination: should respond < 1500ms
- Complex aggregation endpoints: should respond < 3000ms

Test with: no data, small dataset, large dataset (if available — see `/test-data-manager` for locating a large tenant). Measure the **last page** of a paginated list as well as the first; `OFFSET`-based pagination degrades with page number. Any POST/PUT used for timing goes through the qa-standards Mutation Safety Gate.

### 3. Database Query Performance
Using `mcp__mcp_server_mysql__mysql_query` (DB tool: `PROJECT-PROFILE.md §6`; adapt `EXPLAIN` / `SHOW INDEX` syntax to the engine in `PROJECT-PROFILE.md §4`). Find the real query first — read the ORM call in `<backend repo: PROJECT-PROFILE.md §3/§9>` or enable the engine's query log — then plan it:
```sql
-- Query plan of the query the endpoint actually runs (copy it from the ORM log, not a guess)
EXPLAIN SELECT ... FROM [table] WHERE ...;

-- Check table sizes
SELECT table_name, table_rows, data_length, index_length
FROM information_schema.tables
WHERE table_schema = '<test DB name: PROJECT-PROFILE.md §6>'
ORDER BY data_length DESC;

-- Check indexes on the columns the WHERE / JOIN / ORDER BY use
SHOW INDEX FROM [table_name];
```
Flag: full table scans (`type = ALL`) on large tables, `Using filesort` / `Using temporary` on list endpoints, N+1 patterns (one query per row in the network/ORM log), missing index on a FK or a soft-delete column used in every WHERE, and `SELECT *` on wide tables. Record the plan output in the ledger.

### 4. Network Analysis
Using `mcp__chrome-devtools__list_network_requests`:
- Count total requests per page load
- Identify large payloads (> 1MB)
- Identify slow requests (> 2s)
- Check for unnecessary duplicate requests (the same endpoint fired twice on one render)
- Verify caching headers (Cache-Control, ETag) and compression (Content-Encoding)
- Note over-fetching: a list endpoint returning fields the page never renders

### 5. Console Errors Impact
Using `mcp__chrome-devtools__list_console_messages`:
- JavaScript errors that could cause re-renders
- Memory leak warnings
- Deprecation warnings
(Any error found here is also a finding for `/observability-check` — record it, do not drop it because the page was fast.)

---

## Execution Flow

1. **Identify target** — pages, endpoints, or features to test; capture the branch / commit and the dataset sizes
2. **Baseline** — measure current performance (3+ samples; capture the median in the ledger with provenance)
3. **Analyze** — identify bottlenecks; trace each slow number to its layer (FE render / network / API handler / query) before naming it
4. **Report** — document findings with metrics, the Execution Register and the verdict

---

## Output Format

### Performance Report

| Test | Target | Metric | Value (median of N) | Threshold | Dataset | Env @ commit | Status |
|------|--------|--------|---------------------|-----------|---------|--------------|--------|
| Page Load | /dashboard | LCP | 2.1s (n=3) | < 2.5s | 1,200 rows | Test @ abc1234 | PASS |
| API | GET /api/users | Response | 340ms (n=3) | < 500ms | 5,000 users | Test @ abc1234 | PASS |
| DB | users table | Query time | 120ms | < 200ms | 5,000 rows | Test @ abc1234 | PASS |

`Status` is one of the canonical area results (qa-standards -> Verdict Contract): **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED**. A target in scope that was not measured is NOT YET VERIFIED — never an implied pass. This table doubles as the **Execution Register** for the run.

### Bottlenecks Identified

| # | Layer | Issue | Measured | Impact | Root cause `path:line` / query | Recommendation |
|---|-------|-------|----------|--------|-------------------------------|---------------|

### Overall Performance Rating
- **GOOD** — All metrics within thresholds
- **ACCEPTABLE** — Some metrics in acceptable range, no critical issues
- **POOR** — Critical performance issues found

The rating is this skill's alias; it prints **after** the canonical run verdict (qa-standards -> Verdict Contract: **GO / NO-GO / PARTIAL**) with the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`. Under the strict-binary default policy any threshold FAIL is a confirmed bug -> NO-GO; if `PROJECT-PROFILE.md §16` sets another verdict policy (e.g. perf findings are advisory below a severity), apply it and say which one you applied. When this skill runs inside `/full-qa`, it reports the measured rating and the register; the run-level verdict call is the orchestrator's.

---

## Plugins & escalation (only when it adds value)
If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`):
- Before declaring a target GOOD / a metric PASS -> `superpowers:verification-before-completion` (numbers before assertions).
- A non-obvious bottleneck whose root cause is unclear after the standard pass -> `superpowers:systematic-debugging`.

If the `mattpocock-skills` plugin is installed, `mattpocock-skills:diagnosing-bugs` (diagnosis phases only) fits a performance regression whose layer is unclear. Otherwise do the equivalent by hand: re-run the measurement with one variable changed at a time (dataset size, cache cold/warm, role, endpoint params), note which change moves the number, and read the code path that the moving variable selects. If `PROJECT-PROFILE.md §16` says sub-agents are disabled, run everything in-session.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/endpoint/table/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** target + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; the rating GOOD/ACCEPTABLE/POOR may follow in parentheses), the measured numbers with env @ commit and dataset size (so a later run can compare like with like), bottlenecks (layer, measured number vs threshold, NEW/DUPLICATE), test data (URLs/endpoints/dataset sizes), root-cause `path:line` (slow query / N+1 / unindexed column), regression risks for next time, any prior memory disproved. A remembered number is a lead for the next run, never its baseline — re-measure.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
