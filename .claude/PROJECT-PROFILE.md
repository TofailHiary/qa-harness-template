# Project Profile

> Single source of truth for this project's QA harness. The bootstrap (`/configure-project`)
> fills this in. Every skill reads from here. Edit anytime, then re-run `/configure-project`
> to regenerate the plumbing (hooks / MCP / settings). Imported automatically by `CLAUDE.md`.
>
> See `PROJECT-PROFILE.example.md` for a fully filled-in example. **Never write a password, token
> or API key into this file** — name the environment variable instead.

## §1 Identity
- **Project name:**
- **One-line description:**
- **Domain:**

## §2 Capability Map
> `on` = configured & reachable. `off` = skip dependent skills (see `docs/capability-matrix.md`).
- DB: off
- API: off
- Browser: off
- Admin: off
- Reporting: off
- GitHub: off
- LocalRepos: off
- Postman: off
- Prod-DB: off
- Jira: off
- SSH: off
- Demo: off   (demo-creator: Node + Playwright + ffmpeg + a TTS engine; `node .claude/skills/demo-creator/scripts/setup.js --check`)

## §3 Repositories
| Repo path | Description | Default branch |
|---|---|---|
|  |  |  |

(Mark any repo that is the team's OWN tooling, not a QA target, in §12 "Owned repos".)

## §4 Tech stack
- **DB engine:** (MySQL / MariaDB / Postgres / Mongo / SQLite / none)
- **Backend:** (language + framework)
- **Frontend:** (framework + UI library / none)
- **ORM:**
- **Auth method:** (JWT / session / OAuth / hosted identity provider such as Firebase / SSO / none)
- **Cloud / infra:**

## §5 Environments & URLs
| Surface | Test | Dev | Prod (read-only) |
|---|---|---|---|
| Main app |  |  |  |
| Admin |  |  |  |
| Backend API |  |  |  |
| Report API |  |  |  |

- **Default environment:** Test. Prod is never a functional test target.

## §6 DB connections
| Env | Host | Port | DB name | User | Password env var | MCP tool | Writes allowed |
|---|---|---|---|---|---|---|---|
| test |  |  |  |  | ${QA_DB_PASS} | mcp__mcp_server_mysql__mysql_query | insert/update/delete? |
| prod |  |  |  |  | ${PROD_DB_PASS} | mcp__mcp_server_mysql_prod__mysql_query | NONE (read-only) |

- **Prod access path (if Prod-DB is on):** (e.g. "SSH tunnel to the bastion on 127.0.0.1:<port>; bring it up with `<command>`" — commands only, never credentials)
- **Local replica (optional):** (a mutable copy for fixture seeding / destructive tests; host:port)

## §7 Auth & test accounts
- **Login method:**
- **SSO / impersonation path:**
- **Passwords are per account** — take them from the env vars below; never assume one shared password.

| Role | Username / email | Password env var |
|---|---|---|
|  |  |  |

## §8 Roles
- (list the project's user roles, e.g. Admin / Manager / User / Guest, and where roles live in the schema)

## §9 Key code paths
- **Frontend API layer:**
- **Frontend pages / components:**
- **Frontend route constants:**
- **Backend routes (and where they are mounted):**
- **Backend models:**
- **Auth middleware:**
- **Admin controllers:**
- **Workers / Lambdas / cron:**

## §10 Key tables & gotchas
- **Important tables:**
- **Relationships / FKs:**
- **Schema gotchas (soft-delete mechanism per table, nullable surprises, enum values, column comments that carry contracts):**
- **Active-row predicate per table:**

## §11 External / async consumers (blast radius)
- (S3 / queues / Lambda / cron / email / webhooks that read or write the data under test)
- **Terminal writers:** (for each async chain: enqueue → worker → the table it finally writes)

## §12 Evidence & memory paths
- **Evidence folder:** `${PROJECT_ROOT}/qa-evidence`
- **Memory folder:** (Claude Code auto-memory dir for this project; blank = derived by the hooks)
- **Protected source repos (write-blocked):** (folder names under the project root)
- **Owned repos (edits / commits / PRs allowed — the team's own tooling, never a QA target):** (folder names; leave empty if none)

## §13 Docs
- (reference docs to read on-demand)
- **Sample-file library (upload / import / parser fixtures):** (folder; see `test-data-manager` → INPUT-CLASS FIXTURE REGISTRY)
- **API contract collections (Postman workspace / collection ids):**

## §14 Project-specific MCP server / typed tools (optional)
- **Server name in `.mcp.json`:**
- **Session / status tools:**
- **Typed tools to prefer over raw HTTP:**
- **Raw fallback tool:**
- (leave empty if the project has no such server; skills then use `mcp__http-client__*`)

## §15 Issue tracker
- **Tracker:** (Jira via `mcp__claude_ai_Atlassian__*` / GitHub Issues / none)
- **Project key:**   · **Ticket id pattern:** (regex, e.g. `APP-\d+`; also set `gate.ticket_id_pattern` in `harness-config.json`)
- **Never touch:** (projects / queues QA must not write to)
- **Issue types:** (bug found while testing a story → ? ; standalone bug → ?)
- **Labels:**
- **Assignment rule:**
- **Transitions after QE:** (pass → ? ; fail → ? ; read the available transitions live each time)
- **Attachments:** (connector limitation, if any — e.g. "cannot upload files; list them in chat")

## §16 QA policy
- **Verdict policy:** strict-binary (default) | severity-weighted: (threshold text)
- **Sub-agents:** allowed (default) | disabled (everything runs in-session, including the verdict audit)
- **Execute every generated case:** yes (default) | (exceptions)
- **Completion gate:** advisory (default) | enforced (`QA_GATE_ENFORCE=1` in `.claude/settings.json → env`, or `gate.enforce` in `harness-config.json`)
- **Perf thresholds:** template defaults | (overrides)
- **Report language / style:**
- **Customer-facing messages:** (who sends them; QA drafts only)

## §17 Optional plugins
- `superpowers`: installed | not installed
- `mattpocock-skills`: installed | not installed
- (skills use the by-hand equivalent when a plugin is not installed)

## §18 Demo recording defaults (demo-creator)
- **Voice:** (e.g. en-US-JennyNeural)  · **Rate:**  · **Language:**
- **Badge text when recording on Prod or custom data:**
- **Demo folder:** `qa-evidence/<KEY>-<yyyymmdd>/demo/`
