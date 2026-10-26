---
name: ai-output-eval
description: Use when an AI/ML-generated or computed output (score, recommendation, KPI, aggregate, snapshot, report figure) must be checked against its source data, for determinism across repeated computations, or for edge cases. Triggers include "is this score right", "verify the recommendation picked correctly", "the dashboard KPI looks wrong", "does the report match the source records", "recompute this output", "is this output deterministic".
argument-hint: "which output to evaluate (pipeline + entity, e.g. 'recommendation for user 267' or 'report snapshot for account 98')"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__mcp_server_mysql__mysql_query", "mcp__mcp_server_mysql_prod__mysql_query", "mcp__http-client__*", "mcp__playwright__*", "mcp__github__*", "Skill(qa-standards)", "Write"]
---

# AI Output Evaluation

> **Capability gate:** This skill requires **DB**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no DB configured, so `/ai-output-eval` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.
>
> **API** and **Browser** are optional enhancers for the cross-layer step (DB → API → UI); **Prod-DB**
> (read-only) for confirming a prod repro. Skip and name the layers whose capability is `off`.

Validate an AI/ML-generated or computed output against the source data that produced it: **correctness**
(recompute vs actual), **determinism** (same input → same output, every time), and the **edge cases**
that repeatedly bite derived-data pipelines.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (QA Modes,
Scope Lock, Evidence Ledger, Mutation Safety Gate, Cross-Layer Consistency, MCP Server Routing, Verdict
Contract, Memory Ritual). The safety-critical gates are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which output should I evaluate, and for which entity? Name the pipeline (from the table below, or the
> worker/job that produces it) plus the IDs (user / group / record / account). Which QA mode — targeted /
> regression / full?"

Do NOT guess the pipeline or the entity. Do NOT run any query/call until scope is known.

---

## The project's pipelines (fill in once; keep in sync with `PROJECT-PROFILE.md` §11/§13)

Every AI/computed output in the project belongs to a pipeline: a producer (worker, Lambda, cron, request
handler, model call), its source inputs, and the place the output lands. Fill this table from
`PROJECT-PROFILE.md` §11 (async consumers) and §13 (docs), then **verify it against the code** — docs
go stale, code is truth:

| Pipeline | What it produces | Source inputs (tables / files / events) | Output location (table / endpoint / UI) | Known edge case |
|---|---|---|---|---|
| *(e.g. scoring)* | a score per attempt | the submitted answers / file | `score` table, `GET /api/.../score` | async timing; file-encoding |
| *(e.g. recommendation)* | next items to show per user | per-user mastery rows, item ordering | recommendation table / picker response | all-items-mastered user |
| *(e.g. KPI / dashboard)* | counts, rates, flags | source rows joined across groups | dashboard endpoint, UI cards | unordered source list; falsy zero |
| *(e.g. snapshot / report)* | materialized aggregates | live rows at snapshot time | `report_*` tables, exports | snapshot scope ≠ live scope; staleness |
| *(e.g. model score)* | ability / rank per user | recorded events | per-user score table | `updated_at` not bumped on recompute |

**Discover pipelines from the code, not from memory:** list the workers / Lambdas / cron jobs / queue
consumers in `PROJECT-PROFILE.md` §11, then Grep `<backend repo: PROJECT-PROFILE.md §3/§9>` (and any
worker repo in §3) for the writers of the output table (`INSERT`/`UPDATE`/`upsert`/`bulkCreate` on it)
and for the readers that serve it (`<routes path: PROJECT-PROFILE.md §9>`, the reporting service in §3
when the project has one). The output is only "wrong" relative to a documented rule — **find the rule in
code first** (`mcp__github__*` or `Read`), never assume it.

---

## Scope Lock — REQUIRED before any tool runs (qa-standards)
Output the Scope Lock table first. Pin **which pipeline**, the exact source tables, the output
table/endpoint/UI, the entity IDs, the rule's code location (`path:line`), and the environment. Do not run
a single query until it is filled; ask if a critical field is unknown.

## Mutation Safety Gate (qa-standards)
This skill is **read-only by default** — it compares stored source vs stored output, it does not
regenerate. If a test needs a staged input (e.g. flip one mastery row to force an all-mastered user),
follow the full gate: SELECT + log the original, WHERE on every UPDATE, restore + verify after, **never
mutate prod**. Prefer existing disposable test data (`test-data-manager`) over new rows.

---

## Workflow

### 1. Identify the pipeline and its rule
Confirm which pipeline is under test and read its rule in code: the selection/ordering/aggregation logic,
the thresholds, the filters, the NULL handling, the trigger that recomputes it. Quote `path:line` for each
— these citations are the "expected" side of every comparison (qa-standards → Authoritative Source
Hierarchy).

### 2. Pull SOURCE inputs and the OUTPUT, side by side
- **Source** (the pipeline's inputs): the per-entity rows, attempts, events, or file the rule consumes.
- **Output** (what the pipeline produced): the recommendation row, the score, the KPI value, the snapshot
  row.
Query both via `mcp__mcp_server_mysql__mysql_query` (test/dev; DB tool: `PROJECT-PROFILE.md` §6) or
`mcp__mcp_server_mysql_prod__mysql_query` (prod confirm, read-only). Keep the source rows and the output
row together — **that pairing IS the proof**.

### 3. Recompute expected vs actual
- **Scores:** recompute the produced value from the source answer set / file; check derived columns are
  populated, not NULL, wherever attempts exist.
- **Recommendations / picks:** run the documented pick logic against the source (e.g. priority asc, score
  asc; mastered items excluded) and compare the pick **set** (and order, if order is a contract) to the
  produced recommendation. The gold standard is a harness that imports the real selection function and
  runs it on the source rows — keep such a harness under `qa-evidence/<run>/`, never in the product repo.
- **KPIs / snapshots / aggregates:** recompute the aggregate from the source rows and compare to the
  displayed/stored value. **State the NULL coercion before declaring a mismatch**: an average that excludes
  NULL and one that treats NULL as 0 can differ by a factor of three on sparse columns *(illustrative: a
  column ~75% NULL gave 37 vs 12 under the two rules)*. Find which rule the code uses, then recompute.
- **Model scores / rankings:** recompute from the recorded events; confirm the stored value equals the
  recomputed one and that `updated_at` moved when it was last recomputed.

### 4. Edge cases that repeatedly bite derived-data pipelines — test EVERY applicable one explicitly

| Edge case | What to force / check | Past shape *(illustrative)* |
|---|---|---|
| **All-mastered / all-complete entity** | every item already complete → the recommendation must NOT return completed items; the KPI/chart must show a positive "done" state, not blank / "No data available" | a priority override re-recommended mastered items; a chart filtered to nothing showed "No data" instead of "100%" |
| **Zero / null score (falsy zero)** | a real `0` must render as `0`, not "-" / blank; NULL handled, not crashed | a summary card rendered `{value ? value : "-"}`, so every genuine zero showed as "-" |
| **Non-deterministic source-record selection** | the output must be identical across requests; never `items[0]` of an unordered list, a `.find()` on an unordered join, or `LIMIT 1` without `ORDER BY` | a KPI flipped between two values depending on which of two ids an unordered list returned first |
| **Snapshot vs live scope** | does the snapshot include ONLY a subset (one mode, one source) while the live aggregate includes everything? Both must state their scope, and the UI must label it | a snapshot built from one record mode disagreed with the live aggregate over all modes by a wide margin |
| **Silent drops / caps / truncation** | does the pipeline drop rows below a threshold, cap a list, or truncate without surfacing it? No silent loss | a `.filter(x !== 0)` emptied a chart; a hard cap hid the rows past the limit |
| **Stale recompute trigger** | does the output update on ALL relevant source mutations, or only some events? Is `updated_at` bumped? | a snapshot rebuilt on one event type only; a score table's `updated_at` stayed frozen across recomputes |
| **Partition cardinality** | the rule assumes one record per (entity × dimension); does the data now hold two? (`/latent-pattern-sweep` P1) | a "first row" pick became random when a partition grew to two rows |

Any applicable edge case you did NOT exercise is a coverage gap — name it in the result, never imply it
passed.

### 5. Cross-layer consistency (qa-standards)
The same value must agree across **DB → API → UI**. Compare in one table
`| Field | DB | API | Browser | Match? |`. Hit the service that actually serves the dashboard — projects
with a separate reporting service (`PROJECT-PROFILE.md` §3/§5, "Report API") read from it, NOT from the
main backend; a value that is right in one service and wrong in the other is a **Report** bug. Use
`mcp__http-client__*` (or the typed project tools in `PROJECT-PROFILE.md` §14) and `mcp__playwright__*`
when those capabilities are `on`; otherwise mark the layer NOT YET VERIFIED.

### 6. Determinism
Run the SAME input through the output path **N = 3 times minimum** (more when the first runs disagree)
and confirm identical results. Non-determinism (a different KPI per page load, a different pick order per
request) is itself a bug — capture the differing outputs as evidence *(illustrative: six identical calls
whose list order flipped roughly half the time exposed an unordered source list)*.

### 7. Findings + Evidence Ledger (REQUIRED)
Produce findings per qa-standards. Every finding maps to >=1 ledger row, and for computed outputs the
load-bearing evidence is the **source rows next to the output row** proving the claim.

**Evidence Ledger (every finding AND every PASS):**
| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

**Proof pairing (include for each correctness claim):**
| Entity | Source rows (input) | Rule (`path:line`) | Expected (recomputed) | Actual (output) | Determinism (N runs) | Match? |
|---|---|---|---|---|---|---|

Hard rules: no evidence = no finding; no reproduction = no confirmed bug; no DB/API/UI comparison = no
cross-layer claim; save proof for PASS too. Classify every confirmed bug FE / BE / Admin / Report / DB /
Both (qa-standards → Bug Classification) and give the verdict in Verdict Contract words (CONFIRMED BUG /
NOT A BUG / CANNOT CONFIRM / DUPLICATE per finding; area result PASS / FAIL / BLOCKED / NOT APPLICABLE /
NOT YET VERIFIED).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot
be persisted -> **HALT and tell the user**; never report success.

1. **Cross-reference first** — grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for the pipeline,
   output table, entity IDs, and symptom. If an entry already covers this output's root cause (an
   all-mastered override, an unordered-list pick, a snapshot-scope mismatch), **UPDATE it** with today's
   recompute — do NOT file a duplicate.
2. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool
   (the only path it is allowed). Frontmatter `name` / `description` / `metadata.type`.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** pipeline + entity + date, verdict, bugs (ID, severity, layer, NEW/DUPLICATE), the
   **source-vs-output proof pairing** + the recompute formula used (so it is re-runnable), which edge cases
   were exercised and which were coverage gaps, the NULL-coercion rule the code uses, test data (entity
   IDs only), root-cause `path:line`, any prior memory this run disproved.
5. **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
6. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
