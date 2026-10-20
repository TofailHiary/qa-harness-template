---
name: db-check
description: Use when a feature, story, PR, or bug needs deep database-layer validation — schema vs ORM-model drift, foreign-key / orphan integrity, soft-delete mechanism correctness, data-quality / enum / null checks, tenant scoping, relationship-count reconciliation, or index coverage. Triggers include "check the DB", "db-check a table", "validate schema for X", "are there orphaned rows", "do the counts reconcile", "which tables have deleted_at", "confirm a prod data repro".
argument-hint: "table name, feature, or full"

agent: db-validator
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__filesystem__write_file", "Write"]
---

# Database Validation Specialist

> **Capability gate:** This skill requires **DB**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no DB configured, so `/db-check` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Deep database integrity validation for this project — schema, FK/orphan, soft-delete, data quality, counts, tenant scoping, enum width, indexes — every finding backed by the exact query and its result.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below. Verdict words come from its **Verdict Contract**; what a value *should* be comes from its **Authoritative Source Hierarchy** (the database and its `COLUMN_COMMENT` semantics are a source of state, never of correctness on their own).

**Sub-agent knob:** if `PROJECT-PROFILE.md §16` says sub-agents are disabled, run this skill in-session; otherwise the `db-validator` agent may run it under the orchestrator's Scope Lock (its report is a lead — the orchestrator re-runs any query it files).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which table(s), feature, or entity set should I db-check (or `full`)? Are we validating test/dev, or confirming a prod data repro (read-only)?"

Do NOT guess scope. Do NOT run a single query until the Scope Lock is filled.

---

## Scope Lock (REQUIRED — before any query runs)

State the scope as a contract before the first query (qa-standards -> Scope Lock). If a critical field is unknown, ask — do not guess.

| Field | Value |
|---|---|
| Feature / story / bug / PR | |
| Tables / entities in scope | |
| Tenant key(s) for those tables | direct column or FK path (`PROJECT-PROFILE.md §10`) |
| Checks to run | schema / FK-orphan / data-integrity / index / relationship-counts / data-quality / tenant-scoping / enum-width |
| Related tables (blast radius) | FK parents + children, report/dashboard readers, aggregates, async writers (`PROJECT-PROFILE.md §11`) |
| Out of scope (explicit) | |
| Environment | Test/Dev (default) / Prod (read-only) |
| Branch / commit of the owning repo | `<branch: PROJECT-PROFILE.md §3> @ <git rev-parse --short HEAD>` — for evidence provenance |
| Risk level | Low / Medium / High |
| Stop conditions | table/column missing / wrong DB / schema not migrated |

Do not silently narrow scope to make a PASS easier; if you drop a check, say so and why.

---

## Layer Rule — read `.claude/rules/db-gotchas.md` and `PROJECT-PROFILE.md §10` before querying

The project's real schema gotchas live in `PROJECT-PROFILE.md §10` (table names, soft-delete columns, FK directions, enum values) and `.claude/rules/db-gotchas.md`. Typical shapes to expect *(illustrative — verify against THIS schema)*:
- `user` may have **no `role_id`** and **no `deleted_at`** — roles live in a membership / join table (`PROJECT-PROFILE.md §8`).
- A parent table may use `status enum(..., 'deleted')` instead of `deleted_at`; a membership / join table may be **hard delete** with no marker at all.
- A child table may key on `user_id` rather than the domain name you expect (`customer_id`, `member_id`).
- A `status` column is **not** always a soft-delete marker — it can be a lifecycle or result state (`pending / in_progress / complete`, `correct / wrong / na`). Read the enum before using it as an "active rows" filter.

### Confirm the soft-delete mechanism before writing any membership / active-row predicate
Run this once per table set and quote the result in the ledger (MySQL `information_schema`; use the engine equivalent for Postgres):
```sql
SELECT TABLE_NAME,
  MAX(CASE WHEN COLUMN_NAME='deleted_at' THEN 'YES' ELSE '' END) AS has_deleted_at,
  MAX(CASE WHEN COLUMN_NAME='status'     THEN COLUMN_TYPE ELSE '' END) AS status_col
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='<test DB name: PROJECT-PROFILE.md §6>' AND TABLE_NAME IN ('<table_1>','<table_2>')
GROUP BY TABLE_NAME;
```
A `WHERE deleted_at IS NULL` on a table without that column either errors or — through a joined alias or subquery — **silently returns the wrong rows**. *(illustrative)* A prevalence query once returned 0 instead of 2 because it assumed `deleted_at` on a table that uses a `status` enum; the affected users vanished from the report. Record what you find in `PROJECT-PROFILE.md §10` so the next session does not re-discover it.

### Read the column's semantic contract before judging a value
Aggregated, pipeline-written or snapshot columns often carry their rule in `COLUMN_COMMENT` — the re-aggregation rule, additive vs non-decomposable, sentinel meanings (`-1`, `NULL` vs `0`), and which columns are documented-unclamped. Judging a value without reading its comment produces both false-positive bug reports and missed real defects.
```sql
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='<test DB name: PROJECT-PROFILE.md §6>' AND TABLE_NAME='<table>'
ORDER BY ORDINAL_POSITION;
```
If the comment is empty, the contract is the ORM model + the writer's code (`path:line`) — cite it.

### Check the scope predicate before filing "missing rows"
If a reader (report, pipeline, export, dashboard) filters by a type / mode / flag column, rows outside that filter are absent **by design** — not orphans, not a defect. Quote the predicate from code (`path:line`) in the finding, or withdraw it. *(illustrative)* Two independent lanes filed the same false bug for rows a pipeline excluded on purpose because they checked one type column but not the second one the code actually filters on.

---

## Database Connection

- **Test / Dev:** host, port, DB name and user from `PROJECT-PROFILE.md §6` — tool `mcp__mcp_server_mysql__mysql_query` (DB tool: PROJECT-PROFILE.md §6; `/configure-project` rebinds the tool id when the project uses another engine). The SQL in this skill is MySQL-flavoured — for Postgres use `\d`-equivalents (`information_schema` / `pg_indexes`) in place of `DESCRIBE` / `SHOW INDEX`.
- **Prod (read-only, only if Prod-DB is `on` in §2):** `mcp__mcp_server_mysql_prod__mysql_query`, or whatever read-only prod access §6 describes (tunnel, self-contained query runner). Use it **only** to confirm a repro already found on Test or to measure prevalence. **Never mutate prod.** Environment attribution: a prod observation is evidence for prod only (qa-standards -> Evidence provenance).
- **Always schema-qualify** (`<db>.<table>`) when the tool's default database is not guaranteed.

### DB-tool gotchas *(verify per installation)*
- DATETIME may render shifted by the server timezone with a fake `Z` — use `DATE_FORMAT(col,'%Y-%m-%d %H:%i:%s')` whenever a timestamp matters.
- The tool's SQL parser may reject operators such as `<=>` — write `a <> b OR a IS NULL`.
- `SUM((a<0)+(b<0))` false-negatives on NULL — use `COUNT(CASE WHEN a<0 OR b<0 THEN 1 END)`.
- **Run queries ONE AT A TIME, never in parallel.**
- Large result sets: add `LIMIT` and a `COUNT(*)` companion query; never paste thousands of rows into the chat — save them as `<slug>.csv` evidence.

---

## Mutation Safety Gate — before any write

db-check is read-only by default. If a check genuinely requires a write (e.g. seeding a fixture to reproduce an integrity scenario), the full 7-step gate applies (qa-standards -> Mutation Safety Gate):

1. Confirm the target is **in scope**. 2. Prefer **existing disposable test data** (`Skill(test-data-manager)`). 3. **SELECT + log original state** first. 4. Have a **rollback plan**. 5. **Never mutate prod** — the prod tool is read-only by policy. 6. Every UPDATE/DELETE **has a WHERE**; never hard-DELETE — prefer the table's own soft-delete mechanism (status / `deleted_at`, as confirmed above). 7. After the test, **restore + SELECT again to confirm**, and log:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

No clean restore path -> **STOP and ask the user** before mutating.

---

## Key Tables

The authoritative list is `PROJECT-PROFILE.md §10`. Generic shape *(illustrative)*:

| Table | Purpose |
|-------|---------|
| user | All users (admins, managers, users) — role_id often NOT here |
| account / user_account | Tenants + user-account-role mappings (may have `deleted_at` or `status`) |
| order / order_item | Parent records + line-item mappings |
| subscription | Account subscriptions (may be soft-deleted) |
| invoice | Billing records |
| product / category | Catalogue and categories |
| audit_log | Append-only audit trail |
| role | Role definitions (referenced via the membership table) |

---

## Validation Categories

### 1. Schema vs ORM model
```sql
DESCRIBE [table]; SHOW CREATE TABLE [table];
```
Compare against the ORM models in `<models path: PROJECT-PROFILE.md §9>` — column types, nullability, defaults, enum members, indexes, missing/extra columns. Model <-> schema drift is a recurring bug class; call out these drift shapes explicitly:
- **Model default != DB default** — the model says `status='active'` but the column has no default, so real rows hold NULL (`SELECT COUNT(*) WHERE col IS NULL`).
- **Enum members present in the DB but absent from the model, the API union or the FE union** (enum width — qa-standards -> Judgement Discipline). Every value the column can hold must be handled by every reader.
- **Soft-delete declared in the model (`paranoid` / `deletedAt`) but the column is absent**, or the column exists and the model ignores it.
- **FK declared in the model but no constraint / index in the DB** (or the reverse).

### 2. Foreign Key / Orphans
```sql
SELECT c.id FROM [child] c
LEFT JOIN [parent] p ON c.[fk_column] = p.id
WHERE p.id IS NULL
  AND c.deleted_at IS NULL;   -- ONLY if the mechanism query showed the child HAS deleted_at; else use its status predicate, or no predicate for hard-delete tables
```
Check every FK (parent + child) per `PROJECT-PROFILE.md §10` / `.claude/rules/db-gotchas.md`; no orphans; cascade / restrict behaves as the model declares; join tables have no rows pointing at a deleted parent unless the design says they may.

### 3. Data Integrity
No unexpected duplicates (`GROUP BY ... HAVING COUNT(*) > 1` on every natural key); NOT NULL honored; status within the expected enum; dates ordered (`created_at <= updated_at`); active rows per the confirmed soft-delete mechanism; sentinel values used as the `COLUMN_COMMENT` documents them.

### 4. Index Analysis
```sql
SHOW INDEX FROM [table];
```
Indexes exist on FK columns, tenant-key columns and frequently-queried / sorted columns; flag missing indexes that risk performance (hand the query shape to `/perf-test` for an `EXPLAIN`).

### 5. Relationship Consistency (counts)
Membership counts vs the join table (users per account vs `user_account`); child rows for every processed parent (an audit / log row for every completed order); aggregate or snapshot tables (`PROJECT-PROFILE.md §11`) vs a recomputation from the source rows — **recompute, do not transcribe**: the aggregate equalling the API proves transport, not correctness.

### 6. Data Quality
No whitespace-only name fields; valid email/phone formats; no HTML/script tags in text fields (stored-XSS smell); no test-looking data in a non-test environment.

### 7. Tenant Scoping
Every row of a tenant-owned table resolves to exactly one tenant (direct column or FK path from §10); no row resolves to two tenants or to none. Cross-tenant read check: pick an id owned by tenant A, run the application's own query shape with tenant B's predicate — it must return 0 rows. Any reader query in code that omits the tenant predicate is an IDOR surface — hand it to `/security-review` with the `path:line`.

### 8. Enum / State Width
`SELECT [col], COUNT(*) FROM [table] GROUP BY [col]` on every enum / state column in scope. Compare the distinct set with (a) the DB enum, (b) the ORM model, (c) the API union, (d) the FE union. Values that exist in the DB definition but sit at 0 rows are **never-executed branches**: report them as NOT YET VERIFIED coverage and hand them to `/test-data-manager` (NEEDS PREP) or `/latent-pattern-sweep` — never as an implied pass.

---

## Impact Analysis tie-in

A table is never tested in isolation. Before the verdict, name what else touches each in-scope table — FK parents/children, **report/dashboard readers** (snapshot tables per `PROJECT-PROFILE.md §11`, reporting service dashboards), aggregates that drift from live rows, async writers (queues, Lambdas, crons listed in §11). An integrity issue in a shared table radiates into every reader — cover them (qa-standards -> Impact Analysis).

---

## Prod data repro (read-only)

Only when Prod-DB is `on` and a defect is **already reproduced on Test**: run the same read-only query against prod to measure prevalence (how many rows / tenants / users). Label every such ledger row `Env = PROD-readonly`. Never use prod to *find* bugs, never as a first stop, never with a write.

---

## Execution Flow

Scope (tables + blast radius) -> mechanism + contract queries (Layer Rule) -> run categories 1-8 in order -> Evidence Ledger + Issues table + summary (+ Execution Register in `full` / `regression` / `release` mode: one row per table x check).

**IMPORTANT:** Run queries ONE AT A TIME, never in parallel.

---

## Evidence Ledger (REQUIRED in the output)

**No evidence = no finding.** Every issue cites the **exact query + its result** (one you actually ran, not a hypothetical). PASS results need a row too — proof the check was exercised.

| Evidence ID | Type | Source | Query / Result | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

Save query dumps (`<slug>.csv`) / notes under `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` via `mcp__filesystem__write_file` (the read-only hook blocks `Write`/`Edit` for `qa-evidence/`). Findings stay in the chat, not as markdown in `qa-evidence/`.

---

## Output Format

### Summary

| Check | Tables | Passed | Failed | Issues |
|-------|--------|--------|--------|--------|
| Schema / FK / Data Integrity / Indexes / Relationship Counts / Data Quality / Tenant Scoping / Enum Width | N | N | N | N |

### Issues Found

| # | Table | Check | Issue | Severity | Query (and result) |
|---|-------|-------|-------|----------|--------------------|

Classify any data bug as FE / BE / Admin / Report / DB / Both (qa-standards -> Bug Classification). Each check ends as **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED** (qa-standards -> Verdict Contract) and the run closes with the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: ...`. State coverage gaps explicitly — an unrun check is never an implied PASS.

---

## Plugins and escalation
- Non-obvious integrity root cause after the standard query pass: if the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`) use `superpowers:systematic-debugging`; otherwise by hand — hypothesis, isolate one table / one predicate per re-run, verify with a fresh query, then classify.
- Before declaring the DB clean / PASS: `superpowers:verification-before-completion` if installed; otherwise re-run each proving query in this session and re-read the ledger row behind every PASS (evidence before assertions).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Naming `project_<slug>.md` / `feedback_<slug>.md` / `reference_<slug>.md`; frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the table/column/entity-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** feature + date + Env + commit, verdict = the canonical run verdict per qa-standards -> Verdict Contract (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), issues (table, check, severity, layer, NEW/DUPLICATE), the soft-delete mechanism and contract facts you confirmed (so §10 can be updated), test data (ids/tables/DB), root-cause location, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
