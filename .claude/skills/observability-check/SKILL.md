---
name: observability-check
description: Use when you need to surface errors the UI HIDES during a flow — frontend console errors, failed or slow network calls, backend 5xx, and server-side error state — even when the screen "looks fine". Triggers include "check for hidden errors", "any console errors on this page", "is the backend throwing 500s", "scan the network tab", "the UI looks ok but is it really", or a clean-looking flow you don't trust.
argument-hint: "the flow / page to instrument for hidden errors"
allowed-tools: ["Read", "Grep", "Glob", "mcp__chrome-devtools__*", "mcp__playwright__*", "mcp__http-client__*", "mcp__mcp_server_mysql__mysql_query", "Skill(qa-standards)", "Write"]
---

# Observability Check — Surface What the UI Hides

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/observability-check` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.
> With Browser `off` and API `on`, skip Steps 1–3 (say so) and run Steps 4–5 against replayed
> requests. With DB `off`, the DB error-state check in Step 4 is a named coverage gap, not a pass.


Run a flow and inspect the layers the UI swallows: the browser console, the network tab, the backend responses, and server-side error state. **A console error, a 5xx, or a failed request is a finding even when the page renders perfectly** — a green-looking screen routinely sits on top of a silenced error.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Evidence provenance, Bug Classification, Cross-Layer Consistency, Escape classes, Verdict Contract, Memory ritual). This skill cites those sections and does not restate them.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which flow or page should I instrument for hidden errors, and as which role? I'll run it while watching console, network, and the backend." Do not pick a flow from conversation; do not navigate until the target is known.

---

## Rules
1. Use ultrathink — the interesting failures are the ones the UI deliberately catches and hides.
2. **"UI looks fine" is not a PASS.** A clean screen with a console error or a 5xx underneath is a FAIL — report it.
3. Capture console + network on **every** flow, not just when something looks off.
4. Don't stop at the browser: a failed/slow call seen in the network tab must be **confirmed server-side** (replay it; check DB error columns) before you classify the layer.
5. Memory is ON-DEMAND for loading; the Post-Session ritual is MANDATORY.
6. Read-only by default — replays use safe GETs / idempotent calls; any mutation needs the qa-standards Mutation Safety Gate.
7. **A success flash proves nothing about an async step.** For anything handed to a queue / job / email / webhook (`PROJECT-PROFILE.md §11`), read the terminal state, never the enqueue.
8. **A masked error is its own defect.** When the stored or logged error is not the first real error, file the masking separately from the underlying bug.
9. **Tokens in logs.** DEV builds may log an auth token to the console on purpose. Quote only the lines that carry the signal and keep such logs (including the Playwright MCP console dumps) out of tickets and chats.

---

## Step 0: Scope Lock (compact)
Before the first navigation record: flow / page · role (`<roles: PROJECT-PROFILE.md §8>`) · environment and URL (`PROJECT-PROFILE.md §5`) · branch / commit (`<branch: PROJECT-PROFILE.md §3>` @ short sha, captured once for provenance) · run folder `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` · the async consumers this flow touches (`PROJECT-PROFILE.md §11`) · the error-state tables / columns this feature writes (`<key tables: PROJECT-PROFILE.md §10>`) · out of scope.

## Step 1: Run the flow
Drive the target flow end-to-end with `mcp__playwright__*` (login as the in-scope role, walk the journey). The goal is to *exercise* the surface so every console message and network call fires — not to judge the UI yet. Cross-check memory first: grep `<memory folder: PROJECT-PROFILE.md §12>` for the page/endpoint/symptom in case a hidden error here is already known. Keep one tab per portal until you have verified this project does not log the first tab out when a second one opens; list the tabs (`browser_tabs`, `action: "list"`) before every read.

## Step 2: Console — `mcp__chrome-devtools__list_console_messages`
Capture **errors AND warnings** across the whole flow (`mcp__playwright__browser_console_messages` when the devtools server is not configured). Flag: uncaught exceptions, failed-resource errors, framework key/prop warnings, `Unhandled promise rejection`, CORS errors, CSP violations, deprecation/security warnings. An error logged but visually swallowed is exactly the kind of finding this skill exists for. Redact any token or credential before the message goes into the ledger.

## Step 3: Network — `mcp__chrome-devtools__list_network_requests`
Inspect every request the flow made and flag three classes:
- **4xx / 5xx** — any non-2xx/3xx status (a 500 the FE catches and renders as an empty state is still a backend bug).
- **Failed** — requests that never completed (blocked, CORS, timeout, connection reset).
- **Slow** — calls with notably high duration that risk timeouts or jank (note the duration; correlate with any spinner the user sees; thresholds per `/perf-test` unless `PROJECT-PROFILE.md §16` sets others).

Also note the **absent** request: a write step that fired no call at all (a cached response, a local-state-only save) is recorded as `Path exercised = validation-only` and is not a PASS for the write.

## Step 4: Server-side confirmation
For each suspicious call from Step 3, confirm it's real on the backend, not a browser artifact:
- **Replay** the request (clear stale headers, set auth) and confirm the status reproduces — if `PROJECT-PROFILE.md §14` lists a project MCP server with typed tools for this surface, prefer it; otherwise use `mcp__http-client__*`. A reproduced 5xx is a confirmed backend bug; classify **BE** (qa-standards Bug Classification).
- **DB error state** — where the feature records errors, query it via `mcp__mcp_server_mysql__mysql_query` (DB tool: `PROJECT-PROFILE.md §6`): e.g. rows with `status='error'` in an error log / job / audit table, or any feature-specific error/status column (`<key tables: PROJECT-PROFILE.md §10>`). A populated error column during/after the flow is server-side evidence even if the UI never surfaced it.
- **Server logs** — if the project exposes application logs (SSH / log tool in `PROJECT-PROFILE.md §2/§14`), pull the entries for the request's timestamp and correlation id.

### Step 4b: Masked errors
For every failed job / upload / import row, compare the stored error message (`error_log` column, job `error` field, or the equivalent) with the **FIRST** error the code would log on that path (read the handler in `<backend repo: PROJECT-PROFILE.md §3/§9>`). If the stored message is a runtime/type error (`must be of type`, `Cannot read`, `undefined is not`) rather than a domain message, an earlier real error was overwritten. File the masking as its own finding (qa-standards -> Escape classes, "masked error") and go find the original. *(Illustrative)* a handler whose `throw` on "no input records found" was commented out let execution continue to a line that dereferenced the missing result, so every such failure surfaced as a `TypeError` about an unrelated argument — the real cause was invisible for months.

### Step 4c: Silent async no-ops
For any action dispatched to an async consumer (`PROJECT-PROFILE.md §11` — deploy, import, batch processing, report generation, notification), the success toast proves enqueue only. Read the **terminal state**: the row that should exist, its status, its timestamp. A success flash with no row within the expected window is a finding, not a wait. *(Illustrative)* a job handler that returned silently when a draft already existed — the UI showed "created", nothing was created, and no log line said why. Record the expected window and the actual arrival time in the ledger.

## Step 5: Report each error with its source
For every issue, state **where it surfaced** (console / network / replayed API / DB error column / server log) and attach evidence. Build the **Evidence Ledger** (qa-standards) with provenance: `| Evidence ID | Type | Source | File/URL/Tool | Env | Branch / Commit | Captured at | What it proves |`. Per finding: the message or status · the request (method/url) if network · the server-side confirmation · the layer. `No evidence = no finding.`

Output a clean summary table:

| # | Where surfaced | Detail (message / status / column) | UI showed it? | Server-confirmed? | Masked? | Layer |
|---|---|---|---|---|---|---|

Then the **Execution Register** (qa-standards) — one row per surface checked (console, network, each replayed call, each error table, each async consumer) with `Result` as a canonical area result (**PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED**), the run verdict as the canonical word (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses) and the confidence line `Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`.

If the flow is genuinely clean — zero console errors, all requests 2xx/3xx within normal timing, no DB error rows, every async consumer reached its terminal state — say so explicitly and attach the console + network captures as PASS evidence (a clean result still needs proof it was exercised). State which escape classes were actively checked (masked error, silent async no-op, validation-only path).

---

## Plugins & escalation (only when it adds value)
If the `superpowers` plugin is installed (`PROJECT-PROFILE.md §17`): before declaring the flow clean -> `superpowers:verification-before-completion`; a reproduced error whose origin is unclear after the replay and the DB read -> `superpowers:systematic-debugging`. Otherwise do the equivalent by hand: re-open the console and network captures and confirm they cover the whole flow (first navigation to last action), then for the unclear error write one hypothesis per layer (FE handler, API, async consumer), test each with one replay or query, and record which one reproduced it. If `PROJECT-PROFILE.md §16` says sub-agents are disabled, run everything in-session.

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never claim success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool. Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep for the page/endpoint/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** flow/page + date, verdict = the canonical run verdict per `qa-standards` -> Verdict Contract (**GO / NO-GO / PARTIAL**), every hidden error found with its **source** (console/network/API/DB/log) and layer, whether the UI masked it, whether the stored error masked an earlier one, the exact request/status or DB error column, async consumers and their terminal-state check, test data (URLs/user IDs — identifiers only, no tokens), root-cause `path:line` where known, any prior memory confirmed or disproved. Record the silenced errors precisely — the whole value is that the next session knows what the UI hides here.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` non-zero, else HALT.
