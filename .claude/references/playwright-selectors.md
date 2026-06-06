# Playwright Selectors (Reference)

> Generic selector guidance for browser testing (only if Browser is on, §2). Project-specific stable
> selectors are discovered per page — record the good ones here as you find them.

## Preference order (most → least robust)
1. Role + accessible name: `getByRole('button', { name: 'Save' })`
2. Label / placeholder / text: `getByLabel`, `getByPlaceholder`, `getByText`
3. `data-testid` if the app provides them
4. CSS/structure selectors — last resort (brittle)

## Tips
- Prefer the accessibility snapshot (`browser_snapshot`) to find elements over guessing CSS.
- Wait on state (`browser_wait_for`), not on fixed timeouts.
- App URLs per environment: `PROJECT-PROFILE.md` §5; login: §7.

## Discovered selectors (fill in per project)
| Page | Element | Selector |
|------|---------|----------|
|  |  |  |
