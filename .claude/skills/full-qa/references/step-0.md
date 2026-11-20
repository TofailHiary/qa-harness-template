# Full QA — Step 0: forms, the `/goal` decision, and how the cycle consumes the prompt

Part of `full-qa` (Step 0). Read it at Step 0. The forms are produced by `prompt-generator` (its Forms section); this file says which one a `/full-qa` run asks for and what every later step does with it.

## Which form Step 0 uses

| Situation | Step 0 form | Output |
|---|---|---|
| QA mode `full` or `release` | **FULL** | all ten Research Register rows, the complete execution prompt, the Run with block |
| The prompt is handed to a fresh session, `claude -p`, or another model (any mode) | **FULL** | the consumer has no context; the prompt must stand alone |
| `smoke`, `targeted`, `bugfix` or `regression` with the owner present | **LIGHT** | Request Card + live ticket (R2) + memory (R3) + code state (R5: changed files, HEAD per repo, PR merge state) + Execution shape + the Run with block; about one page, no full prompt |
| Owner says "skip Step 0" | **Run with only** | one block: `/goal` / `/loop` / neither, each with its reason |
| Owner pastes a ready prompt, or `00-prompt-<subject>.md` already exists in the run folder | **Reuse** | prompt-generator's freshness check only (plus a Run with block if the prompt has none); the prompt is this run's charter; nothing is regenerated |

Why the forms exist: a FULL generation can cost more than a short run itself *(illustrative: hundreds of thousands of tokens and about twenty minutes before the first test)*. The `/goal` / `/loop` decision is the one part no form drops.

## The `/goal` decision never stops the run

The Run with block exists before Phase 0 in every form. When it recommends `/goal`, print the exact line for the owner and **continue into Step 0a in the same turn**. `/goal` is a built-in only the owner can type; they arm it whenever they want and it applies from that moment (an unattended run starts as `claude -p "/goal …"`). The run waits for the owner only when the owner asked to be consulted. When it recommends `/loop`, print that line for the owner the same way and keep going; once the owner starts it, every iteration follows the block as written (what repeats, what each iteration validates, the stop condition); "neither" with a reason is a valid answer. One goal per session; a loop and a goal are not combined.

### /goal

For a long `release` or `full` run the Run with block recommends a `/goal` condition; print it and keep going. A separate evaluator re-checks it after every turn and the session keeps working until it resolves, which turns the Completion Gate from something you must remember into something the harness enforces. Example (example only):

> `/goal Every row of the Execution Register carries one of the five canonical values (qa-standards -> Verdict Contract), every finding has an Evidence Ledger row, and the Phase 8a audit returned AUDIT_PASSED with a complete case-completeness line and a Skills loaded line that matches the session.`

Claude Code stops the run if it stalls, so keep the condition objective and checkable (`prompt-generator/references/goal-loop-rules.md`).

## How the rest of the cycle consumes the prompt

A block the prompt does not have (Run with only, the LIGHT form, or a pasted prompt without it) is built by that step from its own instructions in SKILL.md.

- **Step 0a** takes the Scope Lock from the prompt's Scope section and Execution shape (QA mode, stakes → Risk level, stop conditions) and writes out the six questions starting from its Request Card and Research Register (fill gaps; never narrow silently).
- **Step 0b** starts from the prompt's Impact map (LIGHT form: only the changed-file list, so Step 0b builds the map); `pr-risk-analyzer` still runs for a PR and may only widen it.
- **Phase 0** expands the prompt's Requirement register and combination matrix into cases (LIGHT form: the acceptance criteria in R2); `test-cases-generator` keeps the prompt's IDs and derives `M` from the code (its Step 1b), never from the prompt's row count.
- **Phase 1** turns every Research Register row marked UNKNOWN / RETRIEVE / "not available" / "not researched (light form)" into a check (deploy state, missing fixture, open question); a row that cannot be closed becomes a named coverage gap or a stop condition, never silence. `test-data-manager` starts from the prompt's accounts (R7) and fixtures (R8).
- **Phases 2–8** execute the prompt: every check it asks for (end-to-end chains, layer sections, downstream lifecycle, concurrency, independent calculations, the escape classes it marks as armed) is a Phase 0 case or a register row before its phase runs.
- **Phase 8a** audits the prompt too: an area or check it names with no register row fails the audit (`references/audit.md`).
- The prompt copy lives at `qa-evidence/<run-folder>/00-prompt-<subject>.md`; later attachments sit beside it.
