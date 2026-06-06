# QA Harness — a portable, self-configuring QA agent for Claude Code

A read-only QA harness you drop into **any** project. It brings a full cross-layer QA toolkit —
**29 skills + 5 sub-agents** covering test-case generation, DB validation, API testing, browser/E2E,
visual + accessibility checks, security review, performance, regression, bug verification, and GO/NO-GO
reporting — and a bootstrap that **fits itself to your project** and turns off the parts you don't need.

Derived from a battle-tested QA harness built for a real production platform; all project-specifics and
secrets have been removed and replaced by a single profile you fill in.

## Quickstart (3 steps)
1. **Copy** `.claude/`, `.mcp.json.template`, and `SETUP.md` into your project's root.
2. **Install just Node.js 18+ and Python 3.** You do NOT install the MCP servers yourself — Claude does
   that during setup (they run via `npx` and auto-install; Claude also runs `npx playwright install` for
   browsers and adds any server your stack needs).
3. **Open Claude Code** in your project and say:
   > "Read SETUP.md and configure this QA harness for my project."

`/configure-project` then **does the rest for you**: auto-detects your stack, asks only for secret values
+ approval for any new server, **installs/configures the MCP servers end-to-end**, writes
`.claude/PROJECT-PROFILE.md` and a git-ignored `.mcp.json` (with your secrets in it), wires the read-only
hooks, rebinds/enables only the skills your project supports, and live-verifies. Your only manual steps:
paste secrets when asked, approve the servers at Claude Code's trust prompt, and restart once.

## How it works — three layers
- **Generic QA Brain** — `CLAUDE.md`, the skills, agents, hooks, rules, references. Identical for
  everyone; never edited per project.
- **`PROJECT-PROFILE.md`** — the ONE file that holds your project's URLs, DB, repos, code paths,
  tables, roles, and accounts. `CLAUDE.md` imports it automatically. See `PROJECT-PROFILE.example.md`
  for a worked example.
- **Bootstrap** — `SETUP.md` + the `/configure-project` skill that fills the profile and wires
  everything. Re-run it anytime.

## Capability model
Each skill declares a required capability (DB, API, Browser, GitHub, …). The profile's **Capability
Map (§2)** is the switchboard: a skill whose capability is `off` cleanly disables itself and points you
to `/configure-project`. Orchestrators (`/full-qa`, `/qa-validate`, …) skip the phases your project
can't run. Full mapping: `docs/capability-matrix.md`. So the same harness scales from "just a database"
to "DB + API + browser + admin + CI".

## Read-only safety
This harness **never modifies your product code**. PreToolUse hooks (`.claude/hooks/`) block Write/Edit,
Bash, PowerShell, and filesystem-MCP writes to anything except the auto-memory folder and the harness's
own config. It documents bugs; it does not fix them. The hooks are portable — they resolve paths from
`CLAUDE_PROJECT_DIR` and a generated `harness-config.json`, so they work on any machine with no edits.

## Secrets
Credentials are supplied via **environment variables**, never committed. `.mcp.json.template` ships with
every secret as `${ENV_VAR}`. Your filled `.mcp.json` is git-ignored. Never commit real credentials.

## What's inside
```
.claude/
  CLAUDE.md                     generic QA persona (imports PROJECT-PROFILE.md)
  PROJECT-PROFILE.md            the one file you fill in
  PROJECT-PROFILE.example.md    worked example
  settings.json                 permissions + hook wiring
  skills/                       29 QA skills + configure-project (the bootstrap)
  agents/                       5 QA sub-agents
  hooks/                        portable read-only enforcement
  rules/ references/            generic QA guidance
  mcp-servers/http-client/      bundled dependency-free HTTP MCP
.mcp.json.template              MCP servers (secrets as ${ENV})
SETUP.md                        how to configure
docs/capability-matrix.md       which skill needs which capability
```

## Requirements
Claude Code, Node.js 18+, Python 3. **The MCP servers are installed/configured for you by
`/configure-project`** — you don't set them up by hand. GitHub/Jira are optional Claude Code connectors
(enable them if you want those capabilities). Note: Claude Code shows a one-time trust prompt to approve
project MCP servers, and newly added servers connect after a restart — these two steps are yours.
