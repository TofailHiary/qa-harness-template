---
name: test-data-manager
description: Use when a test needs specific data located, prepared, snapshotted, or restored safely in the target environment — find rich existing records for a scenario, or create/modify disposable data under the Mutation Safety Gate with a verified restore. Triggers include "find test data for X", "prepare a user with no orders", "I need an account with a zero score", "set up and then restore data for this test".
argument-hint: "the data scenario needed (entities + states)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__filesystem__*", "Skill(qa-standards)"]
---

# Test Data Manager — Locate, Prepare, Snapshot, Restore

> **Capability gate:** This skill requires **DB**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no DB configured, so `/test-data-manager` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Get the right data for a test **without damaging shared data**. Default is locate-and-reuse; creation/modification is the exception, always under the gate.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; the **Mutation Safety Gate** governs every write.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "What data scenario do you need? Describe the entities and states (e.g. 'a Manager in account X with users who have 0 orders')." Do not guess.

---

## Step 1: Define the data shape
From the scenario, list the entities, relationships, and states required (roles, counts, null/zero/empty, draft/published, active/deleted). Read the relevant models (`<backend repo: PROJECT-PROFILE.md §3/§9>/models/`) and `.claude/rules/db-gotchas.md` (roles live in `user_account`; which tables have `deleted_at`).

## Step 2: LOCATE first (preferred — no mutation)
Query `mcp__mcp_server_mysql__mysql_query` (test/dev DB) for existing records matching the shape, with their relationships intact. Output the concrete IDs/emails so the test can use them directly. To check whether a prod-like record exists, query `mcp__mcp_server_mysql_prod__mysql_query` (read-only). **If suitable data exists, stop here and return it** — never create what you can reuse.

## Step 3: PREPARE (only if nothing suitable exists) — under the Mutation Safety Gate
1. Confirm the change is in scope and the minimal way to reach the state.
2. Prefer a **disposable, owned** record (your test account) over touching shared data. Never prepare data in prod.
3. **SELECT + log the full original state** of every row you will touch.
4. Write the **snapshot** (the rollback source-of-record) to `qa-evidence/<scenario-slug>/snapshot.json` via `mcp__filesystem__write_file`.
5. Build the rollback plan (re-INSERT/UPDATE statements in FK-safe order) BEFORE mutating.
6. Make the minimal change. `UPDATE`/`DELETE` need a `WHERE`; never hard-DELETE — use status / `deleted_at`.

## Step 4: SNAPSHOT ledger
Record every change:

| # | Table | ID | Column | Original | Test value | Restored? (verified) |
|---|---|---|---|---|---|---|

## Step 5: RESTORE + verify
After the test, restore from the snapshot, then **SELECT again** to confirm the row matches the original field-for-field. Mark "Restored? = yes (verified)". If a clean restore is impossible -> **STOP and ask the user before mutating** (or, if already mutated, surface it immediately).

## Step 6: Return
Output the data the test should use (IDs/emails/states) OR confirmation that prepared data was created and restored. Hand the IDs to the calling skill's Scope Lock "Test Data".

---

## Post-Session
Light memory note (qa-standards -> Memory Ritual): the scenario, the located/prepared IDs, and confirmation of restoration — so future sessions can reuse the same fixtures instead of re-deriving them. Cross-reference existing memory first.
