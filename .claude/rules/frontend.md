---
paths:
  - "<legacy frontend repo: PROJECT-PROFILE.md §3>/**"
---

# Frontend Rules (<legacy frontend repo: PROJECT-PROFILE.md §3>)

## Stack
- See PROJECT-PROFILE.md §4 for the actual stack (e.g. React / Vue / Angular + TypeScript).
- Branch: see PROJECT-PROFILE.md §3 (branch names can be case-sensitive)

## Key Paths
- API calls: `<legacy frontend repo: PROJECT-PROFILE.md §3>/src/<api-layer: PROJECT-PROFILE.md §9>`
- Components: `<legacy frontend repo: PROJECT-PROFILE.md §3>/src/components/`
- Pages: `<legacy frontend repo: PROJECT-PROFILE.md §3>/src/pages/`

## QA Checks
- Verify FE API calls match BE route signatures
- Check React hooks usage (dependency arrays in useEffect)
- Check React Query cache keys for consistency
- Verify no memory leaks (cleanup in useEffect)
- Verify i18n translations used (no hardcoded user-facing strings)
- Check for `dangerouslySetInnerHTML` usage (XSS risk)
- Verify loading, error, and empty states handled
- Check UI component library usage follows design system (see PROJECT-PROFILE.md §4)
