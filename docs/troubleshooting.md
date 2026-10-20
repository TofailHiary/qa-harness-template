# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
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
