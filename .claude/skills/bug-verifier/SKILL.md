---
name: bug-verifier
description: Use when a suspected bug must be confirmed 100% real before it is reported or counted in a verdict — eliminates false positives from stale data, caching, env, or wrong assumptions. Triggers include "verify this bug", "is this actually a bug", a suspected issue from testing, or the gate before /bug-report.
argument-hint: "bug description or bug ID"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "Skill(flaky-race-verifier)", "Skill(evidence-manager)"]
---

# Bug Verifier — Confirm 100% Valid Issues

Verify a suspected bug is REAL before a report is written or it enters a GO/NO-GO verdict.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Bug Classification, Cross-Layer Consistency, Memory ritual).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which bug should I verify? Give the description, bug ID, or the suspected issue." Do not guess from conversation; do not run queries/tests until the target is known.

---

## Rules
1. Use ultrathink for every verification.
2. Run DB queries ONE AT A TIME (sequentially) to avoid cascading MCP errors.
3. Verify ONE bug at a time — if several, ask which first.
4. Memory is ON-DEMAND for loading; the Memory ritual at the end is MANDATORY.
5. Every step that supports the verdict gets an Evidence Ledger row. **No reproduction = no confirmed bug.**

---

## Verification Checklist (ALL MUST PASS)
1. **Understanding** — Do I fully understand expected behavior? Could this be intentional?
2. **Reproduction** — Confidence ≥ 90%? Deterministic: 1–2 attempts; intermittent (race): ≥ 5 attempts + compute a reproduction rate; default if unclear: 3. Consistent across data/users?
3. **Data** — Test data valid, not stale/corrupt?
4. **Code** — Read the actual implementation; does logic match expectation?
5. **Environment** — Correct env (Test default)? Code current on the expected branch (`PROJECT-PROFILE.md §3`)? Caching ruled out?
6. **Assumptions** — Every assumption verified, not assumed?

---

## Verification Steps

### Pre-Step: Environment (always) + API Contract (if the bug touches an API)
1. **Environment** — correct test env, session authenticated, repos on the expected branch + current.
2. **API Contract** (only if API-related) — `mcp__postman-api-mcp__*` to confirm endpoint/method/headers/auth/body/response schema. **Skip** for purely UI/CSS, i18n/typo, static-asset, a11y, or browser-only (no network) bugs.

### Step 1: Clarify Expected Behavior + Cross-Check Memory
Read code/comments/docs; check how similar functionality behaves elsewhere. **Grep memory** (`~/.claude/projects/c--Users-<user>-<project>/memory/*.md`) for the endpoint, file path, user IDs, ticket/bug IDs, symptom keywords. If a prior entry covers this root cause -> mark **DUPLICATE-CHECK**, verify whether the prior fix regressed or holds, and UPDATE that entry (not a new one) in the post-session.

### Step 2: Reproduce Consistently
Reproduce 3+ times with exact steps. Run `mcp__playwright__*` + `mcp__chrome-devtools__*` together every attempt: drive the UI + screenshot, capture `list_network_requests` and `list_console_messages` at the moment of failure (the network/console layer often shows the failure before the UI does).

**If it does NOT reproduce every time (intermittent)** -> hand off to `Skill(flaky-race-verifier)` to get a reproduction rate + the race/timing/ordering cause.

### Step 3: Verify Test Data
`mcp__mcp_server_mysql__mysql_query` — confirm test data valid, relationships in place. To check whether the same bug exists in prod, query read-only via `mcp__mcp_server_mysql_prod__mysql_query` (tunnel first; never mutate prod).

### Step 4: Verify API Behavior
Hit the endpoint directly (`mcp__http-client__*` / `mcp__postman-api-mcp__*`) — response, auth, format; `mcp__chrome-devtools__*` for the FE's real request.

### Step 5: Read the Code
FE components, BE routes/models, Admin controllers. Business logic, error handling, edge cases. Read the relevant `.claude/rules/{frontend,backend,admin,db-gotchas}.md`.

### Step 6: Cross-Reference Layers
| Layer | Check | Tool | Status |
|-------|-------|------|--------|
| Frontend | Component behavior correct? | `mcp__playwright__*` | [ ] |
| API | Endpoint returns expected data? | `mcp__http-client__*` / `mcp__postman-api-mcp__*` | [ ] |
| Backend | Business logic correct? | `Read`, `Grep`, `Glob` | [ ] |
| Database | Data state correct? | `mcp__mcp_server_mysql__mysql_query` | [ ] |
| Browser | UI displays correctly? | `mcp__playwright__*` + `mcp__chrome-devtools__*` | [ ] |

### Step 7: Eliminate Alternatives
Rule out: expected behavior, user error, test-data issue, env issue, caching, timing/race, missing prerequisite.

### Step 8: Classify the Layer
Apply qa-standards -> Bug Classification (FE / BE / Admin / Report / DB / Both). Output the layer in the verdict so `/bug-report` doesn't re-derive it.

---

## Decision Matrix
| Scenario | Verdict | Action |
|----------|---------|--------|
| Reproducible + code defect + valid data | **CONFIRMED BUG** | Build the Evidence Ledger -> `Skill(bug-report)` |
| Reproducible but expected behavior | **NOT A BUG** | Document as expected |
| Not reproducible | **CANNOT CONFIRM** | Escalation path below |
| Data issue causing behavior | **NOT A BUG** | Fix test data |
| Environment/deployment issue | **NOT A BUG** | Note env issue |

## CANNOT CONFIRM — Escalation Path
Run in order; stop as soon as reproduction succeeds.
- **Round 1 — Different user** (same role; then a 2nd account of that role).
- **Round 2 — Different test data** (other valid records / states: draft vs published, active vs inactive).
- **Round 3 — Clean session** (clear cookies, re-auth — rules out stale token/UI).
- **Round 4 — Direct API** (bypass UI via `mcp__http-client__*` using the Pre-Step contract; fails without UI = backend, passes = FE-specific).
- **Intermittent signal (fails only sometimes)?** Before declaring Unverifiable -> `Skill(flaky-race-verifier)` to quantify the reproduction rate and find the race/timing cause.
- **Root cause non-obvious after the rounds?** Escalate to `superpowers:systematic-debugging` (hypothesis -> isolate -> verify) before declaring unverifiable.
- **All rounds fail -> Declare Unverifiable.** Document exact steps per round, users/data tried, network captured, and what would be needed to reproduce. Do NOT loop the same approach.

---

## Evidence (Confirmed bugs only)
Build the **Evidence Ledger** (qa-standards): `| Evidence ID | Type | Source | File/URL/Tool | What it proves |`. Save attachments to `qa-evidence/BUG-YYYYMMDD-HHMMSS/` (HHMMSS avoids parallel-session collisions). Write them via `mcp__filesystem__write_file` or Bash heredoc (the Write/Edit tool is blocked for `qa-evidence/`); Playwright screenshots: pass `filename: qa-evidence/BUG-YYYYMMDD-HHMMSS/<name>.png` to `browser_take_screenshot` (a bare filename saves to the repo root, NOT qa-evidence). On CONFIRMED, hand the ledger + layer to `Skill(bug-report)`.

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never claim success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool. Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep for the endpoint/path/user-ID/symptom; UPDATE an existing entry (esp. on DUPLICATE-CHECK) instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** bug + date, verdict (CONFIRMED / NOT A BUG / CANNOT CONFIRM / DUPLICATE), layer, reproduction rate, test data (IDs/emails), root-cause `path:line`, any prior memory confirmed/disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
