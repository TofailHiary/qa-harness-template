---
name: db-check
description: Use when a feature, story, PR, or bug needs deep database-layer validation — schema vs ORM-model drift, foreign-key / orphan integrity, soft-delete correctness, data-quality / enum / null checks, relationship-count reconciliation, or index coverage. Triggers include "check the DB", "db-check a table", "validate schema for X", "are there orphaned rows", "do the counts reconcile", "confirm a prod data repro".
argument-hint: "table name, feature, or full"

agent: db-validator
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__filesystem__write_file"]
---

# Database Validation Specialist

> **Capability gate:** This skill requires **DB**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no DB configured, so `/db-check` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Deep database integrity validation for this project — schema, FK/orphan, data quality, counts, indexes — every finding backed by the exact query and its result.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

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
| Checks to run | schema / FK-orphan / data-integrity / index / relationship-counts / data-quality |
| Related tables (blast radius) | FK parents + children, report/dashboard readers, aggregates |
| Out of scope (explicit) | |
| Environment | Test/Dev (default) / Prod (read-only) |
| Risk level | Low / Medium / High |
| Stop conditions | table/column missing / wrong DB / schema not migrated |

Do not silently narrow scope to make a PASS easier; if you drop a check, say so and why.

---

## Layer Rule — read `.claude/rules/db-gotchas.md` before querying

Always relevant here. Key gotchas it encodes:
- `user` has **no `role_id`** and **no `deleted_at`** — roles live in `user_account` -> `role`.
- `order` has **no `deleted_at`**; `order_item` keys on **`user_id`** (not a derived entity name).
- Soft-delete tables: `account`, `subscription`. Verify a `deleted_at` column exists **before** adding `WHERE deleted_at IS NULL`.

---

## Database Connection

- **Host:** <DB host: PROJECT-PROFILE.md §6> | **Port:** 3306 | **User:** admin
- **DB:** `<test DB name: PROJECT-PROFILE.md §6>` (test) / `<DB name: PROJECT-PROFILE.md §6>` (dev) — tool `mcp__mcp_server_mysql__mysql_query`
- **Prod (read-only, confirm a prod repro only):** `mcp__mcp_server_mysql_prod__mysql_query` — DB `<DB name: PROJECT-PROFILE.md §6>`; needs an SSH tunnel on `<prod DB via tunnel: PROJECT-PROFILE.md §6>` first. **Never mutate prod.**

---

## Mutation Safety Gate — before any write

db-check is read-only by default. If a check genuinely requires a write (e.g. seeding a fixture to reproduce an integrity scenario), the full 7-step gate applies (qa-standards -> Mutation Safety Gate):

1. Confirm the target is **in scope**. 2. Prefer **existing disposable test data**. 3. **SELECT + log original state** first. 4. Have a **rollback plan**. 5. **Never mutate prod** — the prod tool is read-only by policy. 6. Every UPDATE/DELETE **has a WHERE**; never hard-DELETE — prefer status / `deleted_at`. 7. After the test, **restore + SELECT again to confirm**, and log:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

No clean restore path -> **STOP and ask the user** before mutating.

---

## Key Tables

| Table | Purpose |
|-------|---------|
| user | All users (managers, admins, guests) — role_id NOT here |
| account / user_account | Accounts + user-account mappings (have `deleted_at`) |
| order / order_item | Orders + line-item mappings |
| subscription | Account subscriptions (has `deleted_at`) |
| invoice | Billing records |
| product / category | Product catalogue and categories |
| audit_log | Append-only audit trail |
| role | Role definitions (referenced via user_account) |

---

## Validation Categories

### 1. Schema
```sql
DESCRIBE [table]; SHOW CREATE TABLE [table];
```
Compare against ORM models in `<backend repo: PROJECT-PROFILE.md §3/§9>/models/` — column types, nullability, defaults; missing/extra columns (model<->schema drift is a recurring bug class).

### 2. Foreign Key / Orphans
```sql
SELECT c.id FROM [child] c
LEFT JOIN [parent] p ON c.[fk_column] = p.id
WHERE p.id IS NULL AND c.deleted_at IS NULL;   -- drop the deleted_at clause if child has no such column
```
Check every FK (parent + child) per the FK table in `.claude/rules/db-gotchas.md`; no orphans; cascade behaves.

### 3. Data Integrity
No unexpected duplicates; NOT NULL honored; status within expected enums; dates ordered (`created_at <= updated_at`); `deleted_at IS NULL` for active rows (only on tables that HAVE it).

### 4. Index Analysis
```sql
SHOW INDEX FROM [table];
```
Indexes exist on FK columns + frequently-queried columns; flag missing indexes that risk performance.

### 5. Relationship Consistency (counts)
User counts (`user` vs role query via `user_account`); account members vs `user_account`; order items vs `order_item`; audit rows for every processed `order`.

### 6. Data Quality
No whitespace-only name fields; valid email/phone formats; no HTML/script tags in text fields (stored-XSS smell).

---

## Impact Analysis tie-in

A table is never tested in isolation. Before the verdict, name what else touches each in-scope table — FK parents/children, **report/dashboard readers** (snapshot tables per `PROJECT-PROFILE.md` §11, reporting service dashboards), aggregates that drift from live rows, async writers (order processing, audit, report, and model-output Lambdas/crons). An integrity issue in a shared table radiates into every reader — cover them (qa-standards -> Impact Analysis).

---

## Execution Flow

Scope (tables + blast radius) -> run categories 1-6 in order -> Evidence Ledger + Issues table + summary.

**IMPORTANT:** Run queries ONE AT A TIME, never in parallel.

---

## Evidence Ledger (REQUIRED in the output)

**No evidence = no finding.** Every issue cites the **exact query + its result** (one you actually ran, not a hypothetical). PASS results need a row too — proof the check was exercised.

| Evidence ID | Type | Source | Query / Result | What it proves |
|---|---|---|---|---|

Save query dumps (`<slug>.csv`) / notes under `qa-evidence/<FEATURE-SLUG>/` or `qa-evidence/BUG-YYYYMMDD-HHMMSS/` via `mcp__filesystem__write_file` (the read-only hook blocks `Write`/`Edit` for `qa-evidence/`). Findings stay in the chat, not as markdown in `qa-evidence/`.

---

## Output Format

### Summary

| Check | Tables | Passed | Failed | Issues |
|-------|--------|--------|--------|--------|
| Schema / FK / Data Integrity / Indexes / Relationship Counts | N | N | N | N |

### Issues Found

| # | Table | Check | Issue | Severity | Query (and result) |
|---|-------|-------|-------|----------|--------------------|

Classify any data bug as FE / BE / Admin / Report / DB / Both (qa-standards). State coverage gaps explicitly — an unrun check is never an implied PASS.

---

## Superpowers escalation
Non-obvious integrity root cause after the standard query pass -> `superpowers:systematic-debugging` (hypothesis -> isolate -> verify). Before declaring the DB clean / PASS -> `superpowers:verification-before-completion` (evidence before assertions).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the table/column/entity-ID/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** feature + date, verdict (PASS/FAIL/CONFIRMED/DUPLICATE), issues (table, check, severity, layer, NEW/DUPLICATE), test data (IDs/tables/DB), root-cause location, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.
