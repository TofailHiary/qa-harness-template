#!/bin/sh
# Launch a Python hook with whichever Python 3 this machine has.
#
#   sh run-hook.sh <script.py>              guard mode: FAIL CLOSED - no Python 3, a missing script or a
#                                           crashed guard BLOCKS the tool call (exit 2) with a reason
#   sh run-hook.sh <script.py> --fail-open  advisory mode (the Stop gate): problems are reported, never block
#
# Why: Claude Code treats every exit code other than 0 and 2 as NON-blocking. A guard launched as `python`
# on a machine that only has `python3` (or the reverse, or a Windows store stub) would start, fail, and
# protect nothing - silently.
# Fast path: the input is captured once and the guard runs directly (one Python start). Only an exit code
# other than 0/2 triggers an interpreter probe, to tell a broken interpreter name (try the next one) from
# a crashed guard (block). Without `cat` on PATH it probes first and needs no external command at all.
# QA_HOOK_PYTHONS overrides the interpreter names tried (space-separated); the red-team runner uses it.
case "$0" in */*) HOOK_DIR=${0%/*} ;; *) HOOK_DIR=. ;; esac
SCRIPT="$1"
MODE="${2:-}"

fail() {
  if [ "$MODE" = "--fail-open" ]; then
    printf '%s\n' "QA harness (advisory hook): $1 Run: python .claude/scripts/doctor.py" >&2
    exit 0
  fi
  msg="READ-ONLY QA: $1 The tool call is blocked because a guard that cannot run must not allow. Run: python .claude/scripts/doctor.py"
  printf '{"decision": "block", "reason": "%s"}\n' "$msg"
  printf '%s\n' "$msg" >&2
  exit 2
}

usable() { "$1" $2 -S -E -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' </dev/null >/dev/null 2>&1; }

finish() {   # $1 = exit code, $2 = guard stdout
  if [ "$1" -eq 0 ]; then
    [ -n "$2" ] && printf '%s\n' "$2"
    exit 0
  fi
  printf '%s\n' "$2"
  printf '%s\n' "$2" >&2
  exit 2
}

[ -n "$SCRIPT" ] && [ -f "$HOOK_DIR/$SCRIPT" ] || fail "hook script '$SCRIPT' is missing from .claude/hooks."

if command -v cat >/dev/null 2>&1; then
  INPUT=$(cat)
  CAPTURED=1
else
  CAPTURED=
fi

for PY in ${QA_HOOK_PYTHONS:-python3 python py}; do
  command -v "$PY" >/dev/null 2>&1 || continue
  if [ "$PY" = "py" ]; then FLAG="-3"; else FLAG=""; fi
  if [ -n "$CAPTURED" ]; then
    OUT=$(printf '%s' "$INPUT" | "$PY" $FLAG "$HOOK_DIR/$SCRIPT")
    RC=$?
    if [ "$RC" -eq 0 ] || [ "$RC" -eq 2 ]; then finish "$RC" "$OUT"; fi
    usable "$PY" "$FLAG" || continue
  else
    usable "$PY" "$FLAG" || continue
    OUT=$("$PY" $FLAG "$HOOK_DIR/$SCRIPT")
    RC=$?
    if [ "$RC" -eq 0 ] || [ "$RC" -eq 2 ]; then finish "$RC" "$OUT"; fi
  fi
  fail "hook '$SCRIPT' exited with code $RC under '$PY' (a crashed guard must not allow)."
done
fail "no Python 3 interpreter found (tried: ${QA_HOOK_PYTHONS:-python3 python py -3})."