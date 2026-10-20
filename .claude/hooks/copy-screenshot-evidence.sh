#!/bin/bash
# Hook: PostToolUse for mcp__playwright__browser_take_screenshot (portable).
# Ensures Playwright screenshots end up in the evidence folder, even when a skill
# passed a bare filename (which Playwright saves to the project-root cwd).
#
#   1) If the tool response names a file, copy it into the evidence folder.
#   2) BACKSTOP SWEEP: any *.png written to the project root or .playwright-mcp
#      in the last ~90s is MOVED into the evidence folder (preserving its name).
#
# Project root resolves from CLAUDE_PROJECT_DIR (falls back to PWD). The evidence
# folder comes from .claude/hooks/harness-config.json -> evidence_root (default
# qa-evidence). JSON is parsed with python (jq is not assumed to exist).

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EV_REL=$(python -c "import json,sys
try:
    print(json.load(open(sys.argv[1], encoding='utf-8')).get('evidence_root') or 'qa-evidence')
except Exception:
    print('qa-evidence')" "$HOOK_DIR/harness-config.json" 2>/dev/null)
[ -n "$EV_REL" ] || EV_REL="qa-evidence"
case "$EV_REL" in
  /*|[A-Za-z]:*) EVIDENCE_DIR="$EV_REL" ;;
  *) EVIDENCE_DIR="$ROOT/$EV_REL" ;;
esac
TS=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$EVIDENCE_DIR"

INPUT=$(cat)

# 1) Explicit filename from the tool payload (field name varies across versions)
FN=$(printf '%s' "$INPUT" | python -c "import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for k in ('tool_response','tool_output','tool_input'):
    v=d.get(k) or {}
    if isinstance(v,dict):
        for f in ('filename','path'):
            if v.get(f):
                print(v[f]); sys.exit(0)" 2>/dev/null)
if [ -n "$FN" ] && [ -f "$FN" ]; then
  case "$FN" in
    "$EVIDENCE_DIR"/*) : ;;  # already in the evidence folder, leave it
    *) cp "$FN" "$EVIDENCE_DIR/${TS}_$(basename "$FN")" 2>/dev/null ;;
  esac
fi

# 2) Backstop sweep: recent PNGs at the project root or .playwright-mcp -> move in
for dir in "$ROOT" "$ROOT/.playwright-mcp"; do
  [ -d "$dir" ] || continue
  for f in "$dir"/*.png; do
    [ -f "$f" ] || continue
    if [ -n "$(find "$f" -mmin -1.5 2>/dev/null)" ]; then
      base=$(basename "$f")
      if [ -e "$EVIDENCE_DIR/$base" ]; then
        mv "$f" "$EVIDENCE_DIR/${TS}_${base}" 2>/dev/null || cp "$f" "$EVIDENCE_DIR/${TS}_${base}" 2>/dev/null
      else
        mv "$f" "$EVIDENCE_DIR/$base" 2>/dev/null || cp "$f" "$EVIDENCE_DIR/${TS}_${base}" 2>/dev/null
      fi
    fi
  done
done

exit 0
