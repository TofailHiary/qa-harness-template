---
name: pr-risk-analyzer
description: Use when you have a PR, diff, commit, or branch and need its blast-radius risk map BEFORE testing — what files, APIs, DB tables, UI, roles and background jobs it touches directly AND indirectly, with a per-area risk score, so the test plan covers the whole impact, not just the diff. Triggers include "what's the risk of this PR", "impact analysis on #NNN", "what could this change break", "what else uses this table", or the pre-step to /full-qa on a PR.
argument-hint: "PR number, commit, branch, or diff"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__github__*", "mcp__mcp_server_mysql__mysql_query", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)", "Skill(test-cases-generator)", "Write"]
---

# PR Risk Analyzer — Blast-Radius Map

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/pr-risk-analyzer` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Turn a diff into the **full impact surface** so QA tests the blast radius, not just the changed lines. This is the formal front-end to the Scope Lock + Impact Analysis in `qa-standards`.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Impact Analysis & Coverage, Evidence Ledger, Evidence provenance, Escape classes & their gates).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which PR / commit / branch / diff should I analyze? (e.g. 'PR #742 <frontend repo: PROJECT-PROFILE.md §3/§9>')." Do not guess.

---

## Step 1: Get the diff
- PR: `mcp__github__pull_request_read` (files + patch) and `mcp__github__list_commits` (GitHub on).
- Local branch/commit: `git diff`, `git show` (read-only; LocalRepos on). Record `git rev-parse --short HEAD` — it stamps every Evidence Ledger row (qa-standards -> Evidence provenance).
- If a ticket is referenced and Jira is `on` (PROJECT-PROFILE.md §2 / §15), pull the acceptance criteria with `mcp__claude_ai_Atlassian__getJiraIssue` to compare intent vs change. A diff that does more (or less) than the AC is itself a risk row.

## Step 2: Direct impact (what the diff literally changes)
List every changed unit: file, function/component, route, query, DB column, config, migration, feature flag. Note the repo + layer: FE <frontend repo: PROJECT-PROFILE.md §3/§9>, BE <backend repo: PROJECT-PROFILE.md §3/§9>, Admin <admin repo: PROJECT-PROFILE.md §3/§9>, Report <report repo: PROJECT-PROFILE.md §3>, async workers / serverless functions / integration jobs (PROJECT-PROFILE.md §11).

## Step 3: Indirect blast radius (where missed bugs live — the core)
For each changed unit, trace outward with `Grep`/`Glob`/`mcp__github__search_code`:
- **Shared FE components** — grep importers of a changed component across `<frontend repo: PROJECT-PROFILE.md §3/§9>/src/` (and the legacy frontend, if the project keeps one). Every consumer page is in scope.
- **Shared API endpoints** — other callers of a changed route/handler; different roles/params hitting it.
- **Shared DB tables/columns** — what else reads/writes the changed table: other endpoints, reports (<report repo: PROJECT-PROFILE.md §3>), dashboards, CSV exports, snapshot tables (`PROJECT-PROFILE.md §11`). Query `information_schema` (DB on) or grep models for the column.
- **Async consumers** — cron, serverless functions / workers (order processing, parsing, report generation, recommendations — whatever `PROJECT-PROFILE.md §11` lists), queues, storage events, email templates.
- **Caches & snapshots** — client query-cache keys, materialized aggregates that drift from live data.
- **Contract changes** — a changed response shape breaks every FE consumer of that field; a changed request shape breaks the BE.
- **Other repos / async owners** — "FE / BE / Admin" is not the whole system. If the changed data is written or read by a worker in another repo (`PROJECT-PROFILE.md §11`), that repo is in the blast radius too; trace the chain to its terminal writer (qa-standards -> Escape classes, E7).
- **Data-shape assumptions (latent)** — if the diff adds an enum value, a content mode, a file format, or touches code that assumes "exactly one" row per partition, a populated field, or a branch the data has never taken, add a row for `Skill(latent-pattern-sweep)`: the risk is not in the diff but in the data growing past the assumption (qa-standards -> Escape classes, E3).

### Step 3b: Fix PRs — does the diff reach the root cause?
When the PR claims to fix a ticket, compare `git diff --name-only <base>..<fix>` (or the PR file list) with the root-cause `path:line` the ticket, bug report or memory names. If the root-cause file is NOT in the diff, the top row of the impact map is **"symptom patch — original bug still reachable"** at Likelihood H / Impact H, and the handoff to `code-review` must run its Root-Cause Check (qa-standards -> Escape classes, E6).

## Step 4: Roles, states & inputs
- **Roles** — which roles (<roles: PROJECT-PROFILE.md §8>, e.g. Admin / Manager / User / Guest) reach each impacted surface; which cannot and must still be denied (cross-tenant).
- **States** — which data states matter: empty / null / zero / many / max; draft vs published; active vs deleted. Flag falsy/zero and null handling explicitly — `0`, `false`, `null`, `""`, `[]` and "missing key" are different states and a recurring bug class (qa-standards -> Judgement Discipline, "partially-empty beats empty").
- **Input classes** — for any parser / upload / import surface in scope, list the input classes the code must handle (e.g. text-layer vs scanned PDF, image-only, CSV with and without header, empty file) and name the one production has never held. Fixtures come from the sample-file library in `PROJECT-PROFILE.md §13`, if any, else from `test-data-manager`.

## Step 5: Risk-scored output

**Impact map** (one row per impacted area):

| Area | Layer | Direct/Indirect | Roles | Likelihood (H/M/L) | Impact (H/M/L) | Risk | Why it could break | Test focus |
|---|---|---|---|---|---|---|---|---|

Sort by Likelihood×Impact, highest first. Then:

**Test focus summary** — the top areas the test plan MUST cover, and the regression areas that look unrelated but share code/data with the change.

**Coverage denominator** — count the cells the map implies (surfaces × roles × states × input classes). This number, not intuition, becomes `M` in the Scope Lock and the Execution Register (qa-standards -> Escape classes, E12 "guessed denominator").

**Evidence Ledger** (qa-standards) — cite the diff (`mcp__github__pull_request_read` or `git show`), each grep result (`path:line`), and any DB query that proves a shared reader; stamp Env + Branch / Commit + Captured at. `No evidence = no finding` applies to risk claims too — "probably also used by the dashboard" is not a row until the import is cited.

## Step 6: Handoff
Feed the impact map into the **Scope Lock "Indirect blast radius"** row and into `Skill(test-cases-generator)` so cases are generated for the whole surface. For a full run, this is `full-qa` Step 0b done in depth. Hand the Step 3b result to `code-review` and any latent row to `latent-pattern-sweep`.

**Sub-agents (policy knob, PROJECT-PROFILE.md §16):** this skill runs in-session by default. If §16 allows sub-agents and the diff spans three or more repos, one read-only Explore agent per repo may do the grep fan-out — but the risk scores are assigned by the orchestrator from the cited evidence, never copied from an agent's summary (qa-standards -> Verdict Integrity: agreement between your own sub-agents is not independent confirmation).

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion (qa-standards -> Memory Ritual); if it cannot be persisted -> HALT and tell the user.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the PR / feature / table / component; UPDATE an existing entry if the PR or feature already has one.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** PR + date, the high-risk areas identified, the indirect consumers found (so the next regression pass starts from the known blast radius), any contract change, the Step 3b result for fix PRs, and any latent row handed to `latent-pattern-sweep`.
5. **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
6. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
