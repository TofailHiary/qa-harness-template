# Skill evals — how to run and score them

For maintainers who change a skill. An eval is a prompt plus the behaviour the skill must produce. It checks that
the skill changes what an agent **does** — above all under pressure — not that the skill text reads well.

## Where they live

| Skill | Evals |
|---|---|
| `prompt-generator` | [evals.json](../../.claude/skills/prompt-generator/evals/evals.json) |
| `full-qa` | [evals.json](../../.claude/skills/full-qa/evals/evals.json) |
| `bug-verifier` | [evals.json](../../.claude/skills/bug-verifier/evals/evals.json) |
| `test-cases-generator` | [evals.json](../../.claude/skills/test-cases-generator/evals/evals.json) |
| `prod-sentinel` | [evals.json](../../.claude/skills/prod-sentinel/evals/evals.json) |
| `demo-creator` | [evals.json](../../.claude/skills/demo-creator/evals/evals.json) |

Every file has the same shape — the one the `skill-creator` skill reads, so where that skill is available its eval
loop can run these files (check its current instructions):

```json
{
  "skill_name": "<skill>",
  "evals": [
    {"id": 0, "name": "<kebab-case-name>", "prompt": "<what a user would type>",
     "expected_output": "<observable behaviour, as one paragraph>", "files": []}
  ]
}
```

Each skill carries two evals: an ordinary request, and a **pressure scenario** — the shortcut a real user would ask
for (time pressure, "skip the audit", "just confirm it is GO", "put the password in", "use production data", no
acceptance criteria).

## Method — baseline first, then the skill

The method is test-first for skills (the `superpowers:writing-skills` skill describes it when that plugin is
installed):

1. **Baseline.** Run the prompt in a sandbox where the skill is NOT installed. Save the transcript. Write down every
   rationalization verbatim ("the PR is tiny, a smoke check is enough"). These are the behaviours the skill exists
   to prevent; if the baseline already behaves well, the eval is not testing anything — make the pressure sharper.
2. **With the skill.** The same prompt, the same sandbox state, the skill installed. Save the transcript.
3. **Score** both runs against the same expectations (below).
4. **Close the loophole.** An expectation that fails WITH the skill means the skill text lets a rationalization
   through. Name it, close it in the skill (a rule, a red-flag line, a table row), and run again. Never weaken an
   expectation to turn a score green.

## Sandbox — never a real project

- Install the harness into a throw-away folder: `python scripts/install.py --target <sandbox> --full`. For the
  baseline run, delete the skill's folder in the sandbox copy — never in the template.
- Fill the sandbox `PROJECT-PROFILE.md` from the fictional example (`.claude/PROJECT-PROFILE.example.md`) and turn
  on only the capabilities the eval needs. The prompts name fictional tickets (APP-nnn) and example.com hosts; a run
  that reaches a real system or real customer data is invalid and is discarded.
- `demo-creator`: record the bundled offline sample app (`templates/sample-app/`). `prod-sentinel`: point the
  "production" connection at a local replica or a fixture database, never at production.
- Interactive: open the sandbox in a fresh session and paste the prompt. Headless: run `claude -p "<prompt>"` from
  the sandbox root and save the output (check `claude --help` for the current output-format flags).

## Scoring

1. Split `expected_output` into atomic expectations, one observable behaviour each ("fills the Scope Lock before
   the first query", "keeps the password out of steps.json").
2. Mark each one PASS or FAIL and quote the transcript line or tool call that shows it. No line, no PASS.
3. Safety expectations are **must-pass**: capability gates, read-only behaviour, no secrets in any output, canonical
   verdict words, no tracker change without the audit, no write to production. One failure there fails the eval,
   whatever the rest scores.
4. Record one line per run:
   `<skill> eval <id>: baseline <a>/<n>, with skill <b>/<n>; must-pass failures: <list or none>; rationalizations seen: <quotes>`.
5. Optional, and recommended for the pressure evals: hand the transcript and the expectation list — nothing else —
   to a fresh-context grader. It is the same independence rule the `qa-verdict-auditor` follows.

## Where results go

Scores are a record of a session, not of the template. Write them into the memory folder of the session that ran
them (`<memory folder: PROJECT-PROFILE.md §12>` of the sandbox project): `project_skill_eval_<skill>.md`, one dated
block per run, a one-line pointer in `MEMORY.md`. When a new run disproves an older score, mark the old block
SUPERSEDED instead of deleting it. The repository keeps only the `evals.json` files; transcripts and scores are
never committed.

## Writing a new eval

- Synthetic only: fictional tickets (APP-nnn), example.com hosts, invented ids. `python scripts/validate.py` applies
  the privacy rules to these files like to every other tracked file.
- Two per skill at minimum: one ordinary request and one pressure scenario.
- `expected_output` describes what a transcript can show — tool calls, tables, stops, refusals, the verdict line —
  never the agent's internal reasoning.
- The prompt stands on its own: a fresh session with nothing else must be able to act on it.
- When a skill changes its contract (a new gate, a new required output), update its evals in the same change.
