# Integrations

> **Last checked 2026-10-26.** MCP server versions are pinned in `.mcp.json.template`; each server's
> `_tested` field says whether that version was exercised with this template. Package names, flags and
> connector behaviour change between releases: re-check them when you bump a pin (`docs/upgrading.md`).

Every integration is **optional** and switched by `PROJECT-PROFILE.md` §2. Nothing here requires the
original author's accounts or infrastructure. This page says what each one provides, how it is set up,
and what to use instead when it is unavailable.

## MCP servers (`.mcp.json`, generated from `.mcp.json.template` by `/configure-project`)

| Server | Capability | Setup | Alternative when off |
|---|---|---|---|
| `filesystem` (`@modelcontextprotocol/server-filesystem`) | always | `npx -y`; allowed dirs = evidence folder + `.claude` | Bash heredocs into `qa-evidence/` |
| `http-client` (bundled) | API | `node .claude/mcp-servers/http-client/server.js`, no install | `curl` in Bash (read-only GETs are allowed; writes follow the Mutation Safety Gate) |
| `playwright` (`@playwright/mcp`) | Browser | `npx -y`; browsers via `npx playwright install chromium` | API-level checks only; UI phases are reported as coverage gaps |
| `chrome-devtools` (`chrome-devtools-mcp`) | Browser | `npx -y` | Playwright's `browser_console_messages` / `browser_network_requests` |
| `mcp_server_mysql` (`@benborla29/mcp-server-mysql`) | DB (MySQL/MariaDB) | `npx -y`; secrets `QA_DB_*`; write flags ship `false` | — (DB phases skipped) |
| another engine (Postgres, Mongo, SQLite, …) | DB | `/configure-project` proposes the matching MCP package, you approve, it rebinds the DB tool id in every skill/agent | — |
| `mcp_server_mysql_prod` | Prod-DB | disabled by default; read-only; document the access path (tunnel/replica) in §6 | prod repros are reported as NOT YET VERIFIED |
| `postman-api-mcp` | Postman | `POSTMAN_API_KEY`; collection ids in §13 | derive contracts from the backend routes (§9) |
| a project MCP server with typed tools | §14 | add its block to `.mcp.json`; list the tools in §14 | `mcp__http-client__*` with manual auth |

## Claude Code connectors (configured outside `.mcp.json`)

| Connector | Capability | What the harness uses | Alternative |
|---|---|---|---|
| GitHub (`mcp__github__*`) | GitHub | PR files/diffs, commits, code search; PR create/update only for owned repos (hook-gated) | local repos (`LocalRepos`) with read-only `git` verbs |
| Jira / Confluence (`mcp__claude_ai_Atlassian__*`) | Jira | acceptance criteria, live ticket status, transitions, filing per §15; the connector cannot upload attachments — skills list "files to upload manually" | paste the ticket text; GitHub Issues; no tracker (findings stay in chat) |
| SSH manager | SSH | tunnels and server checks; deploy/upload/sudo tools are denied in `settings.json` | document the tunnel command in §6 and run it yourself |

Authorize connectors in Claude Code (`/mcp`) or your claude.ai connector settings; the harness never
stores their credentials.

## Plugins (`PROJECT-PROFILE.md` §17)

| Plugin | Marketplace | Used for | Without it |
|---|---|---|---|
| `superpowers` | `claude-plugins-official` | systematic debugging, verification-before-completion, brainstorming/writing skills, parallel dispatch | the by-hand steps written into each skill |
| `mattpocock-skills` | `claude-plugins-official` | `grilling` (ambiguous AC, numbered rounds), `diagnosing-bugs` phases 1–4 (repro harness before hypotheses), `writing-for-agents` (editing skills) | the by-hand equivalents written into each skill |

Install with `/plugin` inside Claude Code, then set §17. Plugin skills that write code or repository
files (`tdd`, `implement`, the fix phases of `diagnosing-bugs`, patching code reviews) are never used in a
read-only QA session; the hooks would block them anyway.

## Demo creator dependencies (`Demo` capability)

`node .claude/skills/demo-creator/scripts/setup.js` installs Playwright into the project (creating a
`package.json` if none exists), the matching Chromium build, `edge-tts` (Python; free Microsoft neural
voices, internet at record time) and, on Windows, ffmpeg via winget. Offline narration fallbacks:
Windows SAPI, macOS `say`, Linux `espeak-ng`. `--check` only reports. See
[usage-examples.md](usage-examples.md#demo-creator) for a run against the bundled offline sample app.

## Environment flags you may want (`settings.json → env`)

| Flag | Effect | Default |
|---|---|---|
| `QA_GATE_ENFORCE` | `1` makes the completion gate block verdict turns that fail its checks | `0` (advisory) |
| `CLAUDE_CODE_USE_POWERSHELL_TOOL` | `1` exposes the PowerShell tool on Windows (the PowerShell guard hook covers it) | unset |

## Cross-runtime notes

The template targets Claude Code. The source setup it was derived from also carried installers that
mirror the skills into other agent runtimes; those were not ported because they hard-wired one
workstation's paths and repository list. The skills are plain `SKILL.md` folders and the hooks are plain
Python, so a parity installer for another runtime can be built on top of `catalog.json` and
`scripts/install.py` — see [platforms-and-limitations.md](platforms-and-limitations.md).
