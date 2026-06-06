---
name: configure-project
description: Use FIRST on a fresh install of this QA harness, or to reconfigure it. Auto-detects the project's stack, fills PROJECT-PROFILE.md, INSTALLS + CONFIGURES the MCP servers end-to-end (incl. ones not in the template), writes .mcp.json with your secrets, wires the read-only hooks, rebinds/enables only the skills the project supports, and live-verifies. Asks the user ONLY for secret values and for approval to add a new server. Triggers include "configure this harness", "set up QA for my project", "read SETUP.md and configure".
argument-hint: "(none) — run on a fresh project; re-run after a restart to finish live-verify"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "AskUserQuestion", "Write", "Edit", "mcp__filesystem__*"]
---

# Configure Project — QA Harness Bootstrap (auto-provisioning)

Fit this generic QA harness onto THIS project with as little user work as possible. **Do everything you
can automatically** (detect, install, configure, write files, rebind skills). **Ask the user only for
two things:** (1) secret values you cannot know, and (2) yes/no approval before adding a brand-new MCP
server that is not in the template. When the user lacks a capability ("no access / N/A"), mark it `off`
and move on — never block the whole setup.

Source of truth = `.claude/PROJECT-PROFILE.md` (§1–§13). Worked example = `PROJECT-PROFILE.example.md`.
Capability→skill map = `docs/capability-matrix.md`. MCP template = `.mcp.json.template`.

## Step 1 — Detect (no questions yet)
Inspect the project root. Do not assume any stack. From `package.json`/`composer.json`/
`requirements.txt`/`go.mod`/`pom.xml`/`Gemfile` get language+framework; from `git remote -v` + sub-folders
get repos+branches; from `.env.example`/`docker-compose.yml`/`prisma/schema.prisma`/`knexfile*`/
`ormconfig*`/`config/database.*` get the DB engine + connection shape; a routes/controllers dir → API; a
FE framework marker (`vite`/`next`/CRA/Angular/Vue) → Browser. Note which MCP servers the detected stack
implies (e.g. Postgres engine → a Postgres MCP, which is NOT in the template). Show a short
"here's what I detected" summary.

## Step 2 — Ask only for the gaps (one area at a time)
Walk §1→§13. For each area show what you detected and ask the user ONLY to confirm or fill what you
could not infer. Prefer `AskUserQuestion` for bounded choices. Critically, for §6 DB and §7 Auth, ask
for the **secret values themselves** (passwords/keys) — you will write them into the git-ignored
`.mcp.json` so the user never edits a file. If the user says "no access / N/A" for an area, set its
`§2 Capability Map` flag `off` with a one-line reason and continue.

## Step 3 — Write the profile
Write all answers into `.claude/PROJECT-PROFILE.md` (the `Write` tool is allowed for this file). Set §2
accurately. Record, in §6, the **MCP tool id** that will serve the DB (e.g.
`mcp__mcp_server_mysql__mysql_query` for MySQL, `mcp__postgres__query` for Postgres) — this is the
"tool binding" used in Step 6.

## Step 4 — Provision prerequisites (automatic, via Bash)
Run and report:
- `node -v` and `python --version`. If either is missing, print the exact install command for the
  user's OS and pause (this is an OS-level install you cannot silently do).
- The bundled http-client server needs nothing (`node` + built-ins).
- For each ENABLED capability, the MCP server is launched via `npx -y …`, which auto-installs on first
  use — so there is no separate install. Optionally warm the cache + surface errors early, e.g.
  `npx -y @benborla29/mcp-server-mysql --help` (DB), and for Browser run
  `npx playwright install chromium` (real browser download).

## Step 5 — Generate .mcp.json + harness-config.json (automatic)
- Copy `.mcp.json.template` → `.mcp.json`. Replace every `${PROJECT_ROOT}` with this project's absolute
  path. Set `"disabled": true` on each server whose `_capability` is `off` in §2. **Substitute the secret
  values the user gave you directly into the `env` blocks** (`.mcp.json` is git-ignored, so this is safe
  and means the user sets no environment variables). If the user prefers env vars instead, leave the
  `${VAR}` placeholders and tell them which to export.
- Write `.claude/hooks/harness-config.json`: `memory_root` (blank = auto-derive), `evidence_root`
  (`qa-evidence`), `protected_repos` = the repo folder names from §3, keep `allowed_write_globs`.

## Step 5b — Add a server NOT in the template (only with approval)
If Step 1 found the project needs an MCP server the template lacks (Postgres, Mongo, Redis, a cloud SDK,
etc.):
1. Use `AskUserQuestion` to propose it ("Your project uses Postgres — add the Postgres MCP server? It
   runs via `npx -y <pkg>`."). Only proceed on yes.
2. Add its block to `.mcp.json` (command/args/env), with secrets the user provides.
3. Record its tool id in PROJECT-PROFILE §6 (or a new "Tool bindings" note) for Step 6.
4. Warm it with `npx -y <pkg> --help` and report success/failure.

## Step 6 — Bind tools + toggle skills (automatic)
- **Tool rebind (only if a tool id differs from the template default).** The template's DB skills/agents
  call `mcp__mcp_server_mysql__mysql_query`. If §6's DB tool id is different (e.g. Postgres/Mongo),
  rebind it across the harness by running a one-shot replace via Bash (this edits `.claude/**`, which is
  allowed because `.claude` is NOT a protected source repo — only product repos are write-blocked):
  ```bash
  python - "$CLAUDE_PROJECT_DIR" "mcp__mcp_server_mysql__mysql_query" "<NEW_TOOL_ID>" <<'PY'
  import sys, glob, os
  root, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
  for f in glob.glob(os.path.join(root, ".claude", "skills", "*", "SKILL.md")) + \
           glob.glob(os.path.join(root, ".claude", "agents", "*.md")):
      s = open(f, encoding="utf-8").read()
      if old in s:
          open(f, "w", encoding="utf-8").write(s.replace(old, new))
          print("rebound:", os.path.basename(os.path.dirname(f)) or os.path.basename(f))
  PY
  ```
  (Add the new tool id to the affected skills' `allowed-tools` the same way if it is missing.)
- **Skill toggle.** Each `required`/`any[...]` skill self-disables via its capability guard when its
  capability is `off`. Optionally declutter by moving disabled skills into `.claude/skills-disabled/`
  with Bash `mv` (reversible; `.claude` is writable). Report the active vs disabled list.

## Step 7 — Live-verify (after the user approves + restarts)
New project MCP servers require (a) the user to approve them at Claude Code's trust prompt and (b) a
restart to connect. So:
- If you just wrote/added servers, tell the user: **"Approve the MCP servers when Claude Code asks, then
  restart Claude Code and run `/configure-project` again to finish verification."** Then stop cleanly.
- On the re-run (servers now live), probe each ENABLED capability and report pass/fail: DB `SELECT 1`;
  API GET a health/base URL; Browser open the app URL + snapshot; GitHub read the repo; Postman list
  collections. Any failure → flip that capability `off` (or tell the user the one thing to fix).

## Step 8 — Summary + memory
Print the final Capability Map: what works now, what is `off` and why, and the EXACT remaining user
actions (approve servers / restart / set any OS-level prereq). Save a memory note: configured project
name, enabled capabilities, tool bindings, date.

## Guardrails
- May write `PROJECT-PROFILE.md`, `settings.json`, `harness-config.json`, `.mcp.json` (Write tool), and
  may edit/move files anywhere under `.claude/**` via Bash (the harness owns those). MUST NOT modify
  product source code, run git writes, or touch protected repos.
- Never print a secret back to the user; write it into the git-ignored `.mcp.json` and confirm by name only.
- Idempotent: safe to re-run — re-detect, re-confirm, overwrite generated files, re-probe.
