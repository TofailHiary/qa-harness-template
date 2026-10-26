# Changelog

All notable changes to the QA harness template. Dates are ISO (YYYY-MM-DD).

## 2.1.1 — 2026-10-26

### Added
- MIT license (`LICENSE`, GitHub's official template). A byte-identical copy at `.claude/LICENSE` is installed
  with every project-level install, so each installed copy carries the notice the license requires.
- README: License section. Validator: both license files exist, are identical, and the README links them.

## 2.1.0 — 2026-10-26

Implements `docs/maintainers/enhancement-backlog-2026-10-26.md`. Measured before/after:
`docs/maintainers/before-after-2.1.md`.

### Security (guards)
- **Fail-closed launcher.** Every Python hook runs through `.claude/hooks/run-hook.sh`: it tries `python3`,
  `python`, `py -3`, skips broken names, and BLOCKS when no Python 3 works or a guard crashes. Before, a
  missing interpreter made every guard silently non-blocking. Stop hooks use `--fail-open` (advisory).
- **Guards a session cannot loosen.** `block-writes.py` checks the CONTENT of every Write/Edit/MultiEdit of
  `settings.json` and `harness-config.json`: dropping a guard hook, `disableAllHooks`, removing a deny rule,
  adding an owned repo, removing a protected repo, widening the allow-globs, risky `memory_root` /
  `evidence_root` moves or unparseable JSON need a human (`QA_HARNESS_ADMIN=1` set before Claude Code
  starts). The Bash and PowerShell guards refuse shell writes to the guard surface (`.claude/hooks/**`,
  `.claude/settings*.json`).
- **Escapes closed (Bash):** `>|`, `find -delete` / `-exec rm`, `pathlib.write_text`, `shutil.rmtree`,
  `os.*` writes, `fs.rmSync` / `fs.promises.writeFile` and friends, `git.exe`, `cd` inside `sh -c '...'`,
  and opaque execution (`base64 -d | sh`, computed `eval`, `sh -c "$VAR"`, `pwsh -EncodedCommand`).
- **Escapes closed (PowerShell):** `Start-Process git -ArgumentList push`, `-EncodedCommand`,
  `Invoke-Expression` / `iex` of a computed string or a pipeline, `[scriptblock]::Create`,
  `[IO.Directory]::Delete`, pathlib / shutil / fs writes, `git.exe`.
- **False positives removed:** a quoted pattern given to `grep` / `rg` / `echo` / `printf` / `Select-String` /
  `Write-Output` is no longer read as a git command (unless the line executes something); `*.md` is no
  longer read as the `md` alias.
- A Python heredoc after `&&` is now scanned for writes (case `b-esc-15`; the gap existed in 2.0 too), and the
  guard-surface check no longer misreads absolute paths when the working directory is `.claude`. These two
  shell-guard fixes are applied by a human (`docs/maintainers/before-after-2.1.md`).
- Red-team suite: 136 -> 209 cases, plus 8 launcher tests driven through a real POSIX `sh`.

### Verdict integrity
- **Run record** `qa-evidence/<run-folder>/run.json` (`qa-standards/references/run-record.md`): scope, the
  code-derived matrix, register (with an Expected source column), ledger, findings, phases, checkpoint,
  verdict. `qa-standards/scripts/verdict_check.py` recomputes `N of M` and the run verdict, resolves every
  evidence id to a file, enforces PASS/FAIL/BLOCKED/NOT APPLICABLE requirements and the write-path rule,
  writes the auditor's `package.md` and prints a cross-run `--summary`. Shipped fixtures prove it accepts a
  consistent run and catches all eight planted contradictions in a tampered one.
- Orchestrators create, checkpoint and resume from the run record; the verdict auditor reads `package.md`,
  not the chat. The completion gate (check 14) recomputes any run folder a verdict names.

### Install and configuration
- `.claude/scripts/doctor.py` - first-run diagnostics with a live probe of every guard.
- `.claude/scripts/render_mcp.py` - the only supported way to make `.mcp.json`: capability toggles, `cmd /c`
  on Windows only, secrets as `${ENV}` placeholders, user-added servers kept, `--add-server`.
- `.claude/scripts/rebind.py` + `.claude/tool-bindings.json` - DB tool rebinding that the installer
  re-applies after every upgrade (2.0 lost it on upgrade).
- MCP packages pinned (no `@latest`), each with a `_tested` note, and `scripts/check_deps.py [--online]` reports drift; `Read(.mcp.json)` denied; secrets default
  to environment variables; `/configure-project` uses the three scripts and routes guard-loosening changes
  to the human.
- Five utility skills work without a profile (user-level install), labelling answers INFERRED.

### Skills
- New: `api-contract-check`, `data-migration-check` (read-only), `i18n-check` (39 skills).
- `perf-test/scripts/load.js` - a light concurrency probe that refuses PROD hosts and non-GET without the
  Mutation Safety Gate.
- Feature-flag / remote-config dimension in `test-cases-generator` and `env-health` (profile §9);
  `Mobile` capability flag with no skill yet (§2, capability matrix).
- `qa-standards` 44 KB -> 24 KB, `qa-team` / `release-check` / `qa-validate` under 24 KB: reference material
  moved to `references/` with a pointer under every original heading.
- Every skill that takes arguments stops when none are given; every memory block has the placeholder, the
  `ls -la` verify line and the SUPERSEDED rule (four skills had no memory block at all); descriptions state
  triggers only; one confidence-line template and one result vocabulary everywhere; stale `Task` tool
  removed; perf thresholds live only in `perf-test`.
- Evals for `full-qa`, `bug-verifier`, `test-cases-generator`, `prod-sentinel`, `demo-creator`;
  `docs/maintainers/skill-evals.md`.

### Other agent runtimes
- `scripts/install.py --runtime codex|opencode|cline|kilo` (`scripts/runtime_adapters.py`): MCP config in each
  runtime's own format, its strongest read-only policy, pointer skills in `.agents/skills` for Codex and
  Kilo, a merge snippet for Cline's global MCP settings, and an honest enforced-vs-advisory summary. Codex CLI
  0.144.1 parsed the generated config; no other runtime ran a QA session.

### Automation and docs
- `.claude/scripts/ci-run-qa.sh` / `.ps1` and `docs/ci.md`: unattended runs whose exit code comes from the
  run record (0 GO, 1 NO-GO / inconsistent, 2 PARTIAL, 3 setup).
- Validator: conventions, version/count consistency, launcher self-test, MCP template pins, run-record
  fixtures, evals, capability matrix, a "Profile sections read" column in `docs/catalog.md`.
- External facts are date-stamped with what was actually checked.

### Deviations from the backlog plan
- One `run.json` per run instead of separate register / ledger / matrix / checkpoint / summary files.
- C1: the `git` match was kept broad; quoted text is masked only for data-only commands. Re-anchoring `git`
  to command position risked reopening `timeout 5 git push`-style escapes.
- `npm run build` inside a protected repo stays allowed (case `b-pol-01`): build output is git-ignored and
  QA starts apps locally.
- C6 went beyond `harness-config.json`: `settings.json` and the shell route to the guard surface are covered too.

## 2.0.2 — 2026-10-26

### Changed
- Positioning: the template is described as a QA harness for AI coding agents — the method, skills,
  rules and profile are runtime-neutral; installation, hooks and the completion gate are Claude Code
  native; other runtimes (Codex, OpenCode, Cline, Kilo Code, …) use the new root `AGENTS.md`. README,
  SETUP, `docs/platforms-and-limitations.md` and `catalog.json` carry an explicit runtime support matrix.
- `.claude/rules/backend.md` no longer hardcodes a stack; it points at `PROJECT-PROFILE.md` §4/§9.

### Added
- `AGENTS.md` (root): startup instructions and tool-name mapping for runtimes that read it.
- `docs/maintainers/external-review-prompt.md`: a reusable prompt for independent enhancement reviews.

## 2.0.1 — 2026-10-26

### Fixed
- `scripts/validate.py`: the privacy scanner no longer carries the names, accounts, ticket prefixes,
  passwords, hostname fragments or tunnel port of the source setup. It ships shape-based rules only
  (credentials, keys, tokens, user-home paths, non-example e-mails and hostnames, non-generic ticket keys,
  loopback ports) and merges an optional git-ignored `scripts/private-patterns.json`; when that file is
  present it also fails if any of its literals appears anywhere in the tracked repo text.

## 2.0.0 — 2026-10-20

A full refresh from the current private source setup, generalized per
`docs/maintainers/generalization-conventions.md`.

### Added
- Skills: `prompt-generator` (Step 0 of /full-qa, with the 18-section template, research map and
  /goal-/loop rules), `latent-pattern-sweep`, `prod-sentinel`, `ai-output-eval`, `test-together`
  (with `api_peek.js` and `smoke_register.js`), `demo-creator` (the external demo creator: recorder,
  narration, build, frame check, offline sample app).
- Agent: `qa-verdict-auditor` (fresh-context verdict audit).
- Hooks: `completion-gate.py` (Stop/SubagentStop, advisory by default), `block-github-writes.py`
  (owned repos only); `owned_repos` and `gate` settings in `harness-config.json`.
- Rules: `anomaly-disposition.md`, `pushback-protocol.md`.
- References: `system-map.md` template (replaces five unreferenced reference stubs).
- `PROJECT-PROFILE.md` §14 project MCP, §15 issue tracker, §16 QA policy, §17 plugins, §18 demo defaults;
  `Demo` capability; owned repos; prod access path; sample-file library.
- `catalog.json`, `scripts/install.py` (full / group / single skill with dependency resolution / user-level),
  `scripts/validate.py` (frontmatter, references, catalog, JSON, hooks, links, hygiene, privacy),
  `scripts/hook-redteam/` (protocol-aware qualification suite for the guards).
- Docs: installation, configuration, integrations, usage examples, platforms & limitations,
  troubleshooting, upgrading, maintainers' generalization conventions and migration inventory.
- `.gitattributes` (LF normalization).

### Changed
- `qa-standards`: Completion Gate, Verdict Integrity, Authoritative Source Hierarchy, Fresh vs Historical,
  Execution Register, Evidence provenance, Verdict Contract, Judgement Discipline, the six questions,
  Escape classes E1–E13; plugin use is conditional with by-hand equivalents; sub-agents are a policy knob.
- Every existing skill merged with the newer source depth (path-exercised rule, input classes,
  expected-value sources, code-derived denominator, independent audit before the verdict, provenance
  columns, tracker rules via §15) while keeping the capability gates and profile placeholders.
- `full-qa`: Step 0 prompt-generator, Phase 8/8a/8b ordering (assemble → audit → render), escape-class wiring.
- Agents: preload `qa-standards`, canonical verdict vocabulary, typed-tool preference, no model pins.
- Hooks: Bash guard is now a read-only git allow-list with heredoc-aware scanning, cwd-aware write
  detection and an owned-repo exemption; PowerShell guard mirrors it and ignores here-string bodies;
  memory rotation handles CRLF indexes; screenshot hook no longer needs `jq`.
- `settings.json`: wires the new hooks, broadens SessionStart, extends the deny list; git write denies
  moved into the hooks so owned repos can be exempted.
- `bug-report`: "Reported By = QA Agent" plus an optional "Raised By" row; tracker filing rules from §15.

### Removed
- `.claude/references/{api-endpoints,database-queries,memory-entities,playwright-selectors,postman-collections}.md`
  (unreferenced stubs; content folded into the system map and the skills that use it).

## 1.0.0

Initial portable template: 29 skills, 5 agents, read-only hooks, capability model, bootstrap.
