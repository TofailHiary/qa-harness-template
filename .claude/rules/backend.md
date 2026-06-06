---
paths:
  - "<backend repo: PROJECT-PROFILE.md §3/§9>/**"
---

# Backend Rules (<backend repo: PROJECT-PROFILE.md §3/§9>)

## Stack
- Node.js, Express.js, Sequelize ORM
- Branch: see PROJECT-PROFILE.md §3 (case-sensitive)

## Key Paths
- Routes: `<backend repo: PROJECT-PROFILE.md §3/§9>/routes/`
- Models: `<backend repo: PROJECT-PROFILE.md §3/§9>/models/`
- Auth middleware: `<backend repo: PROJECT-PROFILE.md §3/§9>/middleware/auth.js`
- Controllers: `<backend repo: PROJECT-PROFILE.md §3/§9>/controllers/`

## QA Checks
- Verify Sequelize models match DB schema (`DESCRIBE` vs model definition)
- Check parameterized queries (no raw SQL string concatenation)
- Verify auth middleware applied on all protected routes
- Check error handling (no empty catch blocks, no stack traces in responses)
- Verify soft delete consistency (`deleted_at` checks in queries)
- Look for N+1 query problems in includes/joins
- Async/await with proper try/catch error handling
- No `console.log` in production code paths
