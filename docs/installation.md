# Installation

Four supported shapes. All of them copy files from this template into the place Claude Code reads them;
nothing is downloaded from anywhere else, and nothing in the template points at the machine it was
written on.

Prerequisites: Claude Code, Python 3 (for the installer, the hooks and the validator), Node.js 18+ (for
the bundled HTTP MCP server, the memory-rotation hook and the `npx` MCP servers). Git is optional.

## 1. The complete setup (project level)

```bash
git clone <this repo> qa-harness-template
python qa-harness-template/scripts/install.py --target /path/to/your/project --full
```

Copies `.claude/` (persona, profile, settings, skills, agents, hooks, rules, references, bundled MCP),
`.mcp.json.template`, `SETUP.md`, `catalog.json`, `scripts/`, `docs/` and `README.md`. Then open Claude
Code in the project and say *"Read SETUP.md and configure this QA harness for my project."*

Manual alternative: copy `.claude/`, `.mcp.json.template` and `SETUP.md` into the project root.

## 2. One standalone skill (project level)

```bash
python qa-harness-template/scripts/install.py --target /path/to/your/project --skill browser-test
```

The installer resolves what the skill needs and copies all of it:

| It copies | Why |
|---|---|
| `.claude/skills/browser-test/` | the skill itself (every file in its folder: references, scripts, templates) |
| `.claude/skills/qa-standards/` | the shared standard every skill reads |
| every `Skill(x)` the skill references and their dependencies, transitively (the shared `qa-standards` text mentions most skills as "slot in when relevant"; those mentions are not followed) | so no `Skill(...)` call points at a missing folder |
| every agent the skill dispatches (`Agent(x)` / `subagent_type: "x"`) | so parallel lanes and the verdict audit work |
| the **core**: `CLAUDE.md`, `PROJECT-PROFILE.md` (+ example), `settings.json`, hooks, rules, references, `.mcp.json.template`, `SETUP.md`, `docs/capability-matrix.md` | the read-only hooks are what make a QA session safe; the profile is where the skill reads its bindings |

Use `--dry-run` to see the plan first, `--with-scripts` to also copy `scripts/`, `docs/` and the catalog.

Declared dependencies live in `catalog.json` (`requires`, `agents`); references found in the skill text
are added automatically, so the catalog cannot silently drift from the skills. `scripts/validate.py`
fails the build when a reference does not resolve.

## 3. A related group of components

```bash
python qa-harness-template/scripts/install.py --target /path/to/your/project --group layers
python qa-harness-template/scripts/install.py --list     # groups: bootstrap, shared, orchestrators, planning, layers, verification, production, collaboration
```

Groups are defined in `catalog.json`; dependencies are resolved the same way as for a single skill.

## 4. A skill together with its shared resources (user level)

```bash
python qa-harness-template/scripts/install.py --user --skill explainer
```

Copies the skill, `qa-standards` and the skills it references into `~/.claude/skills/` so they are
available in every project. **User-level installs carry no hooks, rules or agents** — those are project
scoped. A skill installed this way still reads `PROJECT-PROFILE.md` from the project it runs in; if the
project has none, the skill's capability gate tells you to run `/configure-project` (which needs the
project-level core).

## 5. Another agent runtime (Codex, OpenCode, Cline, Kilo Code)

```bash
python scripts/install.py --target /path/to/project --full --runtime codex     # or opencode / cline / kilo
```
The harness is installed in its normal layout, then the adapter adds what that runtime needs: its MCP
config generated from `.mcp.json.template` and your profile, its strongest read-only policy, and pointer
skills where the runtime does not read `.claude/skills`. It prints what that runtime enforces and what stays
advisory (the Claude Code hooks never run there). Details per runtime: `AGENTS.md` -> Per-runtime wiring.

## Preservation during install and upgrade

The installer never overwrites `.claude/PROJECT-PROFILE.md`, `.claude/settings.json`,
`.claude/hooks/harness-config.json`, `.mcp.json`, `.gitignore` or `.gitattributes` when they already
exist; it writes the template version next to them as `<name>.new` for you to merge. Everything else
(skills, agents, hooks, rules, references, docs) is replaced by the template version. `--force`
overwrites the preserved files too. See [upgrading.md](upgrading.md).

## Hidden dependencies — there are none

- No path in the template points at the author's machine; hooks derive everything from
  `CLAUDE_PROJECT_DIR` and `harness-config.json`.
- No globally installed package is assumed: MCP servers run through `npx -y`, the bundled HTTP server
  uses Node built-ins, the hooks use the Python standard library, the demo creator installs Playwright
  into the project with its own `setup.js`.
- Optional services (Postman, Jira, GitHub, Prod-DB, SSH, a project MCP server, plugins) are off until
  you turn them on, and every skill says what it skips when they are off.

## Verifying an install

```bash
python .claude/scripts/doctor.py              # first: machine, hook wiring, a live probe of every guard -> READY
python scripts/validate.py --installed        # inside the project: hooks compile, settings wired, .mcp.json generated
python scripts/hook-redteam/runner.py --hooks /path/to/your/project/.claude/hooks   # the guards behave
```
