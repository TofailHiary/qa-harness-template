---
name: test-data-manager
description: Use when a test needs specific data located, prepared, snapshotted, or restored safely in the target environment — find rich existing records for a scenario, create/modify disposable data under the Mutation Safety Gate with a verified restore, provision a fresh tenant or fixture set, or pick the right sample file class for an upload/import/parser test. Triggers include "find test data for X", "prepare a user with no orders", "I need an account with a zero score", "set up and then restore data for this test", "which fixture covers this input class", "is there a sample file for a scanned PDF".
argument-hint: "the data scenario needed (entities + states)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__filesystem__*", "Skill(qa-standards)", "Write"]
---

# Test Data Manager — Locate, Prepare, Snapshot, Restore

> **Capability gate:** This skill requires **DB**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no DB configured, so `/test-data-manager` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Get the right data for a test **without damaging shared data**. Default is locate-and-reuse; creation/modification is the exception, always under the gate. **A missing fixture is NEEDS PREP, never a coverage gap**, until every resource in "Data resources" below has been exhausted.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session: the **Mutation Safety Gate** governs every write; **Verdict Integrity** (operational vs structural blockers) governs what may be called BLOCKED; **Fresh vs Historical** means a remembered fixture is a lead to re-verify, never a fact.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "What data scenario do you need? Describe the entities and states (e.g. 'a Manager in account X whose users have 0 orders', 'an upload of an image-only PDF')." Do not guess.

---

## Environment policy — DEFAULT IS TEST. Read this before touching anything else.

**Every run happens on TEST unless the task explicitly says otherwise.** The resources below are NOT a menu to pick from. They are escalation paths with strict, narrow purposes:

| Environment | When it is allowed |
|---|---|
| **TEST** (`<test DB name: PROJECT-PROFILE.md §6>`) | **DEFAULT — use this.** All functional QA, all stories, all bugs. |
| **DEV** (`<dev DB name: PROJECT-PROFILE.md §6>`, if §6 lists one) | Contrast only, when a fixture does not exist on TEST. Label every row as Dev. |
| **PROD** (read-only; only if Prod-DB is `on`) | **ONLY to measure the real-world prevalence / impact of a defect ALREADY reproduced on TEST.** Never for routine testing, never to find bugs, never as a first stop. **NEVER mutate prod — no INSERT / UPDATE / DELETE / DDL, ever, for any reason.** |
| **Local mutable replica** (if §6 lists one) | Sandbox for fixture seeding, destructive-action tests, scale/volume tests. Scope rules below. |

Do not read this section as "test on prod". The only sentence that authorises prod is: *a defect is already reproduced on TEST, and you need to know how many real users it affects.* That is it. An observation on any non-TEST environment is evidence for that environment only (qa-standards -> Evidence provenance).

### Operational vs structural blockers
A closed port, a stopped container, an expired token, an untried credential is an **operational** blocker — start / renew it rather than recording a false coverage gap. But start the *right* one for the environment you are allowed to be in. Record a gap only when the resource itself is unavailable AND cannot be started — and say what would unblock it (BLOCKED always carries an unblock condition; qa-standards -> Verdict Contract).

**Probe first** (hosts and ports from §6):
```bash
for p in <port list: PROJECT-PROFILE.md §6>; do (echo > /dev/tcp/<DB host: PROJECT-PROFILE.md §6>/$p) 2>/dev/null && echo "$p OPEN" || echo "$p closed"; done
```

---

## Data resources — exhaust these before recording a coverage gap

| Resource | How to reach it | Use it for |
|---|---|---|
| **TEST / DEV DB** | `mcp__mcp_server_mysql__mysql_query` — `<test DB name: PROJECT-PROFILE.md §6>` on `<DB host: PROJECT-PROFILE.md §6>` (DB tool: §6; `/configure-project` rebinds the id for other engines) | Day-to-day QA: locate, prepare, snapshot, restore |
| **Read-only PROD** | the prod read-only access described in `PROJECT-PROFILE.md §6` (`mcp__mcp_server_mysql_prod__mysql_query`, or a self-contained read-only query runner) — only if Prod-DB is `on` | Prevalence / impact numbers, prod-shaped data scans, confirming a prod repro. **NEVER mutate.** |
| **Mutable local replica** | container / host / port and start command from `PROJECT-PROFILE.md §6` (or §13), if the project has one | **Mutable, prod scale:** seeding fixtures TEST lacks, destructive-action tests, mutating e2e suites, scale / pagination-at-volume |
| **Platform-made fixtures** | the admin panel (`<admin URL: PROJECT-PROFILE.md §5>`), typed tools if `PROJECT-PROFILE.md §14` lists a project MCP server, or the public API via `mcp__http-client__*` as the role that will run the test | Creating entities the way the product does — every side table, join row, counter and identity-provider record filled; role-scoped lookups with no SQL |
| **Token minting** | the auth method in `PROJECT-PROFILE.md §7` — recipes in `Skill(login)` Step 4 | Role-scoped API lookups and platform-made fixtures. `mcp__http-client__*` **persists default headers** — clear with `set_default_headers({}, merge:false)` before minting or a stale `Authorization` header 401s the token request. Tokens are short-lived — re-mint, don't debug a 401 |
| **Admin fixtures / test tenants** | the test tenants and role accounts in `PROJECT-PROFILE.md §7` | Owned, disposable records you may mutate under the gate |
| **Sample-file library** | the sample-file library in `PROJECT-PROFILE.md §13`, if any | Upload / import / parser tests — one row per input class in the registry below. **Add every new sample there, never to the repo root or `qa-evidence/`** |

**Rules**
- Fixtures made through the platform beat hand-written INSERTs: the product fills the side tables you would forget.
- If a fixture does not exist, **seed it** (on the mutable replica if there is one, else on TEST under the gate) rather than declaring the case untestable.
- Before recording a fixture as "not available": check the registry below, then memory (as a lead — re-verify it still exists and still has the state), then the replica, then seed.
- **Replica scope** *(if §6 lists one)*: it is a point-in-time copy — anything merged after its snapshot date is absent, so it is never a substitute for TEST when validating a recent change; pipeline-populated tables may be empty in it; it drifts — re-snapshot before answering "what does prod look like now"; a replica provisioned for one epic is **not** a standing resource — confirm with the user before reusing it for a different story; if there is a read-only baseline replica and a writable one, **seed only on the writable one**; read its root password from the container environment at run time — never write it into a skill, a memory file or evidence.

---

## Step 1: Define the data shape
From the scenario, list the entities, relationships and states required (roles, counts, null / zero / empty, draft / published, active / deleted, tenant). Read the relevant models (`<models path: PROJECT-PROFILE.md §9>`), `PROJECT-PROFILE.md §10` and `.claude/rules/db-gotchas.md` — where roles live, which tables have a tenant key, and **which soft-delete mechanism each table uses** (`deleted_at` vs a `status` enum vs hard delete — run the mechanism query from `/db-check` before writing any "active rows" predicate).

## Step 2: LOCATE first (preferred — no mutation)
Query `mcp__mcp_server_mysql__mysql_query` (TEST) for existing records matching the shape, with their relationships intact. Output the concrete ids / identifiers so the test can use them directly. Alternatively ask the platform as the role that will run the test (typed tools from §14, or the API with a minted token) — live, role-scoped, no SQL. To check whether a prod-like record exists, use the read-only prod access (§6) and label it. **If suitable data exists, stop here and return it** — never create what you can reuse.

## Step 3: PREPARE (only if nothing suitable exists) — under the Mutation Safety Gate
Prefer platform-made fixtures (admin panel / typed tools / API) over raw INSERTs; record the returned ids in the snapshot. Then:
1. Confirm the change is in scope and the minimal way to reach the state.
2. Prefer a **disposable, owned** record (your test tenant / test account from §7) over touching shared data. Never prepare data in prod.
3. **SELECT + log the full original state** of every row you will touch — side tables included.
4. Write the **snapshot** (the rollback source-of-record) to `qa-evidence/<scenario-slug>/snapshot.json` via `mcp__filesystem__write_file`.
5. Build the rollback plan (re-INSERT / UPDATE statements in FK-safe order) BEFORE mutating.
6. Make the minimal change. `UPDATE` / `DELETE` need a `WHERE`; never hard-DELETE — use the table's own mechanism (status / `deleted_at`).
7. **A 200 from an admin form or an API proves nothing.** SELECT the rows (and the side tables) after every step; stop at the first mismatch.

*(illustrative)* **Re-creating endpoints:** some "save" / "next" endpoints RE-CREATE child rows and re-point the join rows at the new ids on every call. Snapshot the id list before the first call; restore by re-pointing the join rows, then delete the new rows in FK order (grandchild -> child -> parent).

## Step 4: SNAPSHOT ledger
Record every change:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

## Step 5: RESTORE + verify
After the test, restore from the snapshot, then **SELECT again** to confirm the row matches the original field-for-field. Mark "Restored? = yes (verified)". If a clean restore is impossible -> **STOP and ask the user before mutating** (or, if already mutated, surface it immediately).

## Step 6: Return
Output the data the test should use (ids / identifiers / states / environment) OR confirmation that prepared data was created and restored. Hand the ids to the calling skill's Scope Lock "Test Data".

---

## Provisioning a fresh tenant / fixture set

When the scenario needs a whole new tenant, account tree or fixture set rather than a row:

1. **Interview first — never invent parameters.** Tenant name, tier / plan, region, settings and feature flags, roles and how many accounts per role, content to attach, the user's naming convention. Write the list down and get it confirmed before creating anything.
2. **Claim an identifier block before creating.** Agree a name prefix and identifier pattern (e.g. `qa-<ticket>-<n>`, `qa-<ticket>-<n>@example.com`) so the set is recognisable and deletable, and **record the baseline `SELECT MAX(id) FROM <table>` for every table you will insert into** — that is the restore boundary.
3. **Document ordering constraints before step one runs.** The product's creation order (tenant -> settings -> roles / accounts -> memberships -> content -> assignments) and which steps must precede others (settings before users so defaults apply; parent before membership). A step done out of order usually produces rows that look fine and behave wrong.
4. **Verify every provisioning step in the DB before the next.** A 200 from an admin form proves nothing: SELECT the new rows and their side tables (membership rows, identity-provider sync, counters, default settings) after each step; stop at the first mismatch and report it — it is usually a finding in its own right.
5. **Record the set** (ids, names, environment, created date, the MAX(id) baselines, the order used) in the snapshot and in memory. The restore is everything above the baseline, removed in FK order — or status-flagged where the table forbids hard delete.

---

## INPUT-CLASS FIXTURE REGISTRY — a fixture per equivalence class, not per flow

*(illustrative)* Three QA runs passed a PDF-import flow with one file and missed a parser defect that only an image-only scan triggers. **Test the CLASS. Vary the file CLASS, not just the file.** Never test a parser, importer or uploader with one class. Keep this table in memory (`reference_fixture_registry.md`) or `PROJECT-PROFILE.md §13`; add a row whenever a new class appears, and mark a class INFERRED or UNKNOWN until it has been inspected and run.

| Input surface | Input class | Sample file / fixture | Where it lives | Last verified | What it exercises |
|---|---|---|---|---|---|
| PDF import | digital text-layer | `<file>` | sample-file library (§13) | `<date>` | text extraction returns text for every region |
| PDF import | scanned, image-only | `<file>` | sample-file library (§13) | `<date>` | the OCR / empty-text path |
| PDF import | mixed (text + image pages) | `<file>` | | | per-page branch switching |
| PDF import | rotated pages | `<file>` | | | orientation handling |
| PDF import | multi-column layout | `<file>` | | | reading order |
| PDF import | 0-byte / corrupt / wrong extension / password-protected / oversize | `<files>` | | | validation + error path, no masked error |
| CSV / roster import | header variants, BOM / encoding, empty file, one row, max rows, duplicate natural key across rows, one email shared by two different people | `<files>` | | | parser branches + merge / collision logic |
| Image upload | each allowed type x size boundary; SVG with script | `<files>` | | | type + size validation, sanitisation |
| Video / binary upload | each allowed type at and above the size limit | `<files>` | | | size-limit class |
| Enum / mode values at 0% in prod | `<value>` | NEEDS PREP (seed it) | | | never-executed branches |
| Partition N = 1 vs N > 1 (templates, sittings, memberships) | `<fixture>` | | | | the "there is exactly one" cardinality assumption |
| Mode A vs mode B of the same feature (inline vs separate, online vs offline) | `<fixture>` | | | | the branch the historical fixtures never took |

**Rule:** before recording a fixture as "not available", check this table, then the mutable replica, then seed. A missing fixture is **NEEDS PREP**, never a coverage gap. A class at 0 rows in production is still a class — it is exactly where the first production row will fail (`/latent-pattern-sweep`).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Naming `reference_fixture_<slug>.md` for reusable fixtures, `project_<slug>.md` for a run; frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the entity / scenario / fixture; UPDATE the existing entry (and the fixture registry) instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer: `- [<title>](<file>.md) — <hook>`.
4. **Content:** the scenario, environment, the located / prepared ids and their state, the MAX(id) baselines, confirmation of restoration (verified), new registry rows, any resource quirk learned (port, start command, replica snapshot date) — **never a password, token or root secret**.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
