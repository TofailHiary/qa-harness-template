---
name: release-note
description: Use when you need a stakeholder-ready release note for an application release — a plain-business-language summary of the tickets/epics shipped, pulled from the issue tracker (Atlassian MCP), a tracker export, manual input, or git history. Triggers include "write the release notes", "draft the release email", "summarize this sprint for leadership".
argument-hint: "[release name, tracker filter, or details]"
disable-model-invocation: true
allowed-tools: ["Read", "Grep", "Glob", "Bash", "AskUserQuestion", "mcp__claude_ai_Atlassian__*", "mcp__github__list_pull_requests", "mcp__github__list_commits", "mcp__github__pull_request_read", "mcp__github__get_file_contents", "mcp__github__search_code", "WebFetch"]
effort: high
---

# Release Note Generator

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/release-note` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.
> Jira (§2) is an optional enhancer: when it is `off`, Option A below is unavailable and the other
> data sources are used.

Generate a polished, stakeholder-ready release note. Output renders directly in chat as markdown.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which release (version, tag or date range) and which audience (end users / internal / both)?"

Do not guess the scope.

---

## Tone and Audience Rules (MANDATORY)

This release note is written by a **Product Owner for stakeholders** (leadership, project managers, client contacts). It is NOT a technical document.

### ALWAYS include
- What changed in **plain business language** (1-2 sentences per ticket)
- Ticket IDs (pattern from `PROJECT-PROFILE.md §15`, e.g. APP-1234) so readers can click through for details
- Bug fixes described by **what was broken and that it is fixed** -- user-visible impact
- Feature descriptions focused on **what the user or system can now do**
- Security fixes at a high level ("Fixed unauthorized access to X" -- no exploit steps)
- **Who reported each solved ticket** (person + organization) when the tracker has a reporter / raised-by field or the originating thread names one; "internal" otherwise — so the fix can be fed back to the person who raised it
- Known issues or operational recommendations
- Summary counts and affected repositories

### NEVER include
- Commit hashes, SHAs, or git log references
- API contracts, request/response schemas, endpoint specs, HTTP methods/paths
- Database table schemas, column definitions, migration file names
- Code file paths, line numbers, function names, variable names
- Root cause analysis, stack traces, or error messages
- CORS configs, cron internals, rate limit implementation details
- Test case lists (TC-1, TC-2...)
- ORM model details (Sequelize, Pydantic, etc.)
- Console output, log samples, or cloud-logging references
- Infrastructure details (Lambda configs, queue or NoSQL internals)
- Credentials, account identifiers, or internal URLs

### Rule of thumb
If a non-technical PM would need to Google a term to understand a bullet point, rewrite it in plain language. The ticket link is where technical details live.

---

## Phase 0: Determine Data Source

Use AskUserQuestion FIRST to determine how the user wants to provide ticket data:

### Option A: Issue tracker (Atlassian MCP) — only when Jira is `on` (§2)
If the user wants to pull from the tracker directly:
1. The Atlassian MCP connector is pre-authenticated in this environment; if a call returns an auth error, tell the user to re-authorise the claude.ai Atlassian connector (it cannot be done from here) and fall back to Option B/C until then.
2. Use the Atlassian MCP tools (`mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`, `mcp__claude_ai_Atlassian__getJiraIssue`) to query tickets by sprint, JQL filter, label, or fix version; the project key and any custom fields (reporter / raised-by) come from `PROJECT-PROFILE.md §15`
3. Extract: ticket ID, summary, type, status, parent/epic, labels, sprint, reporter / raised-by (person + organization)

### Option B: Tracker HTML/CSV Export
If the user pastes or attaches a tracker export (HTML table, CSV, or text):
1. Parse the export to extract ticket data
2. Identify columns: Key, Summary, Type, Status, Sprint, Labels, Parent, Description, Reporter / Raised By

### Option C: Manual Input
If the user provides ticket details directly:
1. Accept a list of ticket IDs + descriptions (+ who reported each, if known)
2. Ask clarifying questions for grouping

### Option D: Git History Cross-Reference
If the user wants to check for unreported changes:
1. Use `mcp__github__list_commits` (GitHub `on`) or Bash `git log` in `<repo path: PROJECT-PROFILE.md §3>` (LocalRepos `on`) to find commits since the last release
2. Extract ticket IDs (pattern from §15) from commit messages
3. Flag any commits without a ticket

Always ask the user which option they prefer. Multiple options can be combined.

---

## Phase 1: Gather Release Information

After determining the data source, use AskUserQuestion to collect any MISSING information. Required:

1. **Release metadata** -- Release date, sprint names, total issue count
2. **Recipient** -- Who is the email addressed to?
3. **Author** -- Who signs off? (defaults to the person running the skill — ask if unknown)
4. **Coverage dates** -- "Since [last release date] till now"
5. **In-progress items** -- Tickets started but NOT included?
6. **Long-running epics** -- Epics from prior releases completing work this cycle?
7. **Known issues or notes** -- Caveats, recommendations, known limitations?
8. **Repositories affected** -- Which repos and branches? (`PROJECT-PROFILE.md §3`)
9. **Tracker dashboard link** -- URL for detailed ticket views?
10. **Reporters** -- For each solved ticket, who raised it (person + organization), taken from the tracker's reporter / raised-by field or the originating email / chat thread; "internal" when it came from the team. Ask only for the ones the data source did not supply.

Do NOT proceed to Phase 2 until you have enough data.

---

## Phase 2: Organize and Group

1. **Identify parent/epic relationships** -- Group child tickets under their parent story/epic
2. **Create feature sections** -- Each epic or standalone feature = one numbered section
3. **Order by impact** -- Largest or most important feature first
4. **Separate bug fixes** -- Child bugs go WITH their parent feature section. Standalone bugs get grouped by area (e.g., "Report Fixes", "Security Fixes")
5. **Count totals** -- Completed vs in-progress
6. **Map repositories** -- Which repos touched by which sections
7. **Flag long-running epics** -- Created before current year? Add historical note
8. **Map reporters** -- Attach "Reported by" to every solved ticket: person + organization, or "internal". Never invent a name; if the source does not say, write "internal" and flag it to the user in Phase 1 item 10.

### Writing Each Ticket Line

For each ticket, write ONE line answering: "What changed for the user or system?"

Good examples:
- "Added real-time error detection in the submission workflow — users receive immediate feedback during data entry"
- "Fixed login failure affecting users in incognito/private browser windows"
- "Fixed security issue where account admins could view manager data from other accounts"
- "New frontend error logging system — captures JavaScript errors in production for developer visibility"

Bad examples (too technical -- rewrite these):
- "WebSocket detect-error action with SVG-to-JPEG capture, adaptive compression"
- "decryptData() crash on corrupt localStorage"
- "Added utf8mb4 migration for audit_log table"

Reported-by examples (synthetic):
- "J. Example — Example Organization" (a customer contact named in the tracker's raised-by field)
- "Support desk — Example Partner Ltd" (raised through a partner's support channel)
- "internal" (found by the team or by QA)

---

## Phase 3: Generate Release Note

Output directly in chat as live markdown. No code blocks around the output.

### OUTPUT FORMAT

Hi [Recipient],
Hope you are doing well.
I wanted to share the release notes for our [Month Year] release ahead of deployment. Below is a summary of what is included -- the full detailed document is attached.

**Release Date:** [Date]
**Sprints:** [Sprint names]
**Total Issues:** [N] ([M] completed, [K] in progress)

---

#### Release Summary

[2-4 sentence executive summary. Highlight top 3-5 themes by name. Stakeholder-friendly language only.]

[If long-running epics: "Note: Epics originally created before [Year] ([IDs]) represent long-running initiatives where remaining tasks were completed in this release cycle."]

---

#### [N]. [Feature Area Name] ([item count] items)

**Epic:** [APP-XXX] | **Label:** [LabelName]

[1-2 sentence business description of this feature area.]

| Ticket | Change | Reported by |
|--------|--------|-------------|
| APP-XXX | Plain-language description (1-2 sentences) | J. Example — Example Organization |
| APP-XXX | Plain-language description | internal |

---

[Repeat numbered sections for each feature area]

---

#### [N]. In Progress -- Not Included in This Release ([count] items)

| Ticket | Status | Description |
|--------|--------|-------------|
| APP-XXX | [Status] | What it is + why not included |

---

#### [N]. Known Issues and Operational Notes (if applicable)

[Plain-language description of known issues, mitigations, and recommendations. No code.]

---

#### Release Summary Table

| Area | Items | Status |
|------|-------|--------|
| [Feature Area 1] | [N] | Completed |
| [Feature Area 2] | [N] | Completed |
| **Completed Subtotal** | **[M]** | |
| [In Progress items] | [K] | In Progress |
| **Grand Total** | **[N]** | |

---

#### Repositories Affected

| Repository | Branch | Changes |
|------------|--------|---------|
| <frontend repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | [feature areas, comma-separated] |
| <backend repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | [feature areas] |
| <admin / report / worker repos: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | [feature areas — only when touched] |

---

**Detailed tracker link:** [URL]

Note that any ticket we have worked on from last release since [start date] till now I have added in this. Please let me know if you notice anything or need any further details.

Best regards,
[Author]

---

## Formatting Rules

1. Ticket tables: | Ticket | Change | Reported by | consistently (drop the third column only if the user explicitly does not want reporters named)
2. 1-2 sentences per ticket in business language, past tense ("Added", "Fixed", "Updated")
3. Epic references on section header line (Epic ID + Label)
4. Item counts in section headers: "([N] items)"
5. Long-running epics: italic note at section bottom
6. No code blocks around the release note output
7. Horizontal rules (---) between major sections
8. **ZERO technical jargon** -- if you write a file path, API endpoint, DB column, or code reference, STOP and rewrite in plain language
9. Reported-by cells name the person and organization exactly as the tracker / thread gives them, or "internal" — never a guess

## Quality Checklist

- [ ] Every ticket in sections is counted in the summary table
- [ ] Item counts match actual tickets per section
- [ ] Completed + In Progress = Grand Total
- [ ] All repos listed in Repositories Affected
- [ ] No ticket in more than one section
- [ ] Every solved ticket has a Reported-by value (person + organization, or "internal")
- [ ] Release Summary mentions top 3-5 themes
- [ ] Email intro and closing included
- [ ] ZERO technical details -- no commits, code, schemas, endpoints, credentials or internal URLs

---

## Post-Output

1. Ask the user if they want adjustments (reorder, reword, add/remove tickets, hide reporters)
2. Offer to save to a file (via Bash heredoc to a user-specified path outside the product repos — the read-only hook blocks writes there)

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool; grep the folder first and UPDATE an existing entry instead of filing a duplicate.
2. **Update** `MEMORY.md` with a one-line (<=200-char) dated pointer.
3. **Content:** release id + date, the tickets / PRs covered, anything left out of the note and why.
4. **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows a non-zero size, else HALT.
