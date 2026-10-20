# Database Schema Gotchas (Always Loaded)

> Project-specific schema facts (real table names, soft-delete columns, FK directions, enum values,
> active-row predicates) live in `PROJECT-PROFILE.md` §10 and `.claude/references/system-map.md` §5.
> The reminders below are **generic** — verify each against this project's actual schema before relying
> on it, and record what you find in §10 so the next session does not re-discover it.

## Generic reminders (verify per project)
- **Soft delete is not universal.** Some tables have a `deleted_at` (or `is_deleted`) column, some use a
  `status` enum, some hard-delete. Before adding `WHERE deleted_at IS NULL`, confirm the column EXISTS on
  that table — querying a non-existent column errors, and assuming soft-delete where there is none
  SILENTLY hides rows *(illustrative: a prevalence query returned 0 instead of 2 for exactly this reason)*.
- **A `status` column is not always soft delete.** It can be a lifecycle or result state
  (`pending / in_progress / complete`, `correct / wrong`). Read the enum before treating it as "deleted".
- **Roles may not be a column.** A `user` table often has no `role_id`; roles can live in a join /
  membership table (user ↔ account ↔ role). Trace the real path before filtering by role.
- **FK column names can surprise you.** A child table may key on `user_id` rather than `student_id`,
  `author_id` rather than `created_by`, etc. Check the actual column, not the one you'd expect.
- **Model default ≠ DB default.** An ORM model may declare a default (e.g. `status='active'`) that the
  database column does not enforce, so real rows can hold NULL. Check both the model and the DDL.
- **Enums drift.** Verify the actual allowed enum values in the live schema, not from docs; compare the
  DB enum, the ORM model, the API union and the frontend union — a value at 0 rows is a branch the
  code has never run (`latent-pattern-sweep`).
- **Scope predicates come in pairs.** Before filing "missing rows", check every column that scopes the
  pipeline (a `type` column AND a `type_id` column, for example); two lanes once filed the same
  false positive by checking one without the other *(illustrative)*.

## Confirm the soft-delete mechanism before any membership / roster predicate
```sql
-- MySQL / MariaDB (adapt for the engine in PROJECT-PROFILE.md §4)
SELECT TABLE_NAME,
  MAX(CASE WHEN COLUMN_NAME = 'deleted_at' THEN 'YES' ELSE '' END) AS has_deleted_at,
  MAX(CASE WHEN COLUMN_NAME = 'status' THEN COLUMN_TYPE ELSE '' END) AS status_col
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('<t1>', '<t2>') GROUP BY TABLE_NAME;
```

## Read the column comment before judging any value
Many projects put the semantic contract of an aggregate column (re-aggregation rule, additive or not,
sentinel values, documented-unclamped ranges) in `COLUMN_COMMENT`. Judging a value without reading it
has produced both real defects and false-positive bug reports.
```sql
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = '<test DB name: PROJECT-PROFILE.md §6>' AND TABLE_NAME = '<table>' ORDER BY ORDINAL_POSITION;
```
If the comment is empty, the contract is the ORM model plus the writer code (`path:line`).

## Generic query pattern — find a user with role (adapt to this project's join path, §10)
```sql
SELECT u.id, u.email, r.name AS role_name
FROM user u
LEFT JOIN user_role ur ON u.id = ur.user_id
LEFT JOIN role r ON ur.role_id = r.id
WHERE u.email = '[EMAIL]';
```

## DB-MCP tooling gotchas (verify per installation)
- Some MySQL MCP servers render DATETIME shifted by the server's offset with a fake `Z` — use
  `DATE_FORMAT(col, '%Y-%m-%d %H:%i:%s')` whenever a timestamp matters.
- Some query parsers reject the `<=>` operator — write `a <> b OR a IS NULL`.
- `SUM((a < 0) + (b < 0))` false-negatives on NULL — use `COUNT(CASE WHEN a < 0 OR b < 0 THEN 1 END)`.
- Do not rely on a default schema — schema-qualify (`<db>.<table>`) when the server hosts several.
- Run queries one at a time; pair every `LIMIT` sample with a `COUNT(*)`.

## Before trusting any of the above
Run a quick `DESCRIBE <table>` / `SHOW COLUMNS` (or the ORM model) to confirm columns, nullability,
and defaults. Record what you find in `PROJECT-PROFILE.md` §10 so the next session does not re-discover it.
