#!/usr/bin/env python3
"""Install the QA harness - the complete setup, a group, or individual skills with their dependencies.

Usage (run from anywhere; the template root is the parent of this scripts/ folder):
  python scripts/install.py --target <project-root> --full
  python scripts/install.py --target <project-root> --skill browser-test[,api-test,...]
  python scripts/install.py --target <project-root> --group layers
  python scripts/install.py --user --skill explainer          # user-level: ~/.claude/skills only
  python scripts/install.py --target <project-root> --skill db-check --dry-run
  python scripts/install.py --list

What "with dependencies" means for a project-level install:
  * the CORE (CLAUDE.md, PROJECT-PROFILE.md, settings.json, hooks, rules, references, MCP template, docs)
    is always installed, because the read-only hooks are what make the harness safe;
  * the requested skills, plus every skill they reference (Skill(x) in SKILL.md and "requires" in
    catalog.json), plus every agent they reference (Agent(x) / subagent_type: "x" / "agents" in
    catalog.json), plus qa-standards.
A user-level install copies skills only (no hooks, no rules, no agents - those are project scoped).

Preservation rules: an existing PROJECT-PROFILE.md, settings.json, harness-config.json, .mcp.json,
.gitignore and .gitattributes are NEVER overwritten; the template version is written next to them as
<name>.new so you can merge by hand. Everything else is overwritten (use --dry-run to see the plan).
The installer never reads or copies anything outside the template root.
"""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ROOT = os.path.abspath(os.path.join(HERE, ".."))
CATALOG_PATH = os.path.join(TEMPLATE_ROOT, "catalog.json")

SKILL_REF = re.compile(r"Skill\(([A-Za-z0-9_-]+)\)")
AGENT_REF = re.compile(r"Agent\(([A-Za-z0-9_-]+)\)|subagent_type:\s*\"([A-Za-z0-9_-]+)\"")
EXCLUDE_DIRS = {"node_modules", "__pycache__", "out", ".git"}
EXCLUDE_SUFFIXES = (".pyc", ".log", ".bak", ".mp4", ".webm", ".wav", ".mp3")


def load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def skill_dir(name):
    return os.path.join(TEMPLATE_ROOT, ".claude", "skills", name)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def agent_name_to_file(catalog):
    return {name: meta["file"] for name, meta in catalog.get("agents", {}).items()}


def resolve(catalog, wanted):
    """Transitive closure of skills + agents starting from `wanted` skill names."""
    skills = catalog["skills"]
    agents_map = agent_name_to_file(catalog)
    todo = list(wanted)
    seen_skills, seen_agents = [], []
    while todo:
        name = todo.pop(0)
        if name in seen_skills:
            continue
        if name not in skills:
            sys.exit("unknown skill: %s (see --list)" % name)
        seen_skills.append(name)
        meta = skills[name]
        deps = list(meta.get("requires", []))
        md = os.path.join(skill_dir(name), "SKILL.md")
        # qa-standards is the shared reference document: it MENTIONS most skills ("slot in when relevant")
        # without depending on them, so its Skill(x) references are not followed.
        if os.path.exists(md) and name != "qa-standards":
            text = read(md)
            deps += [m for m in SKILL_REF.findall(text) if m in skills]
            for a, b in AGENT_REF.findall(text):
                an = a or b
                if an in agents_map and an not in seen_agents:
                    seen_agents.append(an)
        for a in meta.get("agents", []):
            if a in agents_map and a not in seen_agents:
                seen_agents.append(a)
        for d in deps:
            if d not in seen_skills and d not in todo:
                todo.append(d)
    if "qa-standards" in skills and "qa-standards" not in seen_skills:
        seen_skills.append("qa-standards")
    # every agent preloads qa-standards; agents referencing skills are covered by qa-standards.
    return seen_skills, seen_agents


def walk_files(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(EXCLUDE_SUFFIXES):
                continue
            yield os.path.join(dirpath, f)


def plan(catalog, args):
    """Return a list of (relative_path) to copy from the template root."""
    rel = []
    if args.full:
        skills = list(catalog["skills"].keys())
        agents = list(catalog["agents"].keys())
    else:
        wanted = []
        if args.group:
            for g in args.group.split(","):
                if g not in catalog["groups"]:
                    sys.exit("unknown group: %s (groups: %s)" % (g, ", ".join(catalog["groups"])))
                wanted += catalog["groups"][g]
        if args.skill:
            wanted += [s.strip() for s in args.skill.split(",") if s.strip()]
        if not wanted:
            sys.exit("nothing selected: use --full, --group <name> or --skill <name>")
        skills, agents = resolve(catalog, wanted)
    for s in skills:
        for f in walk_files(skill_dir(s)):
            rel.append(os.path.relpath(f, TEMPLATE_ROOT))
    if not args.user:
        for a in agents:
            rel.append(catalog["agents"][a]["file"])
        rel += catalog["core"]["files"]
        if args.with_scripts or args.full:
            for f in walk_files(os.path.join(TEMPLATE_ROOT, "scripts")):
                rel.append(os.path.relpath(f, TEMPLATE_ROOT))
            rel.append("catalog.json")
            for f in walk_files(os.path.join(TEMPLATE_ROOT, "docs")):
                rel.append(os.path.relpath(f, TEMPLATE_ROOT))
            rel.append("README.md")
    # de-duplicate, keep order
    out, seen = [], set()
    for r in rel:
        r = r.replace("\\", "/")
        if r not in seen:
            seen.add(r)
            out.append(r)
    return skills, agents, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", help="project root to install into (project-level)")
    ap.add_argument("--user", action="store_true", help="user-level install into ~/.claude/skills (skills only)")
    ap.add_argument("--full", action="store_true", help="install everything")
    ap.add_argument("--group", help="comma-separated group names from catalog.json")
    ap.add_argument("--skill", help="comma-separated skill names")
    ap.add_argument("--with-scripts", action="store_true", help="also copy scripts/, docs/, catalog.json, README.md (implied by --full)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, copy nothing")
    ap.add_argument("--force", action="store_true", help="overwrite preserved config files too (writes no *.new)")
    ap.add_argument("--list", action="store_true", help="list skills, groups and agents")
    args = ap.parse_args()

    catalog = load_catalog()
    if args.list:
        print("Groups:")
        for g, members in catalog["groups"].items():
            print("  %-14s %s" % (g, ", ".join(members)))
        print("\nSkills:")
        for name, meta in catalog["skills"].items():
            print("  %-22s %-50s %s" % (name, meta["capability"], meta["summary"]))
        print("\nAgents:")
        for name, meta in catalog["agents"].items():
            print("  %-22s %s (%s)" % (name, meta["file"], meta["capability"]))
        return

    if args.user:
        dest_root = os.path.join(os.path.expanduser("~"), ".claude")
        if args.full or args.group:
            sys.exit("--user installs individual skills only: use --skill <name>")
    else:
        if not args.target:
            sys.exit("--target <project-root> is required (or --user)")
        dest_root = os.path.abspath(args.target)
        if os.path.abspath(dest_root) == TEMPLATE_ROOT:
            sys.exit("refusing to install the template into itself")

    skills, agents, files = plan(catalog, args)
    preserve = set(catalog["core"].get("preserve_if_present", []))

    print("Template : %s" % TEMPLATE_ROOT)
    print("Target   : %s (%s)" % (dest_root, "user-level" if args.user else "project-level"))
    print("Skills   : %s" % ", ".join(skills))
    if not args.user:
        print("Agents   : %s" % (", ".join(agents) or "(none)"))
    print("Files    : %d" % len(files))
    copied = kept = 0
    for rel in files:
        src = os.path.join(TEMPLATE_ROOT, rel)
        if args.user:
            # ~/.claude/skills/<name>/... (strip the leading .claude/)
            dst = os.path.join(dest_root, rel[len(".claude/"):] if rel.startswith(".claude/") else rel)
        else:
            dst = os.path.join(dest_root, rel)
        if not os.path.exists(src):
            print("  MISSING in template: %s" % rel)
            continue
        if rel in preserve and os.path.exists(dst) and not args.force:
            dst_new = dst + ".new"
            action = "keep (template copy -> %s)" % os.path.basename(dst_new)
            target = dst_new
            kept += 1
        else:
            action = "copy"
            target = dst
            copied += 1
        if args.dry_run:
            print("  %-45s %s" % (action, rel))
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(src, target)
    print("Done: %d copied, %d preserved%s." % (copied, kept, " (dry run)" if args.dry_run else ""))
    if not args.user and not args.dry_run:
        print("\nNext: open Claude Code in %s and say \"Read SETUP.md and configure this QA harness for my project.\"" % dest_root)
        print("      Review any *.new files next to preserved config and merge what you need.")


if __name__ == "__main__":
    main()
