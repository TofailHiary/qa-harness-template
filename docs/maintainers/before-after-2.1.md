# Before and after 2.1 — measured

Written for maintainers deciding whether 2.1 is ready to commit. Every number below was measured on
2026-10-26 on Windows 11 (Python 3.14, Node 22, Git Bash) by running the **same 2.1 instruments** against two
trees: **2.0** is the committed tree at `cb1eba6`, rebuilt file by file from git; **2.1** is the working tree
after implementing `enhancement-backlog-2026-10-26.md`.

## Headline numbers

| What | 2.0 | 2.1 | How it was measured |
|---|---|---|---|
| Validator, 2.1 rules | 65 errors, 19 warnings | 0 errors, 9 warnings (all "skill > 16 KB") | `scripts/validate.py` from 2.1 run against each tree |
| Red-team guard cases (209) | 159 pass, 50 fail | 204 pass, 5 fail; **209 pass** with the staged guard update | `scripts/hook-redteam/runner.py --hooks <tree>/.claude/hooks` |
| Hook launcher tests (8) | no launcher | 8 of 8 | same runner, through Git Bash `sh` |
| No usable Python on the machine | guard exits 127: **non-blocking**, nothing is guarded | launcher exits 2: **blocked** with a reason | forbidden `git push` sent to each launch form |
| DB tool rebinding after an upgrade | 30 files rebound, then 30 reverted to MySQL | 33 files rebound, 0 reverted | install, rebind, reinstall |
| Verdict that contradicts its run record | not detected (one unrelated gate warning) | flagged: "run.json contradicts itself (10 issues)" | completion gate fed a GO over the tampered fixture |
| Tampered run fixture (8 planted defects) | no checker | 10 contradictions reported, exit 1 | `verdict_check.py` |
| Largest skill | 44,378 bytes | 24,142 bytes | file sizes |
| Skills over 24 KB | 4 | 0 | file sizes |
| Descriptions over 500 characters | 8 | 0 | frontmatter |
| Skills that stop and ask when given no arguments | 25 | 35 (all except the 4 that need no input: configure-project, env-health, sync-repos, qa-standards) | validator rule |
| Complete memory blocks (skills + agents that must keep memory) | 11 of 37 | 40 of 40 | validator parser |
| Skills with evals | 1 | 6 | `evals/evals.json` |
| Skills | 36 | 39 | catalog |
| Unpinned `npx` MCP servers | 6 | 0 | `scripts/check_deps.py` |
| Windows-only `cmd /c` wrappers in the template | 3 | 0 (added at render time on Windows) | template |
| Other runtimes wired by the installer | 0 | 4 (Codex config parsed by Codex CLI 0.144.1) | `install.py --runtime` |
| Time a guard adds to each tool call (Windows) | about 100 ms | about 210 ms | 10 calls each, Git Bash |

The last row is the cost of failing closed: starting `sh` under Git for Windows takes about 40 ms and the
rest is process creation. On macOS and Linux the launcher adds a few milliseconds (not measured here).

### What the 65 validator errors on 2.0 were

| Count | Rule |
|---|---|
| 27 | memory block missing, or without the placeholder / `ls -la` verify line / SUPERSEDED rule |
| 7 | skill takes arguments but never stops when none are given |
| 7 | Python hook launched without the fail-closed launcher |
| 4 | skill over 24 KB |
| 4 | MCP template: `@latest` (1) and Windows-only `cmd /c` wrappers (3) |
| 3 | confidence line drifted ("in-scope files", "in-scope checks", "cases" instead of "in-scope areas") |
| 3 | no run-record checker or its reference |
| 3 | the three helper scripts do not exist |
| 2 | stale `Task` tool name |
| 1 | `catalog.json` said 2.0.0 while the newest CHANGELOG heading was 2.0.1 — a real drift in the committed tree |
| 1 | `Read(.mcp.json)` not denied |
| 1 | launcher self-test failed (no launcher) |
| 1 | `docs/catalog.md` lacks the new column |
| 1 | missing folder the 2.1 tree adds |

### The 50 guard failures on 2.0, grouped

| Group | Cases | Example |
|---|---|---|
| Bash escapes | 12 | `echo x >| <repo>/f`, `find <repo> -delete`, `base64 -d \| sh`, `eval "$(...)"`, `git.exe push`, a Python heredoc after `&&` |
| PowerShell escapes | 7 | `Start-Process git -ArgumentList push`, `-EncodedCommand`, `Invoke-Expression ("gi"+"t push")` |
| False positives (blocked a harmless read) | 4 | `grep -rn "git commit" docs`, `Select-String -Pattern 'git commit'` |
| Session loosens its own guard config | 11 | Write adds an owned repo, drops a guard hook, sets `disableAllHooks`, removes a deny rule |
| Shell writes to the guard surface | 16 | `cp x.py .claude/hooks/block-bash-writes.py`, `Set-Content .claude/settings.json` |

### The 5 failures left in the 2.1 working tree

**One escape, `b-esc-15`, older than 2.1.** A Python heredoc that follows `&&`
(`true && python - <<'PY' ... open('<repo>/x','w') ... PY`) was not scanned for writes: the guard took the
command at the START of the `&&` chain as the heredoc's receiver. 2.0 has the same gap. It was found while
implementing 2.1, when one of the maintainer's own commands wrote a file it should not have reached (a file
in a throw-away test copy). The fix splits the chain on `&&`, `||`, `;`, `|`, newlines and `(`.

**Four false positives.** Cases `p-gs-07`, `p-gs-09`, `b-gs-11`, `b-gs-14`: when the working directory is `.claude`, the new
guard-surface check read the file name of an unrelated path (for example a scratch `*.py`) as a hook file.
They are false positives in the blocking direction, found while implementing 2.1.

Both fixes exist and pass all 209 cases, but they change the two shell guards, and the guards refuse
guard-file writes from a session by design. **A human must apply them before 2.1 is committed.** Until then,
work from the project root.

## Status of every backlog item

**Verified** = executed and observed in this session. **Built** = written and checked statically
(validator, parse, syntax), not exercised in a real QA run.

| ID | Item | Status |
|---|---|---|
| C2 | Fail-closed launcher + self-test | Verified (8 launcher tests, doctor probes, no-Python demo) |
| B1 | Machine-readable run record + `verdict_check.py` | Verified on fixtures; orchestrator wiring built |
| D2 | Durable tool rebinding | Verified (install, rebind, upgrade) |
| C6 | Guard config cannot be loosened by the session | Verified (41 cases); went beyond the spec to `settings.json` and the shell route |
| C1 | Bash escapes and false positives | Verified (cases); deviation: quotes masked for data-only commands instead of re-anchoring `git` |
| C3 | PowerShell escapes and false positives | Verified (cases) |
| D6 | `doctor.py` | Verified (READY on the template and an installed copy) |
| G2 | Version single source | Verified (rule found the 2.0.0 / 2.0.1 drift) |
| G1 | Pinned MCP versions + `check_deps.py` | Verified (offline and online); pins labelled honestly via `_tested` |
| A3 | Heavy skills split | Verified (sizes); pointers left under every moved heading |
| B3 | Audit package | Verified (`--package` writes it); auditor reading it is built |
| A1, A2, A4, A5, A6, G3 | Descriptions, stop blocks, stale tool, vocabulary drift, one threshold source, memory blocks | Verified by validator rules that fail on regression |
| A8, B4, B5 | Checkpoint/resume, expected source, matrix provenance | Checker side verified; resume behaviour built |
| D1 | Profile-less utilities | Built |
| D4, D5 | OS-aware rendering, env-first secrets | Verified (`render_mcp.py` for win32 and darwin) |
| F1, F3 | Matrix and count consistency, profile-sections column | Verified by validator |
| E1 | CI runner | Verified with a stub `claude` (exit codes 0 / 1 / 2 / 3); PowerShell twin parse-checked only; no real CI |
| E2, E3, E6 | `api-contract-check`, `data-migration-check`, `i18n-check` | Built |
| E4, E9 | Flag dimension, Mobile flag | Built |
| E5 | `load.js` concurrency probe | Verified (self-test; PROD host refused before any request) |
| E7 | Cross-run summary | Verified (`--summary`); deviation: folded into `verdict_check.py` |
| E8 | Skill evals | Built (5 skills); not scored yet |
| E10 | Runtime adapters | Verified that all four generate parseable config; Codex CLI parsed its config; no QA session on another runtime |
| G4 | Date-stamped external claims | Done; `/goal` marked as not re-verified |

## What 2.1 costs or changes for users

- About 0.1 s more per tool call on Windows (launcher).
- Editing hooks from inside a session now needs a human (`QA_HARNESS_ADMIN=1` at start, or a hand edit).
- Upgraders must merge `settings.json.new` (the doctor reports FAIL until they do).
- A session can no longer read `.mcp.json`; secrets default to environment variables.
- The validator is stricter: new skills must meet the conventions above to pass.

## Not verified

macOS and Linux; a real CI pipeline; the PowerShell CI script's execution; OpenCode, Cline and Kilo Code
loading their generated files; Codex's experimental rules file; resume of a real interrupted run; the three
new skills and the five evals against a real project.