# Running QA unattended (CI)

The harness can run a QA cycle without a person at the keyboard and turn the result into a CI exit code.
The exit code comes from the **run record** (`qa-evidence/<run-folder>/run.json`), recomputed by
`verdict_check.py` — never from what the agent wrote in the chat.

> Status: the scripts were tested with a stub `claude` binary (all exit codes below), and the PowerShell
> twin was parse-checked only. A real CI pipeline with the Claude Code CLI was **not** executed for 2.1.

## The scripts

```bash
sh .claude/scripts/ci-run-qa.sh "/full-qa APP-123 --mode targeted" APP-123-20261026
pwsh .claude/scripts/ci-run-qa.ps1 "/full-qa APP-123 --mode targeted" APP-123-20261026
```

| Exit | Meaning |
|---|---|
| 0 | GO |
| 1 | NO-GO — or the run left no `run.json`, or `verdict_check.py` found contradictions |
| 2 | PARTIAL (a hard blocker or open rows) |
| 3 | setup problem: no Python, no `claude` CLI, or `doctor.py` reported NOT READY |

What a run does, in order:
1. `python .claude/scripts/doctor.py` → `qa-evidence/<run>/ci-doctor.txt`. NOT READY stops the job (exit 3):
   a CI box without Python 3 or a POSIX shell would otherwise run with the guards failing closed.
2. `claude -p "<prompt> + run-folder instructions" --output-format stream-json --verbose $QA_CLAUDE_FLAGS`
   → `ci-claude-stream.jsonl`. The prompt tells the agent it is unattended: anything it cannot decide is
   BLOCKED with what would unblock it, never a question.
3. `verdict_check.py qa-evidence/<run>` must exit 0, then `verdict.run` decides the exit code.

## Requirements on the runner

- The Claude Code CLI and credentials for it (for example `ANTHROPIC_API_KEY` as a CI secret).
- Python 3, Node 18+, Git and a POSIX `sh` — the read-only hooks run in CI exactly as they do locally.
- The MCP servers the run needs. Pass them explicitly: render a CI copy with
  `python .claude/scripts/render_mcp.py --dry-run --os linux > ci-mcp.json` and add
  `--mcp-config ci-mcp.json --strict-mcp-config` to `QA_CLAUDE_FLAGS`. Database passwords and tokens are CI
  secrets exposed as the environment variables the config names (`QA_DB_PASS`, ...).
- Tool permissions for a non-interactive session: list the read tools the run may use with
  `--allowedTools` in `QA_CLAUDE_FLAGS`. Do not use a bypass-all-permissions mode: the hooks still block
  writes, but a QA run should not depend on that alone.

## GitHub Actions example

```yaml
name: qa-targeted
on: { workflow_dispatch: { inputs: { ticket: { required: true } } } }
jobs:
  qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: npm i -g @anthropic-ai/claude-code
      - name: QA run
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          QA_DB_PASS: ${{ secrets.QA_DB_PASS }}
          QA_CLAUDE_FLAGS: --mcp-config ci-mcp.json --strict-mcp-config --allowedTools Read,Grep,Glob,Bash
        run: |
          python .claude/scripts/render_mcp.py --dry-run --os linux > ci-mcp.json
          RUN="${{ inputs.ticket }}-$(date +%Y%m%d)"
          echo "RUN=$RUN" >> "$GITHUB_ENV"
          sh .claude/scripts/ci-run-qa.sh "/full-qa ${{ inputs.ticket }} --mode targeted" "$RUN"
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: qa-evidence, path: "qa-evidence/${{ env.RUN }}/" }
```

Pin the action and CLI versions you validated; the example uses current major versions for readability.

## Across runs

`python .claude/skills/qa-standards/scripts/verdict_check.py --summary qa-evidence` prints one line per run:
verdict, `N/M`, BLOCKED, NOT YET VERIFIED, skipped phases and whether the record is consistent. Run it on
a folder of downloaded artifacts to see which gates fire and which phases are always skipped.