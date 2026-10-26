---
name: data-migration-check
description: Use when a PR, branch or release adds or changes database migrations, backfills, data fixes or seed scripts, or when a schema change must be judged safe for production data before it ships. Triggers include "check this migration", "is the backfill correct", "will this ALTER lock the table", "can we roll this back", "does the old code still work with the new schema".
argument-hint: "PR, branch or migration file(s), plus the environment where the team applied it"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__github__get_file_contents", "mcp__github__pull_request_read", "mcp__github__list_commits", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__filesystem__write_file", "Skill(qa-standards)", "Skill(db-check)", "Skill(test-data-manager)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# Data Migration Check — schema changes and backfills, judged before production holds them

> **Capability gate:** This skill requires **DB + any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no DB + any of GitHub/LocalRepos configured, so `/data-migration-check` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


**Read-only, always.** This skill never runs a migration, a rollback, a backfill, a seed or a data fix — not on
Test, not on a replica, not on prod. Commands such as `migrate`, `db:migrate`, `migrate deploy`, `upgrade head`,
`flyway migrate` or `liquibase update` are never executed here: the team applies migrations through its own
deploy, and this skill reads the files, the schema and the data before and after. Production is SELECT and
`information_schema` only, date-bounded, no temp tables, through `mcp__mcp_server_mysql_prod__mysql_query` and
only when Prod-DB is `on` in `PROJECT-PROFILE.md §2`.

Why it exists: a migration is a release of the schema AND of the data (`.claude/rules/anomaly-disposition.md`
Rule 2). It passes on Test's small, clean data and fails on production's duplicates, NULLs and size; a backfill
reports "N rows updated" and is still wrong for one partition; and the old code keeps running against the new
schema for the whole length of the deploy.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; schema facts per
`.claude/rules/db-gotchas.md`. `Skill(db-check)` owns general integrity (orphans, soft delete, tenant scoping);
this skill adds the migration-specific checks. Verdict words come from qa-standards → Verdict Contract. Register
and ledger rows go into `qa-evidence/<run-folder>/run.json` (qa-standards → `references/run-record.md`). The
queries live in [references/migration-checklist.md](references/migration-checklist.md).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which PR, branch or migration files? Has the team applied it on Test (or on a local replica) yet? Is a read-only production connection available for the pre-flight checks?"

Do NOT run a query until the Scope Lock is filled.

## Scope Lock (before any query)

| Field | Value |
|---|---|
| Migrations in scope | files, in apply order |
| Tables / columns touched | |
| Migration tool | framework / ORM (`PROJECT-PROFILE.md §4`) |
| Applied where | Test / local replica (`PROJECT-PROFILE.md §6`) — and the commit it was applied from |
| Deploy order | migrate before deploy / after deploy / both (expand → contract) |
| Production pre-flight | Prod-DB `on` (read-only) — or not available, and those rows are BLOCKED |
| Consumers of the touched columns | code paths (`§9`), async consumers (`§11`), reports, exports |
| Branch / commit under test | `git rev-parse --short HEAD` in the repo that owns the migrations — stamps every ledger row |

---

## Step 1 — Inventory the migrations

Read the diff with `mcp__github__pull_request_read` for a PR (GitHub on), or read-only `git diff` / `git show` /
`git log` on a local repo (LocalRepos on). For a wide PR, `pr-risk-analyzer` maps the rest of the blast radius.
Common folders: `migrations/`, `db/migrate/`, `prisma/migrations/`, `alembic/versions/`,
`src/main/resources/db/migration/`, `database/migrations/`. One row per file:

| # | File | Kind (DDL / backfill / data fix / seed) | Tables | Down present? | Transactional? | Notes |
|---|---|---|---|---|---|---|

Read each file against the questions in the checklist §1: down is the inverse of up; DDL and data mixed in one
step (MySQL and MariaDB commit DDL implicitly, so a failure half-way leaves a half-migrated schema); version
collisions with other open branches; renames or drops that the deployed code still reads; NOT NULL without a
default; new UNIQUE indexes and foreign keys; narrowed types; batching and idempotency; application models
imported inside a migration; locks on large tables.

## Step 2 — Schema before and after

- **Before:** production (read-only), or the Test schema recorded before the deploy (memory, or
  `.claude/references/system-map.md`).
- **After:** Test (or the replica) with the migration applied by the team. Not applied yet → those rows are
  BLOCKED, unblock: "apply the migration on Test through the normal deploy". Never apply it yourself.
- Compare with the `information_schema` queries in checklist §2: columns (type, nullability, default, comment),
  indexes, foreign keys, enum values.
- Compare "after" with three more truths: the migration's intended DDL; the ORM model at the PR head (a model
  default is not a DB default, enums drift — `.claude/rules/db-gotchas.md`); and the API and frontend unions for
  every enum it touches (enum width).

## Step 3 — Will it succeed on production data? (pre-flight, read-only)

Answer in writing first: **"What cardinality, mode or format does this change introduce or forbid that
production already holds?"** Then run the matching pre-flight query from checklist §3: duplicates before a UNIQUE
index, NULLs before NOT NULL, orphans before a foreign key, over-long or non-numeric values before narrowing,
removed enum values still stored, table size and row count before a locking ALTER. Pair every sample with a
`COUNT(*)`.

- A hit is a FAIL whose `expected_source` is the migration line that will fail on that data.
- A size risk with no online strategy (an `ALGORITHM` / `LOCK` clause, a concurrent index build, a batched
  copy) is a finding for the team to decide, never a silence.
- Without Prod-DB these rows are BLOCKED (unblock: "read-only production access, or the owner runs the queries
  and shares the output") — never PASS on Test data alone, because Test does not hold production's shape.

## Step 4 — Backfill correctness (where the team ran it)

1. **Eligible vs written** — `COUNT(*)` of the rows the predicate selects vs the rows that now hold the new value;
   the difference is 0 or explained.
2. **Stratified sample** — one row per partition, enum value and edge class: NULL, empty string, maximum value,
   soft-deleted, another tenant (`Skill(test-data-manager)` finds them). "The first 10 rows" is not a sample.
3. **Recompute** every sampled value from its source columns with the rule the PR states, and compare.
   Recompute, never transcribe (qa-standards → Cross-Layer Consistency).
4. **Gap rows** — rows the old code wrote after the backfill ran and before the new code deployed: does anything
   fill them (a dual write, a second pass)?
5. **Idempotency** — prove from the code (the WHERE clause, the "already done" marker) that a second run changes
   0 rows. Never prove it by running it.
6. **Derived data** — aggregates, snapshots, search indexes and caches built from the backfilled column
   (`PROJECT-PROFILE.md §11`, with the terminal writer of each async chain).

## Step 5 — Compatibility window

During a rolling deploy the old and the new code run against the same schema.

| Schema state | Deployed (old) code | New code |
|---|---|---|
| before the migration | today's behaviour | does it read or write columns that do not exist yet? |
| after the migration | do renamed, dropped or NOT NULL columns still work? can it read the new enum values? | the Test result |

Read the old code at the deployed commit (`env-health` names it, or the release tag) for `SELECT *`, ORM column
lists, INSERTs that omit the new column, and exhaustive switches over the enum. A rename or drop without the
expand → migrate → contract sequence is a FAIL when the old code still reads the column during the deploy.

## Step 6 — Rollback plan (reviewed, never executed)

The down migration exists and is the inverse of up; data written between up and down survives the down;
irreversible steps (drops, lossy type changes, destructive data fixes) are named in the PR with a backup point and
a restore time; the order of code rollback and schema rollback is stated; the point of no return is known.
No down migration and no stated plan is a finding.

## Output

| # | Migration | Check | Expected (source) | Observed (evidence) | Result |
|---|---|---|---|---|---|

- One register row per migration × check (Steps 1–6) and one per consumer, written to `run.json`. Every row ends
  as **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED** (qa-standards → Verdict Contract). A failure
  predicted from reading code alone is labelled INFERRED in the row and stays NOT YET VERIFIED until a query shows
  the data that triggers it.
- **Layer:** a defect in the migration or its DDL → DB; in backfill or data-fix code → BE; a consumer that breaks →
  its own layer; both sides → Both.
- Every FAIL goes through `Skill(bug-verifier)`; confirmed ones go to `Skill(bug-report)`.
- A new "exactly one per partition" constraint or a new enum value is a latent-pattern trigger: name the partition
  or the column so `latent-pattern-sweep` and the next `prod-sentinel` run watch it.
- Check the record before you state a result:
  `python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>`.
  Called from an orchestrator, append to its `run.json` and leave the run verdict to the orchestrator.
- Engine: the SQL in the checklist is MySQL / MariaDB; its last section has the Postgres and SQLite forms
  (`PROJECT-PROFILE.md §4` names the engine).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Naming `project_<slug>.md` / `feedback_<slug>.md` / `reference_<slug>.md`; frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the table, the migration file and the symptom; UPDATE an existing entry instead of filing a duplicate. A schema fact this run disproved (a column, a default, an enum) is marked **SUPERSEDED** with the date and the evidence id, and the new fact is written next to it.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer carrying the date in the title: `- [<title> YYYY-MM-DD](<file>.md) — <hook>`.
4. **Content:** migrations checked + date + Env + commit, the schema after (columns, defaults, enums that changed — also worth recording in `PROJECT-PROFILE.md §10`), the pre-flight numbers from production, backfill counts, verdict in Verdict Contract words, findings (ID, layer, NEW/DUPLICATE), the rollback assessment.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
