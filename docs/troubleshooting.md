# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every tool call is blocked: `no Python 3 interpreter found` | `run-hook.sh` found no working `python3` / `python` / `py -3` (fail closed) | install Python 3, or set `QA_HOOK_PYTHONS` to the names that work; `python .claude/scripts/doctor.py` shows which ones are broken |
| Every call is blocked: `hook '<x>.py' exited with code N` | a guard crashed (bad edit, missing `harness_config.py`) and a crashed guard must not allow | `doctor.py`, then `python scripts/hook-redteam/runner.py --hooks .claude/hooks`; restore the hook from the template |
| `doctor.py`: python hooks not behind run-hook.sh | an upgraded project kept its 2.0 `settings.json` | merge `settings.json.new` (`docs/upgrading.md` -> 2.0 to 2.1) |
| `writing the guard surface (.claude/hooks, .claude/settings*.json) is blocked` | shells may not write hooks or settings | edit `settings.json` / `harness-config.json` with the Write or Edit tool (content-checked); for hook maintenance a human edits the file or starts Claude Code with `QA_HARNESS_ADMIN=1` |
| The guard-surface block fires on an unrelated `*.py` path while the working directory is `.claude` | a 2.1.0 guard matched the bare file name of an absolute path (red-team cases `p-gs-07`, `b-gs-11`) | work from the project root, or update the two shell guards to a build that passes those cases |
| `this change to ... LOOSENS the guards` | the Write/Edit content check: a session tried to drop a hook, add an owned repo, widen the allow-globs ... | by design - make the change by hand, or restart Claude Code with `QA_HARNESS_ADMIN=1` for that session |
| `bash` started from PowerShell exits 127 | `C:\Windows\System32\bash.exe` is the WSL launcher and cannot see Windows paths | use Git Bash (`C:\Program Files\Git\usr\bin\sh.exe`); `doctor.py` and the red-team runner skip the WSL stub |
| `rebind.py --check`: STALE references | skills copied after a rebind without re-applying it | `python .claude/scripts/rebind.py --apply` (the installer does this automatically) |
| `verdict_check.py`: INCONSISTENT | the run record contradicts itself (missing evidence file, FAIL without a source, wrong `N of M`, stated verdict not the recomputed one) | fix the record or the verdict - never report until it exits 0 |
| `load.js`: `is a PROD host` | the URL's host is in the Prod column of `PROJECT-PROFILE.md` §5 | by design - load is never generated against production |
| Every skill says "run `/configure-project`" | `PROJECT-PROFILE.md` §2 is still `off` everywhere | run the bootstrap; or set the capability `on` by hand and re-run it to generate `.mcp.json` |
| `Write/Edit … is blocked` while editing the harness itself | the Write/Edit guard only allows the memory folder, the four config files and owned repos | use a Bash heredoc / PowerShell here-string for harness maintenance (sanctioned), or add the path to `owned_repos` |
| `git <verb> is not on the read-only allow-list` | the Bash guard is an allow-list; fetch/pull/status/log/diff/show/branch -a… are allowed | that is the policy; for your own tooling repo add it to `harness-config.json → owned_repos` |
| A read-only command is blocked in a repo folder (`docker ps`, `tar -tf`) | a write verb regex matched, or cwd is inside a protected repo and the command contains `>` | run it from the project root; file a case in `scripts/hook-redteam/cases.json` if it is a false positive |
| PowerShell command blocked because a file's text mentions `git commit` | the here-string body was not recognised (closing `'@` must be at column 0) | put `'@` at column 0 on its own line |
| Screenshots land in the repo root | a bare `filename` was passed to `browser_take_screenshot` | pass `filename: qa-evidence/<run-folder>/<name>.png`; the PostToolUse hook only sweeps as a backstop |
| `copy-screenshot-evidence.sh` does nothing on Windows | no Git Bash on PATH | install Git for Windows (provides `bash`) |
| MCP server shows connected but queries fail | the stdio process started; the driver connects lazily | run `/env-health`; check host/port/credentials in `.mcp.json`; bring up the tunnel for prod |
| New MCP server never appears | not approved at the trust prompt, or no restart | approve, restart Claude Code, re-run `/configure-project` |
| Completion gate blocks an explanatory message | it quoted verdict words | add `example` on those lines, or set `QA_GATE_ENFORCE=0` (advisory) |
| Memory ritual fails: cannot write | memory folder not derivable, or `memory_root` wrong | set `memory_root` in `harness-config.json` explicitly |
| `MEMORY.md` never rotates | index entries have no date in the link title | write `- [Title YYYY-MM-DD](<file>.md) — hook` |
| Demo: `require('playwright')` not found | Playwright not installed in the project root | `node .claude/skills/demo-creator/scripts/setup.js` |
| Demo: `edge-tts failed, using sapi/say/espeak` | no internet, or the voice name is wrong | check `python -m edge_tts --list-voices`; offline fallback is automatic |
| Demo: `STEP FAIL` / `SLOW/CAUGHT` in `out/run.log` | a selector resolved to a vanished or doubled element | fix the locator (role + exact name, `.first()` for duplicated text), re-run with `--fast` |
| Demo: `ffmpeg` not found after install on Windows | PATH not refreshed | open a new terminal, run `setup.js --check` |
| `validate.py` reports CRLF | a file was saved with Windows line endings | `.gitattributes` normalizes on commit; re-save as LF |
| `validate.py` reports "private/source-coupled content" | a hostname, user path, ticket key or token slipped in | replace with a `PROJECT-PROFILE.md` placeholder or a synthetic example |
| Installer refuses `--user --full` | user-level installs are skills only | use `--skill <name>`; the core (hooks/rules) is project scoped |

Diagnostics:
```bash
python scripts/validate.py                      # template consistency + privacy
python scripts/validate.py --installed          # inside a project
python scripts/hook-redteam/runner.py           # guards behave (self-tests the runner first)
python scripts/hook-redteam/runner.py --hooks <project>/.claude/hooks
node .claude/skills/demo-creator/scripts/setup.js --check
```
