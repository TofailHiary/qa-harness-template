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
| `api-test` | required: **API** |
| `browser-test` | required: **Browser** |
| `a11y-test` | required: **Browser** |
| `visual-regression` | required: **Browser** |
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
| `qa-standards` | always on (shared module) |
| `env-health` | always on (probes only enabled capabilities) |
| `evidence-manager` | always on (utility) |
| `qa-report` | always on (utility) |
| `bug-report` | always on (utility) |
| `bug-verifier` | always on (utility) |
| `test-cases-generator` | always on (utility) |
| `full-qa` | always on (orchestrator — skips disabled sub-phases) |
| `qa-validate` | always on (orchestrator — skips disabled sub-phases) |
| `qa-team` | always on (orchestrator — skips disabled sub-phases) |
| `release-check` | always on (orchestrator — skips disabled sub-phases) |
| `regression-runner` | always on (orchestrator — skips disabled sub-phases) |
| `configure-project` | always on (the bootstrap) |

**Optional enhancers** (never gate a skill, just enrich it when present): **Prod-DB** (confirm a prod
repro), **Postman** (existing API collections), **Jira** (pull acceptance criteria), **Admin** /
**Reporting** (extra surfaces), **SSH** (tunnels / server checks).

## How a gated skill behaves when off

Each `required`/`any[...]` skill opens with a guard block. If its capability is `off` in §2 it prints,
for example: *"This project has no Browser configured, so `/browser-test` is unavailable. Run
`/configure-project` to enable it."* — and does not call its tools.

Orchestrators (`full-qa`, etc.) read §2 and skip whole phases: no Browser → skip UI/E2E/visual/a11y;
no DB → skip db-check and data-consistency; no GitHub/LocalRepos → skip code-review/pr-risk. Skipped
phases are stated explicitly in the verdict.
