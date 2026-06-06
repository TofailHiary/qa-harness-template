---
name: perf-test
description: Use when a page, endpoint, or feature needs performance measurement — checking page load / Core Web Vitals, API response times, slow DB queries, payload sizes, or resource usage; or confirming a change did not regress performance. Triggers include "measure page load", "is this endpoint slow", "check the query plan", "perf test this", "did this regress performance".
argument-hint: "page URL, endpoint, or feature to test"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__http-client__http_get", "mcp__http-client__http_post", "mcp__http-client__http_request", "mcp__http-client__set_default_headers", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*"]
---

# Performance Testing

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/perf-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Measure and analyze performance across all layers of the application.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any measurement
State the scope before the first trace/request. Do not measure until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Pages / endpoints under test | |
| QA mode | targeted / regression / full |
| Roles in scope | Admin / Manager / User / Guest |
| DB entities / tables | |
| Dataset sizes to test (empty / small / large) | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Out of scope (explicit) | |

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every finding (bottleneck OR PASS) maps to >=1 row carrying the **actual timing / network numbers** (trace metric, response ms, query time, payload bytes, request count). A threshold claim with no measured number does not exist.

| Evidence ID | Type | Source | File / URL / Tool | What it proves (number) |
|---|---|---|---|---|

---

## Environment

- **Admin Portal:** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main App (Primary FE — Test, DEFAULT):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main App (Primary FE — Dev):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main App (Legacy FE — Test, opt-in):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main App (Legacy FE — Dev, opt-in):** <the relevant URL: PROJECT-PROFILE.md §5>
- **FE selection:** benchmark the primary FE by default. Benchmark the legacy FE (the legacy FE URL: PROJECT-PROFILE.md §5) only when the scope is explicitly about the legacy frontend. Compare both when measuring primary-vs-legacy regressions.
- **Database:** <test DB name: PROJECT-PROFILE.md §6> at <DB host: PROJECT-PROFILE.md §6>

---

## Performance Test Categories

### 1. Page Load Performance
Using `mcp__chrome-devtools__performance_start_trace` and `mcp__chrome-devtools__performance_stop_trace`:
1. Start performance trace
2. Navigate to page via `mcp__playwright__browser_navigate`
3. Wait for page to fully load
4. Stop trace and analyze with `mcp__chrome-devtools__performance_analyze_insight`

**Thresholds:**
| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| First Contentful Paint | < 1.5s | < 3s | > 3s |
| Largest Contentful Paint | < 2.5s | < 4s | > 4s |
| Time to Interactive | < 3s | < 5s | > 5s |
| Total Blocking Time | < 200ms | < 500ms | > 500ms |

### 2. API Response Times
Using `mcp__http-client__*`, measure response time for each endpoint:
- GET requests: should respond < 500ms
- POST/PUT requests: should respond < 1000ms
- List/search with pagination: should respond < 1500ms
- Complex aggregation endpoints: should respond < 3000ms

Test with: no data, small dataset, large dataset (if available).

### 3. Database Query Performance
Using `mcp__mcp_server_mysql__mysql_query`:
```sql
-- Check slow queries
EXPLAIN SELECT ... FROM [table] WHERE ...;

-- Check table sizes
SELECT table_name, table_rows, data_length, index_length
FROM information_schema.tables
WHERE table_schema = '<test DB name: PROJECT-PROFILE.md §6>'
ORDER BY data_length DESC;

-- Check missing indexes on commonly queried columns
SHOW INDEX FROM [table_name];
```

### 4. Network Analysis
Using `mcp__chrome-devtools__list_network_requests`:
- Count total requests per page load
- Identify large payloads (> 1MB)
- Identify slow requests (> 2s)
- Check for unnecessary duplicate requests
- Verify caching headers (Cache-Control, ETag)

### 5. Console Errors Impact
Using `mcp__chrome-devtools__list_console_messages`:
- JavaScript errors that could cause re-renders
- Memory leak warnings
- Deprecation warnings

---

## Execution Flow

1. **Identify target** — pages, endpoints, or features to test
2. **Baseline** — measure current performance (capture the number in the ledger)
3. **Analyze** — identify bottlenecks
4. **Report** — document findings with metrics

---

## Output Format

### Performance Report

| Test | Target | Metric | Value | Threshold | Status |
|------|--------|--------|-------|-----------|--------|
| Page Load | /dashboard | LCP | 2.1s | < 2.5s | PASS |
| API | GET /api/users | Response | 340ms | < 500ms | PASS |
| DB | users table | Query time | 120ms | < 200ms | PASS |

### Bottlenecks Identified

| # | Layer | Issue | Impact | Recommendation |
|---|-------|-------|--------|---------------|

### Overall Performance Rating
- **GOOD** — All metrics within thresholds
- **ACCEPTABLE** — Some metrics in acceptable range, no critical issues
- **POOR** — Critical performance issues found

(Under the full-qa strict policy any threshold FAIL is a bug -> NO-GO; this skill reports the measured rating, the verdict call is the orchestrator's.)

---

## Superpowers escalation (only when it adds value)
- Before declaring a target GOOD / a metric PASS -> `superpowers:verification-before-completion` (numbers before assertions).
- A non-obvious bottleneck whose root cause is unclear after the standard pass -> `superpowers:systematic-debugging`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page/endpoint/table/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** target + date, rating (GOOD/ACCEPTABLE/POOR), bottlenecks (layer, measured number vs threshold, NEW/DUPLICATE), test data (URLs/endpoints/dataset sizes), root-cause `path:line` (slow query / N+1 / unindexed column), regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
