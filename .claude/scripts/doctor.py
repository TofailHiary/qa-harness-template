#!/usr/bin/env python3
"""First-run diagnostics for the QA harness: is this machine and project ready, and do the guards really block?

    python .claude/scripts/doctor.py          # table + READY / NOT READY; exit 1 on any FAIL
    python .claude/scripts/doctor.py --json   # machine-readable

It never reads secret VALUES: for .mcp.json it only reports whether credential-looking keys hold a
${PLACEHOLDER} or an inline value. Standard library only; no network.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(os.path.join(CLAUDE, ".."))
HOOKS = os.path.join(CLAUDE, "hooks")
GUARDS = ["block-writes.py", "block-bash-writes.py", "block-powershell-writes.py", "block-filesystem-writes.py",
          "block-github-writes.py", "completion-gate.py"]
ROWS = []


def row(check, status, detail):
    ROWS.append((check, status, detail))


def run(cmd, **kw):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=kw.pop("timeout", 30), **kw)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return None, type(e).__name__


def find_sh():
    cands = []
    if os.name == "nt":
        gb = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH", "")
        if gb:
            cands += [os.path.join(os.path.dirname(gb), "sh.exe"), gb]
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", ""),
                     os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
            if base:
                cands += [os.path.join(base, "Git", "usr", "bin", "sh.exe"), os.path.join(base, "Git", "bin", "bash.exe")]
    cands += [shutil.which("sh") or "", shutil.which("bash") or ""]
    for p in cands:
        low = p.lower()
        if p and os.path.exists(p) and "system32" not in low and "windowsapps" not in low:
            return p
    return None


def tools():
    row("python (this run)", "OK", sys.version.split()[0])
    names = []
    for n in ("python3", "python", "py"):
        if shutil.which(n):
            rc, _ = run([n] + (["-3"] if n == "py" else []) + ["-S", "-E", "-c", "import sys; sys.exit(sys.version_info[0] != 3)"])
            names.append("%s=%s" % (n, "ok" if rc == 0 else "broken"))
    row("python names hooks can use", "OK" if any(x.endswith("=ok") for x in names) else "FAIL",
        ", ".join(names) or "none on PATH - run-hook.sh will block every tool call")
    rc, out = run(["node", "--version"], shell=(os.name == "nt"))
    m = re.search(r"v(\d+)", out or "")
    if rc == 0 and m:
        row("node", "OK" if int(m.group(1)) >= 18 else "FAIL", out.strip() + ("" if int(m.group(1)) >= 18 else " (need >= 18)"))
    else:
        row("node", "FAIL", "not found (needed for memory rotation, the HTTP MCP server and npx servers)")
    rc, out = run(["git", "--version"])
    row("git", "OK" if rc == 0 else "WARN", (out or "not found").strip())
    sh = find_sh()
    row("POSIX sh (runs hooks)", "OK" if sh else "FAIL", sh or "not found - on Windows install Git for Windows")
    rc, out = run(["ffmpeg", "-version"])
    row("ffmpeg (demo-creator only)", "OK" if rc == 0 else "WARN", (out.splitlines()[0] if rc == 0 and out else "not found"))
    rc, out = run(["claude", "--version"], shell=(os.name == "nt"))
    row("claude CLI (optional)", "OK" if rc == 0 else "WARN", (out or "").strip()[:60] or "not on PATH")
    return sh


def hooks_and_settings(sh):
    missing = [g for g in GUARDS + ["harness_config.py", "run-hook.sh"] if not os.path.exists(os.path.join(HOOKS, g))]
    row("hook files", "FAIL" if missing else "OK", ("missing: " + ", ".join(missing)) if missing else "all present")
    try:
        st = json.load(io.open(os.path.join(CLAUDE, "settings.json"), encoding="utf-8"))
        cmds = [h.get("command", "") for gs in (st.get("hooks") or {}).values() for g in gs for h in g.get("hooks", [])]
        bare = [c for c in cmds if ".py" in c and "run-hook.sh" not in c]
        wired = [g for g in GUARDS if any(g in c for c in cmds)]
        row("settings.json hooks", "FAIL" if bare or len(wired) < len(GUARDS) else "OK",
            ("python hooks not behind run-hook.sh: %d" % len(bare)) if bare else "%d/%d guards wired through run-hook.sh" % (len(wired), len(GUARDS)))
        if st.get("disableAllHooks"):
            row("settings.json disableAllHooks", "FAIL", "true - every guard is off")
        if "Read(.mcp.json)" not in (st.get("permissions") or {}).get("deny", []):
            row("deny Read(.mcp.json)", "WARN", "missing from settings.json deny list")
    except Exception as e:
        row("settings.json", "FAIL", "cannot parse (%s)" % type(e).__name__)
    if not sh:
        row("guard self-test", "FAIL", "skipped - no POSIX sh")
        return
    sys.path.insert(0, HOOKS)
    try:
        import harness_config as hc
        cfg = hc.load()
    except Exception as e:
        row("harness-config.json", "FAIL", "cannot load (%s)" % type(e).__name__)
        return
    row("harness-config.json", "OK", "protected repos: %d, owned repos: %d, gate: %s" % (
        len(cfg["protected_repos"]), len(cfg["owned_repos"]), "enforce" if (cfg.get("gate") or {}).get("enforce") else "advisory"))
    root = cfg["project_root"]
    probes = [
        ("block-bash-writes.py", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, 2),
        ("block-bash-writes.py", {"tool_name": "Bash", "tool_input": {"command": "git status"}}, 0),
        ("block-powershell-writes.py", {"tool_name": "PowerShell", "tool_input": {"command": "git push"}}, 2),
        ("block-powershell-writes.py", {"tool_name": "PowerShell", "tool_input": {"command": "Get-ChildItem"}}, 0),
        ("block-writes.py", {"tool_name": "Write", "tool_input": {"file_path": os.path.join(root, "zz-doctor-probe", "x.txt"), "content": "x"}}, 2),
        ("block-writes.py", {"tool_name": "Write", "tool_input": {"file_path": os.path.join(cfg["memory_root"], "doctor-probe.md"), "content": "x"}}, 0),
        ("block-filesystem-writes.py", {"tool_name": "mcp__filesystem__write_file", "tool_input": {"path": os.path.join(root, "zz-doctor-probe", "x.txt")}}, 2),
        ("block-filesystem-writes.py", {"tool_name": "mcp__filesystem__write_file", "tool_input": {"path": os.path.join(cfg["evidence_root"], "doctor", "x.txt")}}, 0),
        ("block-github-writes.py", {"tool_name": "mcp__github__create_pull_request", "tool_input": {"repo": "zz-doctor-not-owned", "owner": "example"}}, 2),
        ("completion-gate.py", {"last_assistant_message": "hello"}, 0),
    ]
    env = dict(os.environ, CLAUDE_PROJECT_DIR=ROOT)
    bad = []
    for script, payload, want in probes:
        args = [sh, os.path.join(HOOKS, "run-hook.sh").replace("\\", "/"), script] + (["--fail-open"] if script == "completion-gate.py" else [])
        rc, out = run(args, input=json.dumps(payload), env=env)
        if rc != want:
            bad.append("%s expected exit %s got %s" % (script, want, rc))
    row("guard self-test (via run-hook.sh)", "FAIL" if bad else "OK",
        "; ".join(bad) if bad else "%d probes: forbidden actions blocked, allowed ones pass" % len(probes))


def project():
    p = os.path.join(CLAUDE, "PROJECT-PROFILE.md")
    if not os.path.exists(p):
        row("PROJECT-PROFILE.md", "FAIL", "missing")
    else:
        t = io.open(p, encoding="utf-8").read()
        caps = re.findall(r"^- ([A-Za-z-]+): (on|off)\b", t, re.M)
        name = re.search(r"\*\*Project name:\*\*[ \t]*(\S[^\n]*)?$", t, re.M)
        on = [k for k, v in caps if v == "on"]
        configured = bool(name and name.group(1))
        row("PROJECT-PROFILE.md", "OK" if configured else "WARN",
            ("capabilities on: " + (", ".join(on) or "none")) if configured else "not configured yet - run /configure-project")
    m = os.path.join(ROOT, ".mcp.json")
    if not os.path.exists(m):
        row(".mcp.json", "WARN", "not generated yet - python .claude/scripts/render_mcp.py (or /configure-project)")
    else:
        try:
            data = json.load(io.open(m, encoding="utf-8"))
            raw = json.dumps(data)
            inline = 0
            for srv in (data.get("mcpServers") or {}).values():
                for k, v in (srv.get("env") or {}).items():
                    if re.search(r"PASS|KEY|TOKEN|SECRET", k) and isinstance(v, str) and v and not v.startswith("${"):
                        inline += 1
            status = "FAIL" if "${PROJECT_ROOT}" in raw else ("WARN" if inline else "OK")
            row(".mcp.json", status, "unrendered ${PROJECT_ROOT}" if "${PROJECT_ROOT}" in raw else
                ("%d secret value(s) stored inline - prefer ${ENV} placeholders" % inline if inline else "placeholders only"))
        except Exception as e:
            row(".mcp.json", "FAIL", "invalid JSON (%s)" % type(e).__name__)
    rb = os.path.join(HERE, "rebind.py")
    if os.path.exists(rb):
        rc, out = run([sys.executable, rb, "--check"])
        row("tool bindings", "OK" if rc == 0 else "FAIL", out.strip().splitlines()[-1] if out.strip() else "?")


def main():
    sh = tools()
    hooks_and_settings(sh)
    project()
    fails = [r for r in ROWS if r[1] == "FAIL"]
    if "--json" in sys.argv:
        print(json.dumps({"ready": not fails, "checks": [dict(zip(("check", "status", "detail"), r)) for r in ROWS]}, indent=2))
    else:
        w = max(len(r[0]) for r in ROWS)
        for c, s, d in ROWS:
            print("%-*s  %-4s  %s" % (w, c, s, d))
        print("\n%s" % ("READY" if not fails else "NOT READY - fix the FAIL rows (docs/troubleshooting.md)"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())