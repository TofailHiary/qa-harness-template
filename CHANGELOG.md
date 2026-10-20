# Changelog

All notable changes to the QA harness template. Dates are ISO (YYYY-MM-DD).

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
