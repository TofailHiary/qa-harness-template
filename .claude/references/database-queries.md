# Database Queries (Reference)

> Reusable query shapes. Replace table/column names with this project's real ones
> (`PROJECT-PROFILE.md` §10). Tool: `mcp__mcp_server_mysql__mysql_query` (only if DB is on, §2).

## Discover the schema first
```sql
SHOW TABLES;
SHOW COLUMNS FROM <table>;
```

## Generic shapes
```sql
-- Row count + null/empty audit on a column
SELECT COUNT(*) AS total, SUM(<col> IS NULL) AS nulls FROM <table>;

-- Orphan check (child rows whose parent is gone)
SELECT c.* FROM <child> c LEFT JOIN <parent> p ON c.<fk> = p.id WHERE p.id IS NULL;

-- Reconcile a relationship count
SELECT p.id, COUNT(c.id) AS children FROM <parent> p
LEFT JOIN <child> c ON c.<fk> = p.id GROUP BY p.id;

-- Find users with their role (via join table — adapt to this project's real path, §10)
SELECT u.id, u.email, r.name AS role_name
FROM user u
LEFT JOIN user_account ua ON u.id = ua.user_id
LEFT JOIN role r ON ua.role_id = r.id
WHERE u.email = '<email>';

-- Soft-delete check (only on tables that have deleted_at — verify with SHOW COLUMNS first)
SELECT COUNT(*) AS active FROM <table> WHERE deleted_at IS NULL;
SELECT COUNT(*) AS deleted FROM <table> WHERE deleted_at IS NOT NULL;
```

## Save what you learn
Record useful project-specific queries here and in `PROJECT-PROFILE.md` §10 so they are reused, not rediscovered.
