#!/usr/bin/env python3
"""PreToolUse Write|Edit|MultiEdit|NotebookEdit - READ-ONLY QA (portable).

Allow writes ONLY to:
  - the project's auto-memory folder (so QA findings can be persisted),
  - the harness self-config allow-globs (PROJECT-PROFILE.md, settings.json,
    harness-config.json, .mcp.json) so /configure-project can run and re-run, and
  - the team's OWNED repos listed in harness-config.json -> owned_repos (not QA targets).
Block everything else - product source code, secrets, qa-evidence (use the
filesystem MCP), anything. Fail-closed on malformed input.

The two files that configure the guards are checked by CONTENT, not only by path:
  harness-config.json  may be TIGHTENED freely (add a protected repo, drop an owned repo, narrow the
                       allow-globs). LOOSENING it - removing a protected repo, adding an owned repo,
                       widening allowed_write_globs, moving memory_root / evidence_root somewhere that
                       opens product code, switching an enforced gate off, or writing unparseable JSON -
                       needs a human: start Claude Code with QA_HARNESS_ADMIN=1, or edit the file by hand.
  settings.json        may change freely EXCEPT: dropping or re-pointing a guard hook, disableAllHooks,
                       removing a deny rule, switching QA_GATE_ENFORCE off, or setting QA_HARNESS_ADMIN.
A session cannot grant itself an exemption the human did not give it."""
import fnmatch
import json
import os
import re
import sys
import harness_config as hc

GUARD_SCRIPTS = ("block-writes.py", "block-bash-writes.py", "block-powershell-writes.py",
                 "block-filesystem-writes.py", "block-github-writes.py", "completion-gate.py")


def block(reason):
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def admin():
    return os.environ.get("QA_HARNESS_ADMIN") == "1"


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return None


def proposed_text(ti, current):
    """The file content after this Write / Edit / MultiEdit, or None when it cannot be computed."""
    if "content" in ti:
        return ti.get("content") or ""
    cur = current or ""
    edits = ti.get("edits")
    if edits is None and "old_string" in ti:
        edits = [ti]
    if not isinstance(edits, list):
        return None
    for e in edits:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        if not old or old not in cur:
            return None
        cur = cur.replace(old, new) if e.get("replace_all") else cur.replace(old, new, 1)
    return cur


def _names(v):
    return {x.lower() for x in hc._names(v)}


def config_loosening(old, new, root):
    why = []
    gone = _names(old.get("protected_repos")) - _names(new.get("protected_repos"))
    if gone:
        why.append("removes protected repo(s) %s" % sorted(gone))
    added = _names(new.get("owned_repos")) - _names(old.get("owned_repos"))
    if added:
        why.append("adds owned repo(s) %s" % sorted(added))
    wider = set(new.get("allowed_write_globs") or []) - set(old.get("allowed_write_globs") or [])
    if wider:
        why.append("widens allowed_write_globs with %s" % sorted(wider))
    mem_old, mem_new = old.get("memory_root") or "", new.get("memory_root") or ""
    if mem_new and mem_new != mem_old:
        home_claude = hc.norm(os.path.join(os.path.expanduser("~"), ".claude"))
        if not hc.is_under(hc.norm(mem_new), home_claude):
            why.append("moves memory_root outside ~/.claude (it is a write-allowed folder)")
    ev_old, ev_new = old.get("evidence_root") or "qa-evidence", new.get("evidence_root") or "qa-evidence"
    if ev_new != ev_old:
        ev = hc.norm(ev_new if os.path.isabs(ev_new) else os.path.join(root, ev_new))
        repos = _names(new.get("protected_repos")) | _names(new.get("owned_repos"))
        inside_repo = any(hc.is_under(ev, hc.norm(os.path.join(root, r))) for r in repos)
        if ev == hc.norm(root) or not hc.is_under(ev, hc.norm(root)) or inside_repo:
            why.append("moves evidence_root to %r (it must be a sub-folder of the project, outside every repo)" % ev_new)
    if (old.get("gate") or {}).get("enforce") and not (new.get("gate") or {}).get("enforce"):
        why.append("switches an enforced completion gate off")
    return why


_RUNS = r"(?:run-hook\.sh[\x22\x27]?\s+[\x22\x27]?|python[0-9.]*(?:\.exe)?\s+(?:-\S+\s+)*[\x22\x27]?[^\x22\x27\s]*[/\\])"


def guard_hooks(settings):
    out = set()
    for event, groups in ((settings.get("hooks") or {}).items()):
        for g in groups or []:
            for h in (g or {}).get("hooks", []) or []:
                cmd = (h or {}).get("command", "") or ""
                for s in GUARD_SCRIPTS:
                    if re.search(_RUNS + re.escape(s) + r"(?![\w.-])", cmd):
                        out.add((event, g.get("matcher", ""), s))
    return out


def settings_loosening(old, new):
    why = []
    lost = guard_hooks(old) - guard_hooks(new)
    if lost:
        why.append("drops or re-points guard hook(s) %s" % sorted("%s/%s/%s" % t for t in lost))
    if new.get("disableAllHooks") and not old.get("disableAllHooks"):
        why.append("sets disableAllHooks")
    env_old, env_new = old.get("env") or {}, new.get("env") or {}
    if "QA_HARNESS_ADMIN" in env_new:
        why.append("sets QA_HARNESS_ADMIN (only a human may start an admin session)")
    if str(env_old.get("QA_GATE_ENFORCE", "0")) == "1" and str(env_new.get("QA_GATE_ENFORCE", "0")) != "1":
        why.append("switches QA_GATE_ENFORCE off")
    deny_lost = set((old.get("permissions") or {}).get("deny") or []) - set((new.get("permissions") or {}).get("deny") or [])
    if deny_lost:
        why.append("removes deny rule(s) %s" % sorted(deny_lost))
    return why


def check_guard_config(rel, tnorm, ti, root):
    """Content check for the two files that configure the guards. Returns only when the change is allowed."""
    kind = "config" if rel.endswith("hooks/harness-config.json") else "settings" if rel == ".claude/settings.json" else None
    if not kind or admin():
        return
    current = _read(tnorm)
    text = proposed_text(ti, current)
    if text is None:
        block("READ-ONLY QA: cannot compute the new content of %s (edit did not match). Blocked - this file "
              "configures the guards." % rel)
    try:
        new = json.loads(text)
        assert isinstance(new, dict)
    except Exception:
        block("READ-ONLY QA: the new %s is not a JSON object. An unparseable file would silently switch the "
              "guards off. Blocked." % rel)
    try:
        old = json.loads(current) if current else {}
        old = old if isinstance(old, dict) else {}
    except Exception:
        old = {}
    why = config_loosening(old, new, root) if kind == "config" else settings_loosening(old, new)
    if why:
        block("READ-ONLY QA: this change to %s LOOSENS the guards (%s). A session cannot grant itself that. "
              "Ask the user to make the change by hand, or to restart Claude Code with QA_HARNESS_ADMIN=1."
              % (rel, "; ".join(why)))


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
    target = ti.get("file_path") or ti.get("path") or ti.get("notebook_path") or ""
    tnorm = hc.norm(target)
    if not tnorm:
        block("READ-ONLY QA: no file_path in tool input. Write/Edit blocked.")

    # 1) allow the auto-memory folder
    if hc.is_under(tnorm, cfg["memory_root"]):
        sys.exit(0)

    # 2) allow the team's owned repos (folder names under the project root)
    for name in cfg.get("owned_repos", []):
        if hc.is_under(tnorm, hc.norm(os.path.join(cfg["project_root"], name))):
            sys.exit(0)

    # 3) allow the harness's own config files (project-relative globs) - guard config checked by content
    try:
        rel = os.path.relpath(tnorm, cfg["project_root"]).replace("\\", "/")
    except Exception:
        rel = ""
    for g in cfg["allowed_write_globs"]:
        if rel and fnmatch.fnmatch(rel.lower(), g.lower()):
            check_guard_config(rel.lower(), tnorm, ti, cfg["project_root"])
            sys.exit(0)

    block(
        "READ-ONLY QA: Write/Edit to '%s' is blocked. Allowed: the memory folder, the owned repos "
        "(harness-config.json -> owned_repos) and the harness config (PROJECT-PROFILE.md, settings.json, "
        "harness-config.json, .mcp.json). Product code is read-only; use the filesystem MCP for "
        "qa-evidence attachments." % target
    )


if __name__ == "__main__":
    main()