#!/usr/bin/env python3
"""Shared config loader for the portable read-only QA hooks.

Resolves the project root from CLAUDE_PROJECT_DIR (set by Claude Code) and reads
harness-config.json sitting next to this file. The bootstrap (/configure-project)
generates harness-config.json from PROJECT-PROFILE.md; if a field is empty we fall
back to a sensible default derived from the project root.

Fields (all optional):
  memory_root          absolute path of the auto-memory folder ("" = derive from CLAUDE_PROJECT_DIR)
  evidence_root        evidence folder, relative to the project root or absolute (default "qa-evidence")
  allowed_write_globs  project-relative globs the Write/Edit tools may touch (the harness's own config)
  protected_repos      folder names (under the project root) that are READ-ONLY product source
  owned_repos          folder names that are the team's OWN code: edits, commits and pushes are allowed
                       there (the exemption applies only when no protected repo is in reach)
  gate                 completion-gate settings (see completion-gate.py)
"""
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


def _names(v):
    """Accept a list of folder names (or a single string); drop blanks."""
    if isinstance(v, str):
        v = [v]
    return [str(x).strip().strip("/\\") for x in (v or []) if str(x).strip()]


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
        "protected_repos": _names(cfg.get("protected_repos", [])),
        "owned_repos": _names(cfg.get("owned_repos", [])),
        "gate": cfg.get("gate", {}) or {},
    }
