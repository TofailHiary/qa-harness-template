---
name: test-together
description: Use when the user wants to pair-test a story, ticket, feature or fix with you in a shared browser, asks you to open the browser and tell them what to click, or wants live data and steps for a quick manual smoke test on Test or Dev. Triggers include "test this together", "let's test APP-123 together", "open the browser and tell me what to click", "guide me through the smoke test", "give me the steps and the data for a manual check".
argument-hint: "ticket key, story text, or feature to pair-test"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__mcp_server_mysql__mysql_query", "mcp__http-client__*", "mcp__claude_ai_Atlassian__getJiraIssue", "mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql", "mcp__filesystem__*", "Skill(qa-standards)", "Skill(login)", "Skill(test-data-manager)", "Skill(bug-report)", "Write"]
---

# Test Together: guided pair-testing in a shared browser

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/test-together` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.
>
> **DB** and **API** are optional enhancers. With DB `on`, expected values are read from the database
> (`mcp__mcp_server_mysql__mysql_query`, DB tool: `PROJECT-PROFILE.md` §6). With API `on`, from the API
> via `scripts/api_peek.js` or `mcp__http-client__*` (prefer a project MCP server with typed tools if
> `PROJECT-PROFILE.md` §14 lists one). With neither, the user supplies the expected values and every
> case stays labelled **INFERRED** until a quotable source exists.

The user drives the browser. You prepare the data, say what to do next, and check every step from the
live page. A PASS here means "the screen shows what the system's data says right now", which is why every
expected value is read live in this session.

Follows `qa-standards` (Evidence Ledger, Verdict Contract, Execution Register, Memory Ritual). Logins come
from the `login` skill (accounts: `PROJECT-PROFILE.md` §7); fixtures and environment rules from
`test-data-manager`.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which story, ticket or feature are we testing together, and on which environment
(Test by default)?" Do not open a browser until the scope is named.

## Ground rules

- **Environment:** Test by default (`<main app URL: PROJECT-PROFILE.md §5>`). Dev only when a case needs a
  fixture that Test lacks; say so on the sheet. Prod is out of scope for pair-testing (read-only DB counts
  only, per `test-data-manager`).
- **Live values:** read each expected value from the API or DB **during this session**. Data moves between
  sessions *(illustrative: a leaderboard's user pool more than doubled in one day)*, so memory and old
  evidence only tell you where to look, never what to expect.
- **Every expected value needs a quotable source** (qa-standards → Authoritative Source Hierarchy): the API
  response or DB row you read now, formatted by a rule you can cite (rounding, ordering, label text from
  the code). If you cannot quote a source, the case's expected value is **UNKNOWN — ask**; never write
  down what the screen happens to show.
- **One step per message.** The user acts, you verify, then you send the next step.
- **Plain words:** name each control the way the user sees it: card title, button label or arrow icon,
  tooltip text.
- **Hands mostly off:** in the shared browser you may read, hover, measure and switch tabs. Ask before any
  click that changes state, and change data only when the user asks and `test-data-manager`'s Mutation
  Safety Gate is followed.
- **Secrets stay out of the chat:** the data table names the account and the password **env-var name**
  from `PROJECT-PROFILE.md` §7, never the password. Tokens are never pasted or logged.

## Step 1: Scope

1. Read the story or ticket fresh from the issue tracker (`PROJECT-PROFILE.md` §15):
   `mcp__claude_ai_Atlassian__getJiraIssue` with comments when Jira is `on`; otherwise ask the user to
   paste the story and the latest developer notes. The latest dev comments are the current contract.
2. Find the page (FE route or component in `<frontend repo: PROJECT-PROFILE.md §3/§9>`) and the API
   endpoints it calls: grep the FE for the endpoint, and read the BE handler
   (`<routes path: PROJECT-PROFILE.md §9>`) when a value needs explaining.
3. Confirm the build under test is deployed: the FE build (many SPAs print a version line to the console
   at startup — read it with `browser_console_messages` after load — or the hashed bundle name in the page
   source), and the BE via one request that only the new code answers in its new way.
4. Fresh-read the open tickets on this feature (`searchJiraIssuesUsingJql` when Jira is `on`; otherwise
   ask). They become the sheet's "known open, don't report as new" list.

Done when you can state, from reads made now: environment, page URL, API endpoints, FE and BE builds, and
the known-open list.

## Step 2: Data

1. Pick one primary account where the feature has rich data, plus one account for each special shape a
   case needs (a user in several groups, ties, empty state, another role from `PROJECT-PROFILE.md` §8).
   Look in this feature's memory file (`<memory folder: PROJECT-PROFILE.md §12>`), `test-data-manager`,
   and `login`; query the DB to find a missing shape.
2. Prove each account with the API reader. It authenticates with the method you give it and prints the
   response compactly, never the token:
   ```
   node .claude/skills/test-together/scripts/api_peek.js --base <API base URL: PROJECT-PROFILE.md §5> \
        --login-url <login endpoint: PROJECT-PROFILE.md §7> \
        --login-body '{"email":"<role account: PROJECT-PROFILE.md §7>","password":"${QA_USER_PASS}"}' \
        --token-path <dot.path of the token in the login response> \
        --path <endpoint/without/leading/slash> --query "sort=-score&pageSize=10" \
        --pick data.items --fields name,group_names,score
   ```
   `${QA_USER_PASS}` is expanded by the script from the environment, so the password never appears on
   the command line or in the chat. Already have a token? Use `--token-env NAME` instead; a cookie
   session uses `--cookie-env NAME`. Run `node .claude/skills/test-together/scripts/api_peek.js` with no
   arguments for the full option list. Write `--path` **without** a leading slash: Git Bash rewrites `/x`
   into a Windows path (the script undoes that too).

Done when every planned case has an account that logs in and returns the data it needs, or the gap is
named.

## Step 3: Smoke sheet

Write 6 to 10 cases, in the order the user will click:
- the landing state;
- each toggle, direction or tab;
- filters keep the chosen state;
- one case per recently fixed ticket (the regression check);
- one edge: empty state, limits, or long names;
- optional: the network call and a console check.

Each case gets an ID (SM-01, SM-02 …), the account, the action in UI words, the expected result with
concrete live values formatted the way the UI shows them (rounding, "first group +N"), **the source of
that expected value**, and the pass rule. Save the values you fetched with
`api_peek.js --out qa-evidence/<run>/smoke/expected-<case>.json` (or a DB result saved through
`mcp__filesystem__write_file`).

Send three tables: **data** (environment, login, password env-var name, used in), **cases**, and **known
open tickets**.

Done when every case has a concrete expected value read in this session, with its source.

## Step 4: Open the browser

1. Run folder: `qa-evidence/<TICKET-KEY>-<yyyymmdd>/`, or `qa-evidence/SMOKE-<yyyymmdd-HHMMSS>/` when
   there is no ticket.
2. Playwright MCP: `browser_navigate` to the login page, then `browser_snapshot`. Next `browser_type` the
   email and the password (typing replaces any remembered value). Then `browser_click` the login button
   and `browser_wait_for` text unique to the target page. SSO or other login methods: follow the `login`
   skill.
3. Read the starting state with a page probe (`references/page-probes.md`) and compare it with SM-01.
4. Tell the user which account and page are open. Check how the app treats a second tab of the same app
   in one session; if a second tab logs the first one out (some session implementations do), tell the
   user to keep one tab per app — another site in the same tab is fine.

Done when the page is open as the right user and SM-01's state has been read from the page.

## Step 5: Guided loop

For each case on the sheet:

1. **Send one step:** where (card or section title), what to do (the control by its visible label or icon,
   plus its tooltip), and the expected result in at most three lines. End with "type done or send a
   screenshot".
2. **On reply:** list the tabs (`browser_tabs`) and select the one the user used. Probe the live page there
   and read their screenshot too.
3. **Judge:**
   - PASS: name the values that match.
   - FAIL: give the expected and the actual values.
   - The user did a different action: say what you see and guide them to the intended control.
4. **Second read before any FAIL:** wait, then probe again. Confirm the tab. Rule out the items in
   `references/known-noise.md` and any probe misread, such as an empty first cell, hidden nodes, or a
   tooltip not open yet.
5. **Record:** `node .claude/skills/test-together/scripts/smoke_register.js qa-evidence/<run> add <ID> <PASS|FAIL|NA|NYV|BLOCKED> "<what proved it>" [evidence-path]`
6. **Reply:** give the result in one line, then send the next step.

You can run some checks yourself while the user waits; say what you did. You can hover to read a tooltip,
measure overflow, read the console, and list network calls. Save screenshots with an explicit path:
`qa-evidence/<run>/screens/SMOKE-<ID>-<what>.png` (a bare filename lands in the repo root).

Done when every case has a register row. If the user stops early, record the remaining cases as NYV (NOT
YET VERIFIED) — never drop them.

Example of one step *(illustrative)*:
> **Step 2 (SM-02):** On the left card **"Top 10 Accounts"**, next to **Sort**, click the grey **↑**. Its
> tooltip is "Show lowest first".
> Expect: the title changes to "Lowest 10 Accounts"; rows 1-4 show 0%; rows 8-10 are the three accounts
> tied at 57.7% (source: `expected-SM-02.json`, ties keep A-Z order per `<handler path:line>`). Type
> **done** or send a screenshot.

## Step 6: When a case fails

1. Reproduce once more, with a reload or a second account. Capture a screenshot, the console
   (`browser_console_messages`) and the network calls (`browser_network_requests`).
2. Classify the layer: correct API with a wrong screen is FE; a wrong API with a correct DB is BE
   (`qa-standards`, Bug Classification).
3. Fresh-read related tickets. If it is already known, note the key. If it is new, tell the user and offer
   to file it with `bug-report`. File it only when the user says so.

## Step 7: Close

Send:
- **Results:** every case with PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED (Verdict
  Contract). `smoke_register.js qa-evidence/<run> summary` prints the table and the counts.
- **Evidence Ledger:** the expected-value files, screenshots, page-probe reads, and console and network
  reads.
- **Tickets:** the state of every ticket you mention, re-read now.
- **Noise:** each noise item you saw, with its source.
- **Confidence line:** `Verified N of M cases; BLOCKED k; NOT YET VERIFIED j; Remaining Risk: …`

Then run the memory ritual (`qa-standards` → Memory Ritual): update the feature's memory file under
`<memory folder: PROJECT-PROFILE.md §12>` with the accounts that worked (identifiers only), the
expected-values path, the results, and any new noise with its source. Verify with
`ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"`; if it cannot be persisted, HALT and say so.

Some dev builds print the auth token to the console. Treat `.playwright-mcp/` logs as secret: quote only
the lines that carry the signal, and keep the files out of tickets and chats.

## Reference

- `references/page-probes.md`: read cards, tables, toggles and tooltips; measure overflow; tabs, console,
  network. Adapt the selectors to your UI library.
- `references/known-noise.md`: things that look like bugs but are not, each with its source. Add a row
  when you confirm a new one; an item without a source is a finding, not noise.
- `scripts/api_peek.js`: pluggable-auth GET reader (`node scripts/api_peek.js` prints usage).
- `scripts/smoke_register.js`: the per-case results register and the close-out summary.
