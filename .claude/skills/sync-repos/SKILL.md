---
name: sync-repos
description: Use at the start of a QA task to make sure local repos reflect the current code under test — pulls the latest commits on the correct branch for every application repo (or a single named repo). Triggers include "sync the repos", "pull latest before testing", "update <backend repo: PROJECT-PROFILE.md §3/§9>".
argument-hint: "optional: specific repo name"
allowed-tools: ["Bash", "Read", "mcp__github__*"]
---

# Sync Repositories

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/sync-repos` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Pull the latest code for all application repositories so QA runs against current code.

**Read-only git only.** This utility uses non-mutating git operations exclusively — `pull` / `fetch` / `status` / `branch --show-current` / `log`. It never `commit`s, `push`es, `merge`s, `checkout`s, or otherwise rewrites a repo (the Bash hook blocks those anyway). If a repo is on the wrong branch, **report it** — do not switch it automatically.

## ARGUMENTS
$ARGUMENTS

---

## Repositories & Branches

| Repository | Branch | Path |
|------------|--------|------|
| <legacy frontend repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<legacy frontend repo: PROJECT-PROFILE.md §3> |
| <frontend repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<frontend repo: PROJECT-PROFILE.md §3/§9> |
| <backend repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<backend repo: PROJECT-PROFILE.md §3/§9> |
| <admin repo: PROJECT-PROFILE.md §3/§9> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<admin repo: PROJECT-PROFILE.md §3/§9> |
| <report repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<report repo: PROJECT-PROFILE.md §3> |
| <apps repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<apps repo: PROJECT-PROFILE.md §3> |
| <apps repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<apps repo: PROJECT-PROFILE.md §3> |
| <migrations repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<migrations repo: PROJECT-PROFILE.md §3> |
| <lambda repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<lambda repo: PROJECT-PROFILE.md §3> |
| <integration repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<integration repo: PROJECT-PROFILE.md §3> |
| <infra repo: PROJECT-PROFILE.md §3> | <branch: PROJECT-PROFILE.md §3> | <project root: PROJECT-PROFILE.md §3>/<infra repo: PROJECT-PROFILE.md §3> |

**Branch names are case-sensitive!** Use the branch names defined in PROJECT-PROFILE.md §3.

---

## Sync Flow

### If a specific repo is provided in $ARGUMENTS:
1. Navigate to that repo's path.
2. Check current branch: `git -C [path] branch --show-current`.
3. If it is on the wrong branch, **stop and report it** (do not check out — read-only). The caller decides whether to switch.
4. Pull latest: `git -C [path] pull origin [branch]`.
5. Verify: `git -C [path] log --oneline -3`.
6. Optionally use `mcp__github__list_commits` to compare local vs remote HEAD.

### If no arguments (sync all):
For each repo in the table:
1. Check the directory exists.
2. Check the current branch (`git -C [path] branch --show-current`).
3. If on the wrong branch, flag it in the Issues table (do not auto-switch).
4. Pull latest (`git -C [path] pull origin [branch]`).
5. Report status.

---

## Output Format

### Repository Sync Status

| Repository | Branch | Status | Last Commit |
|------------|--------|--------|-------------|
| <legacy frontend repo: PROJECT-PROFILE.md §3> | <branch: §3> | Up to date / Updated / Wrong branch / Error | [hash] [message] |
| <frontend repo: PROJECT-PROFILE.md §3/§9> | <branch: §3> | Up to date / Updated / Wrong branch / Error | [hash] [message] |
| <backend repo: PROJECT-PROFILE.md §3/§9> | <branch: §3> | Up to date / Updated / Wrong branch / Error | [hash] [message] |
| ... | ... | ... | ... |

### Issues (if any)

| Repository | Issue | Resolution |
|------------|-------|------------|
