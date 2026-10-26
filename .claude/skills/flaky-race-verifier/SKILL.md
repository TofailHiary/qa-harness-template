---
name: flaky-race-verifier
description: Use when a flow fails only SOMETIMES and you must quantify it — repeat the exact flow many times, compute a reproduction rate, and hunt for a race/timing/ordering cause. Triggers include "this is flaky", "it only fails sometimes", "intermittent error", "works on retry", "can't reproduce reliably", or the intermittent path of /bug-verifier.
argument-hint: "the intermittent flow + the failure signal (e.g. 'submit order sometimes shows blank status')"
allowed-tools: ["Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__http-client__*", "Skill(qa-standards)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# Flaky / Race Verifier — Quantify the Intermittent

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/flaky-race-verifier` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Take a flow that fails *sometimes*, repeat it under clean state, and turn "it's flaky" into a number: a reproduction rate plus a suspected race/timing/ordering cause. Pairs with `bug-verifier`'s intermittent path — use this to get the rate that the verifier's checklist demands, then hand the confirmed finding back.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Bug Classification, Cross-Layer Consistency, Verdict Contract, Memory ritual).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which intermittent flow should I quantify, and what is the EXACT failure signal (blank field / 500 / wrong value / spinner that never resolves)? I need the precise steps to repeat." Do not guess the flow from conversation; do not run anything until the flow and the signal are pinned.

---

## Rules
1. Use ultrathink — race conditions are non-obvious; reason about ordering and timing, not just the happy path.
2. **A reproduction rate is the deliverable.** "Sometimes" is not a finding; "fails 4/10 runs" is.
3. Each run starts from **clean state** (fresh session / cleared cache / known DB precondition) — otherwise run N is contaminated by run N-1 and the rate is meaningless.
4. Capture the network timing and console on **every** run, pass or fail — the failing run's signature only means something next to the passing runs'.
5. Memory is ON-DEMAND for loading; the Post-Session ritual is MANDATORY.
6. No reproduction in N runs after escalation = **CANNOT CONFIRM** (Verdict Contract), not "no bug" — document what was tried (see qa-standards Evidence Ledger: `No reproduction = no confirmed bug`).
7. **Read-only.** This skill never fixes, patches, or adds retries to product code; it measures and explains.

---

## Step 1: Pin the flow + the failure signal
- Write the EXACT ordered steps (URL -> action -> action) and the **one** observable signal that means "failed this run" (blank status, HTTP 500, value mismatch, spinner > Ns). One signal, unambiguous — so each run is a clean pass/fail, not a judgement call.
- **Cross-check memory** — grep `<memory folder: PROJECT-PROFILE.md §12>/*.md` for the flow/endpoint/symptom. If a prior entry already quantified this, you are RE-VERIFYING: confirm the rate still holds or moved, and UPDATE that entry.
- Define the **clean-state reset** between runs: new Playwright context / re-auth (`login` skill, accounts from `PROJECT-PROFILE.md` §7), cache clear, and the DB/data precondition each run assumes (read-only — do not mutate to set up unless qa-standards Mutation Safety Gate is satisfied).
- Pin the surface: `<main app URL: PROJECT-PROFILE.md §5>` or `<API base URL: PROJECT-PROFILE.md §5>`, and the branch/build under test (`<branch: PROJECT-PROFILE.md §3>`) — a rate measured on the wrong build is worthless.

## Step 2: Run it N times under clean state
- **N = 5** by default. If 5 runs give a borderline rate (1–2 fails, or all-pass-but-user-swears-it-fails), bump to **10+** — small N hides low-probability races.
- Per run, in this order: reset clean state -> drive the flow with `mcp__playwright__*` (or `mcp__http-client__*` for an API-only flow) -> capture `mcp__chrome-devtools__list_network_requests` (URLs, status, **timing/duration**, order) -> capture `mcp__chrome-devtools__list_console_messages` -> record pass/fail against the Step 1 signal -> screenshot on fail (pass `filename: qa-evidence/<slug>/<name>.png`).
- Keep the runs **identical** — same data, same waits, same path. The only thing allowed to vary is what you are hunting: timing/ordering.

## Step 3: Compute the reproduction rate
`reproduction rate = fails / total runs` (e.g. 4/10 = 40%). State it plainly. Note whether failures cluster (e.g. only the first run after a cold cache, only when two requests overlap) — clustering is itself a clue to the cause.

## Step 4: Hunt the cause (race / timing / ordering)
Compare failing runs vs passing runs across these suspects:

| Suspect | What to look for in the captures | Likely layer |
|---|---|---|
| Slow / racing API | A call whose duration spikes on fail runs; UI reads before it resolves | BE (slow) / FE (no await) |
| Missing await / premature render | UI asserts/renders before the network request completes; value blank then fills | FE |
| Request ordering | Two requests fire in different order across runs; the later one wins/loses (e.g. config arrives after the consumer) | FE / BE |
| Cache / stale state | First run cold vs warm; a client query cache (e.g. React Query) serving a stale key; snapshot read before refresh | FE / cache |
| Animation / transition timing | Element not yet interactable; click lands before mount; CSS transition gates the action | FE |
| Backend non-determinism | No `ORDER BY` so row order varies (the `items[0]`-of-an-unordered-list class of bug — see memory and `/latent-pattern-sweep` P1); concurrent write race; a queue/worker (`PROJECT-PROFILE.md` §11) finishing after the read | BE / DB |

Read the implicated code (`Read`/`Grep`) to confirm the mechanism — a rate without a mechanism is a symptom, not a root cause.

**Escalation when the rate is too low to reason about** (plugins are optional, `PROJECT-PROFILE.md` §17):
- If the `mattpocock-skills` plugin is installed, run `Skill(mattpocock-skills:diagnosing-bugs)` **Phases 1–4 only** — its non-deterministic-bug rule applies here. **Never Phase 5+ (fix)** in this read-only setup.
- If the `superpowers` plugin is installed, `superpowers:systematic-debugging` (hypothesis -> isolate -> verify) is the alternative for a non-obvious, cross-layer root cause.
- Otherwise do the same by hand: **loop the trigger** (x20, x50, x100 — a script against the API, or a Playwright loop), **parallelise** (two contexts hitting the flow at once), **add stress** (throttle the network with `mcp__chrome-devtools__*` emulation, run a heavy page alongside), **inject sleeps** at the suspected boundary to widen or close the window, and **narrow the timing window** until the rate is debuggable — a 50% flake is debuggable, a 1% flake is not. Record every amplification step you took; it is part of the evidence.

## Step 5: Output
- **Runs table** — one row per run:

  | Run | Clean state | Result (PASS/FAIL) | Key request + duration | Console errors | Notes |
  |---|---|---|---|---|---|

- **Reproduction rate** — `fails/total = X%`, plus N and clustering observation. If amplification was used, give both the natural rate and the amplified rate, and the conditions for each.
- **Suspected cause** — the row above that fits, with the code reference (`path:line`) and why the failing-run captures support it.
- **Evidence Ledger** (qa-standards) — `| Evidence ID | Type | Source | File/URL/Tool | What it proves |`. Network captures, console logs, screenshots per run; `No evidence = no finding`.
- **Layer classification** (qa-standards Bug Classification) so `bug-report` doesn't re-derive it.
- **Verdict (Verdict Contract):** **CONFIRMED BUG** (rate + mechanism) -> hand to `Skill(bug-verifier)` / `Skill(bug-report)`; or **CANNOT CONFIRM** (0 fails after escalation) with exactly what was tried, the N used, and what would be needed to go further.

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never claim success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool. Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep for the flow/endpoint/symptom; if a prior entry quantified this flow, UPDATE it with today's rate (do not file a duplicate).
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** flow + date, **reproduction rate (X/N) and N used** (natural and amplified, if both), clean-state conditions reset between runs, suspected race/timing/ordering cause + `path:line`, verdict (CONFIRMED BUG / CANNOT CONFIRM), test data (URLs/user IDs), any prior rate confirmed or disproved. The rate + conditions are the whole point — record them precisely so the next session can compare.
5. **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
6. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
