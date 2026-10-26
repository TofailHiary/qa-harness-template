# Component catalog

Generated from `catalog.json` by `python scripts/validate.py --fix-catalog-doc`. Do not edit by hand.

## Skills

| Skill | Group | Capability rule | Profile sections read | What it does |
|---|---|---|---|---|
| `configure-project` | bootstrap | always on (the bootstrap) | §1, §2, §3, §4, §6, §7, §11, §12, §14, §15, §16, §17, §18 | Detects the stack, fills PROJECT-PROFILE.md, writes .mcp.json + harness-config.json, rebinds tools, live-verifies. |
| `qa-standards` | shared | always on (shared module) | §3, §5, §6, §8, §12, §15, §16, §17 | The shared standard: modes, scope lock, evidence ledger, mutation gate, completion gate, verdict contract, escape classes, memory ritual. |
| `full-qa` | orchestrators | always on (orchestrator — skips disabled sub-phases) | §2, §3, §5, §8, §10, §11, §12, §14, §15, §16, §17 | Master orchestrator: prompt → cases → code → DB → API → UI → security → perf → regression → audit → report → GO/NO-GO. |
| `qa-validate` | orchestrators | always on (orchestrator) | §2, §3, §5, §6, §7, §8, §9, §10, §11, §12, §13, §14, §15, §17 | Lighter cross-layer validation of one story/bug ending in ready / not-ready (GO / NO-GO). |
| `qa-team` | orchestrators | always on (orchestrator) | §2, §3, §4, §5, §6, §7, §8, §9, §10, §11, §12, §13, §14, §15, §16, §17 | Three parallel lanes (UI, API, DB) with one synthesized, audited report. |
| `release-check` | orchestrators | always on (orchestrator) | §2, §3, §5, §6, §7, §8, §9, §10, §11, §12, §13, §14, §15, §16, §17 | Release-level sign-off across areas with the release checklist and an independent audit. |
| `regression-runner` | orchestrators | always on (orchestrator) | §2, §3, §6, §8, §11, §12, §14, §16, §17 | Guards the indirect blast radius after a change. |
| `prompt-generator` | planning | always on (utility; register rows degrade per §2) | §2, §3, §5, §6, §7, §9, §11, §12, §13, §14, §15, §16, §17 | Step 0 of /full-qa: researches the request and writes one self-contained execution prompt (template + research map + /goal and /loop rules). |
| `test-cases-generator` | planning | always on (utility) | §2, §3, §6, §7, §9, §11, §12, §13, §14, §15, §16, §17 | Executable, traceable test plan with a code-derived denominator, input classes and expected-value sources. |
| `pr-risk-analyzer` | planning | required: any[GitHub, LocalRepos] | §2, §3, §8, §9, §11, §12, §13, §15, §16 | Blast-radius risk map of a PR/diff before testing. |
| `test-data-manager` | planning | required: DB | §2, §5, §6, §7, §9, §10, §12, §13, §14 | Locate / prepare / snapshot / restore test data under the Mutation Safety Gate; input-class fixture registry; provisioning pattern. |
| `env-health` | planning | always on (probes only enabled capabilities) | §2, §3, §5, §6, §7, §9, §10, §11, §12, §14, §15 | Preflight: MCP servers, repos, portals, DB, auth, deployed build, release radar, prod sentinel. |
| `sync-repos` | planning | required: any[GitHub, LocalRepos] | §2, §3, §9, §12 | Pull every repo to the branch under test with read-only git verbs; report HEAD per repo. |
| `login` | planning | required: any[Browser, API] | §2, §3, §5, §6, §7, §8, §9, §10, §12, §14 | Authenticated session per role: browser, API token, or SSO impersonation. |
| `code-review` | layers | required: any[GitHub, LocalRepos] | §2, §3, §4, §6, §9, §10, §11, §12, §15, §16, §17 | Code-level review incl. root-cause check for fix PRs and latent-pattern hints. |
| `db-check` | layers | required: DB | §2, §3, §6, §8, §9, §10, §11, §12, §16, §17 | Schema vs ORM drift, FK/orphans, soft-delete mechanism, tenant scoping, enum width, indexes. |
| `api-test` | layers | required: API | §2, §3, §5, §6, §7, §9, §11, §12, §14, §16, §17 | Auth, RBAC, validation, errors, schema, pagination, DB-write consistency. |
| `browser-test` | layers | required: Browser | §2, §3, §5, §6, §7, §8, §11, §12, §13, §14, §16, §17 | Full user journeys with console/network capture and the path-exercised rule. |
| `visual-regression` | layers | required: Browser | §2, §3, §5, §7, §8, §9, §12, §16, §17 | Layout / overflow / responsive checks across breakpoints with measured evidence. |
| `a11y-test` | layers | required: Browser | §2, §3, §5, §7, §8, §9, §12, §16, §17 | Keyboard, ARIA, focus, contrast — scanner hits are leads, the Tab walk is the proof. |
| `observability-check` | layers | required: any[Browser, API] | §2, §3, §5, §6, §8, §9, §10, §11, §12, §14, §16, §17 | Errors the UI hides: console, failed/slow calls, 5xx, masked errors, silent async no-ops. |
| `security-review` | layers | required: any[API, Browser] | §2, §3, §4, §5, §6, §7, §8, §9, §12, §14, §16, §17 | 10-point audit mapped into the verdict contract; CSP/host allow-list method. |
| `perf-test` | layers | required: any[API, Browser] | §2, §3, §4, §5, §6, §8, §9, §10, §12, §14, §16, §17 | Page load / Web Vitals / API latency / query plans with measurement discipline. |
| `ai-output-eval` | layers | required: DB | §2, §3, §5, §6, §9, §11, §12, §13, §14 | Recompute computed / model-generated outputs vs source rows; determinism; edge cases. |
| `bug-verifier` | verification | always on (utility) | §2, §3, §5, §6, §7, §8, §9, §10, §11, §12, §13, §14, §15, §16, §17 | Confirms a suspected bug is real: CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE. |
| `bug-report` | verification | always on (utility) | §2, §3, §5, §6, §7, §8, §9, §11, §12, §15, §16 | Standard bug report with layer classification, evidence ledger, optional tracker filing per §15. |
| `flaky-race-verifier` | verification | required: any[Browser, API] | §2, §3, §5, §7, §11, §12, §17 | Reproduction rate for intermittent bugs; race/timing hunt. |
| `evidence-manager` | verification | always on (utility) | §2, §3, §5, §6, §7, §15 | Captures, names and files evidence; assembles the ledger with provenance. |
| `qa-report` | verification | always on (utility) | §2, §3, §5, §6, §8, §11, §12, §15, §16 | Renders the audited register/ledger into the 9-section report. |
| `release-note` | verification | required: any[GitHub, LocalRepos] | §2, §3, §9, §12, §15 | Customer-facing release notes with a 'reported by' column. |
| `explainer` | verification | required: any[GitHub, LocalRepos] | §1, §2, §8, §11, §12, §15 | Plain-language, per-role before/after explanation of a change. |
| `latent-pattern-sweep` | production | required: any[DB, Prod-DB] + any[GitHub, LocalRepos] | §2, §3, §4, §6, §9, §10, §12 | Crosses code assumptions (cardinality / branch / input class) against the live data distribution. |
| `prod-sentinel` | production | required: Prod-DB | §2, §4, §6, §7, §10, §11, §12, §15, §16 | Read-only production anomaly scan against a baseline (7 scan templates). |
| `test-together` | collaboration | required: Browser | §2, §3, §5, §6, §7, §8, §9, §12, §14, §15 | Guided pair-testing in a shared browser with live expected values. |
| `demo-creator` | collaboration | required: Demo (Node + Playwright + ffmpeg + TTS) | §2, §5, §7, §12, §18 | Narrated, captioned MP4 demo of a real flow recorded with Playwright. |
| `automation-writer` | collaboration | required: any[Browser, API] | §2, §3, §5, §7, §9, §14, §15 | Turns a confirmed manual case into a Playwright or HTTP test script. |
| `api-contract-check` | layers | required: API | §2, §3, §5, §6, §9, §11, §12, §13, §14, §16, §17 | Diffs live API behaviour against its OpenAPI / Postman / GraphQL contract, classifies each difference as additive, breaking or undocumented, and names the consumers it breaks. |
| `data-migration-check` | layers | required: DB + any[GitHub, LocalRepos] | §1, §2, §3, §4, §6, §9, §10, §11, §12 | Read-only review of migrations and backfills: schema before/after, production pre-flight, backfill recompute, compatibility window, rollback plan. |
| `i18n-check` | layers | required: Browser | §1, §2, §3, §4, §5, §6, §7, §8, §9, §11, §12 | Per-locale rendered sweep: raw keys, untranslated text, text expansion and RTL layout, date/number/currency/plural formats, server-rendered text. |

## Agents

| Agent (dispatch name) | File | Capability |
|---|---|---|
| `ui-tester` | `.claude/agents/qa-ui-tester.md` | required: Browser |
| `api-tester` | `.claude/agents/qa-api-tester.md` | required: API |
| `db-validator` | `.claude/agents/qa-db-validator.md` | required: DB |
| `reporter` | `.claude/agents/qa-reporter.md` | always on |
| `security-auditor` | `.claude/agents/qa-security-auditor.md` | required: any[API, Browser] |
| `qa-verdict-auditor` | `.claude/agents/qa-verdict-auditor.md` | always on (fresh-context audit) |

## Groups

| Group | Skills |
|---|---|
| `bootstrap` | `configure-project` |
| `shared` | `qa-standards` |
| `orchestrators` | `full-qa`, `qa-validate`, `qa-team`, `release-check`, `regression-runner` |
| `planning` | `prompt-generator`, `test-cases-generator`, `pr-risk-analyzer`, `test-data-manager`, `env-health`, `sync-repos`, `login` |
| `layers` | `code-review`, `db-check`, `api-test`, `browser-test`, `visual-regression`, `a11y-test`, `observability-check`, `security-review`, `perf-test`, `ai-output-eval`, `api-contract-check`, `data-migration-check`, `i18n-check` |
| `verification` | `bug-verifier`, `bug-report`, `flaky-race-verifier`, `evidence-manager`, `qa-report`, `release-note`, `explainer` |
| `production` | `latent-pattern-sweep`, `prod-sentinel` |
| `collaboration` | `test-together`, `demo-creator`, `automation-writer` |

## Core files (installed with every project-level install)

- `.claude/CLAUDE.md`
- `.claude/PROJECT-PROFILE.md`
- `.claude/PROJECT-PROFILE.example.md`
- `.claude/settings.json`
- `.claude/hooks/harness-config.json`
- `.claude/hooks/harness_config.py`
- `.claude/hooks/block-writes.py`
- `.claude/hooks/block-bash-writes.py`
- `.claude/hooks/block-powershell-writes.py`
- `.claude/hooks/block-filesystem-writes.py`
- `.claude/hooks/block-github-writes.py`
- `.claude/hooks/completion-gate.py`
- `.claude/hooks/copy-screenshot-evidence.sh`
- `.claude/hooks/memory-rotation.js`
- `.claude/hooks/run-hook.sh`
- `.claude/scripts/doctor.py`
- `.claude/scripts/ci-run-qa.sh`
- `.claude/scripts/ci-run-qa.ps1`
- `.claude/scripts/rebind.py`
- `.claude/scripts/render_mcp.py`
- `.claude/tool-bindings.json`
- `.claude/rules/testing.md`
- `.claude/rules/db-gotchas.md`
- `.claude/rules/anomaly-disposition.md`
- `.claude/rules/pushback-protocol.md`
- `.claude/rules/frontend.md`
- `.claude/rules/backend.md`
- `.claude/rules/admin.md`
- `.claude/references/README.md`
- `.claude/references/system-map.md`
- `.claude/mcp-servers/http-client/README.md`
- `.claude/mcp-servers/http-client/package.json`
- `.claude/mcp-servers/http-client/server.js`
- `.mcp.json.template`
- `.gitignore`
- `.gitattributes`
- `SETUP.md`
- `docs/capability-matrix.md`

## Optional external components

- **superpowers** — Claude Code plugin
- **mattpocock-skills** — Claude Code plugin
- **mcp servers** — .mcp.json.template; GitHub and Jira are Claude Code connectors configured outside .mcp.json. Other engines (Postgres, Mongo) are added by /configure-project with approval.
