---
name: observability-check
description: Use when you need to surface errors the UI HIDES during a flow — frontend console errors, failed or slow network calls, backend 5xx, and server-side error state — even when the screen "looks fine". Triggers include "check for hidden errors", "any console errors on this page", "is the backend throwing 500s", "scan the network tab", "the UI looks ok but is it really", or a clean-looking flow you don't trust.
argument-hint: "the flow / page to instrument for hidden errors"
allowed-tools: ["Read", "Grep", "Glob", "mcp__chrome-devtools__*", "mcp__playwright__*", "mcp__http-client__*", "mcp__mcp_server_mysql__mysql_query", "Skill(qa-standards)"]
---

# Observability Check — Surface What the UI Hides

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/observability-check` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Run a flow and inspect the layers the UI swallows: the browser console, the network tab, the backend responses, and server-side error state. **A console error, a 5xx, or a failed request is a finding even when the page renders perfectly** — a green-looking screen routinely sits on top of a silenced error.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (Evidence Ledger, Bug Classification, Cross-Layer Consistency, Memory ritual).

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

---

## Step 1: Run the flow
Drive the target flow end-to-end with `mcp__playwright__*` (login as the in-scope role, walk the journey). The goal is to *exercise* the surface so every console message and network call fires — not to judge the UI yet. Cross-check memory first: grep `~/.claude/projects/c--Users-<user>-<project>/memory/*.md` for the page/endpoint/symptom in case a hidden error here is already known.

## Step 2: Console — `mcp__chrome-devtools__list_console_messages`
Capture **errors AND warnings** across the whole flow. Flag: uncaught exceptions, failed-resource errors, React key/prop warnings, `Unhandled promise rejection`, CORS errors, CSP violations, deprecation/security warnings. An error logged but visually swallowed is exactly the kind of finding this skill exists for.

## Step 3: Network — `mcp__chrome-devtools__list_network_requests`
Inspect every request the flow made and flag three classes:
- **4xx / 5xx** — any non-2xx/3xx status (a 500 the FE catches and renders as an empty state is still a backend bug).
- **Failed** — requests that never completed (blocked, CORS, timeout, connection reset).
- **Slow** — calls with notably high duration that risk timeouts or jank (note the duration; correlate with any spinner the user sees).

## Step 4: Server-side confirmation
For each suspicious call from Step 3, confirm it's real on the backend, not a browser artifact:
- **Replay** the request via `mcp__http-client__*` (clear stale headers, set auth) and confirm the status reproduces — a reproduced 5xx is a confirmed backend bug; classify **BE** (qa-standards Bug Classification).
- **DB error state** — where the feature records errors, query it via `mcp__mcp_server_mysql__mysql_query`: e.g. rows with `status='error'` in an error log or audit table, or any feature-specific error/status column. A populated error column during/after the flow is server-side evidence even if the UI never surfaced it.

## Step 5: Report each error with its source
For every issue, state **where it surfaced** (console / network / replayed API / DB error column) and attach evidence. Build the **Evidence Ledger** (qa-standards): `| Evidence ID | Type | Source | File/URL/Tool | What it proves |`. Per finding: the message or status · the request (method/url) if network · the server-side confirmation · the layer. `No evidence = no finding.`

Output a clean summary table:

| # | Where surfaced | Detail (message / status / column) | UI showed it? | Server-confirmed? | Layer |
|---|---|---|---|---|---|

If the flow is genuinely clean — zero console errors, all requests 2xx/3xx within normal timing, no DB error rows — say so explicitly and attach the console + network captures as PASS evidence (a clean result still needs proof it was exercised).

---

## Post-Session (MANDATORY — enforced)
Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted -> **HALT and tell the user**; never claim success.

1. **Write/update** a memory file under `~/.claude/projects/c--Users-<user>-<project>/memory/` with the `Write` tool. Frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep for the page/endpoint/symptom; UPDATE an existing entry instead of filing a duplicate.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer.
4. **Content:** flow/page + date, every hidden error found with its **source** (console/network/API/DB/log) and layer, whether the UI masked it, the exact request/status or DB error column, test data (URLs/user IDs), root-cause `path:line` where known, any prior memory confirmed or disproved. Record the silenced errors precisely — the whole value is that the next session knows what the UI hides here.
5. **Verify:** `ls -la ~/.claude/projects/c--Users-<user>-<project>/memory/<file>.md` non-zero, else HALT.
