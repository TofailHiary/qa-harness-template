# QA Harness — a portable, self-configuring, read-only QA harness for AI coding agents

A QA harness you drop into **any** project, for AI coding agents that read skills and instruction files
(Claude Code natively; Codex, OpenCode, Cline, Kilo Code and similar through `AGENTS.md` — see
[Runtime support](#runtime-support)). It brings a complete cross-layer QA toolkit —
**39 skills + 6 sub-agents** covering prompt research, test-case generation, DB validation, API testing,
browser/E2E, visual + accessibility checks, security review, performance, regression, production
anomaly scanning, latent-defect sweeps, bug verification, independent verdict audits, GO/NO-GO reporting,
pair-testing and narrated demo videos — plus a bootstrap that **fits itself to your project** and turns
off the parts you don't need.

Derived from a battle-tested QA setup built for a real production platform. Every project-specific
binding, account, host, ticket key and incident was replaced by a single profile you fill in; the
methods, gates and safeguards were kept. See [CHANGELOG.md](CHANGELOG.md) for what is new in 2.0.

## What this project is, in one picture

```
 you: "/full-qa APP-412"                                   ┌──────────────────────────────┐
   │                                                       │  PROJECT-PROFILE.md (§1–§18)  │
   ▼                                                       │  URLs · DB · repos · roles    │
 CLAUDE.md persona ──reads──► qa-standards (shared rules)  │  tracker · policy · plugins   │
   │                                                       └──────────────┬───────────────┘
   ▼                                                                      │ every skill reads it
 full-qa orchestrator                                                     ▼
   ├─ Step 0  prompt-generator      (researched, self-contained charter)
   ├─ Phase 0 test-cases-generator  (code-derived matrix, input classes, expected sources)
   ├─ Phase 1 env-health · test-data-manager · sync-repos · login
   ├─ Phase 2–7 code-review · db-check · api-test · browser-test · visual · a11y ·
   │            observability · security-review · perf-test · regression-runner
   ├─ Phase 8  bug-verifier → bug-report → Execution Register + Evidence Ledger
   ├─ Phase 8a qa-verdict-auditor  (fresh-context audit: AUDIT_PASSED / AUDIT_FAILED)
   └─ Phase 8b qa-report → GO / NO-GO / PARTIAL + confidence line
                       ▲
   hooks (read-only guards, completion gate, memory rotation) run under all of it
```

Beside the cycle sit the production watchers (`prod-sentinel`, `latent-pattern-sweep`), the computed-output
checker (`ai-output-eval`), the collaboration tools (`test-together` pair-testing, `demo-creator` narrated
videos, `automation-writer`), and the communication skills (`explainer`, `release-note`). The bootstrap
(`configure-project`) fits all of it to your project. Every component is listed in
[docs/catalog.md](docs/catalog.md).

## Runtime support

The QA method, the 39 skills, the rules and the project profile are plain Markdown and runtime-neutral
(the skills use the open `SKILL.md` frontmatter). The *enforcement* layer is runtime-specific. What each
runtime gets today:

| Runtime | Skills, rules, profile, qa-standards | Sub-agents | Read-only hooks + completion gate | MCP servers | Bootstrap (`/configure-project`) |
|---|---|---|---|---|---|
| **Claude Code** | native (`.claude/`) | native | native (`settings.json` hooks) | `.mcp.json` | yes |
| Codex, OpenCode, Cline, Kilo Code, others that read `AGENTS.md` | yes — `AGENTS.md` points at the same files; copy skills to the runtime's skill folder (`scripts/install.py --user` or your runtime's path) | runtime-specific format; the agent files are usable as prompts | **not available** — express the read-only policy with the runtime's permission/approval settings; the completion gate becomes a checklist | same servers, the runtime's own config file; tool names may flatten (`mcp__x__y` → `x_y`) | manual: fill `PROJECT-PROFILE.md` by hand |

The safety guarantees described below (blocked writes, git allow-list, verdict gate) are **only enforced
under Claude Code**. On other runtimes the same rules are stated in `AGENTS.md` and `qa-standards`, but
nothing stops a mutation mechanically — configure the runtime's own permissions accordingly.

## Quickstart — the complete setup (3 steps)
1. **Install** into your project (copies `.claude/`, `.mcp.json.template`, `SETUP.md`, `docs/`, `scripts/`):
   ```bash
   git clone <this repo> qa-harness-template
   python qa-harness-template/scripts/install.py --target /path/to/your/project --full
   ```
   (or copy `.claude/`, `.mcp.json.template` and `SETUP.md` by hand — see [docs/installation.md](docs/installation.md)).
2. **Have Node.js 18+ and Python 3.** You do NOT install the MCP servers yourself — the bootstrap does that
   during setup (they run via `npx` and auto-install).
3. **Open Claude Code** in your project and say:
   > "Read SETUP.md and configure this QA harness for my project."
   On another runtime, open the project, make sure it reads `AGENTS.md`, and fill `PROJECT-PROFILE.md`
   following `PROJECT-PROFILE.example.md`.
4. **Check the machine and the guards:** `python .claude/scripts/doctor.py` must end with `READY`. It
   finds Python / Node / Git Bash problems and drives every guard with a forbidden and an allowed action.

`/configure-project` then **does the rest**: auto-detects your stack, asks only for the NAMES of the
environment variables that hold your secrets (the values stay in your environment) and approval for any new
server, **installs/configures the MCP servers end-to-end**, writes
`.claude/PROJECT-PROFILE.md` and a git-ignored `.mcp.json`, wires the read-only hooks, enables only the
skills your project supports, and live-verifies. Your only manual steps: set the environment variables it
prints, approve the servers at Claude Code's trust prompt, and restart once.

## Quickstart — one skill
```bash
python qa-harness-template/scripts/install.py --target /path/to/your/project --skill browser-test
python qa-harness-template/scripts/install.py --user --skill explainer      # user-level, skills only
python qa-harness-template/scripts/install.py --list                        # everything available
```
A single-skill install brings the skill, the skills and agents it references, the shared
`qa-standards` module and (project-level) the core: persona, profile, hooks, rules. Dependencies are
resolved from the skill text and [catalog.json](catalog.json). Details: [docs/installation.md](docs/installation.md).

## How it works — three layers
- **Generic QA Brain** — `CLAUDE.md`, the skills, agents, hooks, rules, references. Identical for
  everyone; never edited per project.
- **`PROJECT-PROFILE.md`** — the ONE file that holds your project's URLs, DB, repos, code paths,
  tables, roles, accounts, tracker rules, QA policy knobs and plugin availability (§1–§18).
  `CLAUDE.md` imports it automatically. See `PROJECT-PROFILE.example.md` for a worked example.
- **Bootstrap** — `SETUP.md` + the `/configure-project` skill that fills the profile and wires
  everything. Re-run it anytime.

## Capability model
Each skill declares a required capability (DB, API, Browser, GitHub, Prod-DB, Demo, …). The profile's
**Capability Map (§2)** is the switchboard: a skill whose capability is `off` cleanly disables itself and
points you to `/configure-project`. Orchestrators (`/full-qa`, `/qa-validate`, …) skip the phases your
project can't run and say so in the verdict. Full mapping: [docs/capability-matrix.md](docs/capability-matrix.md).
Catalog of every component: [docs/catalog.md](docs/catalog.md).

## Read-only safety
This harness **never modifies your product code**. PreToolUse hooks (`.claude/hooks/`) block Write/Edit,
Bash, PowerShell, filesystem-MCP and GitHub-PR writes to anything except the auto-memory folder, the
harness's own config and (optionally) repos you mark as your own tooling. It documents bugs; it does not
fix them. The hooks are portable — they resolve paths from `CLAUDE_PROJECT_DIR` and a generated
`harness-config.json` — and are qualified by an adversarial suite (`scripts/hook-redteam/`, 200+ cases plus
launcher tests). Every guard runs through `run-hook.sh`, which **fails closed**: no Python 3 or a crashed
guard blocks the call instead of silently allowing it. The files that configure the guards are checked by
content, so a session cannot loosen its own guards; only a human can (`QA_HARNESS_ADMIN=1`). A Stop hook
(advisory by default) flags verdicts that lack evidence, a register or a confidence line, and recomputes the
run from its machine-readable run record (`qa-evidence/<run>/run.json`).

## Secrets
Credentials are **environment variables** by default: `.mcp.json` is rendered by
`.claude/scripts/render_mcp.py` with every secret left as `${ENV_VAR}`, and `Read(.mcp.json)` is denied so a
session cannot print it. Inline values in the git-ignored `.mcp.json` exist only if you ask for them. Never commit real credentials; never write
a password into `PROJECT-PROFILE.md` (name the env var instead).

## What's inside
```
.claude/
  CLAUDE.md                     generic QA persona (imports PROJECT-PROFILE.md)
  PROJECT-PROFILE.md            the one file you fill in (§1–§18)
  PROJECT-PROFILE.example.md    worked example
  settings.json                 permissions + hook wiring
  skills/                       39 skills incl. configure-project (bootstrap) and demo-creator
  agents/                       6 sub-agents incl. qa-verdict-auditor
  hooks/                        portable read-only enforcement + completion gate + memory rotation;
                                run-hook.sh launches every Python hook and fails closed
  scripts/                      doctor.py, render_mcp.py, rebind.py, ci-run-qa.sh / .ps1
  tool-bindings.json            which DB tool ids the skills call (re-applied after every upgrade)
  rules/ references/            always-loaded rules; system-map template
  mcp-servers/http-client/      bundled dependency-free HTTP MCP
.mcp.json.template              MCP servers (secrets as ${ENV})
SETUP.md                        how to configure
catalog.json                    component manifest (installer + validator)
scripts/                        install.py, validate.py, hook-redteam/
docs/                           installation, configuration, integrations, usage, limitations,
                                troubleshooting, upgrading, catalog, capability matrix, maintainers/
```

## Documentation
- [docs/installation.md](docs/installation.md) — one skill, a group, the complete setup; project vs user level
- [docs/configuration.md](docs/configuration.md) — every profile section and config variable, with safe example values
- [docs/integrations.md](docs/integrations.md) — MCP servers, connectors, plugins, and alternatives
- [docs/usage-examples.md](docs/usage-examples.md) — generic walkthroughs incl. the demo creator
- [docs/platforms-and-limitations.md](docs/platforms-and-limitations.md) — supported platforms, known limits
- [docs/troubleshooting.md](docs/troubleshooting.md) · [docs/upgrading.md](docs/upgrading.md) · [docs/ci.md](docs/ci.md) — unattended runs
- [docs/maintainers/before-after-2.1.md](docs/maintainers/before-after-2.1.md) — what the 2.1 backlog changed, measured before and after
- [docs/maintainers/skill-evals.md](docs/maintainers/skill-evals.md) — how to run and score the skill evals
- [docs/maintainers/generalization-conventions.md](docs/maintainers/generalization-conventions.md) — how future source changes are reviewed and generalized
- [docs/maintainers/migration-inventory.md](docs/maintainers/migration-inventory.md) — what was ported, adapted, or excluded and why

## Project status and versioning
- **2.1.0** (2026-10-26): fail-closed hook launcher, guards that cannot be loosened by the session, a
  machine-checked run record, durable tool rebinding, doctor, CI runner, three new skills - see
  [CHANGELOG.md](CHANGELOG.md).
- **2.0.0** (2026-10-20): full refresh. Semantic versioning; `catalog.json`
  carries the version the installer stamps.
- Validated in this release on Windows 11 (Python 3.14, Node 22); macOS/Linux paths are implemented from the
  same scripts but not executed here — see [docs/platforms-and-limitations.md](docs/platforms-and-limitations.md).
- Quality gates for contributors: `python scripts/validate.py` (must print 0 errors) and
  `python scripts/hook-redteam/runner.py` (must pass every case). Both run from the repo root.

## Requirements
An AI coding agent runtime (Claude Code for the full experience; see Runtime support), Node.js 18+,
Python 3. **Under Claude Code the MCP servers are installed/configured for you by `/configure-project`**.
GitHub/Jira are optional connectors. The demo creator additionally
needs Playwright (installed into your project by its `setup.js`), ffmpeg and a TTS engine. Note:
Claude Code shows a one-time trust prompt for project MCP servers, and newly added servers connect after
a restart — these two steps are yours.
