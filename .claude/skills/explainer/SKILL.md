---
name: explainer
description: Use when someone wants a change, feature, story, or bug explained in plain language from the actual user's point of view — "what does this mean for a Manager / User / Guest / Admin?" — as a before -> after narrative with an everyday scenario or analogy, even when no formal story or acceptance criteria are provided (infer from the PR diff, code, or ticket). Triggers include "explain this change as a user scenario", "what will the manager actually see now", "ELI5 this PR", "describe this bug in human terms", "what could they not do before that they can now", "write the release note line for this".
argument-hint: "the change to explain — a PR number, ticket key, file/feature name, or a pasted diff"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__github__*", "mcp__claude_ai_Atlassian__*", "Skill(qa-standards)"]
---

# Explainer — what this change means for the real user

> **Capability gate:** This skill requires **any of GitHub/LocalRepos**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no any of GitHub/LocalRepos configured, so `/explainer` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Turn a technical change (PR / diff / ticket / code) into a plain-language, per-role story: "as a Manager, before you saw a blank chart; now you see your team's numbers." This is an explanation, not a test — there is **no verdict, no test plan, no Evidence Ledger, and no memory ritual**. The output is the explanation itself.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session (for the layer/role vocabulary and the project context only — the project's identity and domain are in `PROJECT-PROFILE.md §1`, its roles in §8; the QA gates do not apply to this utility).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "What change should I explain in user terms? Give me a PR number, a ticket key, a file/feature name, or paste the diff. If you already know the roles affected (<roles: PROJECT-PROFILE.md §8> — e.g. Admin / Manager / User / Guest), tell me — otherwise I'll infer them from the code."

Do NOT guess which change is meant. Do NOT explain the whole platform.

---

## Workflow

### 1. Get the change
- **PR / diff** -> `mcp__github__pull_request_read` (and `get_file_contents` / Read for surrounding context) when GitHub is `on`; local `git show` / `Read` when LocalRepos is `on`.
- **Ticket** -> `mcp__claude_ai_Atlassian__getJiraIssue` for the summary + acceptance criteria when Jira is `on` (PROJECT-PROFILE.md §2 / §15); read the whole comment thread — a developer or product-owner clarification often overrides the original wording.
- **Pasted diff** -> read it directly.
- **Nothing formal given** -> infer the intent from the code: Read/Grep the touched files, look at the function names, the conditionals changed, the strings/labels added, the translation keys. State that you inferred it. **A missing story is normal — reconstruct the user-facing behaviour from the diff.**

### 2. Identify the affected roles
Which of the project's roles (<roles: PROJECT-PROFILE.md §8>) actually touches this surface? Trace it: which page/route renders the changed component, which role calls the changed endpoint, which role reads the changed table/column. A change can hit more than one role (e.g. an order-processing fix affects the User who sees the result AND the Manager who reads the dashboard). A change in a background job (`PROJECT-PROFILE.md §11`) still reaches a person — find the screen, export or email where its output lands. Ignore roles the change never reaches.

### 3. For EACH affected role — a before -> after narrative in THEIR words
Write a short, concrete passage per role. No jargon, no file paths, no function names. Each role gets:
- **Before:** what they experienced (often: blank, wrong number, error page, an action they couldn't take).
- **After:** what they experience now.
- **One everyday scenario or analogy** grounded in their real workflow — "Before, when you opened a user's account summary the score chart said 'No data available', as if it were broken; now it says 'No gaps — this user has completed every item', like a report with all checks passed and a note instead of a blank page."

Keep it human and specific to the application's own vocabulary (`PROJECT-PROFILE.md §1` — the entities the user actually names: accounts, orders, subscriptions, dashboards, reports). Prefer one vivid concrete example over abstract description.

### 4. State plainly the capability / visibility delta
In one or two sentences per role: what could they NOT do (or see) before, and can now — OR what visibly changed — OR, for a bug fix, what was breaking for them and is now correct. Make the practical difference unmistakable.

### 5. One-line "in plain terms" summary
Close with a single sentence anyone non-technical understands — the whole change distilled. This line is also the release-note candidate; if the project's tracker rules (`PROJECT-PROFILE.md §15`) ask for a customer-facing summary on the ticket, this is the sentence to use.

---

## Output shape (the deliverable)

```
## What changed (in one line)
<plain-language headline>

## Who it affects
<roles, and why each is touched>

## For the <Role> — before -> after
Before: ...
After: ...
Scenario: ...
What's different for you: ...

(repeat per affected role)

## In plain terms
<one sentence>
```

## Guardrails
- Explain, don't test. No GO/NO-GO, no pass/fail, no bug-hunting (if a real bug is obvious while reading, mention it in one line and point to the proper QA skill — `bug-verifier` — do not investigate here).
- Concrete over abstract: name the actual screen, the actual number, the actual click. Avoid "improves the experience" filler.
- If you inferred the user impact (no story given), say so honestly rather than overstating certainty — label it "inferred from the code" rather than presenting it as the stated intent.
- No identifiers in the narrative: no emails, account or tenant ids, hostnames, commit hashes or internal ticket chatter. A role name and a screen name are enough.
- Reflect only what the diff does, never what it should do — if the change does less than the ticket asked, say "this change covers X; Y is not in it", without judging it.
- No Evidence Ledger, no Scope Lock table, no memory write — this is a utility, not a QA run.
