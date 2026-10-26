# Run record — `run.json` (machine-readable register, ledger and verdict)

Every orchestrated run (`full-qa`, `qa-validate`, `qa-team`, `release-check`, `regression-runner`) keeps ONE
machine-readable file next to its attachments: `qa-evidence/<run-folder>/run.json`. The markdown tables in the
chat stay the human view; `run.json` is the same content in a form a script can recompute. It is the only
non-attachment file allowed in the run folder, together with the `package.md` the auditor reads.

Why: a prose register cannot be checked. With `run.json`, `verdict_check.py` proves that every evidence id
resolves to a file, that `N of M` is arithmetic, that every FAIL cites an expected source, and that the stated
run verdict is the one the Verdict Contract produces from the rows.

## Write it as you go (it is also the checkpoint)

- Create it at Scope Lock time; update it at the end of EVERY phase (that update is the checkpoint).
- Write it with the filesystem MCP (`mcp__filesystem__write_file`) or a Bash heredoc — `Write`/`Edit` are
  hook-blocked under `qa-evidence/`.
- **Resume:** when a run folder already holds a `run.json` whose `checkpoint.next_step` is set, a new session
  continues from that step instead of starting over. Rows already PASS/FAIL keep their evidence; rows marked
  NOT YET VERIFIED are executed now.

## Check it

```bash
python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>            # final check
python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder> --partial  # mid-run
python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder> --package  # writes package.md for the auditor
python .claude/skills/qa-standards/scripts/verdict_check.py --summary qa-evidence               # one line per run
```
Exit 0 = consistent. Exit 1 = the run record contradicts itself; the printed lines say where. A run verdict is
not reported while the final check exits 1.

## Shape (`schema: "qa-run/1"`)

```json
{
  "schema": "qa-run/1",
  "run_id": "APP-123-20261026",
  "skill": "full-qa",
  "mode": "targeted",
  "subject": "APP-123 order export",
  "env": "TEST",
  "commits": {"app-backend": "main @ 1a2b3c4"},
  "verdict_policy": "strict-binary",
  "started_at": "2026-10-26T09:00:00Z",
  "updated_at": "2026-10-26T11:40:00Z",
  "scope": {
    "in": ["export endpoint", "export button"],
    "out": [{"item": "PDF export", "reason": "not changed by the PR (diff touches csv only)"}],
    "ac_source": "APP-123 description, AC 1-4"
  },
  "matrix": {
    "source": "test-cases-generator Step 1b",
    "dimensions": {"role": ["admin", "user"], "format": ["csv"]},
    "cells": ["admin/csv", "user/csv"],
    "excluded": []
  },
  "register": [
    {"id": "TC-01", "area": "export as admin", "requirement": "AC1", "check": "POST /export then DB read-back",
     "cells": ["admin/csv"], "result": "PASS", "expected_source": "AC1", "evidence": ["E1", "E2"],
     "path_exercised": "write", "finding": null},
    {"id": "TC-02", "area": "export as user", "requirement": "AC2", "check": "role check",
     "cells": ["user/csv"], "result": "BLOCKED", "reason": "user account locked on TEST",
     "unblock": "unlock the fixture user or provide another one", "evidence": []}
  ],
  "ledger": [
    {"id": "E1", "type": "API request/response", "file": "E1-export-response.json", "env": "TEST",
     "commit": "main @ 1a2b3c4", "captured_at": "2026-10-26T10:02:11Z", "proves": "export returns 202"},
    {"id": "E2", "type": "DB query result", "file": "E2-export-row.csv", "env": "TEST",
     "commit": "main @ 1a2b3c4", "captured_at": "2026-10-26T10:02:40Z", "proves": "row written with status queued"}
  ],
  "findings": [],
  "escape_classes": {"E1": "checked", "E2": "not applicable: no import in scope"},
  "phases": [{"name": "Phase 0", "status": "done"}, {"name": "Phase 4", "status": "done"}],
  "checkpoint": {"last_phase": "Phase 4", "next_step": null, "open_rows": []},
  "verdict": {"run": "PARTIAL", "alias": null, "remaining_risk": "user-role export unverified",
              "confidence_line": "Verified 1 of 2 in-scope areas; BLOCKED 1; NOT YET VERIFIED 0; Remaining Risk: user-role export unverified",
              "audit": "not-run"}
}
```

## Field rules (what `verdict_check.py` enforces)

| Field | Rule |
|---|---|
| `register[].result` | exactly one of PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED (Verdict Contract) |
| PASS | at least one evidence id |
| FAIL | `expected_source` + at least one evidence id + `finding` naming a finding id |
| BLOCKED | `reason` + `unblock` |
| NOT APPLICABLE | `reason` (the scope predicate) |
| `path_exercised: "write"` + PASS | evidence includes a network/API row AND a DB row (validation green is not feature green) |
| `register[].evidence[]` | every id exists in `ledger` |
| `ledger[]` | `env`, `commit`, `captured_at` filled; `file` exists in the run folder unless it is a URL or a `path:line` code reference |
| `matrix.cells` | every cell not in `excluded` is covered by at least one register row's `cells` |
| `findings[].status` | CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE; a CONFIRMED BUG has evidence that exists |
| `verdict.run` | GO / NO-GO / PARTIAL, equal to the value recomputed from the rows (below) |
| `verdict.confidence_line` | equal to the recomputed line (the Remaining Risk text is yours) |

**Recomputation.** `M` = register rows that are not NOT APPLICABLE. `N` = PASS + FAIL rows. `k` = BLOCKED rows.
`j` = NOT YET VERIFIED rows. Run verdict: any CONFIRMED BUG -> NO-GO; else any BLOCKED or NOT YET VERIFIED row ->
PARTIAL; else GO. A severity-weighted policy (`PROJECT-PROFILE.md §16`) is stated in `verdict_policy` and its
threshold text; the checker then reports the strict-binary value next to yours instead of failing.

## The audit package (`package.md`)

`--package` renders scope, AC source, register, ledger, findings and the proposed verdict from `run.json` into
`package.md` in the run folder. The `qa-verdict-auditor` is dispatched with that path only and reads the file —
never the orchestrator's reasoning in the chat.
