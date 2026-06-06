---
name: bug-report
description: Use when documenting a CONFIRMED bug found during testing (verify with /bug-verifier first) — produces the standard report with layer classification, a why-is-this-a-bug justification, severity, reproduction, and evidence. Triggers include "write up this bug", "file a bug report", documenting a NO-GO finding.
argument-hint: "bug description"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*"]
---

# Bug Report Generator

Generate a bug report in the standard format. Output must render cleanly as markdown in chat — no ASCII art, no code-block wrapper around the report itself.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Bug Classification, Memory ritual).

## ARGUMENTS
$ARGUMENTS

## Gate: verify before you report
A bug must be CONFIRMED before it gets a report. If it has not been through `Skill(bug-verifier)` (reproduced, cross-layer checked, alternatives eliminated), run that first. **No reproduction = no confirmed bug** (qa-standards). A report without an Evidence Ledger row per claim is incomplete.

---

## Pre-Report Investigation
1. **Reproduce** the bug at least twice (`mcp__playwright__*`); record the rate.
2. **Check DB** (`mcp__mcp_server_mysql__mysql_query`; confirm a prod repro with `mcp__mcp_server_mysql_prod__mysql_query`, read-only, only if needed).
3. **Console** (`mcp__chrome-devtools__list_console_messages`) and **network** (`mcp__chrome-devtools__list_network_requests`) for JS errors / failed calls.
4. **Root cause** — read related code (`Read`, `Grep`, `Glob`), cite `path:line`.

---

## FE vs BE Classification (MANDATORY)
Classify every bug (full tree in qa-standards -> Bug Classification). Summary:

### Step 1: Check the API Response (call it directly)
- Wrong data, or unexpected 500/404 -> Step 2a (likely BE)
- Correct data but UI shows it wrong -> **FE**
- No API call when one was expected -> **FE**

### Step 2a: API wrong -> Check the DB
- DB correct, API wrong -> **BE** (query/logic)
- DB wrong -> **BE** (write-side) or **DB** (migration/schema)

### Step 3: Edge cases
| Scenario | Classification |
|----------|---------------|
| API correct, UI shows wrong | **FE** |
| API wrong, DB correct | **BE** |
| API wrong, DB also wrong | **BE** (write-side) |
| No API call when expected | **FE** |
| API 500 / 200-but-wrong-schema | **BE** |
| FE sends wrong params | **FE** (root cause) |
| FE correct params, API ignores | **BE** |
| Admin panel issue | **Admin** |
| <report repo: PROJECT-PROFILE.md §3> service | **Report** |
| API wrong AND UI mishandles error | **Both FE & BE** |

---

## Why Is This a Bug? (MANDATORY)
Justify every report. Pick a category and answer the 3 questions.

**Categories:** Requirements Violation · Data Integrity · API Contract · Security · UX/Usability · Error Handling · Regression · Cross-Layer Inconsistency · Design Violation · Best Practice.

**3-Question Method:** (1) What rule is violated? (2) What is the evidence (DB query / API response / screenshot)? (3) Why does it matter (user/system impact)?

## Severity
| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | System unusable, data loss, security | Login broken, data corruption, SQLi |
| **High** | Major feature broken, no workaround | Cannot create orders, order processing fails |
| **Medium** | Impaired, workaround exists | Slow perf, UI glitch w/ workaround |
| **Low** | Minor, cosmetic | Typo, alignment |

---

## Output Template
Render directly as markdown (do NOT wrap in a code block).

## [BUG-YYYYMMDD-NNN] — [One-line title]

| Field | Value |
|-------|-------|
| **Bug ID** | BUG-YYYYMMDD-NNN |
| **Reported By** | QA (Claude Code) |
| **Date** | YYYY-MM-DD |
| **Environment** | Test — specify which surface it reproduced on (`<the relevant URL: PROJECT-PROFILE.md §5>`) |
| **Branch** | <branch: PROJECT-PROFILE.md §3> |
| **Severity** | Critical / High / Medium / Low |
| **Priority** | P1 / P2 / P3 / P4 |
| **Component** | Frontend / Backend / Report / Admin / Both / DB |
| **Affected Area** | [feature/module] |

### Bug Classification
**Layer:** FE / BE / Report / Admin / Both / DB
| Check | Result |
|-------|--------|
| API Response | correct / wrong / error / missing |
| DB State | correct / wrong / N/A |
| UI Display | correct / wrong / missing |

**Verdict:** [e.g. "BE bug — API returns wrong data while DB is correct"]

### Why Is This a Bug?
**Category:** [pick one] · **Rule Violated:** [one sentence] · **Impact:** [one sentence]

### Description
[2–4 sentences: endpoints, fields, URLs, role context; end with impact.]

### Steps to Reproduce
**Pre-conditions:** [access / data state]
**Steps:** 1. … 2. … 3. [trigger]
**Reproduction Rate:** Always / Sometimes / Rarely (N/N attempts)

### Expected Result
[concrete values]

### Actual Result
[concrete values + short example]

### Test Data Used
- **User:** [email] (user_id=N, role) · **Password:** [<test password from §7>] · **Key IDs:** [account_id, user_account_id, …]

### Evidence Ledger
Every claim above maps to a row (qa-standards). `No evidence = no finding.`

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|
| E1 | API request/response | … | … | … |
| E2 | DB query result | … | … | … |
| E3 | Browser screenshot | qa-evidence/BUG-…/ | … | … |

(Console errors, API response snippet, and the SQL query+result go in the rows above; attachments live in `qa-evidence/BUG-YYYYMMDD-HHMMSS/`.)

### Root Cause
**File:** [path/to/file:line] · **Issue:** [what the code does wrong] · **Suggested Fix:** [direction]

### Related
- **User Story / Tickets:** [TICKET-XXX] · **Related Bugs:** […] · **Regression:** Yes/No · **Workaround:** […]

---

## Optional: file to Jira
Only when the user asks, file the report to Jira with `mcp__claude_ai_Atlassian__createJiraIssue` (or attach a comment with `addCommentToJiraIssue`). Otherwise the report lives in chat + evidence in `qa-evidence/`.

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never claim success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool (the only path it allows). Frontmatter:
   ```markdown
   ---
   name: <short title>
   description: <one-line searchable hook>
   metadata:
     type: project | feedback | reference | user
   ---
   ```
2. **Cross-reference first** — grep the folder for the endpoint / file path / user ID / symptom; if an entry covers this root cause, **UPDATE it** with today's reproduction instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** bug ID + title + date, severity, layer, NEW/DUPLICATE, test data (IDs/emails), root-cause `path:line`, regression risk, any prior memory disproved.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
