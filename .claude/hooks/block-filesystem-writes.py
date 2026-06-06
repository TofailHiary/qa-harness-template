#!/usr/bin/env python3
"""PreToolUse filesystem MCP write/edit/move/mkdir - READ-ONLY QA (portable).

The filesystem MCP's own allowed_directories may be broad; this hook narrows it
so the MCP can only write under the evidence folder (evidence_root from
harness-config.json). Source code and everything else are denied."""
import json
import sys
import harness_config as hc


def block(reason):
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def targets(ti):
    out = []
    for k in ("path", "destination", "source"):
        v = ti.get(k)
        if v:
            out.append(v)
    return out


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            block("READ-ONLY QA: empty filesystem hook input. Blocked.")
        data = json.loads(raw)
    except Exception as e:
        block("READ-ONLY QA: bad filesystem hook input (%s). Blocked." % type(e).__name__)
        return

    cfg = hc.load()
    root = cfg["evidence_root"]
    tlist = targets(data.get("tool_input", {}) or {})
    if not tlist:
        block("READ-ONLY QA: no path in filesystem tool input. Blocked.")
    for t in tlist:
        if not hc.is_under(hc.norm(t), root):
            block(
                "READ-ONLY QA: filesystem MCP write to '%s' is blocked. Only the evidence folder "
                "(%s) is permitted for the filesystem MCP; use the Write tool for memory files." % (t, root)
            )
    sys.exit(0)


if __name__ == "__main__":
    main()
