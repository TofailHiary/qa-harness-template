---
name: evidence-manager
description: Use when another QA skill needs to capture, name, and organize evidence artifacts and assemble the Evidence Ledger — creating the finding folder, saving an API response / screenshot / log / CSV / note with the standard naming, and producing the ledger table. Triggers include "save this as evidence", "set up the evidence folder for this bug", "assemble the evidence ledger", or a producer skill handing off proof to be filed. A utility helper other skills call — it captures evidence, it does not test.
argument-hint: "the finding (BUG-id or FEATURE-slug) + the artifact(s) to file"
allowed-tools: ["Bash", "Read", "Glob", "mcp__filesystem__*", "mcp__playwright__*", "Skill(qa-standards)"]
---

# Evidence Manager — Capture & Assemble the Evidence Ledger

A utility helper. It captures and organizes QA evidence consistently and assembles the Evidence Ledger, per the qa-standards "Evidence folder convention". Other skills (db-check, api-test, browser-test, regression-runner, bug-verifier, qa-report) call it to file proof and hand back a ledger — **it does not run tests, lock scope, mutate data, or persist memory.** Those rituals belong to the finding-producer that called it.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session; the **Evidence Ledger** + folder convention it serves are inlined below.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which finding is this evidence for — a bug (`BUG-YYYYMMDD-HHMMSS`) or a feature run (`<FEATURE-SLUG>`)? And what artifact(s) am I filing (API response / screenshot / log / CSV / note)?"

Do NOT guess the finding or invent artifacts. Do NOT save anything until the finding ID/slug is known.

---

## Step 1: Create the finding folder

One folder per finding (qa-standards -> Evidence folder convention):
- **Bug:** `qa-evidence/BUG-YYYYMMDD-HHMMSS/` — the `HHMMSS` avoids collisions across parallel sessions.
- **Feature / run:** `qa-evidence/<FEATURE-SLUG>/` (lowercase-hyphen slug).

Create it with `mcp__filesystem__create_directory`. If it already exists, reuse it (do not clobber sibling artifacts).

## Step 2: Save each artifact with standard naming

`<slug>` = the bug ID or feature slug. Save under the finding folder:

| Artifact | Filename | Notes |
|---|---|---|
| API request/response | `<slug>_api-response.json` | full request + response pair |
| Screenshot | `<slug>.png` | Pass `filename: qa-evidence/<finding>/<slug>.png` to browser_take_screenshot |
| Log / error output | `<slug>.log` | console output, stack traces |
| DB dump / query result | `<slug>.csv` | the exact rows that prove the claim |
| Notes | `<slug>_evidence.md` | supporting notes only — NOT the bug report |
| Config | `<slug>.yml` (or `.json`) | relevant config snippet where it matters |

## Step 3: HOW to write into qa-evidence (IMPORTANT mechanism)

The read-only QA hook **BLOCKS the `Write`/`Edit` tools** for `qa-evidence/`. To persist an artifact, use one of:
1. **`mcp__filesystem__write_file`** with the target path (preferred).
2. **Bash heredoc** into the folder (`cat > qa-evidence/.../<slug>.json <<'EOF' ... EOF`).
3. **Playwright screenshots** — call `mcp__playwright__browser_take_screenshot` with `filename: qa-evidence/<finding>/<name>.png` (a bare filename saves to the repo root). The PostToolUse hook is a backstop only.

Never reach for `Write`/`Edit` here — it will be blocked by design.

## Step 4: Assemble + output the Evidence Ledger

Collect every artifact filed (plus any code/Postman/GitHub references the caller passed) into the ledger and return it to the calling skill:

| Evidence ID | Type | Source | File / URL / Tool | What it proves |
|---|---|---|---|---|

Allowed types: DB query result, API request/response, Browser screenshot, Console log, Network request, Code file reference (`path:line`), Postman contract, GitHub diff/commit.

---

## Rules (state these to the caller)
- **No evidence = no finding.** A claim with no ledger row does not exist.
- **Capture proof for PASS too**, not only bugs — a green result needs evidence it was actually exercised.
- **Bug reports live in the chat conversation, not as markdown files in `qa-evidence/`.** The folder holds attachments only — no index files, no bug-report `.md`. The `<slug>_evidence.md` note is supporting context, never the report itself.
- This helper persists NO memory and makes NO product mutations — the finding-producer that called it owns the Post-Session memory ritual and any Mutation Safety Gate.
