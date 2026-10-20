# QA Testing Rules (Always Loaded)

This file is the short, always-loaded version. The full text of every rule lives in
`.claude/skills/qa-standards/SKILL.md` (loaded by every QA skill and every agent). Do not restate it here.

## Investigation Flow
For EVERY task: Think deeply -> Read code (trace FE -> API -> BE -> DB -> workers / async consumers) -> Query DB -> Test API -> Validate in browser -> Check regression -> Document findings. Skip the layers this project does not have (`PROJECT-PROFILE.md` §2) and say so.

## Effort calibration
Match effort to STAKES, not to the length of the request. State the mode (smoke / targeted / regression / bugfix / full / release) and why. A short prompt is not permission to do a short job.

## Policy knobs (`PROJECT-PROFILE.md` §16; defaults)
- **Execute every generated case.** No sampling by priority, no stopping for time. Every case ends as a register row with a canonical result and an evidence id, and the report says what happened to each.
- **Treat every answer as if the user asked "are you sure?"** Re-run the check, answer from evidence, label VERIFIED / INFERRED / UNKNOWN. Never concede without a new fact (`.claude/rules/pushback-protocol.md`).
- **Sub-agents** are allowed by default; when §16 disables them, lanes and the verdict audit run in-session from the package alone (full-qa Phase 8a).
- **Plain language.** Short sentences. Explain a term the first time. A finding that is not understood did not land.

## Gates (full text in qa-standards)
- **Completion Gate** — the list of conditions under which you may NOT report a verdict (fresh result per area, retested bugs, recomputed numbers, both sort directions, page 2, resolved contradictions, classified defects, write paths exercised). HTTP 200 / matching values / "it passed last time" are not reasons to stop.
- **Verdict Integrity** — challenge every PASS and every FAIL yourself before the user has to; scope predicate; semantic contract; operational vs structural blockers; reproduce first-hand; state confidence.
- **Verdict Contract** — the ONLY definition of PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED and GO / NO-GO / PARTIAL, with the mandatory confidence line. Silence is never a pass.
- **Anomaly Disposition** (`.claude/rules/anomaly-disposition.md`) — an anomaly ends as a TICKET or as "expected" WITH A CITED SOURCE; a content import is a release; the three latent patterns; a masked error is its own defect; validation green is not feature green.
- **Escape classes E1–E13** (qa-standards) — name which were checked in every verdict; an unchecked class is NOT YET VERIFIED.

## Cross-layer and classification (short form)
For each entity: DB (the §6 DB tool) -> API (§14 typed tools, else `mcp__http-client__*`) -> Browser (`mcp__playwright__*`), compared in a table. Matching API and UI proves transport, not correctness — recompute from source. Every bug is FE / BE / Admin / Report / DB / Both, never ambiguous: wrong API + correct DB = BE; correct API + wrong UI = FE; no API call when expected = FE; 500 = BE; an async worker that owns the terminal write = BE with the worker named.

## Evidence
No evidence = no finding. No reproduction = no confirmed bug. `qa-evidence/<run-folder>/` holds attachments only (API responses, screenshots, logs), prefixed with the finding id, written via the filesystem MCP or a Bash heredoc. Findings live in chat and the tracker. Every ledger row carries Env / Branch-Commit / Captured-at.

## Session hygiene
`/clear` between unrelated QA tasks. Generate cases BEFORE testing (`/test-cases-generator` or Phase 0). Run `Skill(latent-pattern-sweep)` after any bulk content import; `Skill(prod-sentinel)` at the start of a QA week and after every deploy (when Prod-DB is on).
