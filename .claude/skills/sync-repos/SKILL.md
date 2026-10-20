---
name: sync-repos
description: Use at the start of a QA task to make sure local repos reflect the current code under test — pulls the latest commits on the correct branch for every application repo (or a single named repo) and reports the HEAD commit per repo for evidence provenance. Triggers include "sync the repos", "pull latest before testing", "update the backend repo", "which commit are we testing", "is the local checkout current".
argument-hint: "optional: specific repo name"
allowed-tools: ["Bash", "Read", "mcp__github__*"]
---

# Sync Repositories

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/sync-repos` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Pull the latest code for all application repositories so QA runs against current code, and record **the HEAD per repo** — it fills the **Branch / Commit** provenance column of every Evidence Ledger row in the session (qa-standards -> Evidence provenance).

**Read-only git only.** This utility uses non-mutating git verbs exclusively — `fetch` / `pull --ff-only` / `status` / `branch --show-current` / `log` / `rev-parse`. It never `commit`s, `push`es, `merge`s, `checkout`s, `stash`es, `reset`s, `rebase`s or clones into place (the Bash hook blocks those anyway). If a repo is on the wrong branch, has local changes, or has diverged, **report it** — do not fix it.

**Capability variants**
- **LocalRepos on** — run the local sync below.
- **LocalRepos off, GitHub on** — remote-only: `mcp__github__list_branches` + `mcp__github__list_commits` report the remote HEAD per repo; state "no local checkout — code reads go through `mcp__github__get_file_contents`".
- **Both on** — sync locally, then compare local HEAD with the remote HEAD from `mcp__github__list_commits`; a difference after the pull is an Issue.

## ARGUMENTS
$ARGUMENTS

---

## Repositories & Branches

The authoritative list is `PROJECT-PROFILE.md §3` (repo path, description, default branch). Build the table from it at run time — do not keep a copy here:

| Repository | Branch (exact, case-sensitive) | Path | Purpose |
|------------|--------------------------------|------|---------|
| `<frontend repo: PROJECT-PROFILE.md §3/§9>` | `<branch: PROJECT-PROFILE.md §3>` | `<project root: PROJECT-PROFILE.md §3>/<frontend repo>` | main app UI |
| `<backend repo: PROJECT-PROFILE.md §3/§9>` | `<branch: PROJECT-PROFILE.md §3>` | `<project root: PROJECT-PROFILE.md §3>/<backend repo>` | API |
| `<admin repo: PROJECT-PROFILE.md §3/§9>` | `<branch: PROJECT-PROFILE.md §3>` | `<project root: PROJECT-PROFILE.md §3>/<admin repo>` | admin panel |
| `<report repo: PROJECT-PROFILE.md §3>` | `<branch: PROJECT-PROFILE.md §3>` | `<project root: PROJECT-PROFILE.md §3>/<report repo>` | reporting service |
| every other repo §3 lists (legacy frontend, pipelines / workers, lambdas, migrations, integrations, infra, CI buildspecs) | `<branch: PROJECT-PROFILE.md §3>` | `<project root: PROJECT-PROFILE.md §3>/<repo>` | as described in §3 |

**Branch names are case-sensitive.** Copy them exactly from §3 — a mixed-case branch such as `Feature-X` is not `feature-x`; git may fail silently or track the wrong ref. Repos in one project routinely sit on *different* branches (`develop`, `main`, a release branch) — never assume one branch for all.

**Auxiliary repos matter.** The code that owns a defect is often outside the app repos *(illustrative)*: a pipeline / worker repo that writes the tables a dashboard reads (the numbers the UI shows are produced there, not by the backend); a CI / buildspec repo that owns the deploy gate (whether a failing check refuses a deploy is decided there, not in the product repo's own build file); a generator tool that produces an input format. §3 lists each with its purpose — sync them before judging a defect in that area, and never conclude "nothing changed" from the app repo alone.

**Missing directory.** If a repo listed in §3 is not cloned, flag it in the Issues table with the clone command recorded in §3 — do **NOT** auto-clone during a sync unless asked. Some hosts require a username-prefixed HTTPS remote or a token because SSH is blocked in the environment; after the first successful clone, record the working form in §3 so nobody rediscovers it.

---

## Sync Flow

### If a specific repo is provided in $ARGUMENTS:
1. Resolve the repo's path and expected branch from §3.
2. Check the current branch: `git -C [path] branch --show-current`.
3. If it is on the wrong branch, **stop and report it** (do not check out — read-only). The caller decides whether to switch.
4. Check for local changes: `git -C [path] status --porcelain` — a dirty tree is reported (never stashed or discarded).
5. Fetch and fast-forward: `git -C [path] fetch --prune origin` then `git -C [path] pull --ff-only origin [branch]`. A refused fast-forward means local commits or a rewritten remote — report **Diverged**, never merge or reset.
6. Record HEAD: `git -C [path] rev-parse --short HEAD` and `git -C [path] log --oneline -3`.
7. Optionally compare with the remote via `mcp__github__list_commits` (GitHub on).

### If no arguments (sync all):
For each repo in §3:
1. Check the directory exists — if missing, flag it in the Issues table with the clone command from §3; do NOT auto-clone.
2. Check the current branch (`git -C [path] branch --show-current`).
3. If on the wrong branch, flag it in the Issues table (do not auto-switch).
4. Check for a dirty tree (`status --porcelain`) — flag, never touch.
5. Fetch + pull `--ff-only` the branch from §3.
6. Record HEAD (`rev-parse --short HEAD`) and report status.

---

## Output Format

### Repository Sync Status

| Repository | Branch | Status | HEAD | Last Commit |
|------------|--------|--------|------|-------------|
| `<frontend repo>` | `<branch: §3>` | Up to date / Updated / Wrong branch / Dirty tree / Diverged / Missing (clone) / Error | `<short sha>` | [message] |
| `<backend repo>` | `<branch: §3>` | ... | `<short sha>` | [message] |
| ... | ... | ... | ... | ... |

### Issues (if any)

| Repository | Issue | Resolution |
|------------|-------|------------|

### Hand-off
Return the list `<repo>: <branch> @ <short sha>` to the calling skill — it goes into the Scope Lock and into the **Branch / Commit** column of every evidence row. A verdict that cannot be tied to a commit cannot be retested.

---

## Post-Session (light — qa-standards -> Memory Ritual)
Write memory only when something durable changed: a new repo in play, a branch rename, a clone quirk (username-prefixed remote, blocked SSH), a repo found on the wrong branch by design. Cross-reference first and UPDATE the existing entry under `<memory folder: PROJECT-PROFILE.md §12>` (`reference_repos_<slug>.md`) instead of filing a duplicate; then `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT and tell the user. A routine "all up to date" run needs no memory write — say so.
