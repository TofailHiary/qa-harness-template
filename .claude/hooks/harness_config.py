#!/usr/bin/env python3
"""Shared config loader for the portable read-only QA hooks.

Resolves the project root from CLAUDE_PROJECT_DIR (set by Claude Code) and reads
harness-config.json sitting next to this file. The bootstrap (/configure-project)
generates harness-config.json from PROJECT-PROFILE.md; if a field is empty we fall
back to a sensible default derived from the project root."""
import json
import os


def project_root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _here():
    return os.path.dirname(os.path.abspath(__file__))


def _encode_project(path):
    # Mirror Claude Code's auto-memory project-dir encoding: replace ':', '/', '\'
    # with '-', then lowercase the drive letter. e.g. D:\code\proj -> d--code-proj
    p = path.replace("\\", "-").replace("/", "-").replace(":", "-")
    if len(p) >= 2 and p[1] == "-":
        p = p[0].lower() + p[1:]
    return p


def norm(p):
    if not p:
        return ""
    p = os.path.expandvars(os.path.expanduser(p))
    try:
        p = os.path.abspath(p)
    except Exception:
        pass
    return os.path.normcase(os.path.normpath(p))


def is_under(path, root):
    if not path or not root:
        return False
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        # different drives on Windows
        return False


def load():
    cfg = {}
    try:
        with open(os.path.join(_here(), "harness-config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    root = project_root()
    mem = cfg.get("memory_root") or os.path.join(
        os.path.expanduser("~"), ".claude", "projects", _encode_project(root), "memory")
    ev = cfg.get("evidence_root") or "qa-evidence"
    if not os.path.isabs(ev):
        ev = os.path.join(root, ev)
    return {
        "project_root": norm(root),
        "memory_root": norm(mem),
        "evidence_root": norm(ev),
        "allowed_write_globs": cfg.get("allowed_write_globs", []),
        "protected_repos": cfg.get("protected_repos", []),
    }
