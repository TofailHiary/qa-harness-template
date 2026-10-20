# Generalization conventions — how every component in this template is written

This is the contract that every skill, agent, hook, rule and doc in this repository follows. It exists so
that (a) a new user can drop the harness into any project and (b) future improvements pulled from a
private, project-bound setup can be generalized the same way every time without leaking private data.
Read it before editing any file under `.claude/`, and point reviewers at it.

## 1. The single source of project specifics

Everything that is specific to the project under test lives in **`.claude/PROJECT-PROFILE.md`**
(sections §1–§18). No skill, agent, hook or rule hardcodes a URL, hostname, repository name, branch,
table, role, account, ticket key, tool id or path. They *reference* the profile instead.

Reference syntax (use exactly this shape so it can be validated and searched):

| Need | Write |
|---|---|
| A URL / surface | `<main app URL: PROJECT-PROFILE.md §5>`, `<admin URL: PROJECT-PROFILE.md §5>`, `<API base URL: PROJECT-PROFILE.md §5>` |
| A repository or code path | `<backend repo: PROJECT-PROFILE.md §3/§9>`, `<frontend repo: PROJECT-PROFILE.md §3/§9>`, `<routes path: PROJECT-PROFILE.md §9>` |
| A branch | `<branch: PROJECT-PROFILE.md §3>` |
| DB name / host / tool | `<test DB name: PROJECT-PROFILE.md §6>`, `<DB host: PROJECT-PROFILE.md §6>`, `<DB tool: PROJECT-PROFILE.md §6>` |
| Accounts | `<role account: PROJECT-PROFILE.md §7>` — identifiers only; passwords are *never* written anywhere except the git-ignored `.mcp.json` / environment variables |
| Roles | `<roles: PROJECT-PROFILE.md §8>` (illustrative generic set: Admin / Manager / User / Guest) |
| Tables / schema facts | `<key tables: PROJECT-PROFILE.md §10>` |
| Async consumers | `PROJECT-PROFILE.md §11` |
| Evidence folder | `qa-evidence/` (root from `PROJECT-PROFILE.md §12`) |
| Memory folder | `<memory folder: PROJECT-PROFILE.md §12>` (auto-derived by the hooks when blank) |
| Project MCP / typed tools | `PROJECT-PROFILE.md §14` (optional) |
| Issue tracker, project key, ticket pattern, filing rules | `PROJECT-PROFILE.md §15` |
| QA policy knobs (verdict policy, sub-agents, gate) | `PROJECT-PROFILE.md §16` |
| Optional plugins | `PROJECT-PROFILE.md §17` |
| Demo recording defaults | `PROJECT-PROFILE.md §18` |

Generic ticket keys in examples are `APP-123` / `APP-nnn`; generic bug ids are `BUG-YYYYMMDD-HHMMSS`.
Generic domains are `example.com` / `*.example.com`. Generic repos are `app-frontend`, `app-backend`,
`app-admin`, `app-reports`. Generic people are "the owner", "the developer", "the product owner".

## 2. Capability gates

Every skill that needs a capability opens with the gate block (see `docs/capability-matrix.md`). The
block names the capability, tells the user to run `/configure-project`, and the skill does not call the
gated tools when the capability is `off`. Orchestrators never hard-stop; they skip the phase and **say
so in the verdict** ("Phase 3 skipped: DB capability off").

## 3. Tool ids

The template ships with default MCP tool ids (`mcp__mcp_server_mysql__mysql_query`,
`mcp__http-client__*`, `mcp__playwright__*`, `mcp__chrome-devtools__*`, `mcp__filesystem__*`,
`mcp__github__*`, `mcp__claude_ai_Atlassian__*`, `mcp__postman-api-mcp__*`). `/configure-project`
rebinds the DB tool id when the project uses another engine. A skill that mentions a DB tool writes the
default id and, where it matters, adds "(DB tool: PROJECT-PROFILE.md §6)". Never reference a tool that
exists only in one private installation (for example an in-house project MCP server); instead write:
"If `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it;
otherwise use `mcp__http-client__*`."

## 4. Optional plugins and sub-agents

- Plugin skills (`superpowers:*`, `mattpocock-skills:*`) are **optional enhancers**. Every mention is
  conditional: "If the `mattpocock-skills` plugin is installed (PROJECT-PROFILE.md §17), use
  `Skill(mattpocock-skills:grilling)`; otherwise do the equivalent by hand: …" and the by-hand
  equivalent is spelled out so the skill is executable without the plugin.
- Sub-agent use is a **policy knob** (PROJECT-PROFILE.md §16). Skills describe both paths: delegate to
  the agent when allowed, or run the same procedure in-session when the policy says "no sub-agents".

## 5. What is removed, what is kept

Removed on sight: internal domains, hostnames, IPs, tunnel commands, workstation paths
(any path under a user's home directory), usernames, credentials, API keys, collection UIDs, account/tenant/org ids, employee
names, assignee rules, ticket numbers, private memory, production observations, baseline numbers,
owner-decision dates ("ADDED 2026-09-01", "owner decision 2026-10-16"), and product vocabulary that
only makes sense in one domain.

Kept, expressed generically: the method, the ordering of steps, the gates, the tables and their
columns, the failure modes, the "why" behind a rule. A private incident becomes an **illustrative
example** written in generic terms ("a bulk content import added hundreds of rows in a mode production
had never held, so an `else` branch ran for the first time") and is labelled *(illustrative)*.

How the scanner knows: `scripts/validate.py` ships only **shape-based** rules (credentials, keys and
tokens, user-home paths, e-mail addresses and hostnames outside the example domains, ticket keys outside
`APP-nnn` / `BUG-…`, loopback tunnel ports). The names, accounts, hosts and ticket prefixes of the source
setup live in **`scripts/private-patterns.json`**, a git-ignored file kept only on the maintainer's
machine (`{"literals": [...], "patterns": [{"pattern": "...", "why": "..."}]}`). When it is present the
validator merges it into the scan and additionally fails if any of its literals appears anywhere in the
tracked repo text — including in the validator itself — so the scanner can never leak what it protects.

## 6. Shared vocabulary every skill references by section name

`qa-standards` is the one place these are defined; skills cite the section, they do not restate it:
QA Modes · Scope Lock · Impact Analysis & Coverage · Evidence Ledger · Mutation Safety Gate ·
Cross-Layer Consistency · Bug Classification · Test-Case Quality Bar · MCP Server Routing ·
Plugins & escalation · Memory Ritual · Completion Gate · Verdict Integrity · Authoritative Source
Hierarchy · Fresh vs Historical · Execution Register · Evidence provenance · Verdict Contract ·
Judgement Discipline · The six questions · Escape classes & their gates.

Canonical values (Verdict Contract): area result **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET
VERIFIED**; run verdict **GO / NO-GO / PARTIAL** (aliases only in parentheses after the canonical
word); finding verdict **CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE**; confidence line
`Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`.

Evidence folder convention: one folder per run, `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/`,
attachments prefixed with the finding id. Reports and findings live in the chat / tracker, not as
markdown in the evidence folder.

## 7. Frontmatter and file conventions

- `SKILL.md` frontmatter: `name` (letters, digits, hyphens), `description` (third person, starts with
  "Use when…", triggers only, no workflow summary, ≤1024 chars), optional `argument-hint`,
  optional `allowed-tools`.
- Agents (`.claude/agents/*.md`): `name`, `description`, `maxTurns`, `memory: project`, optional
  `effort`, `skills: [qa-standards]`, `tools:`. No `model:` pin — the template inherits the session model.
- Rules (`.claude/rules/*.md`): a `paths:` frontmatter only when the rule is layer-specific; the path
  uses the profile placeholder.
- Hooks read `harness-config.json` through `harness_config.py` / the Node equivalent; they never
  hardcode a path, a repo list or a user.
- Scripts are invoked through their interpreter in prose (`node scripts/x.js`, `python scripts/y.py`).
- Dates: no change-history markers inside skills. Use `CHANGELOG.md` for history.
- Line endings: files are written LF; `.gitattributes` normalizes.

## 8. How to pull a future change from a private source setup

1. Diff the source component against the template component (`git diff --no-index`).
2. Classify each hunk: generic improvement → port; project binding → replace with a profile reference;
   private fact → drop (or turn into an illustrative example with no identifiers).
3. Run `python scripts/validate.py` with your `scripts/private-patterns.json` in place (git-ignored;
   add every product name, person, account, host fragment and ticket prefix of the source) — it fails on
   private-pattern hits, missing profile sections, broken links, bad frontmatter, and catalog drift.
4. Run `python scripts/hook-redteam/runner.py` if a hook changed.
5. Record the change in `CHANGELOG.md` and, if a new component appeared, in `catalog.json` and
   `docs/catalog.md`.
6. Never copy memory files, evidence folders, backups (`*.bak*`, `backups/`), logs or `__pycache__`.
