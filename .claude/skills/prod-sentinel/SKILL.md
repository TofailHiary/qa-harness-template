---
name: prod-sentinel
description: Use when production damage must be caught while still small: a read-only scan of the production database against a recorded baseline (failure rates, error signatures, cardinality, enum drift, bulk content events, silent async no-ops, integrity invariants) at the start of a QA week, after a deploy or after a bulk import. Triggers include "is prod healthy", "did anything break on prod", "prod sentinel", "check prod after the release", "how long has this been happening".
argument-hint: "optional: what changed since the last run (deploy, import, release), and any scan to prioritise"
allowed-tools: ["Read", "Grep", "Glob", "mcp__mcp_server_mysql_prod__mysql_query", "Skill(qa-standards)", "Skill(latent-pattern-sweep)", "Write"]
---

# Prod Sentinel — read-only production anomaly scan

> **Capability gate:** This skill requires **Prod-DB** (read-only). Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If `Prod-DB` is `off`, STOP and tell the user:
> "This project has no read-only production database configured, so `/prod-sentinel` is unavailable.
> Run `/configure-project` to enable it." Do not call this skill's tools when gated off.

Why this skill exists *(illustrative)*: two production defects sat visible in one log table for weeks — a
cardinality assumption quietly corrupting records for over a month, and an upload error rate that tripled
for a whole month. Nobody looked. This skill is the looking.

**Production is READ-ONLY. Never mutate.** Use `mcp__mcp_server_mysql_prod__mysql_query` (the prod row of
`PROJECT-PROFILE.md` §6; if that row says the connection runs through an SSH tunnel, the tunnel must be up
first — `env-health` checks it). SELECT and `information_schema` only; no temp tables, no writes, every
scan date-bounded. Runs in-session: it is seven queries and one table, so the sub-agent policy in §16 does
not change anything here.

Follows `.claude/rules/anomaly-disposition.md`: every anomaly this finds ends as a **ticket** or as
**"expected" with a cited source** — never as a note. Follows qa-standards → Evidence Ledger and Memory Ritual.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Full scan against the recorded baseline (default), or a focused scan (one table / one async chain / one content event)? Is there a deploy or import time to compare before and after?"

Do not guess the scope.

---

## Step 0 — Bind the scan templates to this project (first run; re-bind when the schema changes)

The seven scans below are **templates**. The project binds each one to its own tables once, records the
concrete queries and the first baseline, and every later run reuses them. Binding sources:

| Scan | Needs from this project | Where to find it |
|---|---|---|
| S1, S2 | a job / upload / import log table with a status column, an error-text column and a created timestamp | `PROJECT-PROFILE.md` §10 / §11 |
| S3 | the table(s) where code assumes "exactly one per partition", and the partition columns | ARMED rows in memory from `latent-pattern-sweep`; §10 |
| S4 | the enum / mode / type columns the code switches on | `latent-pattern-sweep` Step 1 output; §10 |
| S5 | the content / template table a bulk import fills, and the threshold N | §10 / §11 |
| S6 | one async chain: the enqueue record, the terminal write, the expected window | §11 (terminal writer per chain) |
| S7 | an invariant between columns that a past bug violated | §10 gotchas; memory of fixed bugs |

Record the bound queries and the first baseline in `<memory folder: PROJECT-PROFILE.md §12>` →
`project_prod_sentinel.md`, or in `.claude/references/system-map.md` §7 if the project maintains one.
**The first run has no baseline:** every row is `EXPECTED → first run`, and its numbers become the baseline.

**Engine note** (`PROJECT-PROFILE.md` §4): the SQL below is MySQL / MariaDB. Postgres: replace
`DATE_FORMAT(c,'%Y-%m')` with `to_char(date_trunc('month', c),'YYYY-MM')` and `DATE_SUB(NOW(), INTERVAL n DAY)`
with `NOW() - INTERVAL 'n days'`. SQLite: `strftime('%Y-%m', c)` and `datetime('now','-n days')`.
`<created col>` is whatever §10 says the timestamp column is called — do not assume `created_at`.

---

## The scans (run all; compare every number to the recorded baseline)

### S1 — Failure / error rate by month on the job log
```sql
SELECT DATE_FORMAT(<created col>,'%Y-%m') AS month, <status col> AS status, COUNT(*) AS n
FROM <job log table>
WHERE <created col> >= DATE_SUB(NOW(), INTERVAL 120 DAY)
GROUP BY month, status ORDER BY month, status;
```
Compute each month's error share (`error rows / all rows`). **Alarm:** any month whose error share exceeds
the trailing 3-month mean by **15 points**. A month with too few rows to mean anything (bind the floor —
tens, not thousands) is printed but not alarmed on share alone; say so in the row.

### S2 — Masked-error signatures
```sql
SELECT LEFT(<error text col>, 90) AS sig, COUNT(*) AS n,
       MIN(DATE_FORMAT(<created col>,'%Y-%m-%d')) AS first_seen
FROM <job log table>
WHERE <status col> = '<error value>' AND <created col> >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY sig ORDER BY n DESC LIMIT 15;
```
A signature that is a language / runtime error (`TypeError`, `must be of type`, `undefined`, `Cannot read`,
`NullPointer`, `KeyError`) rather than a domain message is a **masked error**: the real cause is hidden
behind a crash in the error path. File it (anomaly-disposition Rule 4), then find the cause behind it. A
signature not seen in the previous run is an ANOMALY until a source explains it.

### S3 — Cardinality partitions: is a "there is exactly one" assumption now violated? (latent P1 trigger)
```sql
SELECT <partition cols>, COUNT(*) AS n,
       MIN(DATE_FORMAT(<created col>,'%Y-%m-%d')) AS first_seen
FROM <table with a one-per-partition assumption>
WHERE <active-row predicate: PROJECT-PROFILE.md §10>
GROUP BY <partition cols> HAVING n > 1 ORDER BY n DESC;
```
The baseline is the list of partitions already known and dispositioned. **Alarm:** any NEW partition — and
especially one in a mode / type whose code path carries an unfixed copy of the same assumption (the ARMED
list from `latent-pattern-sweep` names them). `first_seen` dates the blast radius.

### S4 — Enum / mode distribution drift (latent P2 trigger)
```sql
SELECT '<table.col>' AS col, <col> AS val, COUNT(*) AS n
  FROM <table> WHERE <active-row predicate> GROUP BY <col>
UNION ALL
SELECT '<table2.col2>', <col2>, COUNT(*)
  FROM <table2> WHERE <active-row predicate> GROUP BY <col2>
ORDER BY col, n DESC;
```
One `UNION ALL` arm per bound column. **Alarm:** a value going **0 → >0** means a never-executed branch
just went live — test that branch the same day (targeted mode) and sweep it with `Skill(latent-pattern-sweep)`.
Also record values that moved from under 1% to material: that branch is now reachable by ordinary use.

### S5 — Bulk content events (the "data release" detector)
```sql
SELECT DATE_FORMAT(<created col>,'%Y-%m-%d') AS d, COUNT(*) AS n
FROM <content table>
WHERE <created col> >= DATE_SUB(NOW(), INTERVAL 60 DAY)
GROUP BY d HAVING n >= <N> ORDER BY d;
```
Bind N to "more rows than anyone creates by hand in a day". Any day at or above N is a **content import**
→ run `Skill(latent-pattern-sweep)` against it and ask the anomaly-disposition Rule 2 pre-flight question
(what cardinality / mode / format does this content introduce that production has never held?), then
re-test the paths it makes reachable.

### S6 — Silent async no-ops (an enqueue with no terminal write)
```sql
SELECT e.<id col>, e.<created col>
FROM <enqueue table> e
LEFT JOIN <terminal table> t ON t.<fk col> = e.<id col>
WHERE e.<created col> BETWEEN DATE_SUB(NOW(), INTERVAL 30 DAY)
                          AND DATE_SUB(NOW(), INTERVAL <expected window>)
  AND t.<id col> IS NULL
ORDER BY e.<created col> DESC LIMIT 50;
```
One query per chain in §11. Any row is a job that was requested and never finished, and nobody was told.
**If the system has no terminal status record** (the worker returns early behind a success message and
writes nothing), this scan cannot run: file the missing terminal write once as a defect, and **record it as
a known blind spot in every sentinel report** until it is fixed.

### S7 — Integrity spot checks (contradictory rows)
```sql
SELECT COUNT(*) AS n
FROM <table>
WHERE <status col> = '<success value>' AND <score col> = 0
  AND <created col> >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```
One query per invariant the project has learned the hard way (`status = 'correct' AND score = 0`,
`total < sum of its parts`, `completed_at < started_at`). Baseline: 0 after the fix that introduced the
invariant. Any row = regression → ticket.

---

## Output — one table, every row dispositioned

| Scan | Metric now | Baseline | Delta | Verdict (OK / ANOMALY → ticket / EXPECTED → cited source) |
|---|---|---|---|---|

Rules for the table:
- **A sentinel run that finds nothing prints the numbers anyway** — the next run needs them as its baseline.
- `EXPECTED` cites the source (the import record, the deploy, the ticket that explains it); "probably the import" is not a source.
- `ANOMALY` names the ticket id filed per `PROJECT-PROFILE.md` §15 (or quotes the owner's explicit decision not to file).
- The S6 blind spot, while it exists, is its own row in every run.

**Evidence Ledger (qa-standards):** save each scan's query text and result under
`qa-evidence/prod-sentinel-<yyyymmdd>/`; attachments for an ANOMALY ticket go under that ticket's own run folder.

---

## Post-Session (MANDATORY — enforced)

Write the new numbers into memory as the next baseline: grep `<memory folder: PROJECT-PROFILE.md §12>` for
`prod_sentinel` first; update `project_prod_sentinel.md` with a dated block (metrics per scan, dispositions,
ticket ids, blind spots) — one file for the skill, never a new file per run; one-line `MEMORY.md` pointer;
- **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
verify with `ls -la`. **An ANOMALY row without a ticket id is an unfinished run.** If memory cannot be
persisted → HALT and tell the user; never report success.

## Common mistakes

| Mistake | Why it happens | Fix |
|---|---|---|
| Comparing against a remembered baseline | the last run's numbers feel "known" | read `project_prod_sentinel.md`; the baseline is what was written, not what is recalled |
| Alarming on a partial month with a handful of rows | share arithmetic on small n | print it, mark "n too small", alarm next run if it holds |
| `EXPECTED` without a source | the explanation is plausible | cite the import / deploy / ticket, or it is an ANOMALY |
| Running the scans on Test and calling it prod | the Test DB tool is the default everywhere else | the tool is `mcp__mcp_server_mysql_prod__mysql_query`; the schema in the result must match the prod row of §6 |
| A new S4 value treated as "just data" | the branch "obviously works" | 0 → >0 is a never-executed branch going live; test it today |
