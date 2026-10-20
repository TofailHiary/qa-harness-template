# Migration inventory — template 2.0

Every component discovered in the private source setup, with its classification and disposition.
"Source" means the project-bound Claude Code setup this template was derived from; its name, hosts,
accounts and incidents are deliberately not reproduced here (see `generalization-conventions.md` §5).

Classification: **Reusable directly** · **Reusable after adaptation** · **Source-specific** (its purpose
depends on the source product, domain, private data or specialized infrastructure) · **Unavailable /
unresolved**. Validation: *static* = `scripts/validate.py` (frontmatter, references, catalog, privacy,
hygiene); *executed* = run in this release; *simulated* = exercised against synthetic inputs.

## Skills

| Component | Type | Existing destination equivalent | Dependencies | Classification | Action | Validation | Remaining gap |
|---|---|---|---|---|---|---|---|
| qa-standards | skill (shared) | yes (older, 16 KB) | — | Reusable after adaptation | merged: + Completion Gate, Verdict Integrity, Source Hierarchy, Fresh vs Historical, Execution Register, Evidence provenance, Verdict Contract, Judgement Discipline, six questions, Escape classes; plugins conditional; sub-agents a §16 knob; incidents → illustrative | static | behaviour not re-benchmarked |
| full-qa | skill (orchestrator) | yes | prompt-generator, every layer skill, qa-verdict-auditor | Reusable after adaptation | merged: Step 0, Phase 8/8a/8b ordering, escape-class wiring, capability skips | static | — |
| qa-validate, qa-team, release-check, regression-runner | skills (orchestrators) | yes | layer skills, agents | Reusable after adaptation | merged with source depth; audit before verdict; §16 knob | static | `Task` kept beside `Agent` in two allowed-tools lists (harmless) |
| prompt-generator (+ template.md, goal-loop-rules.md, research-map.md, evals.json) | skill + references | no | qa-standards | Reusable after adaptation | added; research map rewritten generically; private evals → synthetic | static; evals JSON parsed | — |
| test-cases-generator, pr-risk-analyzer, test-data-manager, env-health, sync-repos, login | skills (planning) | yes | qa-standards | Reusable after adaptation | merged: code-derived denominator, input classes, expected-value sources, fixture registry, provisioning pattern, release radar, deploy check, pluggable auth | static | — |
| code-review, db-check, api-test, browser-test, visual-regression, a11y-test, observability-check, security-review, perf-test | skills (layers) | yes | qa-standards, agents | Reusable after adaptation | merged: root-cause check, latent hints, soft-delete mechanism, COLUMN_COMMENT rule, path-exercised, Tab-walk rule, masked errors / silent no-ops, rating→contract mapping, measurement discipline | static | — |
| ai-output-eval | skill | no | qa-standards | Reusable after adaptation | added; the source's five product pipelines → a template table the project fills | static | — |
| bug-verifier, bug-report, flaky-race-verifier, evidence-manager, qa-report, release-note, explainer | skills (verification) | yes | qa-standards, bug-report/verifier, reporter agent | Reusable after adaptation | merged: finding verdicts, tracker filing per §15, "Raised By" row, provenance, renderer-not-judge, reported-by column | static | — |
| latent-pattern-sweep | skill | no | qa-standards | Reusable after adaptation | added; precedents → illustrative | static | — |
| prod-sentinel | skill | no | qa-standards, latent-pattern-sweep | Reusable after adaptation | added; the seven scans as templates bound by the project; baselines removed | static | — |
| test-together (+ known-noise.md, page-probes.md, api_peek.js, smoke_register.js) | skill + scripts | no | qa-standards, login, test-data-manager, bug-report | Reusable after adaptation | added; `api_peek.js` rewritten with pluggable auth (token env / login endpoint / cookie), no hardcoded hosts or keys | static; scripts executed against a local throw-away server by the porting agent (`node --check`, usage, login, pick/fields, `--out` path guard) | — |
| demo-creator (+ setup.js, record.js, tts.js, build_video.js, frames.js, templates) | skill + scripts (the external demo creator) | no | qa-standards, login, test-data-manager; Node, Playwright, ffmpeg, TTS | Reusable after adaptation | added; `expand()` → `expandSection()`, cross-platform TTS fallbacks, templates rewritten against a bundled offline sample app | static; `node --check`; end-to-end run on the sample app — see the final report for the executed status | online voices need internet; macOS/Linux fallbacks not executed here |
| product tenant-provisioning skill (+ its admin-form reference) | skill | no | — | Source-specific | excluded: provisions tenants on one product's admin portal with product-specific forms, ids and import ordering; the reusable principles (interview first, verify every step in the DB, document ordering constraints, claim an id block, baseline MAX(id)) were folded into `test-data-manager` → "Provisioning a fresh tenant / fixture set" | — | — |
| configure-project | skill (bootstrap) | destination-only | — | Reusable directly | updated for §14–§18, owned repos, gate, Demo, system-map seeding | static | — |

## Agents

| Component | Type | Destination equivalent | Classification | Action | Validation | Gap |
|---|---|---|---|---|---|---|
| qa-ui-tester, qa-api-tester, qa-db-validator, qa-reporter, qa-security-auditor | agents | yes | Reusable after adaptation | rewritten: preload qa-standards, canonical verdict vocabulary, typed-tool preference, provenance, no model pin, accounts by env var | static | — |
| qa-verdict-auditor | agent | no | Reusable after adaptation | added; verdict policy from §16 | static | — |
| `*.bak-*` agent copies | backups | — | Unavailable / not a component | excluded | — | — |

## Hooks

| Component | Destination equivalent | Classification | Action | Validation | Gap |
|---|---|---|---|---|---|
| block-bash-writes.py (14 KB allow-list version) | yes (4.9 KB blacklist version) | Reusable after adaptation | ported: config-driven repos, allow-list git verbs, heredoc-aware, cwd-aware, interpreter writes, owned-repo exemption | executed: hook red-team suite (see final report) | regex guard, not a sandbox |
| block-powershell-writes.py | yes | Reusable after adaptation | ported + here-string body stripping (new) | executed | — |
| block-writes.py, block-filesystem-writes.py | yes | Reusable after adaptation | kept config-driven; + owned repos | executed | — |
| block-github-writes.py | no | Reusable after adaptation | added; owned repos from config | executed | — |
| completion-gate.py | no | Reusable after adaptation | added; ticket pattern / phrases configurable; advisory default; incidents removed | compiled; smoke-tested with synthetic verdict text (see final report) | heuristic |
| memory-rotation.js | yes | Reusable after adaptation | ported CRLF fix + relaxed entry regex, kept config-driven dir | `node --check`; executed with a synthetic index (see final report) | — |
| copy-screenshot-evidence.sh | yes | Reusable after adaptation | kept portable; `jq` dependency replaced by python; evidence root from config | static | needs Git Bash on Windows |
| `_unused/*`, `*.bak*`, `completion-gate.log`, `__pycache__` | — | Unavailable / not components | excluded | — | — |
| qa-evidence/hook-redteam (runner.py, 110 cases, probe_v4.py) | no | Reusable after adaptation | ported as `scripts/hook-redteam/` with generic cases (protected `app-backend`/`app-frontend`, owned `qa-tools`); `probe_v4.py` (ad-hoc) excluded | executed | — |

## Rules, references, config, docs

| Component | Destination equivalent | Classification | Action | Validation | Gap |
|---|---|---|---|---|---|
| rules/anomaly-disposition.md, rules/pushback-protocol.md | no | Reusable after adaptation | added; incidents → illustrative | static | — |
| rules/testing.md, rules/db-gotchas.md | yes | Reusable after adaptation | rewritten in the newer short form; schema facts → placeholders | static | — |
| rules/frontend.md, backend.md, admin.md | yes | Reusable directly (destination already generic) | LF-normalized | static | — |
| references/system-map.md | no (destination had 5 unreferenced stubs) | Reusable after adaptation | template with the section skeleton, 60-day staleness rule and search recipes; stubs retired | static | the project fills it |
| CLAUDE.md | yes | Reusable after adaptation | rewritten | static | — |
| settings.json | yes | Reusable after adaptation | new hooks wired, denies extended, git denies moved into hooks | JSON + hook paths checked | — |
| settings.local.json | — | Source-specific (workstation permissions, private domains) | excluded | — | — |
| .mcp.json | `.mcp.json.template` | Reusable after adaptation | template kept; in-house product MCP server entry excluded → §14 mechanism; Postman launcher generalized | JSON | package names may change |
| AGENTS.md (Codex/Kilo workspace instructions) | no | Source-specific + cross-runtime | excluded; cross-runtime notes in `docs/integrations.md` | — | — |
| .codex/ parity installer (Install-Parity.ps1, Convert-ClaudeSkill.ps1, Convert-ClaudeAgent.ps1, a hook adapter, smoke/verify scripts), .kilo/ mirror | no | Reusable after adaptation — deferred | not ported: hard-wired to one workstation's paths and repository list; documented as a future extension built on `catalog.json` + `install.py` | — | **gap: no Codex/Kilo installer shipped** |
| .claude/backups/*, prompt-generator eval workspace (runs with private data) | — | Unavailable / not components | excluded | — | — |
| scheduled_tasks.lock, grep.exe.stackdump | — | runtime artifacts | excluded | — | — |

## External components referenced by the source

| Component | Where referenced | Classification | Action | Gap |
|---|---|---|---|---|
| Demo creator | `.claude/skills/demo-creator/` in the source (not an external package) | Reusable after adaptation | ported as above | — |
| In-house product MCP server (typed tools for every portal) | `.mcp.json`, CLAUDE.md, many skills | Source-specific | excluded; generalized as `PROJECT-PROFILE.md` §14 "project MCP / typed tools" with conditional phrasing in every skill | — |
| Bundled HTTP MCP server | `.mcp.json` → an external folder | Reusable directly | already bundled; verified byte-identical to the external copy | — |
| `superpowers`, `mattpocock-skills` plugins | qa-standards, several skills | Reusable directly (optional) | documented as optional integrations with by-hand equivalents | — |
| `frontend-design`, `taste-skill` plugins | user-level install only | unrelated to QA | excluded | — |
| A stray user-level `browser-test` SKILL.md (older copy) | `~/.claude/skills/SKILL.md` | Unresolved (superseded by the project skill) | excluded | — |
| Unrelated repositories on the same workstation (an AI test-automation product, migration scripts, product repos) | working directories | not part of the setup | excluded | — |
| Private memory (237 files), evidence folders, archived evidence, sample-file library | CLAUDE.md, test-data-manager | Source-specific / private | never copied; reusable principles extracted into qa-standards (Judgement Discipline 10–12, Fresh vs Historical, Memory Ritual), anomaly-disposition, test-data-manager (input classes, provisioning), a11y-test (Tab walk), release-note (reported by), bug-report (reporter fields, filing rules) | — |

## Not ported, with reason

- **Codex / Kilo parity installers** — workstation-bound; future extension.
- **Product tenant provisioning skill** — domain-specific purpose.
- **Settings env flags** that reflect one user's preferences (experimental agent teams, background-task
  switches) — documented as optional in `docs/integrations.md`, not shipped on.
- **Private baselines, counts, dates, ticket numbers, assignee rules, transition ids** — replaced by
  `PROJECT-PROFILE.md` fields (§15, §16) and memory-held baselines.
