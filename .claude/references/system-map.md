# System Map — verified from code and the live DB, not from docs (TEMPLATE)

> This file is the project's own verified map. `/configure-project` seeds the headings; **every QA
> run verifies and extends at least one section** and stamps it `verified YYYY-MM-DD / source`.
> A section older than 60 days is UNVERIFIED — re-check it before relying on it. Where something is
> not verified, say so. Never paste documentation here that was not read from code or queried live.
> No secrets, no account passwords; identifiers only.

## 1. Repositories (verified — / `git branch --show-current` in each)

| Repo (`PROJECT-PROFILE.md §3`) | Branch | Owns |
|---|---|---|
|  |  |  |

## 2. Backend API surface (verified — / the route mounts in `<backend repo>/<server entry>`)

| Mount | Router file (under `<routes path: PROJECT-PROFILE.md §9>`) | Auth / roles |
|---|---|---|
|  |  |  |

Route folders present but NOT mounted (verify before assuming reachable):

## 3. Admin panel (verified — / `<admin controllers path: PROJECT-PROFILE.md §9>`)

Controllers / modules and what each one drives (e.g. a deploy action → queue → worker):

## 4. Frontend pages & route constants (verified — / `<frontend pages path: PROJECT-PROFILE.md §9>`)

Pages by role; the route-constants file; the API-call layer; i18n location and fallback language:

## 5. Database families (verified — / `information_schema` on `<test DB name: PROJECT-PROFILE.md §6>`)

Table families by prefix with counts; core join paths and the soft-delete mechanism per table
(`.claude/rules/db-gotchas.md` is authoritative); columns whose `COLUMN_COMMENT` carries a contract:

## 6. Async chains — where the terminal writer lives (verified — / code)

| Action | Enqueue | Terminal writer | Silent-failure mode |
|---|---|---|---|
|  |  |  |  |

## 7. Armed latent risks — the watch-list (verified — / `prod-sentinel` S3/S4, `latent-pattern-sweep`)

| Risk (assumption + `path:line`) | Trigger that fires it | Status (ARMED / LIVE / SAFE) |
|---|---|---|
|  |  |  |

## 8. Fixtures — see `test-data-manager` → INPUT-CLASS FIXTURE REGISTRY (authoritative; not duplicated here)

## 9. How to search this system (recipes that worked)

- **Is a fix deployed?** fetch the site root, extract the hashed entry bundle name, find the lazy chunk
  name inside it, then grep that chunk for a unique string or regex from the fix; or call the backend
  version/health endpoint; or send one request only the new code answers in its new way.
- **Which code path rendered this screenshot?** match the LABEL text to the ternary in the component
  — it pins the mode flags uniquely.
- **When did a defect go live?** `git log -S '<exact line>'` for the code date; `MIN(created_at)` of
  the 2nd row in the partition for the data date.
- **Is this a data-triggered latent bug?** `Skill(latent-pattern-sweep)`.
- **Did the fix touch the root cause?** `git diff --name-only <base>..<fix>` must list the file the
  ticket names.
- **Does the API actually get called on Save?** `browser_network_requests` filtered on the route; a
  per-card Save on an existing card may make NO request.
- **Which sub-agents get which rules?** rules with a `paths:` frontmatter load conditionally; without
  it, always. Agents preload only `qa-standards` — put agent-binding rules there.
