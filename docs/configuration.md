# Configuration

Everything project-specific lives in **`.claude/PROJECT-PROFILE.md`**; two generated files carry the
machine-readable parts: **`.mcp.json`** (MCP servers + secrets, git-ignored) and
**`.claude/hooks/harness-config.json`** (hook policy). `/configure-project` writes all three. This page
lists every variable with a safe example value. The fully worked fictional example is
`.claude/PROJECT-PROFILE.example.md`.

## PROJECT-PROFILE.md

| Section | What goes there | Safe example |
|---|---|---|
| §1 Identity | name, one-liner, domain | `Acme App — multi-tenant B2B SaaS` |
| §2 Capability Map | `on`/`off` per capability: DB, API, Browser, Admin, Reporting, GitHub, LocalRepos, Postman, Prod-DB, Jira, SSH, Demo | `DB: on`, `Prod-DB: off` |
| §3 Repositories | folder, description, default branch (branch names are case-sensitive) | `acme-api/ · Node/Express backend · develop` |
| §4 Tech stack | DB engine, backend, frontend (+ UI library), ORM, auth method, cloud | `MySQL 8 · Express · React+MUI · Sequelize · JWT · AWS` |
| §5 Environments & URLs | per surface: Test (default), Dev, Prod (read-only) | `https://test.acme.example.com` |
| §6 DB connections | host, port, DB name, user, **password env var**, MCP tool id, writes allowed; prod access path; optional local replica | `${QA_DB_PASS}`, `mcp__mcp_server_mysql__mysql_query` |
| §7 Auth & test accounts | login method, SSO/impersonation path, one row per role with the **password env var** | `admin@acme.example.com · ${ADMIN_PASS}` |
| §8 Roles | the roles and where they live in the schema | `Admin, Manager, User, Guest (user → user_account → role)` |
| §9 Key code paths | FE API layer, pages, route constants, BE routes + mount file, models, auth middleware, admin controllers, workers | `acme-api/routes/`, `acme-api/workers/` |
| §10 Key tables & gotchas | tables, FKs, soft-delete mechanism per table, column comments that carry contracts, active-row predicates | `order has NO deleted_at; account uses status enum` |
| §11 Async consumers | queues, workers, cron, email, webhooks; terminal writer per chain | `order placed → SQS → workers/invoice.js → invoice` |
| §12 Evidence & memory | evidence folder, memory folder (blank = derived), protected repos, **owned repos** | `protected: acme-web, acme-api · owned: acme-qa-tools` |
| §13 Docs | reference docs, sample-file library for upload/parser tests, API collection ids | `qa-fixtures/ (digital PDF, scanned PDF, 0-byte PDF)` |
| §14 Project MCP (optional) | server name, session/status tools, typed tools to prefer, raw fallback | `mcp__acme__list_orders` |
| §15 Issue tracker | tracker, project key, **ticket id pattern**, never-touch projects, issue types, labels, assignment rule, transitions, attachment limits | `Jira · APP · APP-\d+ · pass → Ready for release` |
| §16 QA policy | verdict policy (strict-binary default), sub-agents allowed/disabled, execute every case, completion gate advisory/enforced, perf thresholds, report language, who sends customer messages | `strict-binary · sub-agents allowed · gate advisory` |
| §17 Plugins | `superpowers`, `mattpocock-skills` installed or not | `not installed` |
| §18 Demo defaults | voice, rate, language, badge text, demo folder | `en-US-JennyNeural · -3% · "DEMO · TEST DATA"` |

Rules: never write a password, token or API key into the profile — name the environment variable.
Identifiers (emails, ids) are fine. Prod is never a functional test target.

## .mcp.json (generated from .mcp.json.template)

| Server | Capability | Secrets (env vars) | Notes |
|---|---|---|---|
| `filesystem` | always | — | evidence folder + `.claude` as allowed directories |
| `http-client` | API | — | bundled, dependency-free (`.claude/mcp-servers/http-client/server.js`) |
| `playwright` | Browser | — | `npx -y @playwright/mcp@latest` (Windows wraps it in `cmd /c`) |
| `chrome-devtools` | Browser | — | `npx -y chrome-devtools-mcp@latest` |
| `mcp_server_mysql` | DB | `QA_DB_HOST/PORT/USER/PASS/NAME` | write flags ship `false`; swap for your engine's MCP via `/configure-project` |
| `mcp_server_mysql_prod` | Prod-DB | `PROD_DB_*` | read-only, disabled by default; usually behind a tunnel |
| `postman-api-mcp` | Postman | `POSTMAN_API_KEY` | disabled by default |
| *(yours)* | §14 | as needed | added by `/configure-project` with your approval |

`/configure-project` substitutes `${PROJECT_ROOT}`, disables servers whose capability is `off`, and either
writes the secret values into the git-ignored file or leaves `${ENV_VAR}` placeholders for you to export.

## harness-config.json (hook policy)

```json
{
  "memory_root": "",
  "evidence_root": "qa-evidence",
  "allowed_write_globs": [".claude/PROJECT-PROFILE.md", ".claude/settings.json", ".claude/hooks/harness-config.json", ".mcp.json"],
  "protected_repos": ["acme-web", "acme-api"],
  "owned_repos": ["acme-qa-tools"],
  "gate": { "enforce": false, "ticket_id_pattern": "\\bAPP-\\d+\\b", "extra_concession_phrases": [], "extra_example_markers": [], "log": true }
}
```

| Key | Meaning | Default |
|---|---|---|
| `memory_root` | auto-memory folder; blank = derived from `CLAUDE_PROJECT_DIR` the way Claude Code encodes it | `""` |
| `evidence_root` | evidence folder (relative to the project root or absolute) | `qa-evidence` |
| `allowed_write_globs` | the only non-memory paths the Write/Edit tools may touch (the harness's own config) | the four files above |
| `protected_repos` | folder names of product repos — no writes of any kind, no git mutations | `[]` |
| `owned_repos` | folder names of the team's own tooling — edits, commits, pushes and PRs allowed there, only when no protected repo is in reach | `[]` |
| `gate.enforce` | completion gate blocks (true) or only advises (false); `QA_GATE_ENFORCE=1` in `settings.json → env` also enforces | `false` |
| `gate.ticket_id_pattern` | regex the gate uses to spot ticket references | `\b[A-Z][A-Z0-9]+-\d+\b` |
| `gate.extra_concession_phrases` / `extra_example_markers` | add phrases in another language | `[]` |

With `protected_repos` empty the Bash/PowerShell guards still refuse mutating git/npm everywhere but do
not path-block writes; the template ships that way so it can be maintained in place.

## settings.json

Permissions (read-only allow-list, a deny-list for tracker/Postman/SSH/GitHub write tools), the hook
wiring (PreToolUse guards, PostToolUse screenshot copy, SessionStart memory rotation, Stop/SubagentStop
completion gate) and `env.QA_GATE_ENFORCE` (`"0"` by default). The installer preserves an existing
`settings.json` and writes `settings.json.new` next to it.

## Environment variables

| Variable | Used by | Example |
|---|---|---|
| `QA_DB_HOST`, `QA_DB_PORT`, `QA_DB_USER`, `QA_DB_PASS`, `QA_DB_NAME` | `mcp_server_mysql` | `db.test.acme.example.com`, `3306`, `qa_user`, `…`, `acme_test` |
| `PROD_DB_*` | `mcp_server_mysql_prod` | — |
| `POSTMAN_API_KEY` | `postman-api-mcp` | — |
| `ADMIN_PASS`, `MANAGER_PASS`, `USER_PASS` (names you choose in §7) | `login`, `test-together/scripts/api_peek.js` (`--token-env` / `${VAR}` in `--login-body`), `demo-creator` flows (`process.env.DEMO_PASS`) | — |
| `CLAUDE_PROJECT_DIR` | set by Claude Code; the hooks resolve the project root from it | — |
| `QA_GATE_ENFORCE` | completion gate mode | `0` |
