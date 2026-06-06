---
name: automation-writer
description: Use when a CONFIRMED manual test case should become a runnable automated script — generate a Playwright + TypeScript test for a UI flow, or an HTTP/API test for an endpoint, with real selectors and explicit assertions. Triggers include "automate this test case", "turn this into a Playwright script", "write an API test for this", "make this case repeatable". Expects an already-confirmed case (steps + expected); not for exploring or finding bugs.
argument-hint: "the confirmed manual test case (steps + expected) to automate"
allowed-tools: ["Read", "Grep", "Glob", "mcp__playwright__*", "mcp__filesystem__*", "Skill(qa-standards)"]
---

# Automation Writer — Manual Case -> Runnable Script

> **Capability gate:** This skill requires **any of Browser/API**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of Browser/API configured, so `/automation-writer` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Convert ONE confirmed manual test case into a runnable automated test: Playwright + TypeScript for a UI flow, or an HTTP/API test for an endpoint. This is a code-generation **utility**, not a QA verdict step — it does not find bugs, does not produce an Evidence Ledger, and does not run the post-session memory ritual. Feed it a case that has already been confirmed (e.g. by `test-cases-generator` + `bug-verifier`), and it emits a script the team can drop into their suite.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (for environment URLs, auth setup, and MCP routing — the gates/ledger/memory ritual do NOT apply to this utility).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP: "Which confirmed test case should I automate? Paste the steps and the expected result, and tell me if it's a UI flow (Playwright) or an API endpoint (HTTP test)." Do not invent a case; do not generate anything until the case is provided.

---

## Scope of this utility
- **In:** translating a single, already-confirmed manual case into a faithful, runnable script with explicit assertions and auth setup.
- **Out:** discovering new behavior, judging pass/fail, deciding GO/NO-GO, writing memory, building an evidence ledger. If you find the case is wrong or under-specified while automating it, stop and say so — do not silently "fix" it by guessing.

---

## Step 1: Take the manual case
Restate the case you were given: ordered **steps**, concrete **test data** (IDs/emails/credentials), and the **expected result** (the observable outcome each assertion will check). If the expected result is vague ("works"), ask for the precise observable before generating — an assertion needs something to assert.

## Step 2: Capture real selectors / the real contract
- **UI (Playwright):** navigate the flow with `mcp__playwright__*` and take a `mcp__playwright__browser_snapshot` of each page the case touches. Pull selectors from the snapshot's accessibility roles/names (prefer `getByRole`/`getByLabel`/`getByText` over brittle CSS/XPath). Use the **real** rendered structure — never hand-wave selectors from memory.
- **API (HTTP):** confirm the exact method, URL, headers (including any version header), auth scheme, request body, and expected status/response shape. Read the route/controller (`Read`/`Grep`) if anything is ambiguous so the generated request matches the real contract.

## Step 3: Generate the test
Pick the form that matches the case:
- **UI flow -> Playwright + TypeScript** (`@playwright/test`): one `test(...)` per case; auth via a `beforeEach`/login helper or stored auth state; the captured role-based locators; explicit `await expect(...)` assertions for the Step 1 expected result; sensible `await expect(locator).toBeVisible()` / `toHaveText(...)` over arbitrary sleeps.
- **API endpoint -> HTTP/API test** (Playwright `request` fixture or a plain Node script using `fetch`): build the request from Step 2; assert status code, and assert key response fields/schema against the expected result; include the auth/token acquisition step (authenticate per PROJECT-PROFILE.md §7 — JWT/session/OAuth/Firebase — and acquire a Bearer token, per qa-standards) so the script is self-contained and runnable.

Make assertions **explicit and specific** (assert the actual expected value, not just "200 OK" when the case checks data). Parameterize credentials/base-URL via constants or env vars at the top so the team can point it at their environment. Use the environment URLs and auth approach from qa-standards/CLAUDE.md so the script targets the right host out of the box.

## Step 4: Save as a deliverable (READ-ONLY ENV CONSTRAINT)
**Do NOT write into any source repo** (`<frontend repo: PROJECT-PROFILE.md §3/§9>`, `<legacy frontend repo: PROJECT-PROFILE.md §3>`, `<backend repo: PROJECT-PROFILE.md §3/§9>`, `<admin repo: PROJECT-PROFILE.md §3/§9>`, etc.) — the read-only QA environment blocks it, and that's intentional. Save the generated script as a deliverable under `qa-evidence/<slug>/` using `mcp__filesystem__write_file`:
- UI test: `qa-evidence/<slug>/<case-name>.spec.ts`
- API test: `qa-evidence/<slug>/<case-name>.api.spec.ts` (Playwright `request`) or `qa-evidence/<slug>/<case-name>.test.mjs` (standalone Node).

`<slug>` describes the feature/case. The team copies this file into their own test suite (e.g. their `tests/` or `e2e/` folder) and commits it there — this skill only produces the artifact, it doesn't install it.

## Step 5: Output the script + run instructions
Return:
1. The full generated script (in the chat) **and** confirm the saved path under `qa-evidence/<slug>/`.
2. **How to run it**, concretely — e.g. `npx playwright test qa-evidence/<slug>/<case-name>.spec.ts` (UI) or `node qa-evidence/<slug>/<case-name>.test.mjs` (API), plus any prerequisites (Node/Playwright installed, `npx playwright install` for browsers, required env vars / credentials).
3. A one-line note that this is a starting artifact the team copies into their suite, and which selectors/data may need adjusting if the page or credentials change.

Keep it a clean utility — script + run instructions, no QA verdict, no ledger, no memory write.
