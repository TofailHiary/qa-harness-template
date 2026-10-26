---
name: api-contract-check
description: Use when an API endpoint changed and an OpenAPI, Postman or GraphQL contract exists, when a consumer reports a breaking change after a backend deploy, or when the live API and its documented contract may have drifted apart. Triggers include "is this a breaking change", "does the API still match the spec", "check the contract", "diff the response against OpenAPI", "the mobile client broke after the backend release".
argument-hint: "endpoint(s) or PR, plus where the contract lives if known (OpenAPI file, Postman collection, GraphQL schema)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__http-client__http_get", "mcp__http-client__http_post", "mcp__http-client__http_request", "mcp__http-client__set_default_headers", "mcp__postman-api-mcp__*", "mcp__github__get_file_contents", "mcp__github__pull_request_read", "mcp__mcp_server_mysql__mysql_query", "mcp__filesystem__write_file", "Skill(qa-standards)", "Skill(api-test)", "Skill(test-data-manager)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# API Contract Check — live behaviour vs the documented contract

> **Capability gate:** This skill requires **API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no API configured, so `/api-contract-check` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Compare what an endpoint **actually** sends and accepts with what its contract **promises**, classify every
difference as additive, breaking or undocumented, and name the consumers each one hurts. `api-test` asks
"does the endpoint behave correctly?"; this skill asks "does it still behave the way every client was told it
would?" — a correct endpoint can still break a client.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session. Verdict words come
from its **Verdict Contract**; the expected shape comes from its **Authoritative Source Hierarchy** (the contract
is the source, the live response is the observation). Register and ledger rows go into
`qa-evidence/<run-folder>/run.json` (qa-standards → `references/run-record.md`). Postman is optional
(`PROJECT-PROFILE.md §2`): without it the contract is a file in a repo or the schema the server publishes.

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which endpoint(s) or PR? Where does the contract live (OpenAPI file and branch, Postman collection, GraphQL schema)? Which clients consume it? Test (default) or Dev?"

Do NOT guess the contract. Do NOT send a request until the Scope Lock is filled.

## Scope Lock (before any request)

| Field | Value |
|---|---|
| Endpoints / operations | |
| Contract source + version | file `path @ commit`, Postman collection + request id, or the schema the server publishes |
| Baseline contract | the version consumers were built against (usually the default branch) |
| Consumers in scope | web client, admin, report API, mobile, partner webhooks, async workers (`PROJECT-PROFILE.md §9/§11`) |
| Environment | Test (default) / Dev — `PROJECT-PROFILE.md §5`; prod is never a target |
| Branch / commit under test | `git rev-parse --short HEAD` in `<backend repo: PROJECT-PROFILE.md §3/§9>` — stamps every ledger row |
| Non-GET operations | listed — each one goes through the Mutation Safety Gate |

---

## Step 1 — Locate the contract, and decide which version is authoritative

| Source | Where | Notes |
|---|---|---|
| OpenAPI / Swagger file | Glob `**/openapi*.{yml,yaml,json}` and `**/swagger*.{yml,yaml,json}` in `<backend repo: PROJECT-PROFILE.md §3/§9>` | read it at BOTH the baseline commit and the PR head (`git show <ref>:<path>`, or `mcp__github__get_file_contents` with `ref`) |
| Postman collection | collection ids in `PROJECT-PROFILE.md §13`; `mcp__postman-api-mcp__*` when Postman is `on` | saved example responses are part of the contract |
| GraphQL schema | `*.graphql` SDL in the repo; introspection against Test only | introspection is a read; it may be disabled outside Test |
| Typed tools | `PROJECT-PROFILE.md §14` | a typed tool's input/output schema is a contract too |
| Consumer contract | the client's types / validators in `<frontend API layer: PROJECT-PROFILE.md §9>` (TypeScript interfaces, zod / yup schemas, generated clients) | what the consumer actually relies on — diff against it as well |

- Record each contract element as `path:line` (or collection + request id): that is the **expected source** of its row.
- Two contracts disagree (the OpenAPI file says one thing, the Postman example another)? That is a finding on its
  own — record both, take the higher source per the Hierarchy, and file the disagreement.
- **No contract at all:** say so. Contract rows are BLOCKED (unblock: "publish the contract or point me to it");
  offer `Skill(api-test)`, which treats the route handler and its validation schema as the contract.

## Step 2 — Capture the live behaviour

Authenticate per `Skill(api-test)` → Authentication (one session per role; clear stale default headers first).
Prefer the `PROJECT-PROFILE.md §14` typed tools when they exist, otherwise `mcp__http-client__*`. Per operation:

1. **A record that fills every optional field.** `Skill(test-data-manager)` finds one. A field that is `null` in
   every sample was never observed in its non-null type — its type row is NOT YET VERIFIED, not PASS.
2. **Every documented status code** — the 2xx plus each 400 / 401 / 403 / 404 / 409 / 422 the contract lists —
   and the error body of each.
3. **Enum width.** For every enum field, `SELECT DISTINCT` on the DB column behind it with
   `mcp__mcp_server_mysql__mysql_query` (DB tool: `PROJECT-PROFILE.md §6`). The set the API can emit is the DB
   set, not the values you happened to see.
4. **Requests too.** Send only the documented required fields; then add one undocumented field; then drop each
   required field in turn. A contract also promises what the server rejects.
5. **Non-GET operations** go through the Mutation Safety Gate in `Skill(api-test)` (snapshot, rollback plan,
   restore, verify). Never against prod.

Save every request/response pair (secrets as `[REDACTED]`) in the run folder with `mcp__filesystem__write_file`
— `Write`/`Edit` are hook-blocked under `qa-evidence/`.

## Step 3 — Diff element by element

| Dimension | Compare |
|---|---|
| Operation | path + method exist; deprecated flag; the documented auth / security scheme is actually enforced |
| Status codes | each documented code is reachable; any undocumented code observed |
| Response fields | present / absent; type; format (`uuid`, `date-time`); `null` vs missing vs empty (qa-standards → Judgement Discipline 2) |
| Required set | fields the contract marks required are always present |
| Enums | contract enum vs DB distinct values vs the consumer's union — in BOTH directions |
| Additional properties | fields the live response carries that no contract version lists |
| Request validation | the server rejects what the contract forbids and accepts what it allows |
| Headers | pagination, versioning (the header `PROJECT-PROFILE.md §5` names), content type, caching |
| Pagination / errors | page shape (cursor vs offset), error body (code, message, field errors) |

## Step 4 — Classify every difference

| Class | Meaning | Typical examples |
|---|---|---|
| **Additive** | documented in the new contract and safe for existing consumers | new optional response field, new endpoint, new optional request field |
| **Breaking** | an existing consumer can fail | removed / renamed field, type change, `nullable` introduced, new required request field, changed status code, enum value removed from a request or added to a response, pagination or error-shape change, auth tightened without notice |
| **Undocumented** | the live API does something no contract version says | extra response field (check it for data exposure), undocumented status code or endpoint |
| **Contract-only** | documented, never implemented | a field the contract promises that is never sent |

**Judge "additive" from the consumer's side.** A new enum value is additive for the producer and breaking for a
client that switches exhaustively over the old set — Grep the consumer's union or `switch` before you call it
safe. Every difference is an anomaly: it ends as a finding or as "expected" with a cited source (a contract
changelog entry plus the consumer's migration), per `.claude/rules/anomaly-disposition.md`.

## Step 5 — Name the consumers each difference hurts

For every Breaking or Undocumented row, Grep each consumer in scope (the API layer in `PROJECT-PROFILE.md §9`,
admin, report API, async consumers and webhooks in `§11`) for the field or the status code. Each consumer is its
own register row: it handles the difference (PASS, evidence = `path:line`) or it does not (FAIL, evidence =
`path:line` + the live pair). A shared client library fixed is not every consumer fixed (Judgement Discipline 4).

**Layer.** Live wrong, contract right → BE. Live right, contract stale → BE (the contract is a backend artifact
and every generated client inherits the error). Consumer does not handle a documented change → FE (or Admin /
Report). An undocumented field carrying data the caller must not see is also a security lead for `security-review`.

## Output

| # | Operation | Element | Contract says (source) | Live (evidence) | Class | Consumers affected | Result |
|---|---|---|---|---|---|---|---|

Worked example: [references/contract-diff-example.md](references/contract-diff-example.md).

- One register row per operation × differing element, plus one per consumer row from Step 5, written to `run.json`.
  Every row ends as **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED** (qa-standards → Verdict
  Contract); a FAIL carries the contract `path:line` as its `expected_source`.
- Every FAIL goes through `Skill(bug-verifier)` before it counts; confirmed ones go to `Skill(bug-report)`.
- Check the record before you state a result:
  `python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>`.
  Called from an orchestrator, append to its `run.json` and leave the run verdict to the orchestrator.
- Name the escape classes you actively checked (qa-standards → Escape classes & their gates).

## Sub-agents and plugins
- If `PROJECT-PROFILE.md §16` allows sub-agents, the `api-tester` agent may capture the live pairs under this
  Scope Lock; its output is a lead — reproduce any difference it reports before it becomes a row.
- Before claiming PASS: `superpowers:verification-before-completion` if installed (`PROJECT-PROFILE.md §17`);
  otherwise by hand — re-send the request behind every row in this session and re-read the contract line it cites.

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Naming `project_<slug>.md` / `feedback_<slug>.md` / `reference_<slug>.md`; frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the operation, the contract file and the symptom; UPDATE an existing entry instead of filing a duplicate. A prior fact this run disproved is marked **SUPERSEDED** (date + evidence id), never silently deleted.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer carrying the date in the title: `- [<title> YYYY-MM-DD](<file>.md) — <hook>`.
4. **Content:** operations checked + date + Env + commit, the contract source and version (so the next run starts from it), counts per class, verdict in Verdict Contract words, findings (ID, layer, NEW/DUPLICATE), the consumers that break, any mutation made + restored.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
