#!/usr/bin/env python3
"""Bind the DB tool ids the skills and agents call - durably.

    python .claude/scripts/rebind.py --show
    python .claude/scripts/rebind.py --db mcp__postgres__execute_sql [--prod-db mcp__postgres_prod__execute_sql]
    python .claude/scripts/rebind.py --apply      # re-apply .claude/tool-bindings.json (install.py does this)
    python .claude/scripts/rebind.py --check      # exit 1 if any skill/agent still names an unbound id

Why: the skills ship naming the MySQL tool ids. A project on Postgres / Mongo / another server must call its
own tool. A one-off search-and-replace is undone by the next upgrade (the installer overwrites skills), so
the binding lives in .claude/tool-bindings.json and is re-applied after every install.
Only `.claude/skills/**`, `.claude/agents/*.md`, `.claude/CLAUDE.md` and `.claude/rules/*.md` are touched,
and only whole tool ids are replaced. Standard library only.
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.abspath(os.path.join(HERE, ".."))
BINDINGS = os.path.join(CLAUDE, "tool-bindings.json")
DEFAULTS = {"db": "mcp__mcp_server_mysql__mysql_query", "prod_db": "mcp__mcp_server_mysql_prod__mysql_query"}
ID_RE = re.compile(r"^mcp__[A-Za-z0-9_-]+__[A-Za-z0-9_-]+$")
TEXT = (".md", ".json")


def load():
    try:
        with io.open(BINDINGS, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    data.setdefault("history", [])
    return data


def save(data):
    with io.open(BINDINGS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=2) + "\n")


def targets():
    for base in ("skills", "agents", "rules"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(CLAUDE, base)):
            dirnames[:] = [d for d in dirnames if d not in ("node_modules", "__pycache__", "fixtures")]
            for f in filenames:
                if f.endswith(TEXT):
                    yield os.path.join(dirpath, f)
    yield os.path.join(CLAUDE, "CLAUDE.md")


def _pat(tool_id):
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(tool_id) + r"(?![A-Za-z0-9_])")


def apply(data, verbose=True):
    changed = 0
    for role in DEFAULTS:
        bound = data[role]
        olds = {DEFAULTS[role]} | {h["from"] for h in data["history"] if h.get("role") == role}
        olds.discard(bound)
        if not olds:
            continue
        for p in targets():
            if not os.path.isfile(p):
                continue
            with io.open(p, "r", encoding="utf-8") as fh:
                t = fh.read()
            n = t
            for old in olds:
                n = _pat(old).sub(bound, n)
            if n != t:
                with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(n)
                changed += 1
                if verbose:
                    print("  rebound %-8s in %s" % (role, os.path.relpath(p, CLAUDE)))
    return changed


def check(data):
    stale = []
    for role in DEFAULTS:
        bound = data[role]
        olds = {DEFAULTS[role]} | {h["from"] for h in data["history"] if h.get("role") == role}
        olds.discard(bound)
        for p in targets():
            if not os.path.isfile(p):
                continue
            with io.open(p, "r", encoding="utf-8") as fh:
                t = fh.read()
            for old in olds:
                if _pat(old).search(t):
                    stale.append((role, old, os.path.relpath(p, CLAUDE)))
    return stale


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db")
    ap.add_argument("--prod-db")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    data = load()
    if a.show or not (a.db or a.prod_db or a.apply or a.check):
        print(json.dumps({k: data[k] for k in DEFAULTS}, indent=2))
        return 0
    if a.check:
        stale = check(data)
        for role, old, f in stale:
            print("STALE %s: %s still names %s (bound: %s)" % (role, f, old, data[role]))
        print("tool bindings: %s" % ("OK" if not stale else "%d stale reference(s)" % len(stale)))
        return 1 if stale else 0
    for role, new in (("db", a.db), ("prod_db", a.prod_db)):
        if not new:
            continue
        if not ID_RE.match(new):
            sys.exit("ERROR %r is not an MCP tool id (mcp__<server>__<tool>)" % new)
        if new != data[role]:
            data["history"].append({"role": role, "from": data[role], "to": new})
            data[role] = new
    n = apply(data)
    save(data)
    print("tool bindings applied: %d file(s) changed; db=%s prod_db=%s" % (n, data["db"], data["prod_db"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())