# Project Profile

> Single source of truth for this project's QA harness. The bootstrap (`/configure-project`)
> fills this in. Every skill reads from here. Edit anytime, then re-run `/configure-project`
> to regenerate the plumbing (hooks / MCP / settings). Imported automatically by `CLAUDE.md`.
>
> See `PROJECT-PROFILE.example.md` for a fully filled-in example.

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

## §3 Repositories
| Repo path | Description | Default branch |
|---|---|---|
|  |  |  |

## §4 Tech stack
- **DB engine:** (MySQL / Postgres / Mongo / SQLite / none)
- **Backend:** (language + framework)
- **Frontend:** (framework / none)
- **ORM:**
- **Auth method:** (Firebase / JWT / session / OAuth / none)
- **Cloud / infra:**

## §5 Environments & URLs
| Surface | Test | Dev | Prod (read-only) |
|---|---|---|---|
| Main app |  |  |  |
| Admin |  |  |  |
| Backend API |  |  |  |
| Report API |  |  |  |

## §6 DB connections
| Env | Host | Port | DB name | User | Password env var | MCP tool | Writes allowed |
|---|---|---|---|---|---|---|---|
| test |  |  |  |  | ${QA_DB_PASS} | mcp__mcp_server_mysql__mysql_query | insert/update/delete? |
| prod |  |  |  |  | ${PROD_DB_PASS} | mcp__mcp_server_mysql_prod__mysql_query | NONE (read-only) |

## §7 Auth & test accounts
- **Login method:**
- **SSO path:**

| Role | Username / email | Password env var |
|---|---|---|
|  |  |  |

## §8 Roles
- (list the project's user roles, e.g. Admin / User / Guest)

## §9 Key code paths
- **Frontend API layer:**
- **Frontend pages / components:**
- **Backend routes:**
- **Backend models:**
- **Auth middleware:**
- **Admin controllers:**

## §10 Key tables & gotchas
- **Important tables:**
- **Relationships / FKs:**
- **Schema gotchas (soft-delete columns, nullable surprises, enum values):**

## §11 External / async consumers (blast radius)
- (S3 / SQS / Lambda / cron / email / webhooks that read or write the data under test)

## §12 Evidence & memory paths
- **Evidence folder:** `${PROJECT_ROOT}/qa-evidence`
- **Memory folder:** (Claude Code auto-memory dir for this project)
- **Protected source repos (write-blocked):** (folder names under the project root)

## §13 Docs
- (reference docs to read on-demand)
