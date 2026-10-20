# Project Profile — EXAMPLE (a fictional project, "Acme App")

> A worked example showing how a real project fills in `PROJECT-PROFILE.md`. All values here are
> **fictional** (the `example.com` domain is reserved for docs). **Secrets are shown as `${ENV_VAR}`
> names, never literal values** — you supply real values when `/configure-project` asks, and it writes
> them into your git-ignored `.mcp.json`. Copy the blank `PROJECT-PROFILE.md` and fill it like this.

## §1 Identity
- **Project name:** Acme App
- **One-line description:** Multi-tenant B2B SaaS for managing accounts, orders, and subscriptions.
- **Domain:** Generic SaaS

## §2 Capability Map
- DB: on
- API: on
- Browser: on
- Admin: on
- Reporting: on
- GitHub: on
- LocalRepos: on
- Postman: on
- Prod-DB: off  (no read access from QA — left off)
- Jira: on
- SSH: off
- Demo: on  (node + ffmpeg + edge-tts present; `node .claude/skills/demo-creator/scripts/setup.js --check` printed READY)

## §3 Repositories
| Repo path | Description | Default branch |
|---|---|---|
| acme-web/ | React + Vite + TypeScript frontend | develop |
| acme-api/ | Node.js / Express / Sequelize backend | develop |
| acme-admin/ | Admin panel (PHP / Laravel) | develop |
| acme-reports/ | Reporting service | develop |
| acme-qa-tools/ | OUR OWN helper scripts — not a QA target; edits and commits allowed here | main |

## §4 Tech stack
- **DB engine:** MySQL 8
- **Backend:** Node.js / Express.js
- **Frontend:** React + Vite + TypeScript (MUI)
- **ORM:** Sequelize
- **Auth method:** JWT (email/password → Bearer token)
- **Cloud / infra:** AWS (S3, SQS, Lambda)

## §5 Environments & URLs
| Surface | Test | Dev | Prod (read-only) |
|---|---|---|---|
| Main app | https://test.acme.example.com | https://dev.acme.example.com | https://app.acme.example.com |
| Admin | https://admin.test.acme.example.com |  | https://admin.acme.example.com |
| Backend API | https://api.test.acme.example.com |  |  |
| Report API | https://reports.test.acme.example.com (header `Accept-Version: 1.0.0`) |  |  |

## §6 DB connections
| Env | Host | Port | DB name | User | Password env var | MCP tool | Writes allowed |
|---|---|---|---|---|---|---|---|
| test | db.test.acme.example.com | 3306 | acme_test | qa_user | ${QA_DB_PASS} | mcp__mcp_server_mysql__mysql_query | insert+update+delete (test only) |
| prod | (off — no QA access) |  |  |  | ${PROD_DB_PASS} | mcp__mcp_server_mysql_prod__mysql_query | NONE (read-only) |

- **Prod access path (when Prod-DB is on):** e.g. an SSH tunnel to a bastion, or a read-only replica; document the command the QA engineer runs to bring it up, never credentials.

## §7 Auth & test accounts
- **Login method:** JWT — POST credentials to the login endpoint, capture the returned Bearer token; API tests send `Authorization: Bearer <token>`.
- **SSO path:** Admin panel → Accounts → find user → "Impersonate".
- **Passwords are per account:** take them from the env vars below; never assume one shared password.

| Role | Username / email | Password env var |
|---|---|---|
| Admin | admin@acme.example.com | ${ADMIN_PASS} |
| Manager | manager1@acme.example.com | ${MANAGER_PASS} |
| User | user1@acme.example.com | ${USER_PASS} |

## §8 Roles
- Admin, Manager, User, Guest
- (roles resolved via `user` → `user_account` → `role`)

## §9 Key code paths
- **Frontend API layer:** acme-web/src/libs/api/, acme-web/src/libs/helpers/api.helper.ts
- **Frontend pages / components:** acme-web/src/pages/, acme-web/src/components/
- **Frontend route constants:** acme-web/src/routes.ts
- **Backend routes:** acme-api/routes/ (mounted in acme-api/server.js)
- **Backend models:** acme-api/models/
- **Auth middleware:** acme-api/middleware/auth.js
- **Admin controllers:** acme-admin/app/Http/Controllers/
- **Workers / Lambdas:** acme-api/workers/ (invoice generator, nightly aggregation)

## §10 Key tables & gotchas
- **Important tables:** user, account, user_account, role, product, order, order_item, subscription, invoice, audit_log
- **Relationships / FKs:** order.user_id → user.id; order_item.order_id → order.id; subscription.account_id → account.id; user_account.user_id → user.id
- **Schema gotchas:** `user` has NO `role_id` and NO `deleted_at` (roles live in `user_account`); `order` has NO `deleted_at`; soft-delete only on `account` and `subscription`; `audit_log` is append-only (no updates/deletes); `report_*` columns carry their aggregation rule in `COLUMN_COMMENT` — read it before judging a value.
- **Active-row predicate:** `status = 'active'` on account/subscription; no predicate on user.

## §11 External / async consumers (blast radius)
- AWS S3 (file uploads), SQS (async email/order queue), Lambda (invoice generator, nightly report-aggregation cron), email notifications, `report_*` snapshot tables.
- **Terminal writers:** order placed → SQS → `workers/invoice.js` writes `invoice`; nightly cron → `report_daily_*`.

## §12 Evidence & memory paths
- **Evidence folder:** `${PROJECT_ROOT}/qa-evidence`
- **Memory folder:** `~/.claude/projects/<your-encoded-project-dir>/memory/`  (auto-derived by the hooks)
- **Protected source repos (write-blocked):** acme-web, acme-api, acme-admin, acme-reports
- **Owned repos (edits/commits allowed):** acme-qa-tools

## §13 Docs
- ARCHITECTURE.md, docs/qa-guide.md, docs/data-model.md
- **Sample-file library (upload / import / parser fixtures):** `qa-fixtures/` (digital PDF, scanned PDF, 0-byte PDF, CSV with BOM, 2 images)

## §14 Project-specific MCP server / typed tools (optional)
- **Server name in `.mcp.json`:** acme (command: `node acme-qa-tools/mcp/dist/index.js`)
- **Session / status tools:** `mcp__acme__session_status`, `mcp__acme__whoami`
- **Typed tools to prefer over raw HTTP:** `mcp__acme__list_orders`, `mcp__acme__create_order_draft`, `mcp__acme__admin_create_user` (each acts as the profile role you pass)
- **Raw fallback:** `mcp__acme__raw_request`, then `mcp__http-client__*`
- (leave this section empty if the project has no such server)

## §15 Issue tracker
- **Tracker:** Jira (via the `mcp__claude_ai_Atlassian__*` connector) — capability `Jira: on`
- **Project key:** APP (board "Acme App")  · **Ticket id pattern:** `APP-\d+`
- **Never touch:** tickets in project INTAKE (intake queue) — report, do not act
- **Issue type for bugs found while testing a story:** Sub-bug under the story (match the story's fixVersion and labels); standalone bugs: Bug
- **Labels:** `qa-harness`, plus the feature label of the story
- **Assignment rule:** FE → the frontend lead; BE/worker → the backend lead; bugs found while QA-ing a story → that story's assignee; ask once when unsure
- **Transitions after QE:** pass → "Ready for release" (read the available transitions live each time); fail → "Reopen"; never park a failed ticket in "To Do"
- **Attachments:** the connector cannot upload files — list "Files to upload manually" in chat only

## §16 QA policy
- **Verdict policy:** strict-binary (GO = 0 confirmed bugs; NO-GO = 1+ at any severity; PARTIAL = hard blocker)
- **Sub-agents:** allowed (verdict audit by `qa-verdict-auditor` in a fresh context)
- **Execute every generated case:** yes (priority only orders the work)
- **Completion gate:** advisory (set `QA_GATE_ENFORCE=1` in `.claude/settings.json → env` to block)
- **Perf thresholds:** template defaults (page load <3s / API P95 <500ms / payload <500KB)
- **Report language / style:** English, short sentences, explain a term the first time it appears
- **Customer-facing messages:** drafted by QA, sent by the manager

## §17 Optional plugins
- `superpowers` (claude-plugins-official): installed — used per qa-standards → "Plugins & escalation"
- `mattpocock-skills` (claude-plugins-official): installed — `grilling` and `diagnosing-bugs` Phases 1–4 only
- (write "not installed" to make every skill use its by-hand equivalent)

## §18 Demo recording defaults (demo-creator)
- **Voice:** en-US-JennyNeural, rate -3%  · **Language:** en
- **Badge on every frame when recording on Prod or custom data:** "DEMO · TEST DATA"
- **Demo folder:** `qa-evidence/<KEY>-<yyyymmdd>/demo/`
