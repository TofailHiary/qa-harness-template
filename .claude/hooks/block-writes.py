#!/usr/bin/env python3
"""PreToolUse Write|Edit|NotebookEdit - READ-ONLY QA (portable).

Allow writes ONLY to:
  - the project's auto-memory folder (so QA findings can be persisted), and
  - the harness self-config allow-globs (PROJECT-PROFILE.md, settings.json,
    harness-config.json, .mcp.json) so /configure-project can run and re-run.
Block everything else - product source code, secrets, qa-evidence (use the
filesystem MCP), anything. Fail-closed on malformed input."""
import json
import os
import sys
import fnmatch
import harness_config as hc


def block(reason):
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            block("READ-ONLY QA: empty hook input. Write/Edit blocked by default.")
        data = json.loads(raw)
    except Exception as e:
        block("READ-ONLY QA: could not parse hook input (%s). Write/Edit blocked." % type(e).__name__)
        return

    cfg = hc.load()
    ti = data.get("tool_input", {}) or {}
    target = ti.get("file_path") or ti.get("path") or ""
    tnorm = hc.norm(target)
    if not tnorm:
        block("READ-ONLY QA: no file_path in tool input. Write/Edit blocked.")

    # 1) allow the auto-memory folder
    if hc.is_under(tnorm, cfg["memory_root"]):
        sys.exit(0)

    # 2) allow the harness's own config files (project-relative globs)
    try:
        rel = os.path.relpath(tnorm, cfg["project_root"]).replace("\\", "/")
    except Exception:
        rel = ""
    for g in cfg["allowed_write_globs"]:
        if rel and fnmatch.fnmatch(rel, g):
            sys.exit(0)

    block(
        "READ-ONLY QA: Write/Edit to '%s' is blocked. Allowed: the memory folder and the "
        "harness config (PROJECT-PROFILE.md, settings.json, harness-config.json, .mcp.json). "
        "Product code is read-only; use the filesystem MCP for qa-evidence attachments." % target
    )


if __name__ == "__main__":
    main()
