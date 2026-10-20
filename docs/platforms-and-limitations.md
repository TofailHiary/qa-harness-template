# Supported platforms and known limitations

## Platforms

| | Windows 10/11 | macOS | Linux |
|---|---|---|---|
| Hooks (Python 3 stdlib) | yes | yes | yes |
| `memory-rotation.js`, bundled HTTP MCP (Node 18+) | yes | yes | yes |
| `copy-screenshot-evidence.sh` | needs Git Bash (ships with Git for Windows) | yes | yes |
| PowerShell guard hook | yes (PowerShell 5.1 / 7) | only if the PowerShell tool is used | only if the PowerShell tool is used |
| `.mcp.json.template` Playwright / MySQL entries | wrapped in `cmd /c npx …` | use `npx` directly (see the `_note` in the template) | use `npx` directly |
| Demo creator | yes (winget installs ffmpeg; SAPI offline voices) | yes (`brew install ffmpeg`; `say` offline voices) | yes (`apt install ffmpeg espeak-ng`) |
| `scripts/install.py`, `validate.py`, `hook-redteam/runner.py` | yes | yes | yes |

Tested in this release: Windows 11 (Python 3.14, Node 22, Git Bash, PowerShell 5.1). macOS and Linux
paths are implemented from the same scripts but were not executed here — report issues.

## Known limitations

- **Regex guards are not a sandbox.** The hooks block the mutations a QA agent is likely to attempt and
  are qualified by `scripts/hook-redteam/` (130+ cases, self-tested runner), but a determined command can
  still find a path around a regex. Treat them as a strong default, keep product repos in version
  control, and review diffs.
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
