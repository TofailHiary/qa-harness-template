# Capability Matrix

Every skill checks `PROJECT-PROFILE.md` §2 (Capability Map) before doing anything.

- **`required`** — the skill is hard-gated **OFF** when that capability is absent. It stops with a
  message telling the user to run `/configure-project`.
- **`any[...]`** — needs at least **one** of the listed capabilities.
- **`always on`** — utilities and orchestrators that never hard-stop; they skip the sub-parts whose
  capability is off and say so.

| Skill | Capability rule |
|---|---|
| `db-check` | required: **DB** |
| `test-data-manager` | required: **DB** |
| `ai-output-eval` | required: **DB** (API / Browser enrich the cross-layer check; Prod-DB for a prod confirm) |
| `api-test` | required: **API** |
| `browser-test` | required: **Browser** |
| `a11y-test` | required: **Browser** |
| `visual-regression` | required: **Browser** |
| `test-together` | required: **Browser** (DB / API optional enhancers) |
| `login` | required: **any[Browser, API]** |
| `observability-check` | required: **any[Browser, API]** |
| `perf-test` | required: **any[API, Browser]** |
| `security-review` | required: **any[API, Browser]** |
| `automation-writer` | required: **any[Browser, API]** |
| `flaky-race-verifier` | required: **any[Browser, API]** |
| `sync-repos` | required: **any[GitHub, LocalRepos]** |
| `pr-risk-analyzer` | required: **any[GitHub, LocalRepos]** |
| `code-review` | required: **any[GitHub, LocalRepos]** |
| `release-note` | required: **any[GitHub, LocalRepos]** |
| `explainer` | required: **any[GitHub, LocalRepos]** |
| `latent-pattern-sweep` | required: **any[DB, Prod-DB]** + **any[GitHub, LocalRepos]** |
| `prod-sentinel` | required: **Prod-DB** (read-only) |
| `demo-creator` | required: **Demo** (Node + Playwright + ffmpeg + TTS; `setup.js --check` prints READY) |
| `api-contract-check` | required: **API** (Postman optional - a contract file is enough) |
| `data-migration-check` | required: **DB** + **any[GitHub, LocalRepos]** (Prod-DB optional for the pre-flight counts; never runs a migration) |
| `i18n-check` | required: **Browser** |
| `qa-standards` | always on (shared module) |
| `env-health` | always on (probes only enabled capabilities; release radar needs Jira, sentinel needs Prod-DB) |
| `prompt-generator` | always on (utility — each research row degrades to "not available: <capability> off") |
| `evidence-manager` | always on (utility) |
| `qa-report` | always on (utility) |
| `bug-report` | always on (utility; tracker filing needs Jira) |
| `bug-verifier` | always on (utility) |
| `test-cases-generator` | always on (utility) |
| `full-qa` | always on (orchestrator — skips disabled sub-phases) |
| `qa-validate` | always on (orchestrator — skips disabled sub-phases) |
| `qa-team` | always on (orchestrator — skips disabled lanes) |
| `release-check` | always on (orchestrator — skips disabled sub-phases) |
| `regression-runner` | always on (orchestrator — skips disabled sub-phases) |
| `configure-project` | always on (the bootstrap) |

**Optional enhancers** (never gate a skill, just enrich it when present): **Prod-DB** (confirm a prod
repro; a hard gate only for `prod-sentinel`), **Postman** (existing API collections), **Jira** (pull
acceptance criteria, release radar, filing per §15), **Admin** / **Reporting** (extra surfaces), **SSH**
(tunnels / server checks), a **project MCP server with typed tools** (§14), the **`superpowers` /
`mattpocock-skills` plugins** (§17 — every use has a by-hand equivalent).

**Agents** follow the same rules: `ui-tester` needs Browser, `api-tester` needs API, `db-validator`
needs DB, `security-auditor` needs any[API, Browser]; `reporter` and `qa-verdict-auditor` are always on.
Sub-agent use itself is a policy knob (§16): when disabled, orchestrators run the lanes and the audit
in-session.

## How a gated skill behaves when off

Each `required`/`any[...]` skill opens with a guard block. If its capability is `off` in §2 it prints,
for example: *"This project has no Browser configured, so `/browser-test` is unavailable. Run
`/configure-project` to enable it."* — and does not call its tools.

Orchestrators (`full-qa`, etc.) read §2 and skip whole phases: no Browser → skip UI/E2E/visual/a11y;
no DB → skip db-check and data-consistency; no GitHub/LocalRepos → skip code-review/pr-risk. Skipped
phases are stated explicitly in the verdict as coverage gaps — never an implied PASS.

## Mobile

`Mobile` is a capability flag in `PROJECT-PROFILE.md §2` with **no skill yet**: native iOS / Android apps are
out of scope today. A `mobile-test` skill is added only when a maintainer can validate it against a
device or emulator MCP server; until then a mobile-only surface is a named coverage gap in every run that
touches it, never an implied PASS.
