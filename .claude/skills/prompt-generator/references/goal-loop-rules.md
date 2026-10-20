# /goal and /loop — when the generated prompt asks for them

Both are built-in Claude Code commands the owner types (documented in the Claude Code changelog and docs: `/goal` "set a completion condition and Claude keeps working across turns until it's met"; `/loop` runs a prompt or slash command on an interval). The prompt gives the exact line in its **Run with** block; the skill never arms them.

## /goal — a completion condition the harness enforces

`/goal <condition>` keeps the session working across turns and compactions until an evaluator sees the condition met. Use it when the run is long enough to drift: full / release / regression / bugfix modes, an Execution Register with many areas, retest rounds.

Write the condition from checkable objects, never from intent:
- every row of the Execution Register carries one of PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED
- every finding (bug or PASS) has an Evidence Ledger row with an evidence id
- the Phase 8a in-session audit (`qa-verdict-auditor`) returned AUDIT_PASSED
- the confidence line is printed and adds up
- memory is updated (file in `<memory folder: PROJECT-PROFILE.md §12>` + `MEMORY.md` line)
- scope-specific outcomes: "all M cells of the code-derived matrix executed", "the reporter's original input re-run", "the fix touched the root-cause file:line"

Example *(illustrative)*: `/goal Every row of the Execution Register for APP-412 carries a canonical value, every finding has an Evidence Ledger row, Phase 8a returned AUDIT_PASSED, and the memory file for APP-412 is updated.`

One goal per run. Claude Code stops a stalled goal and checks in on long background work (30 min, then 1 h, then 2 h).

## /loop — repeat on a clock

`/loop <interval> <prompt or /command>` re-runs the prompt every interval; `/loop <prompt>` self-paces. Use it when the work waits on something outside the session or must be sampled:

| Situation | What repeats | Validate each iteration | Stop when |
|---|---|---|---|
| Deploy / CI / background-job backfill pending | the env-health deploy check (a unique string from the diff in the deployed bundle, the build id, the worker / function version) | the fix string is live, the build id changed | deployed → continue the run; or the agreed hours pass → report PARTIAL |
| Intermittent bug | the exact repro flow (`flaky-race-verifier`) | reproduced yes / no with evidence per run | the reproduction rate is established over K runs |
| Post-release monitoring | the `prod-sentinel` read-only scan | metric deltas vs the recorded baseline | the baseline stays stable for the agreed window |
| Retest after each fix round | the bugfix checks for the reopened ticket | fix touched the root cause, original input passes, negative control holds | the ticket reaches the ready-for-release state named in `PROJECT-PROFILE.md` §15, with evidence |

Always state: the interval, what repeats, why, what each iteration validates, the stop condition, and what to do on stop. One writer per state file across iterations — two iterations appending to the same memory or evidence file produce a report nobody can trust.

## Neither

Smoke and targeted single-pass runs: write "neither: single pass, ends with the verdict", so the omission is deliberate and visible.

## Facts from the Claude Code documentation (re-check the current docs when a line is load-bearing)
- `/goal <condition>` sets or replaces the one active goal (conditions up to 4,000 characters); `/goal` alone shows status; `/goal clear` (aliases stop / off / reset / none / cancel) removes it.
- Unattended: `claude -p "/goal <condition>"` runs to completion in one invocation (`--output-format stream-json --verbose` shows progress). It does not change the permission mode.
- Whether Claude can arm `/goal` itself is not documented: treat it as typed by the owner.
- `/goal` starts the next turn when the previous one ends; `/loop` starts it on a time interval. They are different triggers; combining them is not documented, so the prompt recommends one primary mechanism and says why.
