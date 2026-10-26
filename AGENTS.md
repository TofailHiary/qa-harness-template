# AGENTS.md — instructions for AI coding agents other than Claude Code

This repository (or the project it was installed into) carries a read-only QA harness. Claude Code loads
`.claude/CLAUDE.md`, the skills, the rules and the hooks automatically. Runtimes that read `AGENTS.md`
(Codex, OpenCode, Cline, Kilo Code and similar) do not, so this file tells them where everything is and
what the rules are. Nothing here is project-specific; project facts live in `.claude/PROJECT-PROFILE.md`.

## Startup

1. Read `.claude/CLAUDE.md` (the QA persona and critical rules) and `.claude/PROJECT-PROFILE.md`
   (every project binding, §1–§18). If the profile is blank, stop and ask the user to fill it following
   `.claude/PROJECT-PROFILE.example.md` — this runtime has no `/configure-project` bootstrap.
2. Read `.claude/skills/qa-standards/SKILL.md` once per session. It is the shared standard every skill
   follows (Scope Lock, Evidence Ledger, Mutation Safety Gate, Completion Gate, Verdict Contract,
   Escape classes, Memory Ritual).
3. The always-loaded rules are `.claude/rules/testing.md`, `db-gotchas.md`, `anomaly-disposition.md`,
   `pushback-protocol.md`; `frontend.md`, `backend.md`, `admin.md` apply when working in that layer.
4. Skills live in `.claude/skills/<name>/SKILL.md` (open Agent Skills frontmatter) - ONE copy, because every
   skill refers to paths inside `.claude/`. `python scripts/install.py --target <project> --full --runtime
   <codex|opencode|cline|kilo>` wires your runtime to it (table below). The catalog is `catalog.json` /
   `docs/catalog.md`; capability rules are in `docs/capability-matrix.md` — a skill whose capability is `off`
   in the profile §2 must say so and stop.
5. Sub-agent definitions in `.claude/agents/*.md` are written for Claude Code's dispatcher; on this runtime
   use them as role prompts for your own sub-agent mechanism, or run their procedure in-session
   (`PROJECT-PROFILE.md` §16 "sub-agents: disabled" describes exactly that mode).

## Per-runtime wiring (`install.py --runtime`)

Checked against each runtime's documentation on 2026-10-26 (Cline's `.agents/skills` scan is in its source,
not its docs). All four read this `AGENTS.md` automatically.

| Runtime | How it finds the skills | MCP servers | What it can enforce | What `--runtime` writes |
|---|---|---|---|---|
| Codex CLI | `.agents/skills` | `.codex/config.toml` (project must be trusted in `~/.codex/config.toml`) | `sandbox_mode = "read-only"`, `approval_policy = "on-request"`, `.codex/rules` command rules (experimental) | `.codex/config.toml`, `.codex/rules/qa-readonly.rules`, pointer skills in `.agents/skills` |
| OpenCode | `.claude/skills` directly | `opencode.json` | `permission`: edit asks, bash asks, read-only git allowed, git/npm writes denied | `opencode.json` |
| Cline | `.claude/skills` directly | global settings file only | nothing per project - switch auto-approve off yourself | `.agents/cline-mcp-settings.snippet.json` to merge by hand |
| Kilo Code | `.agents/skills` (`.claude/skills` only with its Claude compatibility on) | `kilo.jsonc` | `permission` as for OpenCode; most tools default to allow, so the denies matter | `kilo.jsonc`, pointer skills in `.agents/skills` |

Pointer skills carry the real skill's name and description and send you to `.claude/skills/<name>/SKILL.md`.
An existing runtime config is never overwritten: the new one is written next to it as `<name>.new`.
Validated in 2.1: the four adapters generate parseable files, and Codex CLI 0.144.1 parsed the generated
`.codex/config.toml` (`codex mcp list`). No runtime other than Claude Code ran a QA session.

## Read-only policy (enforced by hooks under Claude Code; by YOUR runtime's permissions here)

- Never modify product source code; document bugs, never fix them.
- No mutating git (`commit`, `push`, `checkout`, `add`, `reset`, `stash`, `rebase`, `merge`, …); read-only
  verbs plus `fetch`/`pull` are fine. No `npm publish` / `version` / `ci`.
- Writes are allowed only to: the auto-memory folder (profile §12), the harness config files, the evidence
  folder `qa-evidence/`, and repos listed as owned in profile §12.
- Production databases are read-only; every write to a test database follows the Mutation Safety Gate.
- Configure this runtime's approval/permission settings to match; the hooks in `.claude/hooks/` and the
  policy file `.claude/hooks/harness-config.json` document the intended rules, and
  `scripts/hook-redteam/cases.json` lists the commands that must be blocked or allowed.

## Tool-name mapping

Skills name tools the Claude Code way. Translate:

| In the skills | Meaning | Typical equivalent elsewhere |
|---|---|---|
| `Read`, `Grep`, `Glob` | read a file, search content, find files | your file tools / `rg`, `rg --files` |
| `Write`, `Edit` | write memory files (only) | your edit tool, scoped by your permissions |
| `Bash`, `PowerShell` | shell | your shell tool |
| `Agent` / `subagent_type: "x"` | dispatch a sub-agent defined in `.claude/agents` | your sub-agent mechanism, or in-session |
| `Skill(x)` | invoke skill x | your skill invocation (`$x`, `/x`, or read `.claude/skills/x/SKILL.md` and follow it) |
| `mcp__<server>__<tool>` | an MCP server tool | the same MCP server in your runtime's MCP config; some runtimes flatten the name to `<server>_<tool>` |
| `mcp__claude_ai_Atlassian__*`, `mcp__github__*` | Claude connectors for Jira / GitHub | your runtime's Jira / GitHub integration, or `gh` / REST |
| `TodoWrite` | task list | your task list, or a markdown checklist |
| `SendUserFile` | hand a file to the user | print the path |

MCP servers: `.mcp.json.template` lists them (filesystem, bundled http-client, playwright, chrome-devtools,
MySQL, Postman); re-create the entries in this runtime's MCP configuration and keep secrets in environment
variables.

## What this runtime does NOT get

- The completion gate hook (`.claude/hooks/completion-gate.py`): apply its checks by hand before any
  verdict (qa-standards → Completion Gate and Verdict Contract).
- Memory rotation and the screenshot-evidence hook: save evidence with explicit paths under
  `qa-evidence/<run-folder>/`, and keep `MEMORY.md` entries dated.
- `/configure-project`: fill the profile manually.
- The fail-closed hook launcher and the guard content checks. What still works on any runtime: the plain
  scripts - `python .claude/scripts/doctor.py` (environment part), `python .claude/scripts/render_mcp.py`
  (to see the MCP servers and versions), `python .claude/scripts/rebind.py`, and
  `python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>` before any verdict.
