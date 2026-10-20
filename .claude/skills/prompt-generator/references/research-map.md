# Where each input lives in this setup — the research map for prompt-generator

Read-only lookups, keyed to `.claude/PROJECT-PROFILE.md`. Cite the tool and the id in the Research Register. These are pointers; the environment is the source of truth, so when a pointer and the environment disagree, the environment wins and this file gets corrected.

Capability names come from `PROJECT-PROFILE.md` §2. A row whose capability is `off` is filled "not available: <capability> off → agent must <action>", never skipped.

## R1 Setup rules (always available)
- `.claude/CLAUDE.md` + `.claude/PROJECT-PROFILE.md` (always loaded): identity §1, capabilities §2, repos and branches §3, stack §4, URLs §5, DB connections §6, accounts by identifier §7, roles §8, code paths §9, tables and gotchas §10, async consumers §11, evidence and memory paths §12, docs §13, project MCP / typed tools §14, issue tracker §15, QA policy §16, plugins §17.
- `.claude/skills/qa-standards/SKILL.md`: QA Modes, Scope Lock, Impact Analysis & Coverage, Evidence Ledger, Mutation Safety Gate, MCP Server Routing, Completion Gate, Verdict Contract, Execution Register, Authoritative Source Hierarchy, Judgement Discipline, Escape classes & their gates, Memory Ritual.
- `.claude/rules/*.md`: `testing.md` and `db-gotchas.md` always loaded; `frontend.md` / `backend.md` / `admin.md` per layer; `anomaly-disposition.md` and `pushback-protocol.md` when the project ships them.
- `.claude/hooks/completion-gate.py` → `checks()`: the checks a verdict turn must satisfy (evidence reference, BLOCKED with what unblocks it, live ticket read, named gaps, CANNOT CONFIRM with escalation, dismissal with source, Execution Register present, confidence line and its arithmetic, dissolved-anomaly phrases, PASS-by-toast, fix verified without root cause, concession without a new fact). Count them in the file; do not quote a remembered number.
- `.claude/hooks/harness-config.json`: which folders are write-blocked, where memory and evidence live.
- `.claude/references/system-map.md` (when the project maintains one): route mounts, admin controllers, FE pages and route constants, DB families, async chains, armed risks, search recipes. A section older than its stated verification date is unverified — re-derive it from code.

## R2 Ticket (capability: Jira — the tracker in §15)
- Read the live issue with the tracker tool named in §15 (default `mcp__claude_ai_Atlassian__getJiraIssue` for `APP-nnn`): status, assignee, fix version, parent, description, acceptance criteria, every comment (the newest product-owner / developer comment can override the AC), remote links (PRs).
- Linked and duplicate issues: `mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`, e.g. `project = <project key: §15> AND text ~ "<feature>" ORDER BY updated DESC`.
- Filing rules (project key, issue types, assignee routing, status transitions) are §15 facts; copy them into the prompt only when the owner authorised issue creation.
- Tracker `off`: the AC come from the owner's pasted material → every expectation is labelled INFERRED and the prompt says so.

## R3 Memory (always available)
- `grep -ril "<APP-nnn|feature words|path>" "<memory folder: PROJECT-PROFILE.md §12>"` and the same over any archive sub-folder it has.
- `MEMORY.md` (first 200 lines) is the index; `index_*.md` are sub-indexes when present.
- From each hit: verdict, bugs NEW/DUPLICATE, fixtures (ids / identifiers), root cause `path:line`, SUPERSEDED markers, ARMED findings from `latent-pattern-sweep`. Dated snapshots, never evidence.

## R4 Prior evidence (always available)
- `ls qa-evidence/ | grep -i <id>`; `grep -rl <term> qa-evidence/`; then the archived evidence folder if the project keeps one beside it (quote the path if it has spaces). Record what was captured and what never was.

## R5 Code (capability: GitHub and/or LocalRepos)
- Repo table and branches: §3 (branch names are case-sensitive; different repos may target different branches — read the row, do not assume one branch for all).
- PR: `mcp__github__pull_request_read` (files, diff, base and head, merged state), `mcp__github__list_commits`.
- Local state (read-only verbs only): `git -C <repo> branch --show-current`, `git -C <repo> log -1 --format='%h %ci %s'`, `git -C <repo> diff --name-only <base>..<head>`, `git show`. Pulling is `/sync-repos`, run by full-qa Phase 1, not here.
- File → surface: §9 key code paths (frontend API layer, pages / components, backend routes, models, auth middleware, admin controllers) and `.claude/references/system-map.md` §2–6 when present.
- Shared callers: Grep the component name across the frontend repo; the route path across the backend routes and every frontend that calls it; the table name across every repo in §3 plus the async consumers in §11.
- Is the fix live? The check belongs to `env-health`; the prompt names what to look for (a unique string from the diff in the deployed bundle, a build id, a worker / function version). Deploy state stays UNKNOWN in the prompt.

## R6 Data (capability: DB)
- Columns, enums, comments (MySQL form; adapt per §4): `SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='<test DB name: PROJECT-PROFILE.md §6>' AND TABLE_NAME='<t>' ORDER BY ORDINAL_POSITION`; the soft-delete mechanism per `.claude/rules/db-gotchas.md` and §10 (confirm the column exists before filtering on it).
- Candidate rows: read-only SELECT with LIMIT; record ids only, never personal data.
- Typed tools: if §14 lists a project MCP server with typed tools for the routes under test, name the tool the agent runs as the role; otherwise the agent uses `mcp__http-client__*`.
- Contracts: `mcp__postman-api-mcp__*` when Postman is `on`; otherwise the routes path in §9.

## R7 Environment and tools
- Target env defaults to Test. URLs §5, DB names §6, accounts by identifier and role §7 (passwords live in environment variables / the git-ignored `.mcp.json` — never in the prompt).
- `.mcp.json` lists the servers; `env-health` probes them; a project MCP status tool, if §14 lists one, shows the live sessions / profiles. Deploy state is UNKNOWN until `env-health` runs.

## R8 Fixtures (capability: DB)
- `test-data-manager` Step 2 LOCATE: existing records that fit; input classes (parser / upload / device) and sample files from the folder §13 names, if any; a local replica or writable copy if §6 lists one.
- Only a resource that cannot be started is a gap; a closed tunnel or a stopped container is an operational step the prompt names.

## R9 Armed risks
- §11 async consumers (terminal writer and silent-failure mode per chain); `.claude/references/system-map.md` §6–7 when present; ARMED rows in memory from `latent-pattern-sweep`; `.claude/rules/anomaly-disposition.md` Rule 2 (what cardinality / mode / format does this content introduce that production has never held?) and Rule 3 patterns P1–P3.

## R10 Ambiguities
- Conflicts between ticket text, comments, design and code are findings for the prompt's "sources conflict" procedure.
- Missing or two-way AC, owner present: if the `mattpocock-skills` plugin is installed (§17) → `Skill(mattpocock-skills:grilling)`; otherwise by hand — list each ambiguity as a closed question with the two readings and the test each implies, ask, and record the answer in the owner's words. Facts are looked up in this session, never by a sub-agent.
- Owner absent → open question plus the code-derived reading labelled INFERRED.
