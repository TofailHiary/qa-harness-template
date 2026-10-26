---
name: latent-pattern-sweep
description: Use when hunting DORMANT defects no functional test finds — code whose assumptions hold only because production data has not grown into them (an "exactly one" cardinality, an enum branch never taken, a field assumed populated). Triggers include "why did we miss this", "find similar issues", "are there more like this", a bulk content import, the post-mortem of an escaped bug older than its symptom, or a release shipping new content types or modes.
argument-hint: "the change, import, escaped bug or area to sweep (plus the environment: Prod read-only, or Test)"
allowed-tools: ["Read", "Grep", "Glob", "Bash", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__github__*", "Skill(qa-standards)", "Write"]
---

# Latent Pattern Sweep

> **Capability gate:** This skill requires **DB** (Test) or **Prod-DB** (read-only) for the live
> distribution, plus **LocalRepos** or **GitHub** for the code. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If none of DB / Prod-DB is `on`, STOP and tell the user:
> "This project has no database configured, so `/latent-pattern-sweep` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.

**Core idea: a defect is latent while `code assumption == current data shape`. It becomes live the moment
the data grows. So sweep the ASSUMPTIONS against the LIVE DISTRIBUTION — not the features.**

Why this skill exists *(illustrative)*: three bugs escaped to production in one wave. In all three the
code was old and unchanged (one line was four years old) and the DATA changed — a bulk content import
put hundreds of records into a mode production had never held, and a partition that had always held
one record suddenly held two. No functional test could have caught them, because at test time the
triggering data did not exist.

Follows `.claude/rules/anomaly-disposition.md` (Rules 1–5) and `qa-standards` (Scope Lock, Evidence
Ledger, Memory Ritual).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What should I sweep — a recent import, an escaped bug, a release, or an area of code? Which database
> holds the live distribution (Test, or Prod read-only per PROJECT-PROFILE.md §6)?"

---

## When to run
- After ANY bulk content/data import (mandatory — an import is a release; anomaly-disposition Rule 2).
- In the post-mortem of an escaped bug whose code predates the bug.
- Before a release that ships new content types, modes, or formats.
- When asked "are there more like this?"

---

## The three patterns

| # | Pattern | Code smell | Data question |
|---|---|---|---|
| **P1** | **Cardinality** — "there is exactly one" | `const [first] = rows`, `rows[0]`, `.find()` as *the* record, ONE insert from a SET, `LIMIT 1` without `ORDER BY` | `GROUP BY <partition> HAVING COUNT(*) > 1` |
| **P2** | **Unexercised branch** — a mode the data never took | `if (x == 'A') {...} else {...}`, `switch` on an enum, a default arm | `GROUP BY <enum> COUNT(*)` — flag any value at **0% or <1%** |
| **P3** | **Input class** — "this field is always populated" | `a ?? b` on parser/OCR/upload output, `.required()` on a field some inputs cannot fill, `.trim()` never applied | which real inputs leave it empty/whitespace? |

---

## Procedure

### Step 0 — Scope Lock (qa-standards)
Pin the environment (Test vs Prod read-only), the schema name, the code paths in scope, and the
import/change that triggered the sweep. **Prod is read-only — SELECT / information_schema only.**

### Step 1 — Enumerate the enums (P2 candidates)
Every low-cardinality column is a branch the code may switch on. MySQL/MariaDB form (adapt for the
engine in `PROJECT-PROFILE.md §4`; for Postgres query `pg_enum` / `information_schema.columns`):
```sql
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = '<DB name: PROJECT-PROFILE.md §6>' AND DATA_TYPE = 'enum' ORDER BY TABLE_NAME;
```
Also list boolean-like and short varchar "type/mode/kind/source" columns — they are enums in disguise.

### Step 2 — Compute the LIVE distribution of each
```sql
SELECT <col> AS val, COUNT(*) AS n FROM <table> WHERE <active-row predicate: PROJECT-PROFILE.md §10>
GROUP BY <col> ORDER BY n DESC;
```
**Classify every value:**
- **0 rows** → the branch has NEVER run in production. First use = first bug. HIGHEST risk.
- **<1%** → effectively unexercised; one content import away from mattering.
- balanced → exercised, lower risk.

### Step 3 — Find the partitions (P1 candidates)
For any code that creates ONE thing from a query result, identify its grouping key and ask whether the
group can hold more than one:
```sql
SELECT <partition cols>, COUNT(*) AS n FROM <table> WHERE <active-row predicate>
GROUP BY <partition cols> HAVING n > 1 ORDER BY n DESC;
```
Also record **when** each partition first exceeded 1 (`MIN(created_at)` of the 2nd row) — that is the
date the defect went live, and it dates the blast radius.

### Step 4 — Grep the code for the assumption
Search the repos in `PROJECT-PROFILE.md §3/§9` (Grep, or `mcp__github__search_code`):
```
const \[\w+\] = |rows\[0\]|\[0\]\s*;|\.find\(|LIMIT 1        # P1
if \(\w+\.(code|type|mode|status|kind|source) ==             # P2
\?\?|\|\| ''|\.required\(\)                                   # P3 on parser/upload output
```

### Step 5 — Cross them and classify
For each code assumption × data reality:

| Data state | Verdict | Action |
|---|---|---|
| data ALREADY violates the assumption | **LIVE DEFECT** | reproduce, file, measure blast radius + first-damage date |
| data does not violate it YET, but can | **ARMED** | file as a risk with the exact trigger condition; add a monitor (`prod-sentinel`) |
| data cannot violate it (schema/constraint forbids) | SAFE | record the constraint that makes it safe |

**"Armed" is a reportable finding, not a pass.** *(illustrative)* an armed cardinality assumption fired
54 seconds after the first partition grew to two rows.

### Step 6 — Check the DEFAULT MISMATCH sub-pattern
When a field is optional, compare the default in EVERY layer that supplies one (API controller,
background worker, client, DB column). A mismatch is a latent defect even when currently unreachable.
*(illustrative)* a page-size default was `"A4"` in two controllers but `"letter"` in a worker, while
100% of production content was `letter` — not currently reachable because the API always sent the
value → classify **ARMED / low**, do not report as live.

---

## Output

| Assumption | Location `path:line` | Pattern | Live distribution | Verdict | Trigger that arms it |
|---|---|---|---|---|---|

Plus, for every LIVE row: blast radius and the date of first damage.
Every ARMED row must name the exact data change that would fire it.

**Evidence Ledger (qa-standards):** every row above maps to a query result (the distribution) and a code
reference (`path:line`). Save the query text and output under `qa-evidence/<run-folder>/`.

---

## Worked precedents *(illustrative — calibrate severity against these shapes)*

| Pattern | Assumption | Data change that fired it |
|---|---|---|
| P1 | `const [firstRow] = parsedRows` → one record per (dimension A × B × C) partition | a partition first held 2+ templates; first damage within a minute |
| P2 | `if (template.code == 'mode_a')` — the else-arm never ran | hundreds of `mode_b` rows imported; production had been ~100% `mode_a` |
| P3 | `name: parsed.text ?? fallback` — the parser always returns text | an image-only PDF returned a single space (17 of 46 rows) |

## Post-Session (MANDATORY)
Record every ARMED finding in memory (`<memory folder: PROJECT-PROFILE.md §12>`) with its trigger
condition, so the next import can check it in one query. Update `MEMORY.md` with a one-line pointer.
If memory cannot be persisted → HALT and tell the user; never report success.
- **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
- **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows a non-zero size, else HALT.

