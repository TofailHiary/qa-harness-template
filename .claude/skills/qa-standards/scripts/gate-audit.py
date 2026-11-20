#!/usr/bin/env python3
"""gate-audit.py - run the completion gate's own checks on a saved draft report. Read-only: no gate log, no block.

    python .claude/skills/qa-standards/scripts/gate-audit.py [--assume-passed] <report.md> [session-transcript.jsonl]

Prints every warning the Stop hook would raise for that text (Run line, core-page sweep rows, Regression rows,
case completeness, skills loaded, confidence line, Execution Register, evidence, ...). The verdict audit (full-qa
Phase 8a, or qa-verdict-auditor) saves the DRAFT verdict message to a file in the OS temp folder and runs this with
--assume-passed before it writes AUDIT_PASSED: several checks fire only on a report whose audit passed, so
--assume-passed scores the draft as if it had (it sets the Run line's Audit field to AUDIT_PASSED, or adds the word,
in memory only - the file is never changed). Works with any gate version: the transcript is passed only to a gate
that takes it.
Exit 0 = the gate would pass it, 1 = warnings, 2 = usage error, no gate found, or the text is not a verdict message.
"""
import importlib.util
import inspect
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # a Windows console code page cannot print check marks
except Exception:
    pass
args = sys.argv[1:]
assume = "--assume-passed" in args
args = [a for a in args if a != "--assume-passed"]
if not args or not os.path.isfile(args[0]):
    print(__doc__)
    sys.exit(2)
here = os.path.dirname(os.path.abspath(__file__))
gate_path = os.path.normpath(os.path.join(here, "..", "..", "..", "hooks", "completion-gate.py"))
if not os.path.isfile(gate_path):
    print("No completion gate at %s (run this from an installed harness)." % gate_path)
    sys.exit(2)
spec = importlib.util.spec_from_file_location("completion_gate", gate_path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

with io.open(args[0], encoding="utf-8", errors="replace") as fh:
    raw = fh.read()
if assume:
    run_re = getattr(gate, "RUN_LINE", None)
    lines = raw.split("\n")
    found = False
    for i, ln in enumerate(lines):
        if run_re is not None and run_re.search(ln):
            lines[i] = ln.replace("AUDIT_FAILED", "AUDIT_PASSED")
            found = True
    raw = "\n".join(lines)
    if not found and "AUDIT_PASSED" not in raw:
        raw = raw.rstrip("\n") + "\n\nAUDIT_PASSED (assumed by gate-audit --assume-passed)\n"
text = gate.strip_quoted(raw)
if not text or not gate.VERDICT.search(text):
    print("Not a verdict message: nothing for the gate to check. Pass the draft verdict report.")
    sys.exit(2)
params = inspect.signature(gate.checks).parameters
if "raw" in params:
    warnings = gate.checks(text, raw, args[1] if len(args) > 1 else None)
else:
    warnings = gate.checks(text)
for w in warnings:
    print("- " + w)
print("%d warning(s)%s" % (len(warnings), " (scored as if the audit had passed)" if assume else ""))
sys.exit(1 if warnings else 0)
