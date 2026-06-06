#!/bin/bash
# Hook: PostToolUse for mcp__playwright__browser_take_screenshot (portable).
# Ensures Playwright screenshots end up in <project>/qa-evidence/, even when a
# skill passed a bare filename (which Playwright saves to the project-root cwd).
#
#   1) If the tool response names a file, copy it into qa-evidence.
#   2) BACKSTOP SWEEP: any *.png written to the project root or .playwright-mcp
#      in the last ~90s is MOVED into qa-evidence (preserving its name).
#
# Project root resolves from CLAUDE_PROJECT_DIR (falls back to PWD).

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
EVIDENCE_DIR="$ROOT/qa-evidence"
TS=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$EVIDENCE_DIR"

INPUT=$(cat)

# 1) Explicit filename from the tool payload (field name varies across versions)
FN=$(echo "$INPUT" | jq -r '.tool_response.filename // .tool_response.path // .tool_input.filename // .tool_output.filename // empty' 2>/dev/null)
if [ -n "$FN" ] && [ -f "$FN" ]; then
  case "$FN" in
    "$EVIDENCE_DIR"/*) : ;;  # already in qa-evidence, leave it
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
