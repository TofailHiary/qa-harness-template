---
name: api-test
description: Use when a backend or report API endpoint needs direct testing — auth, RBAC/cross-tenant access, input validation, error handling, response schema, sorting/pagination, and DB-write consistency. Triggers include "test this endpoint/API", verifying a route in a PR, replaying a captured frontend request, or Phase 4 of /full-qa. Tests the API directly, independent of any frontend.
argument-hint: "endpoint or feature to test"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__http-client__http_get", "mcp__http-client__http_post", "mcp__http-client__http_request", "mcp__http-client__set_default_headers", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__postman-api-mcp__*", "Skill(qa-standards)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# API Testing Specialist

> **Capability gate:** This skill requires **API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no API configured, so `/api-test` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Comprehensive API testing for this project's endpoints — every claim backed by the request/response pair **and** the DB row next to it.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; the **Scope Lock**, **Mutation Safety Gate**, and **Evidence Ledger** are inlined below. Verdict words come from its **Verdict Contract**; the expected status/body of every case comes from its **Authoritative Source Hierarchy** (ticket / AC -> Postman contract -> route handler + validation schema) — never from an assumption. If nothing authoritative defines the expected behaviour, say so and record an ambiguity instead of inventing a requirement.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which endpoint(s) or feature? Which roles (including an attacker account from another tenant)? Does any case mutate data? Test (default) or Dev?"

Do NOT guess scope. Do NOT send a request until the Scope Lock is filled.

## Scope Lock (before any request)
State the endpoints in scope, the roles to test (incl. an attacker role for cross-tenant checks), the environment, and whether any case mutates data. Capture `git rev-parse --short HEAD` in `<backend repo: PROJECT-PROFILE.md §3/§9>` once here — it fills the **Branch / Commit** provenance column on every evidence row. Don't fan out to unrelated endpoints; if you must drop a category, say so and why (qa-standards -> Scope Lock).

---

## Environment
- **Backend API:** `<API base URL: PROJECT-PROFILE.md §5>`
- **Report API:** `<report API URL: PROJECT-PROFILE.md §5>` (send any version header §5 names, e.g. `Accept-Version`)
- **Admin:** `<admin URL: PROJECT-PROFILE.md §5>` (only if Admin is `on` in §2)
- **DB (verify writes):** `<test DB name: PROJECT-PROFILE.md §6>` via `mcp__mcp_server_mysql__mysql_query` (DB tool: PROJECT-PROFILE.md §6 — `/configure-project` rebinds the tool id when the project uses another engine). Confirm a **prod** repro only when needed, through the read-only prod access described in §6 (`mcp__mcp_server_mysql_prod__mysql_query` when Prod-DB is `on`). **Never mutate prod.**
- **Default environment is TEST.** Switch to Dev only when `$ARGUMENTS` or the request says so, and label every evidence row with its **Env** — an observation on Dev is evidence for Dev only.

**Tool choice.** If `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it — typed tools normally add the auth / claim / version headers for the role profile and refuse non-GET calls against prod. Otherwise use `mcp__http-client__*`.

If the project has more than one frontend (e.g. a current and a legacy one) they call the same backend — the API contract is identical. To reproduce a FE-specific call, capture the real request via `mcp__chrome-devtools__*` (network) and replay it with `mcp__http-client__*`. The captured body is the wire truth — test against it, never against a mock or a hand-typed guess of the payload (qa-standards -> Judgement Discipline).

## Postman Collections (`mcp__postman-api-mcp__*` — only if Postman is `on` in §2)
| Collection | UID |
|------------|-----|
| `<collection name: PROJECT-PROFILE.md §14>` | `<collection UID: PROJECT-PROFILE.md §14>` |

**Search Postman first** (`searchPostmanElements` -> `getCollectionRequest`) for the exact URL/headers/body/auth — it is the contract source of truth before any manual request. If Postman is off, the contract is the route handler + its validation schema in `<routes path: PROJECT-PROFILE.md §9>`.

## Authentication
Authenticate per `PROJECT-PROFILE.md §7` (login method + role accounts). **Passwords are per account — take them from the env vars named in §7, never assume or guess one.** The per-method recipes (JWT / session cookie / OAuth / hosted identity provider / SSO impersonation) live in `Skill(login)` Step 4; the sequence is always:

1. **Clear stale headers first:** `mcp__http-client__set_default_headers` with `merge:false`, `{ "Content-Type": "application/json" }`. The client **persists default headers across calls** — a leftover `Authorization` header 401s the token request itself.
2. **Perform the login request** for the role under test and capture the token / cookie.
3. **Set `Authorization: Bearer <token>`** (or the session cookie) as the default header for the following requests. Treat the token as a secret — `[REDACTED]` in any output. Tokens expire (often ~1 h): on an unexpected 401, re-mint before debugging.

**Surface mismatch caution.** The admin panel may use a different auth stack from the main app (its own session login vs. the app's identity provider). An admin account may not exist in the identity provider at all — for API tests against the main backend use an account of the right stack per §7.

**One session per role.** Mint a separate session for each role in scope **plus** one for an account in a *different tenant* (the attacker). Cross-tenant checks cannot be run with a single token.

---

## Mutation Safety Gate — before any POST/PUT/PATCH/DELETE (qa-standards)
1. Confirm the endpoint is in scope. 2. Prefer existing disposable test data (`Skill(test-data-manager)` locates it). 3. **SELECT + log the original DB row first** — every row the call may touch, side tables included. 4. Have a rollback plan **before** the call. 5. Never mutate shared/prod data (prod is read-only). 6. After the call, **verify** the DB change, then **restore** and SELECT again to confirm. 7. If rollback is impossible -> **STOP and ask the user.** Log every change in the table:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

*(illustrative)* Some "save" / "next" endpoints **re-create** child rows and re-point join rows at new ids on every call. Snapshot the id list before the first call; restore by re-pointing the join rows and deleting the new rows in FK-safe order.

---

## Test Categories
1. **Happy path** — valid auth + body + params -> 200/201, correct data, matches DB (recompute from source rows; API = DB proves transport, not correctness).
2. **Authentication** — no / invalid / expired token -> 401; a token from the *other* auth stack (admin vs app) is rejected.
3. **Authorization (RBAC + cross-tenant)** — wrong role -> 403; **another tenant's record id -> 403/404, never another tenant's data (IDOR).** Test object-ownership on every `:id` route, every list filter, **and every id inside the body** (parent ids, attachment ids, membership ids) — not just the path parameter.
4. **Input validation** — missing/invalid/boundary fields -> 400/422; SQLi -> no leak; XSS -> sanitized; oversize payload; wrong content-type; unknown fields ignored or rejected consistently.
5. **Error handling** — bad id -> 404; deleted resource -> 404 (per this project's soft-delete mechanism — see 7); duplicate -> 409; server error -> clean message, **no stack trace, no SQL fragment**.
6. **Schema** — all expected fields, correct types, pagination present (and page 2 actually differs from page 1); **no sensitive data leaked** (passwords, tokens, other-tenant fields). **Enum width:** compare the set of values the API can emit for a field (the DB column / ORM-model enum) with the set the FE handles — every value the DB can hold must be reachable and handled; the value no screen has ever shown is where defects hide (qa-standards -> Judgement Discipline, "partially-empty beats empty").
7. **DB consistency** — after a write, query the DB: change persisted, FKs intact, side tables written (join rows, audit/log rows, counters, snapshot/aggregate tables per `PROJECT-PROFILE.md §11`). **Soft delete uses whatever mechanism THIS schema actually has** — a `deleted_at` column, a `status` enum with a `deleted` value, or hard delete. Confirm it with the information_schema query in `/db-check` (or `.claude/rules/db-gotchas.md`) **before** asserting "deleted_at was set"; a predicate on a column that does not exist errors or silently returns the wrong rows. When a returned value looks wrong, read the column's semantic contract (`COLUMN_COMMENT`, the AC, the code comment) before calling it a bug — a surprising number is not automatically a wrong number.
8. **Sorting / filtering / pagination** — both sort directions on every sortable column, each filter alone and combined, page 2 and the last page, the empty page; the count in the response vs `COUNT(*)` with the same predicate in the DB. (qa-standards -> Completion Gate: a sortable column exercised in one direction is not verified.)

---

## Execution Flow (per endpoint)
1. **Contract** — Postman request or typed-tool definition (§14), else the route handler. 2. **Confirm** the route signature in `<routes path: PROJECT-PROFILE.md §9>`. 3. **Read** controller / model / validation logic, the auth middleware (`<auth middleware: PROJECT-PROFILE.md §9>`) and `.claude/rules/backend.md`. 4. **Auth** — one session per role + the attacker. 5. **Run** all applicable categories. 6. **Cross-check** responses vs DB (qa-standards -> Cross-Layer Consistency; recompute, do not transcribe). 7. **Document** with the Evidence Ledger — plus an Execution Register row per endpoint x category in `full` / `regression` / `release` mode (qa-standards -> Execution Register).

## Evidence Ledger (required)
Every finding/PASS -> a row with provenance: `| Evidence ID | Type | Source | File/URL/Tool | Env | Branch / Commit | Captured at | What it proves |`. For APIs, evidence = the request/response pair (method, URL, headers minus secrets, body, status) **+ the DB query result**. Save the pairs under `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/<finding>_api-response.json` via `mcp__filesystem__write_file` (the read-only hook blocks `Write`/`Edit` for `qa-evidence/`). `No evidence = no finding.` A PASS needs a row too — proof it was exercised.

**Per failed test:** name · request (method/url/body) · expected (status/body **and the source that defines it**) · actual (status/body) · DB state. Classify the layer (qa-standards -> Bug Classification) and, if confirmed, hand to `Skill(bug-verifier)` then `Skill(bug-report)`. Every endpoint x category ends as **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED** (qa-standards -> Verdict Contract) — an unrun category is NOT YET VERIFIED, never an implied pass.

---

## Sub-agents and plugins
- If `PROJECT-PROFILE.md §16` says sub-agents are disabled, run this skill in-session; otherwise the `api-tester` agent may run it under the orchestrator's Scope Lock (its report is a lead — the orchestrator reproduces anything it files).
- Non-obvious root cause after the standard pass: if the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`) use `superpowers:systematic-debugging`; otherwise do it by hand — write the hypothesis, change ONE variable per re-run (token / role / id / payload field / header), confirm with the DB row, and only then classify.
- Before claiming PASS: `superpowers:verification-before-completion` if installed; otherwise by hand — re-run the proving request in this session and re-read the ledger row that supports each PASS.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Naming `project_<slug>.md` / `feedback_<slug>.md` / `reference_<slug>.md`; frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the endpoint/route/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** endpoints tested + date + Env + commit, pass/fail counts, verdict in Verdict Contract words, bugs (ID, severity, layer, NEW/DUPLICATE), test data (user/entity ids — never passwords or tokens), root-cause `path:line`, any mutation made + restored, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
