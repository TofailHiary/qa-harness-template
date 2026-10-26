# Supported platforms and known limitations

## Platforms

| | Windows 10/11 | macOS | Linux |
|---|---|---|---|
| Hooks (Python 3 stdlib) | yes | yes | yes |
| `memory-rotation.js`, bundled HTTP MCP (Node 18+) | yes | yes | yes |
| `copy-screenshot-evidence.sh` | needs Git Bash (ships with Git for Windows) | yes | yes |
| PowerShell guard hook | yes (PowerShell 5.1 / 7) | only if the PowerShell tool is used | only if the PowerShell tool is used |
| `.mcp.json` rendering (`render_mcp.py`) | wraps `npx` in `cmd /c` | plain `npx` | plain `npx` |
| Hook launcher `run-hook.sh` (POSIX `sh`) | Git Bash's `sh` (installed with Git for Windows) | yes | yes |
| Demo creator | yes (winget installs ffmpeg; SAPI offline voices) | yes (`brew install ffmpeg`; `say` offline voices) | yes (`apt install ffmpeg espeak-ng`) |
| `scripts/install.py`, `validate.py`, `hook-redteam/runner.py` | yes | yes | yes |

Tested in this release: Windows 11 (Python 3.14, Node 22, Git Bash, PowerShell 5.1). macOS and Linux
paths are implemented from the same scripts but were not executed here — report issues.

## Agent runtimes

| Runtime | Status |
|---|---|
| Claude Code | fully supported and the only runtime validated in this release: skills, agents, hooks, completion gate, MCP template, bootstrap |
| Codex, OpenCode, Cline, Kilo Code (`install.py --runtime`, see `AGENTS.md` -> Per-runtime wiring); other runtimes that read `AGENTS.md` | skills, rules, profile and qa-standards are usable as-is (copy the skills to the runtime's skill folder; `AGENTS.md` carries the startup instructions and the tool-name mapping). No hooks, so the read-only policy and the completion gate are not enforced mechanically; sub-agent and MCP configuration follow the runtime's own formats. Not executed in this release. |

## Known limitations

- **Regex guards are not a sandbox.** The hooks block the mutations a QA agent is likely to attempt and
  are qualified by `scripts/hook-redteam/` (200+ cases, launcher tests, self-tested runner), but a determined command can
  still find a path around a regex. Treat them as a strong default, keep product repos in version
  control, and review diffs.
- **The launcher costs time on Windows.** Measured on Windows 11 (Git Bash): a guard called directly took
  about 100 ms per tool call, through `run-hook.sh` about 210 ms - roughly 40 ms is starting `sh` under Git for
  Windows, the rest is process creation. On macOS and Linux the same overhead is a few milliseconds. It is
  the price of failing closed instead of silently allowing.
- **A guard that cannot run blocks everything.** That is deliberate (fail closed). If every tool call is
  blocked with "no Python 3 interpreter found" or "exited with code", run `python .claude/scripts/doctor.py`.
- **Hook maintenance needs a human.** The guard surface (`.claude/hooks/**`, `.claude/settings*.json`) cannot be
  written from a session's shell, and the guard config cannot be loosened through Write/Edit, unless a human
  started Claude Code with `QA_HARNESS_ADMIN=1`.
- **Hooks need `CLAUDE_PROJECT_DIR`.** Claude Code sets it; running a hook by hand needs it exported, or
  the hook falls back to the current directory.
- **Two tools, two guards.** The Bash guard ignores heredoc bodies fed to an interpreter; the PowerShell
  guard ignores here-string bodies. A document that *mentions* a mutating verb is not blocked; a program
  fed to an interpreter is still scanned for file writes.
- **The completion gate is heuristic.** It pattern-matches verdict turns; explanatory messages that quote
  verdict words should carry the word `example` on those lines. It ships advisory; enforce only after you
  have seen it stay quiet on ordinary turns.
- **Jira connector cannot attach files.** Skills list the files to upload manually in chat.
- **GitHub write tools are denied** except PR create/update for owned repos.
- **Demo creator:** online neural voices need internet at record time (offline fallbacks are robotic);
  the recording is real time (a 40-step demo takes ~7 minutes); `SendUserFile` attachments are limited to
  30 MiB (the skill makes a compact copy); the Playwright version is pinned by `setup.js` to the one the
  recorder was developed against.
- **Capability detection is heuristic.** `/configure-project` infers the stack from common files; confirm
  its summary, especially for monorepos and multiple databases.
- **DB tool rebinding is textual.** For engines other than MySQL, `/configure-project` rewrites the tool
  id in skills and agents; query syntax inside the skills (`DESCRIBE`, `SHOW INDEX`, `DATE_FORMAT`) still
  needs the engine's equivalent, which the skills call out.
- **Memory rotation** archives index entries older than 30 days only when `MEMORY.md` exceeds 24 KB and
  only when the entry title or hook carries a `YYYY-MM-DD` date.
- **Not ported:** installers that mirror the skills into other agent runtimes (Codex, Kilo) existed in the
  source setup but were bound to one workstation; they are a documented future extension, not a shipped
  component (see `docs/maintainers/migration-inventory.md`).
- **Skill testing:** the skills were validated statically (frontmatter, references, privacy, catalog) and
  the scripts, hooks and installer were executed; the skills' *behaviour* under pressure was not
  re-benchmarked in this release (see the `writing-skills` discipline for how to do that per skill).
