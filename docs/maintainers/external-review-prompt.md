# External review prompt

Give this prompt to an independent reviewer (a person or another AI model) when you want an enhancement
backlog for the template. The output format is designed so the backlog can be implemented item by item
and verified with the repository's own validator and hook suite. Replace the repository URL if you fork.

```text
You are a senior reviewer of developer tooling for AI coding agents. Review the public repository
<repository URL> (branch main) and produce a prioritized enhancement
backlog that another implementer will execute. Do not implement anything; do not ask me questions —
make reasonable assumptions and state them.

WHAT THE REPOSITORY IS
A portable, self-configuring, read-only QA harness for Claude Code: 36 skills (.claude/skills/*/SKILL.md),
6 sub-agents (.claude/agents), 8 hook scripts that enforce read-only behaviour (.claude/hooks), always-loaded
rules (.claude/rules), a single project profile that holds every project-specific binding
(.claude/PROJECT-PROFILE.md, §1–§18, with a fictional worked example), an MCP server template
(.mcp.json.template), a bootstrap skill (configure-project), an installer (scripts/install.py +
catalog.json), a validator (scripts/validate.py), an adversarial test suite for the hooks
(scripts/hook-redteam/), and docs/ (installation, configuration, integrations, usage examples, platforms
and limitations, troubleshooting, upgrading, catalog, capability matrix, maintainers/ conventions and
migration inventory). Read README.md, CHANGELOG.md, docs/catalog.md, docs/capability-matrix.md,
docs/maintainers/generalization-conventions.md and .claude/skills/qa-standards/SKILL.md first; they define
the architecture, the shared vocabulary (Scope Lock, Evidence Ledger, Execution Register, Verdict Contract,
Completion Gate, Escape classes E1–E13, Memory Ritual) and the non-negotiable constraints.

NON-NEGOTIABLE CONSTRAINTS (reject any idea that violates them)
1. Generic: no product, organisation, host, account, ticket prefix or incident may be hard-coded; every
   project fact is a PROJECT-PROFILE.md reference. scripts/validate.py must stay green.
2. Read-only QA: the harness documents bugs, never fixes product code; hooks must keep blocking writes and
   git mutations outside the memory folder, the harness config, the evidence folder and declared owned repos.
3. Portable: Windows (Git Bash + PowerShell), macOS, Linux; Python 3 stdlib and Node 18+ only; no globally
   installed packages assumed; optional services stay optional and skills state what they skip when off.
4. Installable piecemeal: one skill with its declared dependencies, a group, or the complete setup; user
   configuration preserved on upgrade.
5. Honest reporting: no skill or doc may claim an unexecuted check passed.

REVIEW DIMENSIONS (cover each; say "no finding" where that is the truth)
A. Skill quality: are the workflows executable step by step by an agent that has only the repo and the
   profile? Find vague steps, missing stop conditions, contradictions between skills and qa-standards,
   descriptions that summarize workflow instead of stating triggers, places where an agent could rationalize
   skipping a gate, and gaps in evidence requirements.
B. Verdict integrity: can a run still produce a false GO / false BLOCKED / unsourced FAIL? Where would an
   independent auditor (qa-verdict-auditor) be unable to refute a claim from the package alone?
C. Safety: read the hooks and scripts/hook-redteam/cases.json; propose concrete escape attempts the suite
   does not cover (shell constructs, PowerShell idioms, interpreter payloads, path tricks, encoding), and
   false positives that would make a user switch the guards off. Each becomes a proposed test case first.
D. Bootstrap and installer: friction a new user hits in the first 30 minutes (configure-project flow,
   MCP provisioning, DB tool rebinding for Postgres/Mongo/SQLite, secrets handling, user- vs project-level,
   upgrades, dry-run output). Propose UX and robustness improvements.
E. Coverage gaps: QA capabilities a mature harness has that this one lacks or treats shallowly (examples to
   consider, not a checklist: CI/CD integration and non-interactive runs, contract/schema testing, data
   migration testing, feature-flag and configuration matrices, load/stress beyond single-request latency,
   mobile/native surfaces, accessibility depth, localization, observability of the harness itself,
   skill evals/benchmarks, telemetry and run summaries, multi-runtime installers).
F. Documentation: contradictions between docs and implementation, missing "why", examples that cannot be
   copied as-is, onboarding order, and what a maintainer needs to generalize future source changes safely.
G. Maintainability: catalog/validator drift risks, duplicated text that will diverge, naming consistency,
   version/compatibility pinning (Playwright, MCP packages, Claude Code features such as /goal and /loop).

OUTPUT FORMAT (strict, so the implementer can act on it)
1. "Verdict on genericity and maturity": 5–10 lines, with the three biggest risks.
2. "Backlog": a table with columns
   ID | Title | Dimension (A–G) | Impact (H/M/L) | Effort (S/M/L) | Files to change | Rationale (why it
   matters, with the exact file:line or section you are reacting to) | Change spec (what to do, concrete
   enough to implement without re-deriving) | Acceptance criteria (how the implementer proves it is done:
   a validator rule, a red-team case, a doc check, a command and its expected output) | Risk / what could
   regress.
   Order by Impact then Effort. Aim for 20–40 items; merge duplicates; do not pad.
3. "Proposed red-team cases": JSON array in the format of scripts/hook-redteam/cases.json
   ({"id","hook","block","cmd","cwd?","src":"auditor"}), each with a one-line reason.
4. "Do not do": ideas you considered and rejected because they would break a constraint, with the constraint
   named.
5. "Assumptions": anything you could not verify from the repository.

RULES FOR YOUR REVIEW
- Cite the repository, not memory: every finding names a file and a section or line.
- Prefer recipes over prohibitions: say what the output should look like, not only what to avoid.
- Keep every suggestion generic and profile-driven; never introduce a real company, product, host or ticket
  system as a hard binding (examples use example.com and APP-nnn).
- If you propose a new skill, give its name, its "Use when…" description (triggers only), its capability
  gate, its dependencies, and its section outline.
- Mark anything that would require changes to Claude Code itself or to third-party MCP servers as
  "external", with the alternative that works today.
```

When the backlog comes back, hand it to the implementer with: "Implement items <IDs> from this backlog in
the template; keep scripts/validate.py and scripts/hook-redteam/runner.py green; add the proposed red-team
cases first and watch them fail before fixing the guards; update CHANGELOG.md and docs/catalog.md."
