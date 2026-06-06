---
name: env-health
description: Use at the very start of a QA session to confirm the environment is testable before any testing begins — MCP servers reachable, repos on the correct branch and current, portals responding, DB reachable, and auth working. Triggers include "check the environment", "is the env ready", "preflight", "are we good to test", or the first step before /full-qa.
argument-hint: "optional: environment (test / dev / prod)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__http-client__*", "mcp__playwright__*", "mcp__github__*", "Skill(qa-standards)"]
---

# Env Health — Preflight Readiness Check

Confirm the target environment is testable BEFORE QA starts, so a run doesn't fail halfway on a stale branch, dead portal, or broken auth. Default target: **Test**.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session.

## ARGUMENTS
$ARGUMENTS  (default to Test if unspecified)

---

## Checklist — run each, fill the readiness table

1. **DB (test/dev)** — `mcp__mcp_server_mysql__mysql_query` `SELECT 1` against `<test DB name: PROJECT-PROFILE.md §6>`. Prod (only if prod is the target): `mcp__mcp_server_mysql_prod__mysql_query` — note the SSH tunnel on `<prod DB via tunnel: PROJECT-PROFILE.md §6>` must be up first.
2. **Portals** — `mcp__http-client__http_get` the target FE + backend URLs; expect 200 / a login page. Default FE `<the relevant URL: PROJECT-PROFILE.md §5>`; backend `<the relevant URL: PROJECT-PROFILE.md §5>`; admin `<the relevant URL: PROJECT-PROFILE.md §5>`.
3. **Repos & branch** — for each repo under test, `git -C <path> branch --show-current` == the expected branch (`PROJECT-PROFILE.md §3`). Use `mcp__github__list_commits` to compare local HEAD vs remote — flag if behind. (Read-only; do not switch branches.)
4. **Auth** — confirm a token can be obtained: authenticate per `PROJECT-PROFILE.md §7` (JWT/session/OAuth/Firebase) -> Bearer token for a User/Manager OR a quick `mcp__playwright__*` login to the portal. Admin credentials are in `PROJECT-PROFILE.md §7`.
5. **MCP servers** — note which of the QA MCP servers responded (mysql, mysql_prod, http-client, playwright, chrome-devtools, postman, github, filesystem, Atlassian). A server that errors here is a stop condition for any skill that needs it.

## Output — Readiness table

| Check | Target | Result | Detail |
|---|---|---|---|
| Test DB | <test DB name: PROJECT-PROFILE.md §6> | GREEN/RED | `SELECT 1` ok? |
| Portal (FE) | test.acme.example.com… | GREEN/RED | status code |
| Backend API | api.test.acme.example.com… | GREEN/RED | status code |
| Admin portal | admin.test.acme.example.com… | GREEN/RED | status code |
| Repos on branch | <expected branch: PROJECT-PROFILE.md §3> | GREEN/RED | which repo is off/behind |
| Auth | User/Manager token | GREEN/RED | token obtained? |
| MCP servers | (list) | GREEN/RED | which failed |

**Verdict:** READY (all green) or NOT READY (list the RED items as **stop conditions** to hand to the QA skill's Scope Lock). If the feature under test is not yet deployed to the target env, say so — it is the most common false-start.

---

## Note
This is a preparatory utility (like `sync-repos`) — it produces a readiness verdict, not bug findings, so no Evidence Ledger or memory ritual is required. If a check is RED, that RED item becomes a documented stop condition for the run.
