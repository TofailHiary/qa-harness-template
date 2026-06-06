---
name: login
description: Use when a QA task needs an authenticated session before testing — log into the project portal as Admin, Manager, or User (browser or API token, or SSO). Triggers include "log me in as a manager", "authenticate as admin", "get a user token".
argument-hint: "admin|manager|user optional:email"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__http-client__*"]
---

# Login Handler

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/login` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Log into the project test portals for QA testing. This is a **utility** used by other QA skills to obtain an authenticated session; it does not itself produce a verdict.

> If login itself fails (wrong credentials, redirect loop, 401, account disabled, auth error), that is a finding — capture the error (screenshot + console messages) and hand it to the calling skill for its Evidence Ledger.

## ARGUMENTS
$ARGUMENTS

---

## Portals & Credentials

### Admin Portal (<admin repo: PROJECT-PROFILE.md §3/§9>)
- **URL:** <the relevant URL: PROJECT-PROFILE.md §5>
- **Username:** <admin email: PROJECT-PROFILE.md §7>
- **Password:** <admin password env var: PROJECT-PROFILE.md §7>

### Main Portal — Current FE (<frontend repo: PROJECT-PROFILE.md §3/§9>) — DEFAULT
- **URL (Test):** <the relevant URL: PROJECT-PROFILE.md §5>
- **URL (Dev):** <the relevant URL: PROJECT-PROFILE.md §5>
- **User Default Password:** `<role password env var: PROJECT-PROFILE.md §7>`
- **Manager Default Password:** `<role password env var: PROJECT-PROFILE.md §7>`
- **When to use:** default for any manager/user login. Switch to Dev only if `$ARGUMENTS` or the user request explicitly says dev.

### Main Portal — Legacy FE (<legacy frontend repo: PROJECT-PROFILE.md §3>) — opt-in
- **URL (Test):** <the relevant URL: PROJECT-PROFILE.md §5>
- **URL (Dev):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Same auth method + same passwords as current FE.**
- **When to use:** ONLY if `$ARGUMENTS` or the user request mentions "legacy", "old frontend", or `<legacy frontend repo: PROJECT-PROFILE.md §3>`.

### SSO Login (Alternative)
1. Open <the relevant URL: PROJECT-PROFILE.md §5>
2. Navigate to the account the user belongs to
3. Find the user or manager
4. Click "Login" button → SSO opens a new tab logged in as that user

---

## Login Flow

### Step 1: Determine Portal
- If `$ARGUMENTS` contains "admin" → use Admin Portal
- If `$ARGUMENTS` contains "manager" or "user" → use Main Portal
- If email provided → look up user in DB to determine role

### Step 2: Find User (if email provided)
```sql
SELECT u.id, u.email, u.name, ua.role_id, r.name as role_name
FROM user u
LEFT JOIN user_account ua ON u.id = ua.user_id
LEFT JOIN role r ON ua.role_id = r.id
WHERE u.email = '[EMAIL]'
LIMIT 1;
```
Run via `mcp__mcp_server_mysql__mysql_query`. (Roles live in `user_account`, not `user` — see `.claude/rules/db-gotchas.md`.)

### Step 3: Browser Login via Playwright
1. Navigate to the portal URL using `mcp__playwright__browser_navigate`
2. Take snapshot to see the login form using `mcp__playwright__browser_snapshot`
3. Fill email field using `mcp__playwright__browser_fill_form` or `mcp__playwright__browser_type`
4. Fill password field
5. Click login button using `mcp__playwright__browser_click`
6. Wait for redirect using `mcp__playwright__browser_wait_for`
7. Take snapshot to confirm login success
8. Check console for errors using `mcp__chrome-devtools__list_console_messages`

### Step 4: API Login (Alternative)

Authenticate per `PROJECT-PROFILE.md` §7 to obtain a session token. Common patterns:

**(a) JWT** — POST credentials to the login endpoint, capture the returned token:
```
POST <login endpoint: PROJECT-PROFILE.md §5>
Content-Type: application/json

{
  "email": "[EMAIL]",
  "password": "<test password from §7>"
}
```
Response contains a token (e.g. `token` or `access_token`). Set `Authorization: Bearer <token>` on subsequent requests.

**(b) Session cookie** — POST credentials to the login endpoint; the server returns a `Set-Cookie` header. Send that cookie on subsequent requests.

**(c) OAuth** — follow the OAuth flow defined in `PROJECT-PROFILE.md` §7 to obtain an access token.

**(d) Firebase** — POST to the identitytoolkit `signInWithPassword` endpoint:
```
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<FIREBASE_API_KEY env var>
Content-Type: application/json

{
  "email": "[EMAIL]",
  "password": "<test password from §7>",
  "returnSecureToken": true
}
```
Response contains `idToken`. Send `Authorization: Bearer <idToken>` on subsequent requests.

Use `mcp__http-client__http_post` to perform the login request. Store the token or cookie for subsequent API calls using `mcp__http-client__set_default_headers`. Treat the token as a secret — `[REDACTED]` it in any output.

### Step 5: Verify Login
- Browser: check for dashboard elements or user name display
- API: verify the token is valid by calling a protected endpoint
- Report login status back to the caller (success, or the captured failure evidence)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Login fails | Check user exists in DB, verify password, check account status — capture the error as a finding |
| Redirect loop | Clear cookies, try incognito, check auth service status |
| 401 on API | Token may be expired, re-login |
| SSO fails | Verify user belongs to the account, check admin access |
