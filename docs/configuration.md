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
| `playwright` | Browser | — | `@playwright/mcp@0.0.83` |
| `chrome-devtools` | Browser | — | `chrome-devtools-mcp@1.12.0` |
| `mcp_server_mysql` | DB | `QA_DB_HOST/PORT/USER/PASS/NAME` | write flags ship `false`; swap for your engine's MCP via `/configure-project` |
| `mcp_server_mysql_prod` | Prod-DB | `PROD_DB_*` | read-only, disabled by default; usually behind a tunnel |
| `postman-api-mcp` | Postman | `POSTMAN_API_KEY` | disabled by default |
| *(yours)* | §14 | as needed | added by `/configure-project` with your approval |

Every package is pinned; each server's `_tested` field says whether that version was exercised with the
template (`docs/upgrading.md` -> Bumping pinned MCP versions). Never copy the template by hand:
`python .claude/scripts/render_mcp.py` substitutes `${PROJECT_ROOT}`, disables servers whose capability is
`off`, wraps `npx` in `cmd /c` on Windows only, keeps servers it does not know (a §14 server, a Postgres
server), and leaves secrets as `${ENV_VAR}` placeholders, printing the export lines (names, never values).
`--add-server name='<json>'` adds a server the template lacks; `--dry-run` shows the result without writing.
`Read(.mcp.json)` is denied in `settings.json`, so a session never prints the file.

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

**Content check.** `block-writes.py` reads the new content of every Write / Edit / MultiEdit of this file.
Tightening always goes through (add a protected repo, drop an owned repo, narrow the allow-globs). Loosening
is blocked unless a human started Claude Code with `QA_HARNESS_ADMIN=1`: removing a protected repo, adding
an owned repo, widening `allowed_write_globs`, moving `memory_root` outside `~/.claude`, moving
`evidence_root` to the project root / outside it / into a repo, switching an enforced gate off, or writing
something that is not a JSON object. Shell writes to the file are refused outright (guard surface).

## settings.json

Permissions (read-only allow-list, a deny-list for tracker/Postman/SSH/GitHub write tools), the hook
wiring (PreToolUse guards, PostToolUse screenshot copy, SessionStart memory rotation, Stop/SubagentStop
completion gate) and `env.QA_GATE_ENFORCE` (`"0"` by default). The installer preserves an existing
`settings.json` and writes `settings.json.new` next to it.

Every Python hook is launched as `sh "$CLAUDE_PROJECT_DIR/.claude/hooks/run-hook.sh" <script>.py`. The
launcher tries `python3`, `python`, `py -3`, skips broken names (a store stub, Python 2) and blocks the tool
call when no Python 3 works or the guard crashes (Stop hooks pass `--fail-open`, so the advisory gate can
never trap a session). The file is content-checked like `harness-config.json`: dropping or re-pointing a guard
hook, `disableAllHooks`, removing a deny rule, switching `QA_GATE_ENFORCE` off or adding `QA_HARNESS_ADMIN`
needs a human.

## Environment variables

| Variable | Used by | Example |
|---|---|---|
| `QA_DB_HOST`, `QA_DB_PORT`, `QA_DB_USER`, `QA_DB_PASS`, `QA_DB_NAME` | `mcp_server_mysql` | `db.test.acme.example.com`, `3306`, `qa_user`, `…`, `acme_test` |
| `PROD_DB_*` | `mcp_server_mysql_prod` | — |
| `POSTMAN_API_KEY` | `postman-api-mcp` | — |
| `ADMIN_PASS`, `MANAGER_PASS`, `USER_PASS` (names you choose in §7) | `login`, `test-together/scripts/api_peek.js` (`--token-env` / `${VAR}` in `--login-body`), `demo-creator` flows (`process.env.DEMO_PASS`) | — |
| `CLAUDE_PROJECT_DIR` | set by Claude Code; the hooks resolve the project root from it | — |
| `QA_GATE_ENFORCE` | completion gate mode | `0` |
| `QA_HARNESS_ADMIN` | set by a HUMAN before starting Claude Code (never in `settings.json`): allows that one session to loosen the guard config and write the guard surface, for hook maintenance | unset |
| `QA_HOOK_PYTHONS` | interpreter names `run-hook.sh` tries, space-separated | `python3 python py` |
| `QA_CLAUDE_FLAGS` | extra `claude` flags for `.claude/scripts/ci-run-qa.sh` / `.ps1` | — |

## tool-bindings.json

`.claude/tool-bindings.json` records which MCP tool ids the skills and agents call for the database
(`db`) and the read-only production database (`prod_db`), plus the history of changes. Change it only with
`python .claude/scripts/rebind.py --db <id> [--prod-db <id>]`; `--check` lists any file still naming an
unbound id. `scripts/install.py` re-applies it after every install, so an upgrade never reverts it.

## The run record (qa-evidence/<run-folder>/run.json)

Orchestrated runs keep one machine-readable record next to their attachments: scope, the code-derived
matrix, the register, the ledger, findings, phases, a checkpoint and the verdict. The shape and rules are in
`.claude/skills/qa-standards/references/run-record.md`; `verdict_check.py` recomputes `N of M` and the run
verdict, resolves every evidence id to a file and writes the auditor's `package.md`. A run whose record has a
`checkpoint.next_step` is resumed from there.
