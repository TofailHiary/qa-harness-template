#!/bin/sh
# Unattended QA run (CI). Judges the run by its run record, never by the chat.
#
#   sh .claude/scripts/ci-run-qa.sh "/full-qa APP-123 --mode targeted" APP-123-20261026
#
# Exit codes: 0 = GO   1 = NO-GO, or the run record is missing / contradicts itself   2 = PARTIAL   3 = setup problem
# Extra claude flags (permission mode, allowed tools, --mcp-config ...) go in QA_CLAUDE_FLAGS.
# Writes into qa-evidence/<run-folder>/: ci-doctor.txt, ci-claude-stream.jsonl, plus what the run itself writes.
PROMPT="$1"
RUN="$2"
if [ -z "$PROMPT" ] || [ -z "$RUN" ]; then
  echo "usage: sh .claude/scripts/ci-run-qa.sh \"<skill + arguments>\" <run-folder>"; exit 3
fi
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
EV="$ROOT/qa-evidence/$RUN"
mkdir -p "$EV" || exit 3
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || { echo "no python on PATH"; exit 3; }
command -v claude >/dev/null 2>&1 || { echo "claude CLI not on PATH (npm i -g @anthropic-ai/claude-code)"; exit 3; }
if ! "$PY" "$ROOT/.claude/scripts/doctor.py" > "$EV/ci-doctor.txt" 2>&1; then
  cat "$EV/ci-doctor.txt"; echo "doctor: NOT READY - fix the FAIL rows first"; exit 3
fi
claude -p "$PROMPT
Run folder: qa-evidence/$RUN/ - keep its run.json (qa-standards references/run-record.md). This is an unattended CI run: never ask a question; anything you cannot decide is BLOCKED with what would unblock it." \
  --output-format stream-json --verbose $QA_CLAUDE_FLAGS > "$EV/ci-claude-stream.jsonl"
RC=$?
[ "$RC" -eq 0 ] || echo "claude exited $RC - judging the run record anyway"
[ -f "$EV/run.json" ] || { echo "no run.json in qa-evidence/$RUN - the run left no record"; exit 1; }
"$PY" "$ROOT/.claude/skills/qa-standards/scripts/verdict_check.py" "$EV" || { echo "run record contradicts itself"; exit 1; }
V=$("$PY" -c "import json,sys; print((json.load(open(sys.argv[1], encoding='utf-8')).get('verdict') or {}).get('run') or '')" "$EV/run.json")
echo "verdict: ${V:-none}"
case "$V" in
  GO) exit 0 ;;
  PARTIAL) exit 2 ;;
  *) exit 1 ;;
esac