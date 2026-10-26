#!/usr/bin/env python3
"""Render .mcp.json from .mcp.json.template and PROJECT-PROFILE.md §2 - the only supported way to make it.

    python .claude/scripts/render_mcp.py                 # write <project>/.mcp.json for this OS
    python .claude/scripts/render_mcp.py --dry-run       # print the result, write nothing
    python .claude/scripts/render_mcp.py --os darwin     # render for another OS (win32 / darwin / linux)
    python .claude/scripts/render_mcp.py --add-server postgres='{"command":"npx","args":["-y","<pkg>@<version>"],"env":{"DATABASE_URL":"${QA_DB_URL}"},"_capability":"DB"}'
                                                         # add (or replace) a server the template lacks - kept on every re-render

What it does:
  * ${PROJECT_ROOT} -> this project's absolute path (forward slashes);
  * disabled:true for every server whose `_capability` is `off` in PROJECT-PROFILE.md §2 ("always" stays on);
  * on Windows, `npx` servers are wrapped as `cmd /c npx ...` (npx is a .cmd shim there); elsewhere plain `npx`;
  * secrets stay as ${ENV_VAR} placeholders - Claude Code expands them at runtime. The script prints the
    export lines to set (names only, never values);
  * servers already in .mcp.json that the template does not know (a project MCP server from §14, a
    Postgres / Mongo server) are KEPT as they are; inline values you chose to keep in a template server's
    env are kept too (counted, never printed).
Standard library only.
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(os.path.join(HERE, "..", ".."))
PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)\}")


def read(p):
    with io.open(p, "r", encoding="utf-8") as fh:
        return fh.read()


def capabilities(profile_text):
    return {k.lower(): v for k, v in re.findall(r"^- ([A-Za-z-]+): (on|off)\b", profile_text, re.M)}


def render(template, caps, root, osname, existing=None):
    out = {"mcpServers": {}}
    kept_inline = 0
    root_fwd = root.replace("\\", "/")
    for name, srv in template.get("mcpServers", {}).items():
        s = json.loads(json.dumps(srv).replace("${PROJECT_ROOT}", root_fwd))
        cap = (s.get("_capability") or "always").lower()
        if cap != "always":
            s["disabled"] = caps.get(cap, "off") != "on"
        if osname == "win32" and s.get("command") == "npx":
            s["command"] = "cmd"
            s["args"] = ["/c", "npx"] + list(s.get("args", []))
        old = (existing or {}).get("mcpServers", {}).get(name) or {}
        for k, v in (old.get("env") or {}).items():
            if k in (s.get("env") or {}) and isinstance(v, str) and not PLACEHOLDER.search(v) and PLACEHOLDER.search(s["env"][k]):
                s["env"][k] = v
                kept_inline += 1
        out["mcpServers"][name] = s
    extra = [n for n in (existing or {}).get("mcpServers", {}) if n not in out["mcpServers"]]
    for n in extra:
        out["mcpServers"][n] = existing["mcpServers"][n]
    return out, kept_inline, extra


def env_names(rendered):
    names = set()
    for srv in rendered["mcpServers"].values():
        if srv.get("disabled"):
            continue
        names.update(PLACEHOLDER.findall(json.dumps(srv.get("env") or {})))
    return sorted(names)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=PROJECT)
    ap.add_argument("--os", default=sys.platform if sys.platform in ("win32", "darwin") else "linux")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--add-server", action="append", default=[], metavar="NAME=JSON",
                    help="add or replace a server that is not in the template (kept on every re-render)")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    tpl = json.loads(read(os.path.join(root, ".mcp.json.template")))
    prof_p = os.path.join(root, ".claude", "PROJECT-PROFILE.md")
    caps = capabilities(read(prof_p)) if os.path.exists(prof_p) else {}
    target = os.path.join(root, ".mcp.json")
    existing = None
    if os.path.exists(target):
        try:
            existing = json.loads(read(target))
        except Exception:
            sys.exit("ERROR .mcp.json exists but is not valid JSON - fix or move it before rendering")
    for spec in a.add_server:
        name, _, blob = spec.partition("=")
        try:
            srv = json.loads(blob)
            assert isinstance(srv, dict) and srv.get("command")
        except Exception:
            sys.exit("ERROR --add-server %r: expected NAME={json with a command}" % name)
        if a.os == "win32" and srv.get("command") == "npx":
            srv = dict(srv, command="cmd", args=["/c", "npx"] + list(srv.get("args", [])))
        existing = existing or {"mcpServers": {}}
        existing.setdefault("mcpServers", {})[name.strip()] = srv
    rendered, kept, extra = render(tpl, caps, root, a.os, existing)
    text = json.dumps(rendered, indent=2) + "\n"
    if a.dry_run:
        print(text)
    else:
        with io.open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("wrote %s (%s)" % (target, a.os))
    on = [n for n, s in rendered["mcpServers"].items() if not s.get("disabled")]
    print("enabled servers: %s" % (", ".join(on) or "none"))
    if extra:
        print("kept servers not in the template: %s" % ", ".join(extra))
    if kept:
        print("kept %d inline env value(s) you set earlier (not shown)" % kept)
    names = env_names(rendered)
    if names:
        print("\nSet these environment variables before starting Claude Code (values are yours; never commit them):")
        print("  bash/zsh   : " + "  ".join("export %s=..." % n for n in names))
        print("  PowerShell : " + "  ".join("$env:%s = '...'" % n for n in names))
        print("  persistent (Windows): setx NAME value   |   (macOS/Linux): add the export lines to your shell profile")
    return 0


if __name__ == "__main__":
    sys.exit(main())