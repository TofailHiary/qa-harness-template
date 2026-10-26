---
name: login
description: Use when a QA task needs an authenticated session before testing — log into the project's main app or admin panel as Admin, Manager, or User (browser, API token, or SSO impersonation from the admin panel). Triggers include "log me in as a manager", "authenticate as admin", "get a user token", "switch to the legacy frontend", "impersonate this user".
argument-hint: "admin|manager|user optional:email optional:dev optional:legacy"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__http-client__*"]
---

# Login Handler

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/login` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Log into the project's portals for QA testing. This is a **utility** used by other QA skills to obtain an authenticated session; it does not itself produce a verdict.

> If login itself fails (wrong credentials, redirect loop, 401, account disabled, identity-provider error), that is a finding — capture the error (screenshot + console messages + the failing request) and hand it to the calling skill for its Evidence Ledger.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which surface (main app / admin) and which role (Admin / Manager / User / Guest, or a named test account from PROJECT-PROFILE.md §7)? Browser session or API token?"

Do not guess the scope.

---

## Ground rules

- **Credentials come from `PROJECT-PROFILE.md §7` only.** Account identifiers are listed there; **passwords are per account — take them from the env var named in §7, never assume, never guess, never reuse another role's.** A role may have had more than one default password across fixture generations; if the profile's value fails, that is a finding (or a question for the user), not a reason to try alternatives.
- **Default environment is TEST** (`PROJECT-PROFILE.md §5`). Switch to Dev only when `$ARGUMENTS` or the request explicitly says dev. Retired hostnames may still resolve — use only the URLs in §5.
- **Never embed an API key or secret** in a request you print or save. Reference the env var (`<identity-provider web API key env var: PROJECT-PROFILE.md §7>`); redact tokens as `[REDACTED]` in every output and evidence file.
- **Session caution — verify once per project, then record it in memory / §7:**
  - A **second tab of the same portal may log out the first** (single-session enforcement or a shared in-memory auth store). Do not assume two roles can be open side by side in one browser context; use separate contexts or sequential sessions until verified.
  - A SPA that keeps the auth session **in memory only** loses it on a hard reload; "page reload logs me out" is then expected behaviour, not a bug — but confirm against the code or the product owner before closing it as expected.
- **Report the role you actually got.** A dashboard that renders is not proof of the intended role — read the role from the header / profile endpoint and hand it to the caller with the environment and the token expiry.

---

## Portals & Credentials

### Admin panel (`<admin repo: PROJECT-PROFILE.md §3/§9>`) — only if Admin is `on` in §2
- **URL:** `<admin URL: PROJECT-PROFILE.md §5>`
- **Account:** `<admin account: PROJECT-PROFILE.md §7>` — password from its env var in §7
- **Auth stack caution:** the admin panel may authenticate differently from the main app (its own session login vs the app's identity provider). Follow §7 "Login method" **for this surface**. An admin account may not exist in the main app's identity provider at all — to mint a main-app API token use a Manager / User account.

### Main app — current frontend (`<frontend repo: PROJECT-PROFILE.md §3/§9>`) — DEFAULT
- **URL (Test):** `<main app URL (test): PROJECT-PROFILE.md §5>`
- **URL (Dev):** `<main app URL (dev): PROJECT-PROFILE.md §5>`
- **Role accounts:** `<role accounts: PROJECT-PROFILE.md §7>` (generic set: Admin / Manager / User / Guest — `PROJECT-PROFILE.md §8`); password env var per account in §7.
- **When to use:** default for any manager/user login.

### Main app — legacy frontend (`<legacy frontend repo: PROJECT-PROFILE.md §3>`) — opt-in, only if §3 lists one
- **URL (Test / Dev):** `<legacy frontend URLs: PROJECT-PROFILE.md §5>`
- **Same auth method + same accounts as the current frontend** (both call the same backend).
- **When to use:** ONLY if `$ARGUMENTS` or the user request mentions "legacy", "old frontend", or the legacy repo name.

### SSO / impersonation from the admin panel (alternative)
Follow the **SSO path in `PROJECT-PROFILE.md §7`**. The typical shape: open the admin panel -> navigate to the tenant / account the user belongs to -> find the user -> click "Login" / "Impersonate" -> a new tab opens logged in as that user. Verify the impersonated session's role before testing (Step 5); the second-tab caution above applies to the admin tab left open.

---

## Login Flow

### Step 1: Determine portal and role
- `$ARGUMENTS` contains "admin" -> Admin panel.
- `$ARGUMENTS` contains "manager" or "user" (or any role named in §8) -> Main app, that role's account from §7.
- An email is provided -> look the user up in the DB to determine the role (Step 2) if DB is `on`; otherwise ask the caller which role the account holds.
- "dev" -> Dev URLs; "legacy" -> legacy frontend. Anything else -> Test, current frontend.

### Step 2: Find user (if an email is provided and DB is `on`)
Roles are often **not** a column on `user` — they live in a membership / join table (`PROJECT-PROFILE.md §8/§10`, `.claude/rules/db-gotchas.md`). Adapt this join path to the real tables:
```sql
SELECT u.id, u.email, u.name, m.role_id, r.name AS role_name, m.<tenant key>
FROM user u
LEFT JOIN <membership table: PROJECT-PROFILE.md §10> m ON u.id = m.user_id
LEFT JOIN role r ON m.role_id = r.id
WHERE u.email = '[EMAIL]'
LIMIT 5;
```
Run via `mcp__mcp_server_mysql__mysql_query` (DB tool: PROJECT-PROFILE.md §6). A user can hold several memberships — note which tenant you are logging into. Never read a password from the DB; it is hashed, and the env var is the only source.

### Step 3: Browser login via Playwright
1. Navigate to the portal URL with `mcp__playwright__browser_navigate`
2. Take a snapshot to see the login form with `mcp__playwright__browser_snapshot`
3. Fill the email field with `mcp__playwright__browser_fill_form` or `mcp__playwright__browser_type`
4. Fill the password field (value from the env var — never typed into the chat)
5. Click the login button with `mcp__playwright__browser_click`
6. Wait for the redirect with `mcp__playwright__browser_wait_for`
7. Take a snapshot to confirm login success **and the role / tenant shown**
8. Check the console for errors with `mcp__chrome-devtools__list_console_messages`; capture the auth request from the network tab if the caller needs the real `Authorization` header

### Step 4: API login (alternative)
**Preferred when available:** if `PROJECT-PROFILE.md §14` lists a project MCP server with session tools (login / whoami / profile switching), use them — the session is minted and renewed server-side and every typed tool accepts the role profile. Otherwise the manual recipe for the method named in §7:

**Always first:** `mcp__http-client__set_default_headers` with `merge:false`, `{ "Content-Type": "application/json" }` — the client persists default headers, and a stale `Authorization` header 401s the login request itself.

**(a) JWT** — POST credentials to the login endpoint, capture the returned token:
```
POST <login endpoint: PROJECT-PROFILE.md §5>
Content-Type: application/json

{ "email": "[EMAIL]", "password": "<value of the account's env var: PROJECT-PROFILE.md §7>" }
```
The response carries a token (`token` / `access_token`). Send `Authorization: Bearer <token>` on subsequent requests.

**(b) Session cookie** — POST credentials to the login endpoint; the server returns `Set-Cookie`. Send that cookie on subsequent requests (the http client keeps it as a default header).

**(c) OAuth** — follow the OAuth flow defined in `PROJECT-PROFILE.md §7` (client id / scopes / redirect from §7) to obtain an access token.

**(d) Firebase / hosted identity provider** — POST to the provider's password sign-in endpoint named in §7, with the web API key **from its env var** (never literal in the request you print):
```
POST <identity-provider sign-in endpoint: PROJECT-PROFILE.md §7>?key=<web API key env var: PROJECT-PROFILE.md §7>
Content-Type: application/json

{ "email": "[EMAIL]", "password": "<value of the account's env var: §7>", "returnSecureToken": true }
```
The response carries a short-lived ID token (often ~1 h). Send `Authorization: Bearer <idToken>`; re-mint on an unexpected 401 instead of debugging it.

**(e) SSO impersonation (admin panel)** — browser-only. To obtain an API token for the impersonated user, capture the frontend's `Authorization` header from the network tab (`mcp__chrome-devtools__*`) after impersonation and replay it with `mcp__http-client__*`.

Use `mcp__http-client__http_post` for the login request. Store the token or cookie for subsequent calls with `mcp__http-client__set_default_headers`. Treat the token as a secret — `[REDACTED]` in any output.

### Step 5: Verify login
- Browser: dashboard elements, the user's name **and role / tenant** in the header or profile page.
- API: call a protected endpoint (ideally a `me` / `whoami` route) and confirm the returned identity, role and tenant match the account you intended.
- Report back to the caller: success / failure evidence, portal + environment, role + tenant actually obtained, token expiry, and any session quirk observed (tab logout, reload logout).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Login fails | Check the user exists in the DB (if DB on), the account is active, and you used the env var for *this* account — capture the error as a finding; do not try other passwords |
| Redirect loop | Clear cookies, use a fresh browser context, check the identity-provider / auth-service status |
| 401 on API right after login | Stale default header (clear with `merge:false`) or an expired token — re-mint |
| Logged out when a second tab opened | Expected if the project enforces single sessions — verify once, record in §7 / memory, use sequential sessions |
| Wrong role after login | The account holds several memberships — log into the intended tenant, or pick the account listed for that role in §7 |
| SSO / impersonation fails | Verify the user belongs to the tenant you opened, and the admin account has impersonation rights |

---

## Post-Session (light — qa-standards -> Memory Ritual)
- **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
Record only what the next session needs: which account/role/environment worked, the auth stack per surface, and any session quirk verified (second-tab logout, reload logout, token lifetime) — **never a password or token**. Cross-reference first and UPDATE the existing entry under `<memory folder: PROJECT-PROFILE.md §12>` (`reference_login_<slug>.md`) instead of filing a duplicate; then `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT and tell the user.

