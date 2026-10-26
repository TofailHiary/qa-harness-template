---
name: configure-project
description: Use FIRST on a fresh install of this QA harness, or to reconfigure it — when PROJECT-PROFILE.md is blank, a capability must be switched on or off, a new MCP server is needed, the DB tool must be rebound, or the user says "configure this harness", "set up QA for my project", "read SETUP.md and configure". Asks the user ONLY for secret values and for approval to add a new server.
argument-hint: "(none) — run on a fresh project; re-run after a restart to finish live-verify"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "AskUserQuestion", "Write", "Edit", "mcp__filesystem__*"]
---

# Configure Project — QA Harness Bootstrap (auto-provisioning)

Fit this generic QA harness onto THIS project with as little user work as possible. **Do everything you
can automatically** (detect, install, configure, write files, rebind skills). **Ask the user only for
two things:** (1) secret values you cannot know, and (2) yes/no approval before adding a brand-new MCP
server that is not in the template. When the user lacks a capability ("no access / N/A"), mark it `off`
and move on — never block the whole setup.

Source of truth = `.claude/PROJECT-PROFILE.md` (§1–§18). Worked example = `PROJECT-PROFILE.example.md`.
Capability→skill map = `docs/capability-matrix.md`. MCP template = `.mcp.json.template`. Component
catalog = `catalog.json` (what is installed and what each component needs).

## Step 1 — Detect (no questions yet)
Inspect the project root. Do not assume any stack. From `package.json`/`composer.json`/
`requirements.txt`/`go.mod`/`pom.xml`/`Gemfile` get language+framework; from `git remote -v` + sub-folders
get repos+branches; from `.env.example`/`docker-compose.yml`/`prisma/schema.prisma`/`knexfile*`/
`ormconfig*`/`config/database.*` get the DB engine + connection shape; a routes/controllers dir → API; a
FE framework marker (`vite`/`next`/CRA/Angular/Vue) → Browser; a `workers/`, `lambda/`, `serverless.yml`,
`template.yaml` or cron config → async consumers (§11); a `.jira`/`JIRA_*` reference or ticket keys in
commit messages → tracker + ticket pattern (§15); an in-house MCP server folder → §14. Note which MCP
servers the detected stack implies (e.g. Postgres engine → a Postgres MCP, which is NOT in the template).
Also detect the demo prerequisites: `node .claude/skills/demo-creator/scripts/setup.js --check`
(Demo capability). Show a short "here's what I detected" summary.

## Step 2 — Ask only for the gaps (one area at a time)
Walk §1→§18. For each area show what you detected and ask the user ONLY to confirm or fill what you
could not infer. Prefer `AskUserQuestion` for bounded choices. For §6 DB and §7 Auth, secrets
default to **environment variables**: confirm the variable NAMES (the template's `${QA_DB_PASS}` style, or
the user's own) and never ask for the values. Only if the user explicitly asks to store values inline in
the git-ignored `.mcp.json` do you take them (Step 5) — `doctor.py` will keep warning about it. If the user says "no access / N/A" for an area, set its
`§2 Capability Map` flag `off` with a one-line reason and continue. For §12 ask which repos are
QA targets (protected) and which are the team's own tooling (owned — edits/commits allowed). For §15
ask the tracker, project key, ticket id pattern and the filing/transition rules. For §16 confirm the
policy knobs (defaults: strict-binary verdict, sub-agents allowed, execute every case, gate advisory).
For §17 check `claude plugin list` (or ask) whether `superpowers` / `mattpocock-skills` are installed.

## Step 3 — Write the profile
Write all answers into `.claude/PROJECT-PROFILE.md` (the `Write` tool is allowed for this file). Set §2
accurately. Record, in §6, the **MCP tool id** that will serve the DB (e.g.
`mcp__mcp_server_mysql__mysql_query` for MySQL, `mcp__postgres__execute_sql` for the Postgres MCP) — this
is the "tool binding" used in Step 6. Seed `.claude/references/system-map.md` section 1 (repos +
branches) from §3 so the map starts verified.

## Step 4 — Provision prerequisites (automatic, via Bash)
Run and report:
- `node -v` and `python --version`. If either is missing, print the exact install command for the
  user's OS and pause (this is an OS-level install you cannot silently do).
- The bundled http-client server needs nothing (`node` + built-ins).
- For each ENABLED capability, the MCP server is launched via `npx -y …`, which auto-installs on first
  use — so there is no separate install. Optionally warm the cache + surface errors early, e.g.
  `npx -y @benborla29/mcp-server-mysql --help` (DB), and for Browser run
  `npx playwright install chromium` (real browser download).
- Demo (only if the user wants demo videos): `node .claude/skills/demo-creator/scripts/setup.js`
  installs Playwright into the project, the Chromium build, `edge-tts` and (on Windows) ffmpeg; set
  `Demo: on` in §2 only when it prints `READY`, and fill §18 defaults.

## Step 5 — Generate .mcp.json + harness-config.json (automatic)
- Run `python .claude/scripts/render_mcp.py`. It writes `.mcp.json` from the template and §2: project path
  substituted, servers of `off` capabilities disabled, `cmd /c` added on Windows only, secrets left as
  `${VAR}` placeholders, servers it does not know (a §14 project server, a Postgres server) kept. Show the
  user the export lines it prints (names only). `Read(.mcp.json)` is denied in settings.json on purpose:
  never open the rendered file to "check" it — re-run the renderer with `--dry-run` instead.
- Inline secrets (only on the user's explicit request): pass them as the server's env through
  `render_mcp.py --add-server <name>='<json>'` built by the user, or let the user edit `.mcp.json` by hand.
  Never echo a value back. If §14 names a project MCP server, add it with `--add-server`.
- Write `.claude/hooks/harness-config.json`: `memory_root` (blank = auto-derive), `evidence_root`
  (`qa-evidence`), `protected_repos` = the QA-target repo folder names from §3/§12, `owned_repos` = the
  owned folder names from §12 (or `[]`), keep `allowed_write_globs`, and `gate` =
  `{"enforce": false, "ticket_id_pattern": "<regex from §15>", "extra_concession_phrases": [], "extra_example_markers": []}`.
  Set `gate.enforce` true only when §16 says the gate is enforced (then also tell the user to restart).
- **The guard config is checked by content.** Adding protected repos, removing owned repos and narrowing
  the allow-globs always go through. Adding an OWNED repo, removing a protected repo, widening
  `allowed_write_globs`, moving `memory_root` / `evidence_root` into risky places or switching an enforced
  gate off LOOSENS the guards: the Write is blocked unless the human started Claude Code with
  `QA_HARNESS_ADMIN=1`. When §12 names owned repos, show the user the exact `"owned_repos": [...]` line
  and let them add it by hand (or restart with the variable set) — never look for another way around it.

## Step 5b — Add a server NOT in the template (only with approval)
If Step 1 found the project needs an MCP server the template lacks (Postgres, Mongo, Redis, a cloud SDK,
etc.):
1. Use `AskUserQuestion` to propose it ("Your project uses Postgres — add the Postgres MCP server? It
   runs via `npx -y <pkg>`."). Only proceed on yes.
2. Add it with `python .claude/scripts/render_mcp.py --add-server <name>='<json>'` (pinned version,
   `${VAR}` placeholders for secrets, `"_capability"` set) — it is kept on every re-render.
3. Record its tool id in PROJECT-PROFILE §6 (or §14 for a project server) for Step 6.
4. Warm it with `npx -y <pkg> --help` and report success/failure.

## Step 6 — Bind tools + toggle skills (automatic)
- **Tool rebind (only if a tool id differs from the template default).** The template's DB skills/agents
  call `mcp__mcp_server_mysql__mysql_query` (prod: `mcp__mcp_server_mysql_prod__mysql_query`). If §6 names
  another id (Postgres, Mongo, a §14 server), run:
  ```bash
  python .claude/scripts/rebind.py --db <NEW_DB_TOOL_ID> [--prod-db <NEW_PROD_TOOL_ID>]
  ```
  It replaces whole tool ids in skills, agents, rules and CLAUDE.md (including `allowed-tools`) and records
  the binding in `.claude/tool-bindings.json`; `scripts/install.py` re-applies it after every upgrade, so
  the rebinding is never silently undone. `rebind.py --check` must print `tool bindings: OK`. SQL written
  for MySQL in skill examples stays MySQL — note the engine in §4 so the skills translate the dialect.
- **Skill toggle.** Each `required`/`any[...]` skill self-disables via its capability guard when its
  capability is `off`. Optionally declutter by moving disabled skills into `.claude/skills-disabled/`
  with Bash `mv` (reversible; `.claude` is writable). Report the active vs disabled list from
  `docs/capability-matrix.md`.

## Step 7 — Live-verify (after the user approves + restarts)
New project MCP servers require (a) the user to approve them at Claude Code's trust prompt and (b) a
restart to connect. So:
- If you just wrote/added servers, tell the user: **"Approve the MCP servers when Claude Code asks, then
  restart Claude Code and run `/configure-project` again to finish verification."** Then stop cleanly.
- On the re-run (servers now live), probe each ENABLED capability and report pass/fail: DB `SELECT 1`;
  API GET a health/base URL; Browser open the app URL + snapshot; GitHub read the repo; Postman list
  collections; Jira read one ticket; §14 server status tool; Demo `setup.js --check`. Any failure →
  flip that capability `off` (or tell the user the one thing to fix).
- Run `python .claude/scripts/doctor.py`. It must end with READY: interpreters, Git Bash / sh, node, the
  hook wiring, a live self-test of every guard through `run-hook.sh`, the profile, `.mcp.json` (placeholders
  vs inline secrets, never the values) and the tool bindings. Any FAIL row is fixed before testing starts.
- Run `python scripts/validate.py --installed` too when the template's `scripts/` folder was installed.

## Step 8 — Summary + memory
Print the final Capability Map: what works now, what is `off` and why, the hook policy (protected vs
owned repos, gate mode), and the EXACT remaining user actions (approve servers / restart / set any
OS-level prereq). Save a memory note: configured project name, enabled capabilities, tool bindings,
tracker rules, date.

## Guardrails
- May write `PROJECT-PROFILE.md`, `settings.json`, `harness-config.json`, `.mcp.json` (Write tool), and
  may edit/move files anywhere under `.claude/**` via Bash (the harness owns those). MUST NOT modify
  product source code, run git writes, or touch protected repos.
- Never ask for, print or read back a secret value. Secrets are environment variables by default; inline
  values exist only when the user explicitly chose them, and are confirmed by name only.
- Idempotent: safe to re-run — re-detect, re-confirm, overwrite generated files, re-probe. Never
  overwrite a filled `PROJECT-PROFILE.md` section the user did not ask to change.
