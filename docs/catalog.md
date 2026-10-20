# Component catalog

Generated from `catalog.json` by `python scripts/validate.py --fix-catalog-doc`. Do not edit by hand.

## Skills

| Skill | Group | Capability rule | What it does |
|---|---|---|---|
| `configure-project` | bootstrap | always on (the bootstrap) | Detects the stack, fills PROJECT-PROFILE.md, writes .mcp.json + harness-config.json, rebinds tools, live-verifies. |
| `qa-standards` | shared | always on (shared module) | The shared standard: modes, scope lock, evidence ledger, mutation gate, completion gate, verdict contract, escape classes, memory ritual. |
| `full-qa` | orchestrators | always on (orchestrator — skips disabled sub-phases) | Master orchestrator: prompt → cases → code → DB → API → UI → security → perf → regression → audit → report → GO/NO-GO. |
| `qa-validate` | orchestrators | always on (orchestrator) | Lighter cross-layer validation of one story/bug ending in ready / not-ready (GO / NO-GO). |
| `qa-team` | orchestrators | always on (orchestrator) | Three parallel lanes (UI, API, DB) with one synthesized, audited report. |
| `release-check` | orchestrators | always on (orchestrator) | Release-level sign-off across areas with the release checklist and an independent audit. |
| `regression-runner` | orchestrators | always on (orchestrator) | Guards the indirect blast radius after a change. |
| `prompt-generator` | planning | always on (utility; register rows degrade per §2) | Step 0 of /full-qa: researches the request and writes one self-contained execution prompt (template + research map + /goal and /loop rules). |
| `test-cases-generator` | planning | always on (utility) | Executable, traceable test plan with a code-derived denominator, input classes and expected-value sources. |
| `pr-risk-analyzer` | planning | required: any[GitHub, LocalRepos] | Blast-radius risk map of a PR/diff before testing. |
| `test-data-manager` | planning | required: DB | Locate / prepare / snapshot / restore test data under the Mutation Safety Gate; input-class fixture registry; provisioning pattern. |
| `env-health` | planning | always on (probes only enabled capabilities) | Preflight: MCP servers, repos, portals, DB, auth, deployed build, release radar, prod sentinel. |
| `sync-repos` | planning | required: any[GitHub, LocalRepos] | Pull every repo to the branch under test with read-only git verbs; report HEAD per repo. |
| `login` | planning | required: any[Browser, API] | Authenticated session per role: browser, API token, or SSO impersonation. |
| `code-review` | layers | required: any[GitHub, LocalRepos] | Code-level review incl. root-cause check for fix PRs and latent-pattern hints. |
| `db-check` | layers | required: DB | Schema vs ORM drift, FK/orphans, soft-delete mechanism, tenant scoping, enum width, indexes. |
| `api-test` | layers | required: API | Auth, RBAC, validation, errors, schema, pagination, DB-write consistency. |
| `browser-test` | layers | required: Browser | Full user journeys with console/network capture and the path-exercised rule. |
| `visual-regression` | layers | required: Browser | Layout / overflow / responsive checks across breakpoints with measured evidence. |
| `a11y-test` | layers | required: Browser | Keyboard, ARIA, focus, contrast — scanner hits are leads, the Tab walk is the proof. |
| `observability-check` | layers | required: any[Browser, API] | Errors the UI hides: console, failed/slow calls, 5xx, masked errors, silent async no-ops. |
| `security-review` | layers | required: any[API, Browser] | 10-point audit mapped into the verdict contract; CSP/host allow-list method. |
| `perf-test` | layers | required: any[API, Browser] | Page load / Web Vitals / API latency / query plans with measurement discipline. |
| `ai-output-eval` | layers | required: DB | Recompute computed / model-generated outputs vs source rows; determinism; edge cases. |
| `bug-verifier` | verification | always on (utility) | Confirms a suspected bug is real: CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE. |
| `bug-report` | verification | always on (utility) | Standard bug report with layer classification, evidence ledger, optional tracker filing per §15. |
| `flaky-race-verifier` | verification | required: any[Browser, API] | Reproduction rate for intermittent bugs; race/timing hunt. |
| `evidence-manager` | verification | always on (utility) | Captures, names and files evidence; assembles the ledger with provenance. |
| `qa-report` | verification | always on (utility) | Renders the audited register/ledger into the 9-section report. |
| `release-note` | verification | required: any[GitHub, LocalRepos] | Customer-facing release notes with a 'reported by' column. |
| `explainer` | verification | required: any[GitHub, LocalRepos] | Plain-language, per-role before/after explanation of a change. |
| `latent-pattern-sweep` | production | required: any[DB, Prod-DB] + any[GitHub, LocalRepos] | Crosses code assumptions (cardinality / branch / input class) against the live data distribution. |
| `prod-sentinel` | production | required: Prod-DB | Read-only production anomaly scan against a baseline (7 scan templates). |
| `test-together` | collaboration | required: Browser | Guided pair-testing in a shared browser with live expected values. |
| `demo-creator` | collaboration | required: Demo (Node + Playwright + ffmpeg + TTS) | Narrated, captioned MP4 demo of a real flow recorded with Playwright. |
| `automation-writer` | collaboration | required: any[Browser, API] | Turns a confirmed manual case into a Playwright or HTTP test script. |

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
| `layers` | `code-review`, `db-check`, `api-test`, `browser-test`, `visual-regression`, `a11y-test`, `observability-check`, `security-review`, `perf-test`, `ai-output-eval` |
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
