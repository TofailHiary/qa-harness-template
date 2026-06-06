---
name: code-review
description: Use when a PR, commit, branch diff, or named file/feature needs a code-level review for bugs, security holes, logic errors, edge cases, and coding-standard compliance — across FE (<legacy frontend repo: PROJECT-PROFILE.md §3>), BE (<backend repo: PROJECT-PROFILE.md §3/§9>), Admin (<admin repo: PROJECT-PROFILE.md §3/§9>), or Report. Triggers include "review this PR", "code-review #NNN", "review the diff", "check this change before merge", "look over a file for bugs".
argument-hint: "file path, feature name, or PR description"

allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__github__*", "mcp__claude_ai_Atlassian__*"]
---

# Code Review Workflow

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/code-review` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Review code for bugs, security issues, logic errors, and standards compliance — every issue cited to `path:line`, and the review covers the diff **plus its blast radius**, not just the changed lines.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What should I review — a PR number, a branch/commit diff, or a file/feature? If it maps to a Jira ticket, give the key so I can pull acceptance criteria."

Do NOT guess scope from conversation. Do NOT review the whole repo.

---

## Scope Lock (REQUIRED — before reviewing)

State exactly which files/diff are under review before reading code (qa-standards -> Scope Lock). If a critical field is unknown, ask — do not guess.

| Field | Value |
|---|---|
| PR / commit / feature | |
| Files / diff in scope | (enumerate the changed files) |
| Layer(s) | FE (<legacy frontend repo: PROJECT-PROFILE.md §3>) / BE / Admin / Report |
| Acceptance criteria source | Jira key / PR body / none |
| Direct dependents | (Impact Analysis) |
| Indirect blast radius | shared components / endpoints / tables / async / caches (Impact Analysis) |
| Out of scope (explicit) | |
| Branch | <branch: PROJECT-PROFILE.md §3> (branch names can be case-sensitive) |
| Risk level | Low / Medium / High |

Pull acceptance criteria from the ticket via `mcp__claude_ai_Atlassian__*` when the source is a Jira issue — review against the AC, not guesses. Do not silently narrow scope to make an APPROVE easier; if you skip a file, say so and why.

---

## Impact Analysis — review the blast radius, not just the diff (REQUIRED)

The #1 cause of missed bugs is reviewing only the changed lines. A change is the diff **plus** everything it can break (qa-standards -> Impact Analysis). Before writing the assessment, trace each outward and review the call sites you find:

- **Shared FE components** — is a changed component/hook reused elsewhere? `mcp__github__search_code` / Grep its imports; a prop/contract change ripples to every consumer.
- **Shared API endpoints** — do other features call a changed route? Different params / roles / pagination?
- **Shared DB tables/columns** — what else reads/writes a touched table? Reports, dashboards, exports, other endpoints, async writers.
- **Async consumers** — background jobs, cron, SQS, S3 events, email templates (see `PROJECT-PROFILE.md §11`).
- **Caches & snapshots** — React Query keys, snapshot tables (`PROJECT-PROFILE.md §11`), materialized aggregates that can drift.

List the blast radius in the Scope Lock and confirm each surface still behaves. An untraced dependent is a coverage gap — name it, do not imply it passed.

---

## Layer Rules — read before reviewing that layer

Read the matching rule file(s) (they encode the project-specific standards + gotchas):
- FE -> `.claude/rules/frontend.md`
- BE -> `.claude/rules/backend.md`
- Admin -> `.claude/rules/admin.md`
- Any DB-touching change -> `.claude/rules/db-gotchas.md` (roles in join tables, soft-delete tables, FK map — see `PROJECT-PROFILE.md §10`).

---

## Repositories & Key Paths

| Repo | Type | Key Paths |
|------|------|-----------|
| <legacy frontend repo: PROJECT-PROFILE.md §3> | Legacy FE | `src/` |
| <frontend repo: PROJECT-PROFILE.md §3/§9> | Primary FE | `<frontend API layer: PROJECT-PROFILE.md §9>`, `src/components/`, `src/pages/` |
| <backend repo: PROJECT-PROFILE.md §3/§9> | Backend | `routes/`, `models/`, `middleware/auth.js`, `controllers/` |
| <admin repo: PROJECT-PROFILE.md §3/§9> | Admin | `controllers/`, `models/`, `views/` |
| <report repo: PROJECT-PROFILE.md §3> | Reporting | `src/` |

**Branch:** <branch: PROJECT-PROFILE.md §3> (branch names can be case-sensitive)

---

## Review Checklist

1. **Business Logic** — implements the AC correctly; edge cases + error paths handled.
2. **Security** — no hardcoded secrets; server-side input validation; SQLi-safe (parameterized queries); XSS-safe (no `dangerouslySetInnerHTML` without sanitization); auth/authz on every protected route (ownership, not just `isAuthenticated`); no sensitive data in logs/responses.
3. **Data Integrity** — DB transactions + rollback for multi-table ops; soft-delete consistency (`deleted_at` only where it exists); FK relationships maintained; null/undefined handled.
4. **Code Quality** — project style; no unused imports/dead code; no empty catch blocks; no `console.log` in prod; meaningful names.
5. **API Design** — RESTful; correct HTTP methods + status codes; consistent response schema; pagination where needed; errors informative but not leaking internals.
6. **Frontend** — hooks correct (deps arrays); `useEffect` cleanup (no leaks); React Query cache keys consistent; i18n (no hardcoded user-facing strings); UI component library per design system (see PROJECT-PROFILE.md §4); loading/error/empty states.
7. **Backend** — models match DB schema (verify via `mcp__mcp_server_mysql__mysql_query`); migrations exist for schema changes; middleware applied; async/await error handling; no N+1 queries.
8. **Cross-Layer** — FE API calls match BE route signatures; request/response types + error handling consistent across layers.

---

## Execution Flow

1. **Identify scope** — `mcp__github__list_pull_requests` + `pull_request_read` for PRs and changed files; `list_commits` for recent commits; pull AC from Jira via `mcp__claude_ai_Atlassian__*` if ticket-driven.
2. **Trace the blast radius** (Impact Analysis above) — `mcp__github__search_code` / Grep every importer / caller / reader of the changed symbols, and review those sites too.
3. **Read each file** — `mcp__github__get_file_contents` (remote) or local `Read`; read the relevant `.claude/rules/*` for the layer; apply the 8-point checklist.
4. **Check against DB** — verify models match schema via `mcp__mcp_server_mysql__mysql_query`.
5. **Document** — every issue as a ledger row with `path:line`.

---

## Evidence Ledger (REQUIRED in the output)

**No evidence = no finding.** Every issue cites a concrete **`path:line`** — a code file reference is valid, sufficient evidence for a code review (no runtime repro needed to flag a code-level defect, but mark "code-level, runtime not verified" when that is the case).

| Evidence ID | Type | Source | path:line / PR | What it proves |
|---|---|---|---|---|

Findings stay in the chat conversation, not as markdown files in `qa-evidence/`.

---

## Output Format

### Code Review Summary

| Metric | Count |
|--------|-------|
| Files Reviewed | N |
| Blast-radius files checked | N |
| Issues Found | N |
| Critical / High / Medium / Low | N / N / N / N |

### Issues

| # | path:line | Severity | Category | Description | Recommendation |
|---|-----------|----------|----------|-------------|---------------|

Classify each issue's layer (FE / BE / Admin / Report / DB / Both) per qa-standards.

### Overall Assessment
- **APPROVED** — no critical/high issues
- **CHANGES REQUESTED** — issues must be fixed
- **NEEDS DISCUSSION** — architectural concerns require team input

State coverage gaps explicitly — an unreviewed dependent is never an implied APPROVE.

---

## Superpowers escalation
Non-obvious defect / unclear root cause after the read-through -> `superpowers:systematic-debugging`. Before declaring APPROVED / clean -> `superpowers:verification-before-completion` (evidence before assertions).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the PR/file path/symbol/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** PR/feature + date, verdict (APPROVED / CHANGES REQUESTED / NEEDS DISCUSSION), issues (`path:line`, severity, layer, NEW/DUPLICATE), files reviewed + blast-radius files, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` shows non-zero size, else HALT.
