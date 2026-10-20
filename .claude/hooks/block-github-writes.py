#!/usr/bin/env python3
"""PreToolUse mcp__github__create_pull_request | mcp__github__update_pull_request - READ-ONLY QA (portable).

Policy: GitHub write tools are allowed ONLY for the repositories the team owns and develops
itself (harness-config.json -> owned_repos, matched against the tool's `repo` field by name,
case-insensitive, any owner). Product repositories (and everything else) stay read-only:
pull requests against them are refused. With no owned_repos configured, everything is refused.

  allow (exit 0)  -> tool_input.repo is one of owned_repos
  block (exit 2)  -> any other repository, a missing repo field, or unreadable input
"""
import json
import sys
import harness_config as hc


def _block(reason):
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            _block("READ-ONLY QA: empty hook input for a GitHub write tool. Blocked by default.")
        data = json.loads(raw)
    except Exception as e:
        _block("READ-ONLY QA: could not parse GitHub hook input (%s). Blocked by default." % type(e).__name__)
        return

    owned = {n.lower() for n in hc.load().get("owned_repos", [])}
    tool_input = data.get("tool_input", {}) or {}
    repo = str(tool_input.get("repo") or "").strip().lower()
    if repo and repo in owned:
        sys.exit(0)
    _block(
        "READ-ONLY QA: GitHub writes are allowed only for the owned repositories (%s); '%s' is a QA "
        "target and stays read-only." % (", ".join(sorted(owned)) or "none configured", repo or "?")
    )


if __name__ == "__main__":
    main()
