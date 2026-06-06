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

## §3 Repositories
| Repo path | Description | Default branch |
|---|---|---|
| acme-web/ | React + Vite + TypeScript frontend | develop |
| acme-api/ | Node.js / Express / Sequelize backend | develop |
| acme-admin/ | Admin panel (PHP / Laravel) | develop |
| acme-reports/ | Reporting service | develop |

## §4 Tech stack
- **DB engine:** MySQL 8
- **Backend:** Node.js / Express.js
- **Frontend:** React + Vite + TypeScript
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

## §7 Auth & test accounts
- **Login method:** JWT — POST credentials to the login endpoint, capture the returned Bearer token; API tests send `Authorization: Bearer <token>`.
- **SSO path:** Admin panel → Accounts → find user → "Impersonate".

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
- **Backend routes:** acme-api/routes/
- **Backend models:** acme-api/models/
- **Auth middleware:** acme-api/middleware/auth.js
- **Admin controllers:** acme-admin/app/Http/Controllers/

## §10 Key tables & gotchas
- **Important tables:** user, account, user_account, role, product, order, order_item, subscription, invoice, audit_log
- **Relationships / FKs:** order.user_id → user.id; order_item.order_id → order.id; subscription.account_id → account.id; user_account.user_id → user.id
- **Schema gotchas:** `user` has NO `role_id` and NO `deleted_at` (roles live in `user_account`); `order` has NO `deleted_at`; soft-delete only on `account` and `subscription`; `audit_log` is append-only (no updates/deletes).

## §11 External / async consumers (blast radius)
- AWS S3 (file uploads), SQS (async email/order queue), Lambda (invoice generator, nightly report-aggregation cron), email notifications, `report_*` snapshot tables.

## §12 Evidence & memory paths
- **Evidence folder:** `${PROJECT_ROOT}/qa-evidence`
- **Memory folder:** `~/.claude/projects/<your-encoded-project-dir>/memory/`  (auto-derived by the hooks)
- **Protected source repos (write-blocked):** acme-web, acme-api, acme-admin, acme-reports

## §13 Docs
- ARCHITECTURE.md, docs/qa-guide.md, docs/data-model.md
