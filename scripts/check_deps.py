#!/usr/bin/env python3
"""List the pinned MCP server packages and, on request, compare them with the registry.

    python scripts/check_deps.py            # offline: every npx server must carry an exact version (no @latest)
    python scripts/check_deps.py --online   # also asks npm for the newest published version (network)

Exit 1 when a server is unpinned. Drift (a newer version exists) is reported, never fatal: bumping a pin is a
deliberate step (docs/upgrading.md -> Bumping pinned MCP versions). Also reports the Playwright version the
demo creator pins, so the two Playwright pins can be compared.
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def pins():
    tpl = json.load(io.open(os.path.join(ROOT, ".mcp.json.template"), encoding="utf-8"))
    out = []
    for name, srv in tpl["mcpServers"].items():
        args = srv.get("args", [])
        if srv.get("command") not in ("npx", "cmd") and "npx" not in args:
            continue
        pkg = next((a for a in args if not a.startswith("-") and a not in ("/c", "npx")), "")
        m = re.match(r"^(@?[^@]+)@(.+)$", pkg)
        out.append((name, m.group(1) if m else pkg, m.group(2) if m else None, srv.get("_tested", "")))
    return out


def main():
    online = "--online" in sys.argv
    bad = 0
    print("%-24s %-44s %-10s %-10s %s" % ("server", "package", "pinned", "registry", "tested"))
    for name, pkg, ver, tested in pins():
        latest = ""
        if online:
            r = subprocess.run(["npm", "view", pkg, "version"], capture_output=True, text=True, shell=(os.name == "nt"))
            latest = (r.stdout or "").strip() or "?"
        flag = ""
        if not ver or ver == "latest":
            flag = "  <- UNPINNED"
            bad += 1
        elif online and latest not in ("", "?") and latest != ver:
            flag = "  <- newer version published"
        print("%-24s %-44s %-10s %-10s %s%s" % (name, pkg, ver or "-", latest or "(offline)", tested[:40], flag))
    setup = os.path.join(ROOT, ".claude", "skills", "demo-creator", "scripts", "setup.js")
    if os.path.exists(setup):
        m = re.search(r"const PW = '(\d+\.\d+\.\d+)'", io.open(setup, encoding="utf-8").read())
        print("\ndemo-creator pins playwright %s (the Browser MCP pins @playwright/mcp separately)" % (m.group(1) if m else "?"))
    print("\n%s" % ("OK: every npx server is pinned" if not bad else "%d unpinned server(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())