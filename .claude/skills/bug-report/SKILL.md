---
name: bug-report
description: Use when documenting a CONFIRMED bug found during testing (verify with /bug-verifier first) — produces the standard report with layer classification, a why-is-this-a-bug justification, severity, reproduction, and evidence. Triggers include "write up this bug", "file a bug report", documenting a NO-GO finding.
argument-hint: "bug description"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__postman-api-mcp__*", "mcp__http-client__*", "mcp__filesystem__*", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(bug-verifier)", "Write"]
---

# Bug Report Generator

Generate a bug report in the standard format. Output must render cleanly as markdown in chat — no ASCII art, no code-block wrapper around the report itself.

> **Capability note:** this skill is **always on** (utility — see `docs/capability-matrix.md`). The Pre-Report Investigation uses only the layers enabled in `PROJECT-PROFILE.md` §2; a layer whose capability is `off` is recorded as "not checked (capability off)" in the Bug Classification table, never inferred. Filing to the tracker needs Jira `on` (§2) and the rules in §15.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Evidence provenance, Bug Classification, Verdict Contract, Memory Ritual).

## ARGUMENTS
$ARGUMENTS

## Gate: verify before you report
A bug must be CONFIRMED before it gets a report. If it has not been through `Skill(bug-verifier)` (reproduced, cross-layer checked, alternatives eliminated, finding verdict **CONFIRMED BUG**), run that first. A **DUPLICATE** verdict updates the existing entry / ticket instead of producing a new report. **No reproduction = no confirmed bug** (qa-standards). A report without an Evidence Ledger row per claim is incomplete.

---

## Pre-Report Investigation
1. **Reproduce** the bug at least twice (`mcp__playwright__*`), with the reporter's original input class when one was given; record the rate.
2. **Check DB** (`mcp__mcp_server_mysql__mysql_query` — DB tool: `PROJECT-PROFILE.md §6`). Confirm a prod repro only if Prod-DB is `on` (§2), read-only via `mcp__mcp_server_mysql_prod__mysql_query` through the access described in §6 — and label that evidence as PROD, never as the test env.
3. **Console** (`mcp__chrome-devtools__list_console_messages`) and **network** (`mcp__chrome-devtools__list_network_requests`) for JS errors / failed calls.
4. **Root cause** — read related code (`Read`, `Grep`, `Glob`; code paths in `PROJECT-PROFILE.md §9`), including the async terminal writer when the row is produced by a worker / cron / queue consumer (§11); cite `path:line`.

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
| Admin panel issue (`<admin repo: PROJECT-PROFILE.md §3/§9>`) | **Admin** |
| Reporting service (`<report repo: PROJECT-PROFILE.md §3>`) | **Report** |
| Row written wrongly by an async consumer (`PROJECT-PROFILE.md §11`) | **BE** (name the consumer) |
| API wrong AND UI mishandles error | **Both FE & BE** |

---

## Why Is This a Bug? (MANDATORY)
Justify every report. Pick a category and answer the 3 questions.

**Categories:** Requirements Violation · Data Integrity · API Contract · Security · UX/Usability · Error Handling · Regression · Cross-Layer Inconsistency · Design Violation · Best Practice.

**3-Question Method:** (1) What rule is violated — and what is the cited source (AC / spec / schema / code comment / named decision)? (2) What is the evidence (DB query / API response / screenshot)? (3) Why does it matter (user/system impact)?

## Severity
| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | System unusable, data loss, security | Login broken, data corruption, SQLi |
| **High** | Major feature broken, no workaround | Cannot create orders, order processing fails |
| **Medium** | Impaired, workaround exists | Slow perf, UI glitch w/ workaround |
| **Low** | Minor, cosmetic | Typo, alignment |

Severity never changes the run verdict under the default strict-binary policy (`PROJECT-PROFILE.md §16`; qa-standards → Verdict Contract) — one confirmed bug of any severity is NO-GO. It does drive the tracker **priority** (below).

---

## Output Template
Render directly as markdown (do NOT wrap in a code block).

## [BUG-YYYYMMDD-NNN] — [One-line title]

| Field | Value |
|-------|-------|
| **Bug ID** | BUG-YYYYMMDD-NNN |
| **Reported By** | QA Agent |
| **Raised By** | [who first raised the issue and where, e.g. "a manager, via the support chat"] — include this row ONLY when someone raised it; omit it otherwise |
| **Date** | YYYY-MM-DD |
| **Environment** | Test — specify which surface it reproduced on (`<main app URL / admin URL: PROJECT-PROFILE.md §5>`) and the env label (TEST / DEV / PROD-readonly) |
| **Branch** | `<branch: PROJECT-PROFILE.md §3>` @ [short sha] |
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
**Category:** [pick one] · **Rule Violated:** [one sentence + cited source] · **Impact:** [one sentence]

### Description
[2–4 sentences: endpoints, fields, URLs, role context (`<roles: PROJECT-PROFILE.md §8>`); end with impact.]

### Steps to Reproduce
**Pre-conditions:** [access / data state]
**Steps:** 1. … 2. … 3. [trigger]
**Reproduction Rate:** Always / Sometimes / Rarely (N/N attempts) · **Input class:** [the reporter's original file / record / account, or the fixture used]

### Expected Result
[concrete values]

### Actual Result
[concrete values + short example]

### Test Data Used
- **User:** `<role account: PROJECT-PROFILE.md §7>` (user_id=N, role) · **Password:** never written — name the env var from §7 · **Key IDs:** [account_id, user_account_id, …]

### Evidence Ledger
Every claim above maps to a row (qa-standards). `No evidence = no finding.` Provenance columns are mandatory on every row (qa-standards → Evidence provenance).

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|
| E1 | API request/response | … | … | TEST | `<branch>` @ sha | timestamp | … |
| E2 | DB query result | … | … | TEST | `<branch>` @ sha | timestamp | … |
| E3 | Browser screenshot | qa-evidence/<run folder>/ | … | TEST | `<branch>` @ sha | timestamp | … |

(Console errors, API response snippet, and the SQL query+result go in the rows above; attachments live in the run folder `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/`.)

### Root Cause
**File:** [path/to/file:line] · **Issue:** [what the code does wrong] · **Suggested Fix:** [direction] · **Masked error?** [if a second, unrelated exception hid this failure, it is a separate bug — reference it]

### Related
- **User Story / Tickets:** [APP-nnn] · **Related Bugs:** […] · **Regression:** Yes/No · **Workaround:** […]

---

## Optional: file to the issue tracker
Only when the user asks, file the report to the issue tracker configured in `PROJECT-PROFILE.md §15` (for Jira: `mcp__claude_ai_Atlassian__createJiraIssue`, or add a comment with `addCommentToJiraIssue`). Otherwise the report lives in chat + evidence in `qa-evidence/`.

**Filing rules come from §15, never from this skill:** project key, ticket pattern, issue-type names, the subtask-level type, labels, fix-version convention, assignee rule, and transition ids. If §15 is blank for a field the tracker requires, ask — do not guess.

**Sub-issue under a story:** if the user names a parent story (e.g. "under APP-123 as a sub-bug"), first read the project's issue-type hierarchy (Jira: `mcp__claude_ai_Atlassian__getJiraProjectIssueTypesMetadata`) to confirm the subtask-level type §15 names, then create with that `issueTypeName`, `parent: "<STORY-KEY>"`, the story's `fixVersions`, and the labels §15 prescribes. Set `priority` explicitly per the report's severity (Critical -> Highest, High -> High, Medium -> Medium, Low -> Low, or the mapping in §15) — do NOT leave it to the tracker default, which lands everything on Medium.

**Filing mistakes:** if a ticket went in with the wrong type, parent, project or fields, STOP and ask the owner how to correct it. Never re-file a replacement and never close or delete the mis-filed ticket on your own initiative — both leave noise in the tracker and break links.

**Evidence attachments — KNOWN CONNECTOR LIMIT (tell the user every time):** the Atlassian MCP connector exposes create/edit/comment/link but has **NO file-attachment upload tool**. Screenshots/CSVs/logs in `qa-evidence/` therefore CANNOT be pushed into the issue from here. So on every tracker filing:
1. Embed the Evidence Ledger as **text** in the description (DB query + result, API snippet, code `path:line`, repro URL).
2. In the **chat reply only**, output an explicit **"Files to upload manually to <ISSUE-KEY>"** list — the exact `qa-evidence/<run folder>/*.png|csv|json|log` paths the user must drag into that issue by hand — so nothing is silently lost. Map each file to the issue it belongs to.
   **NEVER put this list (or any "files to upload" / "connector cannot attach" note) inside the ticket description or a ticket comment** — it is a private instruction to the owner, not ticket content.
3. State plainly in the chat that the images were **not** attached (tool limit, not a skill gap) and that step 2 is the manual action required.

**Reporter fields:** `Reported By` is always **QA Agent**. If a person raised the issue (a manager, support, a developer, a customer via chat or email), add a separate `Raised By` row with who and where — by role and channel ("a manager, via the support chat"; "a customer, via the support inbox"), adding the person's name only when the tracker rules in §15 want it in the ticket. Never write "QA (Claude Code)" and never merge the two into one field.

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never claim success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it allows). Frontmatter:
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
4. **Content:** bug ID + title + date, severity, layer, NEW/DUPLICATE, tracker key if filed, test data (IDs / account identifiers — never passwords), root-cause `path:line`, regression risk, any prior memory disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
