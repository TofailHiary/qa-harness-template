---
name: security-review
description: Use when a feature, endpoint, or area needs a security audit — checking auth/RBAC enforcement, probing for injection/XSS/CSRF, verifying data exposure, signed storage URLs, CORS, security headers, CSP and third-party host allow-lists, or session handling. Triggers include "security review", "audit this endpoint", "is this exploitable", "check for IDOR/injection", "review auth on X", "which hosts does the app contact".
argument-hint: "feature, endpoint, or area to audit"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__http-client__http_get", "mcp__http-client__http_post", "mcp__http-client__http_request", "mcp__http-client__set_default_headers", "mcp__mcp_server_mysql__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__github__*", "Skill(qa-standards)", "Write"]
---

# Security Review — 10-Point Audit

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/security-review` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Perform a comprehensive security audit of an application feature, endpoint, or area.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Scope Lock, Evidence Ledger, Evidence provenance, Mutation Safety Gate, Verdict Contract, Judgement Discipline); safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which feature, endpoint or area? Which roles (including an attacker account from another tenant)? Test (default) or Dev?"

Do not guess the scope.

---

## Inline gates (compact — full detail in qa-standards)

### Scope Lock — REQUIRED before any probe
State the scope before the first request. Do not send a payload until this is filled (ask if a critical field is unknown):

| Field | Value |
|---|---|
| Feature / endpoints under audit | |
| QA mode | targeted / regression / full |
| Roles in scope (attacker + victim) | <roles: PROJECT-PROFILE.md §8> — e.g. Admin / Manager / User / Guest / unauthenticated |
| APIs / endpoints | |
| DB entities / tables | |
| Environment | Test (default) / Dev / Prod (read-only) |
| Build under test | <branch: PROJECT-PROFILE.md §3> @ short commit — stamps every ledger row |
| Out of scope (explicit) | |

### Evidence Ledger — REQUIRED in output (`No evidence = no finding`)
Every vulnerability maps to >=1 row — the **request/response that proves the vuln** (the malicious request + the server's response). A suspected vuln with no reproduction is not a confirmed vuln. Save proof for PASS too (the probe that was sent and the refusal it got).

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

### Mutation safety
Any state-changing probe (POST/PUT/PATCH/DELETE, or a DB write) follows the Mutation Safety Gate in qa-standards: in-scope, prefer disposable test data, SELECT+log original first, WHERE on every write, restore+verify after. **Never mutate prod** (prod DB is read-only). Injection payloads go to disposable rows only — never to a shared fixture another tester relies on.

---

## Environment

- **Main app (primary FE — Test, DEFAULT):** <main app URL: PROJECT-PROFILE.md §5>
- **Admin:** <admin URL: PROJECT-PROFILE.md §5>
- **Backend API:** <API base URL: PROJECT-PROFILE.md §5>
- **Report API (if the project has one):** PROJECT-PROFILE.md §5
- **Secondary / legacy FE (only if the project keeps one, PROJECT-PROFILE.md §5):** opt-in — audit the primary FE by default; audit the legacy FE only when the scope is explicitly about it. CSP / cookies / headers are checked on **every** frontend the project serves, because they are usually set at a shared web-server layer and drift independently.
- **Backend repo:** <backend repo: PROJECT-PROFILE.md §3/§9>
- **Frontend repo:** <frontend repo: PROJECT-PROFILE.md §3/§9> (primary) / <legacy frontend repo: PROJECT-PROFILE.md §3> (legacy)
- **Admin repo:** <admin repo: PROJECT-PROFILE.md §3/§9>
- **Auth:** authenticate per PROJECT-PROFILE.md §7 (JWT / session / OAuth / hosted identity provider) -> Bearer token or session cookie. Accounts per role in §7 — identifiers only; secrets come from the environment.
- **Database:** <test DB name: PROJECT-PROFILE.md §6> at <DB host: PROJECT-PROFILE.md §6> via <DB tool: PROJECT-PROFILE.md §6> (DB on).
- **Tooling:** if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface (role sessions, saved requests), prefer it; otherwise use `mcp__http-client__*`.

---

## 10-Point Security Checklist

### 1. Authentication
- Login endpoint properly validates credentials
- Failed login doesn't reveal user existence (same message + timing for unknown user and wrong password)
- Password not returned in any API response
- Auth tokens properly validated in middleware (per PROJECT-PROFILE.md §7 auth method) — signature, issuer, audience, not just "decodes"
- Token expiry enforced
- Check: `<auth middleware: PROJECT-PROFILE.md §9>`

### 2. Authorization (RBAC)
- Role-based access enforced on all endpoints
- A lower role (User) cannot reach Manager/Admin endpoints; Managers cannot reach Admin endpoints (<roles: PROJECT-PROFILE.md §8>)
- Cross-tenant isolation (users cannot access other tenants' / accounts' data)
- IDOR: a user cannot read/act on another user's object by guessing/enumerating an ID — test every id-bearing path, query and body parameter
- Check route middleware for role checks AND ownership checks (`isAuthenticated` alone is not authorization)

### 3. Input Validation
- All user inputs validated on both FE and BE
- Server-side validation exists (don't trust client-only validation)
- Proper type checking on API parameters
- File upload validation (type, size, extension, content sniffing)

### 4. SQL Injection
- Test all endpoints with SQL injection payloads:
  - `' OR 1=1 --`
  - `'; DROP TABLE user; --`
  - `1 UNION SELECT * FROM user`
- Verify parameterized queries are used (ORM bindings per PROJECT-PROFILE.md §4, not raw SQL string concatenation)
- Check `<backend models: PROJECT-PROFILE.md §9>` and routes for raw queries (`query(`, `literal(`, string-built `WHERE`)

### 5. XSS (Cross-Site Scripting)
- Test input fields with: `<script>alert('xss')</script>`
- Test with: `<img onerror="alert(1)" src="x">`
- Verify the frontend framework's default escaping is not bypassed (no `dangerouslySetInnerHTML` / raw HTML sinks)
- Check stored XSS in DB text fields (write via API, read back in every surface that renders the field)
- Verify the admin (server-rendered templates, if any) escapes output

### 6. CSRF Protection
- Verify CSRF tokens on state-changing operations
- Check SameSite cookie attributes
- Verify Origin/Referer header validation

### 7. Data Exposure
- API responses don't include sensitive fields (passwords, tokens, internal IDs)
- Error responses don't expose stack traces or internal paths
- Check for information leakage in HTTP headers (X-Powered-By, Server)
- Verify object-storage URLs are signed/expiring (not public)

### 8. API Security
- Rate limiting on login and sensitive endpoints
- Request size limits configured
- CORS properly configured (not wildcard in production; credentials never with `*`)
- API versioning consistent
- HTTP methods restricted (no PUT/DELETE where GET expected)

### 9. Security Headers
- Check for: Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, Referrer-Policy, X-XSS-Protection
- Use `mcp__chrome-devtools__list_network_requests` (or `curl -sI`) to inspect response headers — on HTML pages **and** JSON responses **and** error pages; they are often set in different places and drift
- **Host allow-list / "which hosts does the app contact" questions:** a host string in a bundle is NOT proof the page contacts it. Bundles carry unused client objects, library default URLs and URL patterns from plugins. Keep a host only when (a) the live `Content-Security-Policy` header lists it — `curl -sI <main app URL> | grep -i content-security-policy` is the upper bound — and (b) a real call site exists in source (fetch / HTTP client / WebSocket / script loader) that is assigned and referenced in the live chunk. Label conditional hosts by feature and role. *(illustrative)* a string scan of the bundle listed seven hosts the app never contacted, one of them a client object defined but never imported; a line-by-line reviewer caught it, and every wrong host cost trust.

### 10. Session Management
- Tokens expire appropriately
- Logout invalidates session/token (replay the old token after logout — it must fail)
- No session fixation vulnerability
- Secure cookie flags (HttpOnly, Secure, SameSite)

---

## Execution

**Pre-Step — the enforcement baseline.** If Postman is `on` (PROJECT-PROFILE.md §2), use `mcp__postman-api-mcp__searchPostmanElements` to find all endpoints in scope and `mcp__postman-api-mcp__getCollectionRequest` to confirm the declared auth type, required roles, and headers. Otherwise derive the same baseline from the route definitions (`<routes path: PROJECT-PROFILE.md §9>`) and the auth middleware (`<auth middleware: PROJECT-PROFILE.md §9>`). This is the baseline for checks 1 (Authentication) and 2 (Authorization) — test what the contract says should be enforced.

**Role pairs.** Attack from every pair in scope: unauthenticated -> each role; each lower role -> each higher role; same role, other tenant (cross-tenant). Use the accounts in PROJECT-PROFILE.md §7; clear stale headers with `set_default_headers` merge:false before swapping auth, or the "denied" you see is the previous token's.

For each check:
1. **Read code** — Find relevant files with Grep/Glob/Read (or `mcp__github__*` when GitHub is on)
2. **Test manually** — `mcp__http-client__*` (or the project MCP in §14) for API tests, `mcp__playwright__*` for browser tests
3. **Verify** — Cross-check with DB (DB on) and network inspection; a 403 in the UI with a 200 on the wire is a FE-only guard and a FAIL
4. **Document** — Rate as PASS / FAIL / WARNING with an Evidence Ledger row

**Judgement.** A header absent on an error page but present on JSON responses is a finding scoped to that path — say which responses you sampled (N of M). A sanitizer that strips one payload is not proof against the class — try at least two encodings. "Not found" is not "not present": before writing BLOCKED or NOT APPLICABLE, rule out a different route prefix, environment, feature flag or fixture (qa-standards -> Judgement Discipline).

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

For each vulnerability: title, CVSS-like severity, affected component, layer (FE / BE / Admin / Report / DB / Both per qa-standards), evidence (ledger ref — the proving request/response), recommended fix.

### Overall Security Rating

- **SECURE** — No critical/high issues
- **AT RISK** — Critical/high issues found, must fix before release
- **VULNERABLE** — Multiple critical issues, immediate action required

### Mapping into the central contract (REQUIRED when returning to an orchestrator or writing memory)

The security scale is a domain finding scale, not a run verdict. Translate before handing back (qa-standards -> Verdict Contract):

| Security rating | Execution Register `Result` |
|---|---|
| SECURE / PASS | **PASS** |
| AT RISK / WARNING | **FAIL** (a risk you can reproduce is a finding) or **NOT YET VERIFIED** if unproven — never a silent pass |
| VULNERABLE / FAIL | **FAIL** |
| could not test | **BLOCKED** (+ what would unblock) or **NOT APPLICABLE** (+ the scope predicate) |

The orchestrator records the mapped value; the security wording may follow in parentheses. Close with the confidence line: `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: <one line or "none">` (an area here is one of the audit checks).

---

## Sub-agents (policy knob — PROJECT-PROFILE.md §16)
If §16 allows sub-agents, this audit may be delegated to the `security-auditor` agent (`.claude/agents/`), which returns the mapped result above. If §16 says sub-agents are disabled, run the audit in-session. Either way, anything filed externally is reproduced first-hand by the orchestrator — an agent's report is a lead, not a finding (qa-standards -> Verdict Integrity).

## Plugins & escalation (optional — PROJECT-PROFILE.md §17; only when it adds value)
- Before declaring an endpoint SECURE / a check PASS -> `Skill(superpowers:verification-before-completion)` if the `superpowers` plugin is installed; otherwise by hand: for each PASS, name the probe that would have proven it wrong and confirm it was sent.
- A non-obvious finding whose exploitability/root cause is unclear after the standard pass -> `Skill(superpowers:systematic-debugging)` if installed; otherwise by hand: hypothesis -> the one request or line that would disprove it -> run it -> repeat.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/path/CVE-pattern/symptom; UPDATE an existing entry instead of filing a duplicate (security findings are often re-encountered — annotate the existing one).
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** feature/endpoint + date, the mapped result (PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED, with the SECURE / AT RISK / VULNERABLE rating in parentheses), vulns (ID, severity, layer, NEW/DUPLICATE), test data (endpoints / role accounts / entity IDs — never secrets), root-cause `path:line`, headers observed per surface, regression risks for next time, any prior memory disproved.
5. **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
6. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
