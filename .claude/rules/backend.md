---
paths:
  - "<backend repo: PROJECT-PROFILE.md §3/§9>/**"
---

# Backend Rules (<backend repo: PROJECT-PROFILE.md §3/§9>)

## Stack
- See PROJECT-PROFILE.md §4 for the actual stack (e.g. Node/Express, Python/Django, PHP/Laravel, Go) and ORM
- Branch: see PROJECT-PROFILE.md §3 (case-sensitive)

## Key Paths
- Routes: `<routes path: PROJECT-PROFILE.md §9>`
- Models: `<models path: PROJECT-PROFILE.md §9>`
- Auth middleware: `<auth middleware path: PROJECT-PROFILE.md §9>`
- Controllers: `<backend repo: PROJECT-PROFILE.md §3/§9>/controllers/` (or the equivalent for the framework in §4)
- Workers / cron / queue consumers: `<workers path: PROJECT-PROFILE.md §9>` (they often own the terminal write — §11)

## QA Checks
- Verify auth middleware applied to all protected routes
- Check role-based access control on every endpoint (roles from PROJECT-PROFILE.md §8); cross-tenant ids on body and query
- Verify input validation on request bodies and parameters (server-side, not only client-side)
- Verify the ORM models match the DB schema (`DESCRIBE` / information_schema vs model definition; model default ≠ DB default)
- Check error handling (no empty catch blocks, no stack traces in responses, no masked errors — a runtime `TypeError` surfacing instead of a domain message is its own defect)
- Soft delete: confirm the mechanism per table before writing any `deleted_at` / `status` predicate (`.claude/rules/db-gotchas.md`); flag queries that assume a column the table does not have
- Look for N+1 query problems in includes/joins
- Verify transactions wrap multi-step writes; a rejected write leaves rows unchanged
- Check background jobs / queue consumers for idempotency and for the terminal state they write (an enqueue is not a result)
- Grep for the latent patterns on changed code: `rows[0]` / `[first]` cardinality assumptions, enum branches never taken, `a ?? b` on parser output (`latent-pattern-sweep`)
