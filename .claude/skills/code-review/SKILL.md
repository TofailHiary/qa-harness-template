---
name: code-review
description: Use when a PR, commit, branch diff, or named file/feature needs a code-level review for bugs, security holes, logic errors, edge cases, and coding-standard compliance across the project's frontend, backend, admin, reporting, or background-worker code, or when a bug-fix PR must be checked for touching the real root cause. Triggers include "review this PR", "code-review #NNN", "review the diff", "check this change before merge", "look over a file for bugs", "did this fix touch the root cause".
argument-hint: "file path, feature name, or PR description"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)", "Write"]
---

# Code Review Workflow

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/code-review` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Review code for bugs, security issues, logic errors, and standards compliance — every issue cited to `path:line`, and the review covers the diff **plus its blast radius**, not just the changed lines. For a bug-fix PR it also answers one more question: did the fix touch the root cause, or only the symptom?

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Scope Lock, Impact Analysis & Coverage, Evidence Ledger, Verdict Contract, Escape classes & their gates, Memory Ritual); safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What should I review — a PR number, a branch/commit diff, or a file/feature? If it maps to a ticket in the issue tracker (PROJECT-PROFILE.md §15), give the key so I can pull acceptance criteria."

Do NOT guess scope from conversation. Do NOT review the whole repo.

---

## Scope Lock (REQUIRED — before reviewing)

State exactly which files/diff are under review before reading code (qa-standards -> Scope Lock). If a critical field is unknown, ask — do not guess.

| Field | Value |
|---|---|
| PR / commit / feature | |
| Review kind | new feature / refactor / **bug fix** (a bug fix adds the Root-Cause Check below) |
| Files / diff in scope | (enumerate the changed files) |
| Layer(s) | FE (<frontend repo: PROJECT-PROFILE.md §3/§9>) / BE (<backend repo: PROJECT-PROFILE.md §3/§9>) / Admin (<admin repo: PROJECT-PROFILE.md §3/§9>) / Report (<report repo: PROJECT-PROFILE.md §3>) / async worker (PROJECT-PROFILE.md §11) |
| Acceptance criteria source | ticket key (PROJECT-PROFILE.md §15) / PR body / none |
| Direct dependents | (Impact Analysis) |
| Indirect blast radius | shared components / endpoints / tables / async / caches (Impact Analysis) |
| Out of scope (explicit) | |
| Branch / commit | <branch: PROJECT-PROFILE.md §3> @ `git rev-parse --short HEAD` (branch names can be case-sensitive) — stamp every Evidence Ledger row with it |
| Risk level | Low / Medium / High |

Pull acceptance criteria from the ticket via `mcp__claude_ai_Atlassian__*` when Jira is `on` (PROJECT-PROFILE.md §2) and the source is a tracker issue — review against the AC, not guesses. The Authoritative Source Hierarchy in qa-standards ranks the ticket, its AC and the developer / product-owner clarifications on it above the code: the code shows what the change DOES, never what it SHOULD do. Do not silently narrow scope to make an APPROVE easier; if you skip a file, say so and why.

---

## Impact Analysis — review the blast radius, not just the diff (REQUIRED)

The #1 cause of missed bugs is reviewing only the changed lines. A change is the diff **plus** everything it can break (qa-standards -> Impact Analysis). Before writing the assessment, trace each outward and review the call sites you find:

- **Shared FE components** — is a changed component/hook reused elsewhere? `mcp__github__search_code` / Grep its imports; a prop/contract change ripples to every consumer.
- **Shared API endpoints** — do other features call a changed route? Different params / roles / pagination?
- **Shared DB tables/columns** — what else reads/writes a touched table? Reports, dashboards, exports, other endpoints, async writers.
- **Async consumers** — background jobs, cron, queues, storage events, email templates (see `PROJECT-PROFILE.md §11`).
- **Caches & snapshots** — client query-cache keys, snapshot tables (`PROJECT-PROFILE.md §11`), materialized aggregates that can drift.
- **Other repos / async owners** — the code is in more than the FE / BE / Admin repos. A symptom seen in one screen is often produced by a background worker, serverless function or integration job (`PROJECT-PROFILE.md §11`). Trace the chain to its terminal writer before deciding which repo the review covers (qa-standards -> Escape classes, E7 "wrong repo").

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
| <frontend repo: PROJECT-PROFILE.md §3/§9> | Primary FE | `<frontend API layer: PROJECT-PROFILE.md §9>`, `<frontend pages / components: PROJECT-PROFILE.md §9>` |
| <legacy frontend repo: PROJECT-PROFILE.md §3> | Legacy FE (only if the project keeps one) | `src/` |
| <backend repo: PROJECT-PROFILE.md §3/§9> | Backend | `<backend routes: PROJECT-PROFILE.md §9>`, `<backend models: PROJECT-PROFILE.md §9>`, `<auth middleware: PROJECT-PROFILE.md §9>`, controllers |
| <admin repo: PROJECT-PROFILE.md §3/§9> | Admin | `<admin controllers: PROJECT-PROFILE.md §9>`, models, views |
| <report repo: PROJECT-PROFILE.md §3> | Reporting | `src/` |
| Async workers / functions | Background | per `PROJECT-PROFILE.md §11` |

**Branch:** <branch: PROJECT-PROFILE.md §3> (branch names can be case-sensitive). A system overview, when the project has filled it in, lives in `.claude/references/system-map.md`.

---

## Review Checklist

1. **Business Logic** — implements the AC correctly; edge cases + error paths handled.
2. **Security** — no hardcoded secrets; server-side input validation; SQLi-safe (parameterized queries via the ORM in `PROJECT-PROFILE.md §4`, never string concatenation); XSS-safe (no `dangerouslySetInnerHTML` / raw HTML sinks without sanitization); auth/authz on every protected route (ownership and tenant checks, not just `isAuthenticated`); no sensitive data in logs/responses.
3. **Data Integrity** — DB transactions + rollback for multi-table ops; soft-delete consistency (`deleted_at` only where it exists); FK relationships maintained; null/undefined handled.
4. **Code Quality** — project style; no unused imports/dead code; no empty catch blocks; no `console.log` in prod; meaningful names.
5. **API Design** — RESTful; correct HTTP methods + status codes; consistent response schema; pagination where needed; errors informative but not leaking internals.
6. **Frontend** — hooks correct (deps arrays); effect cleanup (no leaks); query-cache keys consistent; i18n (no hardcoded user-facing strings); UI component library per the design system (PROJECT-PROFILE.md §4); loading/error/empty states.
7. **Backend** — ORM models match the DB schema (verify via `mcp__mcp_server_mysql__mysql_query` — DB tool: PROJECT-PROFILE.md §6); migrations exist for schema changes; middleware applied; async/await error handling; no N+1 queries.
8. **Cross-Layer** — FE API calls match BE route signatures; request/response types + error handling consistent across layers.

---

## Root-Cause Check — bug-fix PRs (REQUIRED)

A change that makes the symptom disappear is not a fix of the bug. Before APPROVING a bug-fix PR:

1. **Find the root cause the ticket / bug report / prior memory names** (`path:line`). If none is named, derive it: trace the symptom to the line that *produces* the wrong value — do not stop at the line that *displays* it.
2. **`git diff --name-only <base>..<fix>`** (or the file list from `mcp__github__pull_request_read`) **must include that file**, and a hunk must change that line or its guard.
3. **If it does not, the PR is a symptom patch.** Say so in the verdict — "symptom fixed, root cause untouched" — classify CHANGES REQUESTED, and recommend the ticket stays open. *(illustrative)* a fix PR hid an import error by adding a fallback in the form component, while the numeric-id coercion that caused it, one file away, stayed untouched; the bug returned with the next import.
4. **Negative control.** The edge case that the ORIGINAL bug's fix (or the previous fix in the same area) protected must still be covered — read that code path too, and say whether it is.

This is escape class **E6** in qa-standards -> Escape classes & their gates. Name it in the verdict when you close it.

---

## Latent-pattern hints — grep while you read

A diff can be correct for today's data and still wrong for next month's (qa-standards -> Escape classes, E3 "latent assumption"). While reading, grep the touched files (and the files that feed them) for these assumptions. If any is present, say so in the review and hand it to `Skill(latent-pattern-sweep)`, which crosses the assumption against the LIVE data distribution — do not judge it from the code alone.

| Pattern | Grep hint | Question to ask |
|---|---|---|
| **P1 cardinality** — "there is exactly one" | `const \[\w+\] = `, `rows\[0\]`, `\.find\(` used as *the* record, `LIMIT 1` without `ORDER BY` | can the partition this reads from ever hold two rows? |
| **P2 unexercised branch** — a mode the data never took | `if \(\w+\.(code\|type\|mode\|status\|kind\|source) ==`, `switch` on an enum, a default arm | has the `else` / default arm ever run in production? |
| **P3 input class** — "this field is always populated" | `\?\?`, `\|\| ''`, `.required()` on parser / upload / import output | which real input leaves it empty or whitespace? |

A new enum value, content mode or file format introduced by the diff makes the P2 question mandatory.

---

## Execution Flow

1. **Identify scope** — `mcp__github__list_pull_requests` + `pull_request_read` for PRs and changed files; `list_commits` for recent commits; pull AC from the tracker via `mcp__claude_ai_Atlassian__*` (Jira on) if ticket-driven.
2. **Trace the blast radius** (Impact Analysis above) — `mcp__github__search_code` / Grep every importer / caller / reader of the changed symbols, and review those sites too.
3. **Read each file** — `mcp__github__get_file_contents` (GitHub on) or local `Read` (LocalRepos on); read the relevant `.claude/rules/*` for the layer; apply the 8-point checklist.
4. **Bug fix?** — run the Root-Cause Check. In every case, grep the latent-pattern hints.
5. **Check against DB** — verify models match the schema via `mcp__mcp_server_mysql__mysql_query` when DB is `on`; otherwise compare against the migration files and state that the live schema was not checked.
6. **Document** — every issue as a ledger row with `path:line`.

---

## Evidence Ledger (REQUIRED in the output)

**No evidence = no finding.** Every issue cites a concrete **`path:line`** — a code file reference is valid, sufficient evidence for a code review (no runtime repro needed to flag a code-level defect, but mark "code-level, runtime not verified" when that is the case). Stamp provenance (qa-standards -> Evidence provenance): the branch @ commit from the Scope Lock.

| Evidence ID | Type | Source | path:line / PR | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

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
| Root-Cause Check (bug fixes) | touched / **symptom only** / n/a |
| Latent-pattern hits handed to `latent-pattern-sweep` | N |

### Issues

| # | path:line | Severity | Category | Description | Recommendation |
|---|-----------|----------|----------|-------------|---------------|

Classify each issue's layer (FE / BE / Admin / Report / DB / Both) per qa-standards -> Bug Classification.

### Overall Assessment
- **APPROVED** — no critical/high issues
- **CHANGES REQUESTED** — issues must be fixed (always the result for a symptom patch)
- **NEEDS DISCUSSION** — architectural concerns require team input

**Mapping into the central contract (qa-standards -> Verdict Contract).** When this review feeds an orchestrator (`full-qa`, `release-check`) or the memory file, the canonical word prints first and the review alias follows in parentheses: APPROVED -> **GO (APPROVED)**; CHANGES REQUESTED -> **NO-GO (CHANGES REQUESTED)**; NEEDS DISCUSSION -> **PARTIAL (NEEDS DISCUSSION)** with the open question named as the blocker. Add the confidence line: `Verified N of M in-scope files; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: <one line or "none">`.

State coverage gaps explicitly — an unreviewed dependent is never an implied APPROVE.

---

## Plugins & escalation (optional — PROJECT-PROFILE.md §17)
- Non-obvious defect / unclear root cause after the read-through -> if the `superpowers` plugin is installed, `Skill(superpowers:systematic-debugging)`; otherwise do the equivalent by hand: write the hypothesis, name the one line of code or one query that would disprove it, read it, and repeat until a single hypothesis survives.
- Before declaring APPROVED / clean -> `Skill(superpowers:verification-before-completion)` if installed; otherwise by hand: for every PASS, name the evidence that would prove it wrong and confirm you looked for it (qa-standards -> Verdict Integrity).
- If `PROJECT-PROFILE.md §16` says sub-agents are disabled, do all of this in-session; never delegate the verdict.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the PR/file path/symbol/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** PR/feature + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**; the review alias may follow in parentheses), issues (`path:line`, severity, layer, NEW/DUPLICATE), files reviewed + blast-radius files, Root-Cause Check result for bug fixes, latent-pattern hits handed to `latent-pattern-sweep`, regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
