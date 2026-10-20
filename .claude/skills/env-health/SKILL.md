---
name: env-health
description: Use at the very start of a QA session to confirm the environment is testable before any testing begins — MCP servers reachable, repos on the correct branch and current, app and API responding, DB reachable, auth working, the change under test actually deployed, nothing shipping untested, and production not already bleeding. Triggers include "check the environment", "is the env ready", "preflight", "are we good to test", "is the fix deployed yet", "what is about to ship", or the first step before /full-qa.
argument-hint: "optional: environment (test / dev / prod)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__http-client__*", "mcp__playwright__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)", "Skill(prod-sentinel)", "Skill(latent-pattern-sweep)"]
---

# Env Health — Preflight Readiness Check

> **Capability gate:** always on. This skill probes **only the capabilities that are `on`** in
> `PROJECT-PROFILE.md` §2 (Capability Map) — read it first. A check whose capability is `off` is
> reported as `N/A (capability off)`, never as GREEN and never as RED, and is named in the verdict
> so the orchestrator records it as NOT YET VERIFIED rather than silence.

Confirm the target environment is testable BEFORE QA starts, so a run doesn't fail halfway on a stale branch, dead app, broken auth, or — the most common false-start — a fix that is not actually deployed yet. Default target: **Test**.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Scope Lock stop conditions, Evidence provenance, Escape classes & their gates).

## ARGUMENTS
$ARGUMENTS  (default to Test if unspecified)

---

## Checklist — run each enabled check, fill the readiness table

1. **DB (test/dev)** — *DB on.* `mcp__mcp_server_mysql__mysql_query` (DB tool: PROJECT-PROFILE.md §6) `SELECT 1` against `<test DB name: PROJECT-PROFILE.md §6>`. Prod (only if prod is the target and Prod-DB is `on`): `mcp__mcp_server_mysql_prod__mysql_query` through the prod read-only access described in `PROJECT-PROFILE.md §6` (tunnel, replica or read-only user) — confirm that access is up first. **Never write to prod.**

2. **App & API** — *API or Browser on.* `mcp__http-client__http_get` the target surfaces: main app `<main app URL: PROJECT-PROFILE.md §5>`, backend `<API base URL: PROJECT-PROFILE.md §5>`, admin `<admin URL: PROJECT-PROFILE.md §5>`, report API if the project has one (§5); expect 200 / a login page. If only Browser is on, `mcp__playwright__browser_navigate` and read the page. Keep the response headers — a build id / version header, when the project exposes one, feeds check 5b.

3. **Repos & branch** — *LocalRepos or GitHub on.* For each repo under test (`PROJECT-PROFILE.md §3`): `git -C <path> branch --show-current` == the expected branch (`<branch: PROJECT-PROFILE.md §3>`; branch names are case-sensitive) and `git -C <path> rev-parse --short HEAD`. Use `mcp__github__list_commits` to compare local HEAD vs remote — flag if behind. Read-only: do not switch branches, do not pull (that is `sync-repos`). The branch @ commit you record here is the provenance stamp for every Evidence Ledger row this session.

4. **Auth** — confirm a token / session can be obtained for one non-admin role and, if in scope, Admin, using the method in `PROJECT-PROFILE.md §7` (JWT / session / OAuth / hosted identity provider) — API path -> Bearer token; browser path -> a quick `mcp__playwright__*` login. Accounts per role are in §7 (identifiers only; secrets come from the environment). Fastest, when `PROJECT-PROFILE.md §14` lists a project MCP server with a session / status tool: call it — every preloaded role profile bootstrapped with no errors = GREEN — and let it confirm the target env and that any prod-write switches are off.

5. **MCP servers** — note which of the servers for the enabled capabilities responded (DB, prod DB, http-client, playwright, chrome-devtools, postman, github, filesystem, Atlassian, the project MCP in §14 if any). A server that errors here is a stop condition for any skill that needs it.

   **5b. Is the change under test actually deployed?** A green environment with yesterday's build is the most common false-start; verify the build, not the deploy message.
   - **Frontend:** fetch the site root (`mcp__http-client__http_get <main app URL>`), extract the hashed entry bundle name (e.g. `/assets/index-<hash>.js`), fetch it, find the lazy chunk for the changed screen, fetch that chunk, and grep it for a unique string or regex from the fix (a new label, a renamed key, a new condition). Found -> deployed; not found -> NOT deployed -> RED, stop condition. Two or three calls. If the app prints a version (a console `[App Info] Version …` line, a `/version` route, or a build-id header) record it next to the result.
   - **Backend:** call the version / health / build-info endpoint (`PROJECT-PROFILE.md §5`) when one exists; otherwise send one request that only the new code answers in its new way (a new field, a changed status code, a changed validation message).
   - **Async workers / serverless functions (`PROJECT-PROFILE.md §11`):** the deployed version or alias, when reachable; otherwise record "worker version not verifiable" as Remaining Risk, not as GREEN.
   - **Deploy pending:** do not spin. If the session has a loop / timer facility, re-run only this check on an interval and resume the run when the fix string is live; otherwise report the run as PARTIAL with the deploy as the named blocker.

6. **Release radar** — *optional; Jira / issue tracker on (`PROJECT-PROFILE.md §15`).* What is about to ship that QA has not touched? Search the tracker live (`mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`, or the tracker API named in §15) for issues in the current release / fixVersion whose status is one of the pre-deploy states named in §15 (e.g. Ready for QA, Ready to Deploy, Dev Done). For every hit, read its comments and history: no QA comment and no QA transition = shipping untested -> a RED row with the ticket key. Print the baseline even when it is clean ("N open in the release, k in pre-deploy states, 0 untouched"). *(illustrative)* a ticket sat in the ready-to-deploy state with zero QA comments; its fix carried a data-loss regression that reached production. This is escape class **E11** (qa-standards -> Escape classes & their gates). A remembered ticket status is not evidence — read it live (qa-standards -> Fresh vs Historical).

7. **Prod sentinel** — *optional; Prod-DB on (`PROJECT-PROFILE.md §6`).* Is production already bleeding? Run `Skill(prod-sentinel)` when it is installed — at minimum its failure-rate scan and its bulk-content-event scan. By-hand equivalent against the read-only prod DB: (a) group the project's main error / event log table (`PROJECT-PROFILE.md §10`) by month × status for the last 120 days and flag any month whose error share exceeds the trailing 3-month mean by 15 points; (b) count new rows per day in each content / template table (§10) for the last 60 days and flag any day with 10 or more — that is a content import, i.e. a data release. **A content import in the last 14 days is a stop condition for GO on anything that touches the imported content until `Skill(latent-pattern-sweep)` has run against it.** This is escape class **E10**. Print the numbers even when nothing is alarming — the next run needs them as its baseline.

## Output — Readiness table

| Check | Target | Result | Detail |
|---|---|---|---|
| Test DB | <test DB name: PROJECT-PROFILE.md §6> | GREEN/RED/N/A | `SELECT 1` ok? |
| Main app (FE) | <main app URL: PROJECT-PROFILE.md §5> | GREEN/RED/N/A | status code, build id |
| Backend API | <API base URL: PROJECT-PROFILE.md §5> | GREEN/RED/N/A | status code, version |
| Admin | <admin URL: PROJECT-PROFILE.md §5> | GREEN/RED/N/A | status code |
| Repos on branch | <branch: PROJECT-PROFILE.md §3> @ commit | GREEN/RED/N/A | which repo is off/behind |
| Auth | <role account: PROJECT-PROFILE.md §7> token / session | GREEN/RED/N/A | token obtained? |
| MCP servers | (list for enabled capabilities) | GREEN/RED | which failed |
| Change deployed? | fix string / version per surface | GREEN/RED | bundle grep, version endpoint, worker alias |
| Release radar | current release / fixVersion | GREEN/RED/N/A | tickets in pre-deploy states with no QA touch |
| Prod sentinel — failure rate | main log / event table | GREEN/RED/N/A | share vs trailing baseline |
| Prod sentinel — content events | content / template tables, 60 days | GREEN/RED/N/A | date + count; sweep required? |

**Verdict:** READY (every applicable check GREEN) or NOT READY (list the RED items as **stop conditions** to hand to the QA skill's Scope Lock). Name every `N/A (capability off)` row in the verdict line — "Release radar skipped: Jira off" — so it is recorded as NOT YET VERIFIED, not as a pass. If the feature under test is not yet deployed to the target env, say so first — it is the most common false-start.

---

## Note
This is a preparatory utility (like `sync-repos`) — it produces a readiness verdict, not bug findings, so checks 1–5 need no Evidence Ledger or memory ritual. If a check is RED, that RED item becomes a documented stop condition for the run. Two exceptions:
- **Check 7 ran:** write the sentinel numbers into memory (`<memory folder: PROJECT-PROFILE.md §12>`) as the next baseline, per `prod-sentinel`'s own ritual; an anomaly row without a ticket id is an unfinished run.
- **Check 6 found an untested ticket:** report it to the user and to the orchestrator as a RED row; any comment or transition on the ticket follows the issue tracker rules in `PROJECT-PROFILE.md §15` and happens only when the user asks.
