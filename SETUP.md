# Setup — configure this QA harness for your project

You just dropped a generic, read-only QA harness into your project. **Under Claude Code the agent does the
configuration and MCP-server setup for you.** You only paste secret values when asked, approve the servers,
and restart once. (Other runtimes: read `AGENTS.md`, fill `.claude/PROJECT-PROFILE.md` by hand following
`PROJECT-PROFILE.example.md`, and configure your runtime's MCP file and permissions yourself.)

## Do this
1. Open Claude Code with **this project** as the working directory.
2. Say: **"Read SETUP.md and configure this QA harness for my project."**

Claude runs the **`/configure-project`** skill, which automatically:
- **Inspects** your project to detect stack, repos, database, API, frontend, async workers, tracker.
- **Installs / provisions the MCP servers** it needs (Node `npx` servers auto-install; it runs
  `npx playwright install` for browsers, warms each server, and surfaces any problem).
- **Adds a server that isn't in the template** if your stack needs one (e.g. Postgres/Mongo) — it asks
  yes/no first, then installs and wires it, and **rebinds the affected skills automatically**.
- **Writes `.mcp.json`** with the right servers enabled and **puts the secret values you give it straight
  into that file** (which is git-ignored — you never edit a file or set environment variables).
- **Writes `.claude/PROJECT-PROFILE.md`** (§1–§18: environments, DB, accounts, roles, code paths, tables,
  async consumers, evidence/memory paths, optional project MCP, issue-tracker rules, QA policy knobs,
  plugins, demo defaults), wires the read-only hooks (`harness-config.json`: protected vs owned repos,
  gate mode, ticket-id pattern), seeds the system map, and **turns on only the skills your project
  supports** (see `docs/capability-matrix.md`).
- **Live-verifies** each capability and prints a summary.

## What you still do (the only manual bits)
1. **Set the environment variables** Claude names (DB password, API key, …) — it prints the export lines,
   never the values. Values written inline into the git-ignored `.mcp.json` happen only if you ask for it.
2. **Approve the MCP servers** at Claude Code's one-time trust prompt (a security step Claude can't skip).
3. **Restart Claude Code once** so the new servers connect, then say **"continue configuring"** /
   re-run `/configure-project` — it finishes with the live checks.
4. If Node.js or Python is missing, run the one command Claude gives you (OS-level installs may need you).
5. Optional: install the `superpowers` and `mattpocock-skills` plugins (`/plugin` in Claude Code) and
   mark them in `PROJECT-PROFILE.md` §17; every skill works without them.

Then run `python .claude/scripts/doctor.py`: it must end with `READY`.

Re-run `/configure-project` anytime you gain a capability (e.g. you later get database access or want
demo videos — run `node .claude/skills/demo-creator/scripts/setup.js` and set `Demo: on`).

## Safety
Read-only QA: hooks block edits to your **product source code** and git writes. It documents bugs; it
never fixes them. It only writes its own config, the auto-memory folder, the git-ignored `.mcp.json`,
evidence attachments under `qa-evidence/`, and — if you list them in §12 — repos you mark as your own
tooling. Every guard is launched through `run-hook.sh`, which fails closed: a guard that cannot run blocks
instead of allowing. A session cannot loosen its own guards (drop a hook, add an owned repo); that takes a
human, or a session started with `QA_HARNESS_ADMIN=1`. The completion gate is advisory until you set
`QA_GATE_ENFORCE=1`.
