---
name: pr-risk-analyzer
description: Use when you have a PR, diff, commit, or branch and need its blast-radius risk map BEFORE testing — what files, APIs, DB tables, UI, and roles it touches directly AND indirectly, with a per-area risk score, so the test plan covers the whole impact, not just the diff. Triggers include "what's the risk of this PR", "impact analysis on #NNN", "what could this change break", or the pre-step to /full-qa on a PR.
argument-hint: "PR number, commit, branch, or diff"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__github__*", "mcp__mcp_server_mysql__mysql_query", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)"]
---

# PR Risk Analyzer — Blast-Radius Map

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/pr-risk-analyzer` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Turn a diff into the **full impact surface** so QA tests the blast radius, not just the changed lines. This is the formal front-end to the Scope Lock + Impact Analysis in `qa-standards`.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Impact Analysis, Evidence Ledger).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which PR / commit / branch / diff should I analyze? (e.g. 'PR #742 <frontend repo: PROJECT-PROFILE.md §3/§9>')." Do not guess.

---

## Step 1: Get the diff
- PR: `mcp__github__pull_request_read` (files + patch) and `mcp__github__list_commits`.
- Local branch/commit: `git diff`, `git show` (read-only).
- If a Jira ticket is referenced, pull the acceptance criteria with `mcp__claude_ai_Atlassian__getJiraIssue` to compare intent vs change.

## Step 2: Direct impact (what the diff literally changes)
List every changed unit: file, function/component, route, query, DB column, config. Note the repo + layer (FE <frontend repo: PROJECT-PROFILE.md §3>, BE <backend repo: PROJECT-PROFILE.md §3/§9>, Admin <admin repo: PROJECT-PROFILE.md §3/§9>, Report <report repo: PROJECT-PROFILE.md §3>, Lambda/SAM).

## Step 3: Indirect blast radius (where missed bugs live — the core)
For each changed unit, trace outward with `Grep`/`Glob`/`mcp__github__search_code`:
- **Shared FE components** — grep importers of a changed component across `<frontend repo: PROJECT-PROFILE.md §3/§9>/src/`. Every consumer page is in scope.
- **Shared API endpoints** — other callers of a changed route/handler; different roles/params hitting it.
- **Shared DB tables/columns** — what else reads/writes the changed table: other endpoints, reports (<report repo: PROJECT-PROFILE.md §3>), dashboards, CSV exports, snapshot tables (`PROJECT-PROFILE.md §11`). Query `information_schema` or grep models for the column.
- **Async consumers** — cron, Lambda (order processing / report / recommendation), SQS, S3 events, email templates.
- **Caches & snapshots** — React Query keys, materialized aggregates that drift from live data.
- **Contract changes** — a changed response shape breaks every FE consumer of that field; a changed request shape breaks the BE.

## Step 4: Roles & states
Which roles reach each impacted surface (Admin / Manager / User / Guest). Which data states matter (empty / null / zero / many / max; draft vs published; active vs deleted) — flag falsy/zero and null handling explicitly (a recurring bug class).

## Step 5: Risk-scored output

**Impact map** (one row per impacted area):

| Area | Layer | Direct/Indirect | Roles | Likelihood (H/M/L) | Impact (H/M/L) | Risk | Why it could break | Test focus |
|---|---|---|---|---|---|---|---|---|

Sort by Likelihood×Impact, highest first. Then:

**Test focus summary** — the top areas the test plan MUST cover, and the regression areas that look unrelated but share code/data with the change.

**Evidence Ledger** (qa-standards) — cite the diff (`mcp__github__pull_request_read`), each grep result (`path:line`), and any DB query that proves a shared reader. `No evidence = no finding` applies to risk claims too.

## Step 6: Handoff
Feed the impact map into the **Scope Lock "Indirect blast radius"** row and into `Skill(test-cases-generator)` so cases are generated for the whole surface. For a full run, this is `full-qa` Step 0b done in depth.

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion (qa-standards -> Memory Ritual); if it cannot be persisted -> HALT and tell the user. Record: PR + date, the high-risk areas identified, the indirect consumers found (so the next regression pass starts from the known blast radius), and any contract change. Cross-reference existing memory first; UPDATE if the PR/feature already has an entry. If memory cannot persist -> HALT and tell the user.
