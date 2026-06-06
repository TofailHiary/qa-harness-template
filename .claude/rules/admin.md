---
paths:
  - "<admin repo: PROJECT-PROFILE.md §3/§9>/**"
---

# Admin Rules (<admin repo: PROJECT-PROFILE.md §3/§9>)

## Stack
- See PROJECT-PROFILE.md §4 for actual stack (e.g. Node/Express, Python/Django, PHP/Laravel)
- Branch: see PROJECT-PROFILE.md §3

## Key Paths
- Controllers: `<admin repo: PROJECT-PROFILE.md §3/§9>/controllers/`
- Models: `<admin repo: PROJECT-PROFILE.md §3/§9>/models/`
- Views: `<admin repo: PROJECT-PROFILE.md §3/§9>/views/`

## QA Checks
- Verify output encoding in views (prevent XSS)
- Check CSRF token usage on state-changing operations
- Verify access control filters on controller actions
- Admin account `<admin email: PROJECT-PROFILE.md §7>` uses the auth method from PROJECT-PROFILE.md §4 (not necessarily the same as the main app auth)
- Check for raw SQL queries without parameter binding
