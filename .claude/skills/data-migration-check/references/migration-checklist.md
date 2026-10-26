# Migration checklist and queries (read-only)

Every query here is a SELECT on `information_schema` or on data. None of them changes anything. Run them one at a
time, schema-qualify when the server hosts several databases, and pair every `LIMIT` sample with a `COUNT(*)`
(`.claude/rules/db-gotchas.md`). `<db>` is the database name from `PROJECT-PROFILE.md §6` for the environment you
are reading; `<t>`, `<c>`, `<p>` are the table, column and parent table of the migration under review.

## 1. Per-migration questions (read the file)

| Question | Why it matters |
|---|---|
| Is there a down migration, and is it the inverse of up? | a rollback that does something else is not a rollback |
| Does one step mix DDL with data changes? | MySQL / MariaDB commit DDL implicitly: a failure half-way leaves a half-migrated schema (Postgres DDL is transactional) |
| Is the version / timestamp unique across open branches? | two migrations with the same number apply in an undefined order, or one never applies |
| Does it rename or drop something the deployed code still reads? | the old code keeps running during the deploy |
| NOT NULL without a default, a new UNIQUE index, a new foreign key, a narrowed type? | each one fails on data production already holds (§3) |
| Is the backfill batched, restartable and idempotent? | a long single UPDATE locks the table; a re-run must change 0 rows |
| Does the migration import application models? | it breaks the day the model changes; migrations should carry their own SQL or a frozen model |
| Does it lock a large table? | `ALTER TABLE` without an online algorithm, an index build without `CONCURRENTLY` (Postgres) |
| Who runs it, and when relative to the deploy? | decides which compatibility window (§5) is real |

## 2. Schema snapshot (before and after)

```sql
-- columns
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = '<db>' AND TABLE_NAME IN ('<t>')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- indexes (unique or not)
SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS cols
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = '<db>' AND TABLE_NAME IN ('<t>')
GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE;

-- foreign keys
SELECT k.TABLE_NAME, k.COLUMN_NAME, k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, r.DELETE_RULE, r.UPDATE_RULE
FROM information_schema.KEY_COLUMN_USAGE k
JOIN information_schema.REFERENTIAL_CONSTRAINTS r
  ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME
WHERE k.TABLE_SCHEMA = '<db>' AND k.TABLE_NAME IN ('<t>') AND k.REFERENCED_TABLE_NAME IS NOT NULL;
```

Save both snapshots as ledger rows; the diff between them is the change the migration actually made, which is not
always the change the migration file says.

## 3. Will it succeed on production data? (read-only pre-flight)

| Change in the migration | Query (read-only) | It fails when |
|---|---|---|
| new UNIQUE on (`a`, `b`) | `SELECT a, b, COUNT(*) AS n FROM <db>.<t> GROUP BY a, b HAVING COUNT(*) > 1 LIMIT 20;` and the count of such groups | any group has n > 1 |
| new NOT NULL on `<c>` without a default | `SELECT COUNT(*) FROM <db>.<t> WHERE <c> IS NULL;` | the count is above 0 |
| new foreign key `<t>.<c>` → `<p>.id` | `SELECT COUNT(*) FROM <db>.<t> t LEFT JOIN <db>.<p> p ON p.id = t.<c> WHERE t.<c> IS NOT NULL AND p.id IS NULL;` | the count is above 0 (orphans) |
| narrowing `VARCHAR(n)` | `SELECT MAX(CHAR_LENGTH(<c>)), SUM(CHAR_LENGTH(<c>) > <new n>) FROM <db>.<t>;` | values longer than the new size (truncation or failure, per SQL mode) |
| text → number | `SELECT COUNT(*) FROM <db>.<t> WHERE <c> IS NOT NULL AND <c> NOT REGEXP '^-?[0-9]+([.][0-9]+)?$';` | non-numeric values exist |
| enum narrowed | `SELECT <c>, COUNT(*) FROM <db>.<t> GROUP BY <c>;` | a removed value is still stored |
| any ALTER on a big table | `SELECT TABLE_ROWS, ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024) AS mb FROM information_schema.TABLES WHERE TABLE_SCHEMA = '<db>' AND TABLE_NAME = '<t>';` | the size makes a blocking ALTER unacceptable in the deploy window |

`TABLE_ROWS` is an estimate for InnoDB; use it for the order of magnitude only.

## 4. Backfill verification (on the environment where the team ran it)

```sql
-- eligible rows that still lack the new value: must be 0, or explained
SELECT COUNT(*) FROM <db>.<t> WHERE <eligibility predicate> AND <new col> IS NULL;

-- one row per partition / enum value for the stratified sample
SELECT <partition col>, MIN(id) AS sample_id, COUNT(*) AS n FROM <db>.<t> GROUP BY <partition col>;

-- gap rows: written after the backfill finished, before the new code deployed
SELECT COUNT(*) FROM <db>.<t>
WHERE <created col> > '<backfill finished at>' AND <eligibility predicate> AND <new col> IS NULL;
```

For each sampled id, read its source columns, compute the expected value with the rule the PR states, and compare
with the stored value. Add the edge rows by hand: NULL source, empty string, maximum value, soft-deleted row
(per this table's soft-delete mechanism), a row of another tenant. Idempotency is proven from the code, never by
running the backfill again.

## 5. Compatibility window

| Schema state | Deployed (old) code | New code |
|---|---|---|
| before the migration | works (today) | breaks if it needs the new column, table or value |
| after the migration | breaks on a renamed / dropped column, an INSERT that omits a new NOT NULL column, an exhaustive switch over a widened enum | works (the Test result) |

The safe sequence for a breaking change is **expand → migrate → contract**: add the new structure (nullable, no
constraint) → write both old and new → backfill → switch reads → enforce the constraint → drop the old structure in
a later release. A PR that does several of those steps at once needs a reason.

## 6. Rollback review

| Question | A finding when |
|---|---|
| Is there a down migration? | no down and no stated alternative |
| Is it the inverse of up? | it restores a different type, default or index |
| Does data written after up survive the down? | the down drops a column that holds new data |
| Are irreversible steps named? | a drop or lossy conversion with no backup point and no restore time |
| Is the order of code and schema rollback stated? | the old code cannot run on the schema the down leaves behind |

## Postgres and SQLite forms

- **Postgres:** `information_schema.columns` (lower-case names) also works; indexes from
  `SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = '<t>';`; sizes from
  `SELECT pg_total_relation_size('<t>') / 1024 / 1024 AS mb;`; regex with `<c> !~ '^-?[0-9]+([.][0-9]+)?$'`;
  enum values with `SELECT unnest(enum_range(NULL::<enum type>));`. DDL is transactional; large index builds need
  `CREATE INDEX CONCURRENTLY`, which cannot run inside a transaction.
- **SQLite:** `PRAGMA table_info('<t>');`, `PRAGMA index_list('<t>');`, `PRAGMA foreign_key_list('<t>');`.
  Many `ALTER TABLE` forms rebuild the table; foreign keys are enforced only with `PRAGMA foreign_keys = ON`.
