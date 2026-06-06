---
name: api-test
description: Use when a backend or report API endpoint needs direct testing — auth, RBAC/cross-tenant access, input validation, error handling, response schema, and DB-write consistency. Triggers include "test this endpoint/API", verifying a route in a PR, or Phase 4 of /full-qa. Tests the API directly, independent of any frontend.
argument-hint: "endpoint or feature to test"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__http-client__http_get", "mcp__http-client__http_post", "mcp__http-client__http_request", "mcp__http-client__set_default_headers", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__postman-api-mcp__*", "Skill(qa-standards)"]
---

# API Testing Specialist

> **Capability gate:** This skill requires **API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no API configured, so `/api-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Comprehensive API testing for project endpoints.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; the **Scope Lock**, **Mutation Safety Gate**, and **Evidence Ledger** are inlined below.

## ARGUMENTS
$ARGUMENTS

## Scope Lock (before any request)
State the endpoints in scope, the roles to test (incl. an attacker role for cross-tenant checks), and whether any case mutates data. Don't fan out to unrelated endpoints.

---

## Environment
- **Backend:** <the relevant URL: PROJECT-PROFILE.md §5>
- **Report:** <the relevant URL: PROJECT-PROFILE.md §5> (header `Accept-Version: 1.0.0`)
- **Admin:** <the relevant URL: PROJECT-PROFILE.md §5>
- **DB (verify writes):** `<test DB name: PROJECT-PROFILE.md §6>` via `mcp__mcp_server_mysql__mysql_query`. Confirm a **prod** repro via `mcp__mcp_server_mysql_prod__mysql_query` (read-only, tunnel first) only when needed.

If a project has multiple frontends (e.g. a current and a legacy one), they call the same backend — the API contract is identical. To reproduce a FE-specific call, capture it via `mcp__chrome-devtools__*` and replay with `mcp__http-client__*`.

## Postman Collections (`mcp__postman-api-mcp__*`)
| Collection | UID |
|------------|-----|
| <Postman collection> | `<your Postman collection UID>` |
| <Postman collection> | `<your Postman collection UID>` |
| <Postman collection> | `<your Postman collection UID>` |
| <Postman collection> | `<your Postman collection UID>` |

**Search Postman first** (`searchPostmanElements` -> `getCollectionRequest`) for the exact URL/headers/body/auth — it is the contract source of truth before any manual request.

## Authentication
Authenticate per `PROJECT-PROFILE.md` §7 to obtain a session token. Common patterns:

**(a) JWT** — POST credentials to the login endpoint, capture the returned token; send `Authorization: Bearer <token>` on subsequent requests.

**(b) Session cookie** — POST credentials; the server returns `Set-Cookie`; send that cookie on subsequent requests.

**(c) OAuth** — follow the OAuth flow defined in §7.

**(d) Firebase** — `POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<FIREBASE_API_KEY env var>` body `{"email":"<test account email: PROJECT-PROFILE.md §7>","password":"<role password env var: PROJECT-PROFILE.md §7>","returnSecureToken":true}`; capture `idToken`; send `Authorization: Bearer <idToken>`.

Regardless of method:
1. Clear stale headers: `mcp__http-client__set_default_headers` with `merge:false`, `{ "Content-Type": "application/json" }`.
2. Perform the login request per the pattern above.
3. Set `Authorization: Bearer <token>` (or the session cookie) for subsequent requests.

---

## Mutation Safety Gate — before any POST/PUT/PATCH/DELETE (qa-standards)
1. Confirm the endpoint is in scope. 2. Prefer existing disposable test data. 3. **SELECT + log the original DB row first.** 4. Have a rollback plan. 5. Never mutate shared/prod data (prod is read-only). 6. After the call, **verify** the DB change, then **restore** and SELECT again to confirm. 7. If rollback is impossible -> **STOP and ask the user.** Log every change in the table:

| # | Table | ID | Column | Original | Test value | Restored? |
|---|---|---|---|---|---|---|

---

## Test Categories
1. **Happy path** — valid auth + body + params -> 200/201, correct data, matches DB.
2. **Authentication** — no / invalid / expired token -> 401.
3. **Authorization (RBAC + cross-tenant)** — wrong role -> 403; **another account's user/ID -> 403/404, never another tenant's data (IDOR).** Test object-ownership on every `:id` route.
4. **Input validation** — missing/invalid/boundary fields -> 400/422; SQLi -> no leak; XSS -> sanitized.
5. **Error handling** — bad ID -> 404; deleted resource -> 404; duplicate -> 409; server error -> clean message, **no stack trace**.
6. **Schema** — all expected fields, correct types, pagination present; **no sensitive data leaked** (passwords, tokens, other-tenant fields).
7. **DB consistency** — after a write, query DB: change persisted, soft-delete sets `deleted_at` (not hard delete), FKs intact.

---

## Execution Flow (per endpoint)
1. **Postman contract** (`searchPostmanElements` -> `getCollectionRequest`). 2. **Confirm** the route signature in `<backend repo: PROJECT-PROFILE.md §3/§9>/routes/`. 3. **Read** controller/model logic + `.claude/rules/backend.md`. 4. **Auth.** 5. **Run** all applicable categories. 6. **Cross-check** responses vs DB. 7. **Document** with the Evidence Ledger.

## Evidence Ledger (required)
Every finding/PASS -> a row: `| Evidence ID | Type | Source | File/URL/Tool | What it proves |`. For APIs, evidence = the request/response pair + the DB query result. `No evidence = no finding.`

**Per failed test:** name · request (method/url/body) · expected (status/body) · actual (status/body) · DB state. Classify the layer (qa-standards Bug Classification) and, if confirmed, hand to `Skill(bug-verifier)` then `Skill(bug-report)`.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool. Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep for the endpoint/route; UPDATE an existing entry instead of duplicating.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** endpoints tested + date, pass/fail counts, bugs (ID, severity, layer, NEW/DUPLICATE), test data (user IDs/tokens/entity IDs), root-cause `path:line`, any mutation made + restored.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
