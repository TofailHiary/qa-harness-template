---
name: evidence-manager
description: Use when another QA skill must capture, name and file evidence (API response, screenshot, log, CSV, note) in the run folder, or assemble the Evidence Ledger and run record. Triggers include "save this as evidence", "set up the evidence folder for this bug", "assemble the evidence ledger", or a skill handing off proof to be filed. A helper: it files evidence, it does not test.
argument-hint: "the finding (ticket key or BUG-id) + the artifact(s) to file"
allowed-tools: ["Bash", "Read", "Glob", "mcp__filesystem__*", "mcp__playwright__*", "Skill(qa-standards)", "Write"]
---

# Evidence Manager — Capture & Assemble the Evidence Ledger

> **Capability note:** this skill is **always on** (utility — see `docs/capability-matrix.md`). It needs only the filesystem MCP; `mcp__playwright__*` screenshots are used only when Browser is `on` in `PROJECT-PROFILE.md` §2.
>
> **No profile at all? (user-level install - there is no `.claude/PROJECT-PROFILE.md`.)** Do not stop.
> Ask once for what this skill needs - where the run folder should live (default `./qa-evidence`) and the run's ticket key or a BUG timestamp - label every conclusion that rests on those
> answers INFERRED, skip the steps whose tools are not available and say which, and if no memory
> folder exists say in one line that memory was not persisted. A profile that EXISTS but is blank still
> means: run `/configure-project`.

A utility helper. It captures and organizes QA evidence consistently and assembles the Evidence Ledger, per the qa-standards "Evidence folder convention" and "Evidence provenance" sections. Called by `bug-verifier` and `full-qa`; any other skill (db-check, api-test, browser-test, regression-runner, qa-report) may call it when it needs to file attachments — it files proof and hands back a ledger — **it does not run tests, lock scope, mutate data, or persist memory.** Those rituals belong to the finding-producer that called it.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; the **Evidence Ledger** + folder convention it serves are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which finding is this evidence for — a ticket (`<TICKET-KEY>`, pattern in `PROJECT-PROFILE.md §15`) or a bug (`BUG-YYYYMMDD-HHMMSS`)? And what artifact(s) am I filing (API response / screenshot / log / CSV / note)? And what are the provenance values — Env, Branch / Commit, Captured at?"

Do NOT guess the finding or invent artifacts. Do NOT save anything until the finding ID is known.

---

## Step 1: Create the run folder

**ONE convention** (qa-standards -> Evidence folder convention): `qa-evidence/<TICKET-KEY or BUG-YYYYMMDD-HHMMSS>-<yyyymmdd>/` — e.g. `qa-evidence/APP-123-20260827/`, `qa-evidence/BUG-20260827-143012-20260827/`. `<TICKET-KEY>` follows the ticket pattern in `PROJECT-PROFILE.md §15`; the `HHMMSS` avoids collisions across parallel sessions. The older `BUG-YYYYMMDD-HHMMSS/` and `<FEATURE-SLUG>/` forms are retired — do not create them.

**Prior-run lookup first:** before creating a folder, `grep -rl <ticket key or symptom> qa-evidence/` (or `mcp__filesystem__search_files`) to find an earlier run folder for the same finding. Reference what you find in the ledger as **historical** (qa-standards → Fresh vs Historical) — never as current evidence; today's run gets today's dated folder.

Create it with `mcp__filesystem__create_directory`. If it already exists, reuse it (do not clobber sibling artifacts).

## Step 2: Save each artifact with standard naming

`<slug>` = the ticket key or bug ID (plus a short suffix when several artifacts share a type). Save under the run folder:

| Artifact | Filename | Notes |
|---|---|---|
| API request/response | `<slug>_api-response.json` | full request + response pair, with the role/account used (identifier only — never a password or token) |
| Screenshot | `<slug>.png` | Pass `filename: qa-evidence/<run folder>/<slug>.png` to browser_take_screenshot |
| Log / error output | `<slug>.log` | console output, stack traces |
| DB dump / query result | `<slug>.csv` | the exact rows that prove the claim, plus the query that produced them |
| Notes | `<slug>_evidence.md` | supporting notes only — NOT the bug report |
| Config | `<slug>.yml` (or `.json`) | relevant config snippet where it matters, secrets `[REDACTED]` |
| Red-loop command | `<slug>_repro.sh` / `.ts` | the one command that goes red on the symptom, and its red output |

## Step 3: HOW to write into qa-evidence (IMPORTANT mechanism)

The read-only QA hook **BLOCKS the `Write`/`Edit` tools** for `qa-evidence/`. To persist an artifact, use one of:
1. **`mcp__filesystem__write_file`** with the target path (preferred).
2. **Bash heredoc** into the folder (`cat > qa-evidence/.../<slug>.json <<'EOF' ... EOF`).
3. **Playwright screenshots** — call `mcp__playwright__browser_take_screenshot` with `filename: qa-evidence/<run folder>/<name>.png` (a bare filename saves to the repo root). The PostToolUse hook is a backstop only.

Never reach for `Write`/`Edit` here — it will be blocked by design.

## Step 4: Assemble + output the Evidence Ledger

**Machine-readable twin.** Every ledger row also goes into `qa-evidence/<run-folder>/run.json` -> `ledger`
(`qa-standards/references/run-record.md`): `id`, `type`, `file` (exactly as saved in the run folder, or a
URL / `path:line`), `env`, `commit`, `captured_at`, `proves`. Write it with the filesystem MCP or a Bash
heredoc. `python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder> --partial`
proves every id resolves to a file; `--package` renders the auditor's `package.md`; `--summary qa-evidence`
lists every run (verdict, N/M, blocked, not-yet-verified, skipped phases, record consistency).

Collect every artifact filed (plus any code/Postman/GitHub references the caller passed) into the ledger and return it to the calling skill. Provenance columns are mandatory on every row (qa-standards → Evidence provenance):

| Evidence ID | Type | Source | File / URL / Tool | Env | Branch / Commit | Captured at | What it proves |
|---|---|---|---|---|---|---|---|

Allowed types: DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), Postman contract, GitHub diff/commit.

**Filling the provenance columns:**
- **Env** — TEST / DEV / PROD-readonly, using the surface labels in `PROJECT-PROFILE.md §5/§6`. Record it on EVERY row.
- **Branch / Commit** — `<branch: PROJECT-PROFILE.md §3> @ <short sha>` from `git rev-parse --short HEAD` in the repo that owns the code under test. The caller captures it once at Scope Lock time and passes it in; if it is missing, ask — do not guess.
- **Captured at** — timestamp of the observation (not of the filing).

**Environment attribution rule.** A result observed on DEV, on a replica, or on PROD is evidence for THAT environment only. It may never be filed as evidence for the target environment; if the caller must cross environments, label the row and record why.

---

## Rules (state these to the caller)
- **No evidence = no finding.** A claim with no ledger row does not exist.
- **No provenance = incomplete row.** A row missing Env, Branch / Commit or Captured at goes back to the caller unfilled; it cannot be retested or handed over.
- **Capture proof for PASS too**, not only bugs — a green result needs evidence it was actually exercised (an API call or DB state observed, not just a success toast).
- **Bug reports live in the chat conversation, not as markdown files in `qa-evidence/`.** The folder holds attachments only — no index files, no bug-report `.md`. The `<slug>_evidence.md` note is supporting context, never the report itself.
- **Never file a secret.** Tokens, passwords and API keys are `[REDACTED]` before an artifact is written; account identifiers from `PROJECT-PROFILE.md §7` are fine.
- This helper persists NO memory and makes NO product mutations — the finding-producer that called it owns the Post-Session memory ritual and any Mutation Safety Gate.
