# Database Schema Gotchas (Always Loaded)

> Project-specific schema gotchas (real table names, soft-delete columns, FK directions, enum values)
> live in `PROJECT-PROFILE.md` §10. The reminders below are **generic** — verify each against this
> project's actual schema before relying on it.

## Generic reminders (verify per project)
- **Soft delete is not universal.** Some tables have a `deleted_at` (or `is_deleted`) column and some
  do not. Before adding `WHERE deleted_at IS NULL`, confirm the column EXISTS on that table — querying
  a non-existent column errors, and assuming soft-delete where there is none hides rows.
- **Roles may not be a column.** A `user` table often has no `role_id`; roles can live in a join /
  membership table (user ↔ account ↔ role). Trace the real path before filtering by role.
- **FK column names can surprise you.** A child table may key on `user_id` rather than `student_id`,
  `author_id` rather than `created_by`, etc. Check the actual column, not the one you'd expect.
- **Model default ≠ DB default.** An ORM model may declare a default (e.g. `status='active'`) that the
  database column does not enforce, so real rows can hold NULL. Check both the model and the DDL.
- **Enums drift.** Verify the actual allowed enum values in the live schema, not from docs.

## Generic query pattern — find a user with role (adapt to this project's join path, §10)
```sql
-- Replace table/column names with this project's real ones (PROJECT-PROFILE.md §10)
SELECT u.id, u.email, r.name AS role_name
FROM user u
LEFT JOIN user_role ur ON u.id = ur.user_id
LEFT JOIN role r ON ur.role_id = r.id
WHERE u.email = '[EMAIL]';
```

## Before trusting any of the above
Run a quick `DESCRIBE <table>` / `SHOW COLUMNS` (or the ORM model) to confirm columns, nullability,
and defaults. Record what you find in `PROJECT-PROFILE.md` §10 so the next session does not re-discover it.
