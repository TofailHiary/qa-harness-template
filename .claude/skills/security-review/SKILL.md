---
name: security-review
description: Use when a feature, endpoint, or area needs a security audit — checking auth/RBAC enforcement, probing for injection/XSS/CSRF, verifying data exposure, S3 URL signing, CORS, security headers, or session handling. Triggers include "security review", "audit this endpoint", "is this exploitable", "check for IDOR/injection", "review auth on X".
argument-hint: "feature, endpoint, or area to audit"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__http-client__http_get", "mcp__http-client__http_post", "mcp__http-client__http_request", "mcp__http-client__set_default_headers", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__github__*"]
---

# Security Review — 10-Point Audit

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/security-review` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Perform a comprehensive security audit of an application feature, endpoint, or area.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any probe
State the scope before the first request. Do not send a payload until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Feature / endpoints under audit | |
| QA mode | targeted / regression / full |
| Roles in scope (attacker + victim) | Admin / Manager / User / Guest / unauth |
| APIs / endpoints | |
| DB entities / tables | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Out of scope (explicit) | |

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every vulnerability maps to >=1 row — the **request/response that proves the vuln** (the malicious request + the server's response). A suspected vuln with no reproduction is not a confirmed vuln.

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

### Mutation safety
Any state-changing probe (POST/PUT/PATCH/DELETE, or a DB write) follows the Mutation Safety Gate in qa-standards: in-scope, prefer disposable test data, SELECT+log original first, WHERE on every write, restore+verify after. **Never mutate prod** (prod DB is read-only).

---

## Environment

- **Admin Portal:** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Primary FE — Test, DEFAULT):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Primary FE — Dev):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Legacy FE — Test, opt-in):** <the relevant URL: PROJECT-PROFILE.md §5>
- **Main Portal (Legacy FE — Dev, opt-in):** <the relevant URL: PROJECT-PROFILE.md §5>
- **FE selection:** audit the primary FE by default. Audit the legacy FE (the legacy FE URL: PROJECT-PROFILE.md §5) only when the scope is explicitly about the legacy frontend. CSP / cookies / headers should be checked on both.
- **Backend:** <backend repo: PROJECT-PROFILE.md §3/§9>
- **Frontend:** <frontend repo: PROJECT-PROFILE.md §3/§9> (primary FE) / <legacy frontend repo: PROJECT-PROFILE.md §3> (legacy FE)
- **Admin:** <admin repo: PROJECT-PROFILE.md §3/§9>
- **Auth:** authenticate per PROJECT-PROFILE.md §7 (JWT/session/OAuth/Firebase) → Bearer token
- **Database:** <test DB name: PROJECT-PROFILE.md §6> at <DB host: PROJECT-PROFILE.md §6>

---

## 10-Point Security Checklist

### 1. Authentication
- Login endpoint properly validates credentials
- Failed login doesn't reveal user existence
- Password not returned in any API response
- Auth tokens properly validated in middleware (per PROJECT-PROFILE.md §7 auth method)
- Token expiry enforced
- Check: `<backend repo: PROJECT-PROFILE.md §3/§9>/middleware/auth.js`

### 2. Authorization (RBAC)
- Role-based access enforced on all endpoints
- Users can't access manager/admin endpoints
- Managers can't access admin endpoints
- Cross-tenant isolation (users can't access other accounts' data)
- IDOR: a user cannot read/act on another user's object by guessing/enumerating an ID
- Check route middleware for role checks

### 3. Input Validation
- All user inputs validated on both FE and BE
- Server-side validation exists (don't trust client-only validation)
- Proper type checking on API parameters
- File upload validation (type, size, extension)

### 4. SQL Injection
- Test all endpoints with SQL injection payloads:
  - `' OR 1=1 --`
  - `'; DROP TABLE user; --`
  - `1 UNION SELECT * FROM user`
- Verify parameterized queries used (not raw SQL string concatenation)
- Check `<backend repo: PROJECT-PROFILE.md §3/§9>/models/` and routes for raw queries

### 5. XSS (Cross-Site Scripting)
- Test input fields with: `<script>alert('xss')</script>`
- Test with: `<img onerror="alert(1)" src="x">`
- Verify React's default escaping is not bypassed (no `dangerouslySetInnerHTML`)
- Check stored XSS in DB text fields
- Verify admin portal escapes output

### 6. CSRF Protection
- Verify CSRF tokens on state-changing operations
- Check SameSite cookie attributes
- Verify Origin/Referer header validation

### 7. Data Exposure
- API responses don't include sensitive fields (passwords, tokens, internal IDs)
- Error responses don't expose stack traces or internal paths
- Check for information leakage in HTTP headers (X-Powered-By, Server)
- Verify S3 URLs are signed/expiring (not public)

### 8. API Security
- Rate limiting on login and sensitive endpoints
- Request size limits configured
- CORS properly configured (not wildcard in production)
- API versioning consistent
- HTTP methods restricted (no PUT/DELETE where GET expected)

### 9. Security Headers
- Check for: Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, X-XSS-Protection
- Use `mcp__chrome-devtools__list_network_requests` to inspect response headers

### 10. Session Management
- Tokens expire appropriately
- Logout invalidates session/token
- No session fixation vulnerability
- Secure cookie flags (HttpOnly, Secure, SameSite)

---

## Execution

**Pre-Step:** Use `mcp__postman-api-mcp__searchPostmanElements` to find all endpoints in scope. For each endpoint use `mcp__postman-api-mcp__getCollectionRequest` to confirm the declared auth type, required roles, and headers. This is the baseline for checks 1 (Authentication) and 2 (Authorization) — test what the contract says should be enforced.

For each check:
1. **Read code** — Find relevant files with Grep/Glob/Read
2. **Test manually** — Use `mcp__http-client__*` for API tests, `mcp__playwright__*` for browser tests (clear stale headers with `set_default_headers` merge:false before swapping auth)
3. **Verify** — Cross-check with DB and network inspection
4. **Document** — Rate as PASS / FAIL / WARNING with an Evidence Ledger row

---

## Output Format

### Security Audit Summary

| # | Check | Status | Severity | Details |
|---|-------|--------|----------|---------|
| 1 | Authentication | PASS/FAIL/WARN | - | [notes] |
| 2 | Authorization | PASS/FAIL/WARN | - | [notes] |
| ... | ... | ... | ... | ... |
| 10 | Session Management | PASS/FAIL/WARN | - | [notes] |

### Vulnerabilities Found

For each vulnerability: title, CVSS-like severity, affected component, evidence (ledger ref — the proving request/response), recommended fix.

### Overall Security Rating

- **SECURE** — No critical/high issues
- **AT RISK** — Critical/high issues found, must fix before release
- **VULNERABLE** — Multiple critical issues, immediate action required

---

## Superpowers escalation (only when it adds value)
- Before declaring an endpoint SECURE / a check PASS -> `superpowers:verification-before-completion`.
- A non-obvious finding whose exploitability/root cause is unclear after the standard pass -> `superpowers:systematic-debugging`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/CVE-pattern/symptom; UPDATE an existing entry instead of filing a duplicate (security findings are often re-encountered — annotate the existing one).
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** feature/endpoint + date, rating (SECURE/AT RISK/VULNERABLE), vulns (ID, severity, layer, NEW/DUPLICATE), test data (endpoints/tokens/user IDs), root-cause `path:line`, regression risks for next time, any prior memory disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
