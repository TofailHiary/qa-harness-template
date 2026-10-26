#!/usr/bin/env python3
"""Adversarial qualification suite for the read-only write guards (the hooks in .claude/hooks).

    python scripts/hook-redteam/runner.py            # run the guard cases against a throw-away project
    python scripts/hook-redteam/runner.py --selftest # prove the RUNNER itself works
    python scripts/hook-redteam/runner.py --hooks <dir>   # qualify another hooks folder (an installed copy)

The run ends with the LAUNCHER section: run-hook.sh (the fail-closed wrapper settings.json calls) is driven
through a real POSIX sh with a forbidden and an allowed payload, a missing script, a crashing guard, the
advisory --fail-open mode and a PATH with no usable Python.

Exit 0 = every case behaved as declared. Exit 1 = a guard (or the runner) regressed.

HOW IT WORKS
  A temporary project root is created with these folders: app-backend/, app-frontend/ (protected),
  qa-tools/ (owned), qa-evidence/ (evidence), .memory/ (memory root). The hooks are copied next to a
  harness-config.json that names those folders, CLAUDE_PROJECT_DIR points at the root, and every case in
  cases.json is sent to the right hook as the JSON Claude Code would send (tool_input + cwd).
  <root> inside a case is replaced by the temporary root (forward slashes); <rootw> by its Windows form.

WHY THIS FILE IS THE WAY IT IS
  Early versions of this kind of suite reported "all green" while: never sending `cwd` (so the cwd-aware
  guard was never exercised), deciding "blocked" by grepping for a string instead of the hook protocol
  (exit code 2 / permissionDecision deny), detecting crashes only by the literal "Traceback", and having
  no timeout. So: this runner speaks the hook PROTOCOL, carries `cwd`, times out, covers every guard, and
  has `--selftest` with FAKE hooks that deliberately allow, block, crash and hang. A suite that cannot
  detect a broken runner cannot qualify a guard.

RULES
  1. After editing ANY guard hook, run this. Require 0 failures.
  2. A NEW escape gets a case added FIRST. Watch it FAIL. Then fix the guard.
  3. Never delete a case to make the suite green.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_HOOKS = os.path.abspath(os.path.join(HERE, "..", "..", ".claude", "hooks"))
TEMPLATE_SETTINGS = os.path.abspath(os.path.join(HERE, "..", "..", ".claude", "settings.json"))
HOOK_FILES = {
    "bash": "block-bash-writes.py",
    "ps": "block-powershell-writes.py",
    "write": "block-writes.py",
    "fs": "block-filesystem-writes.py",
    "github": "block-github-writes.py",
}
TIMEOUT = 20
BLOCK_EXIT = 2   # hook protocol: exit 2 = block. Text is advisory only and MUST NOT be the signal.


def _decision_from_stdout(stdout):
    """Parse the hook's STDOUT as JSON and look for a deny, in either supported shape."""
    txt = (stdout or "").strip()
    if not txt:
        return None
    try:
        data = json.loads(txt)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    hso = data.get("hookSpecificOutput") or {}
    if isinstance(hso, dict) and str(hso.get("permissionDecision", "")).lower() == "deny":
        return True
    if str(data.get("decision", "")).lower() == "block":
        return True
    return False


def invoke(hook_path, payload, env, timeout=TIMEOUT):
    """Return (blocked, exit_code, broken, timed_out, output)."""
    try:
        p = subprocess.run([sys.executable, "-W", "ignore", hook_path], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return (False, None, True, True, "")
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode == BLOCK_EXIT:
        return (True, p.returncode, False, False, out)
    if p.returncode != 0:
        return (False, p.returncode, True, False, out)   # crash / wrong exit = broken guard (non-blocking in prod)
    return (bool(_decision_from_stdout(p.stdout)), p.returncode, False, False, out)


def build_payload(case, root):
    def sub(s):
        return s.replace("<rootw>", root.replace("/", "\\")).replace("<root>", root)
    hook = case["hook"]
    if hook == "write":
        ti = {"file_path": sub(case["cmd"])}
        if "content" in case:
            ti["content"] = sub(case["content"])
        if "content_from_settings" in case:
            ti["content"] = settings_variant(case["content_from_settings"])
        if "old_string" in case:
            ti["old_string"] = sub(case["old_string"])
            ti["new_string"] = sub(case.get("new_string", ""))
        payload = {"tool_name": case.get("tool", "Write"), "tool_input": ti}
    elif hook == "fs":
        tool = case.get("tool", "mcp__filesystem__write_file")
        ti = {"path": sub(case["cmd"])}
        if "move" in tool:
            ti = {"source": sub(case.get("src_path", case["cmd"])), "destination": sub(case["cmd"])}
        payload = {"tool_name": tool, "tool_input": ti}
    elif hook == "github":
        payload = {"tool_name": "mcp__github__create_pull_request", "tool_input": {"repo": case["cmd"], "owner": "example"}}
    else:
        payload = {"tool_name": "Bash" if hook == "bash" else "PowerShell", "tool_input": {"command": sub(case["cmd"])}}
    if case.get("cwd"):
        payload["cwd"] = sub(case["cwd"])
    return payload


def settings_variant(changes):
    """The shipped settings.json with `changes` merged in; `_drop_deny` removes one deny rule."""
    data = json.load(io.open(TEMPLATE_SETTINGS, encoding="utf-8"))
    for k, v in changes.items():
        if k == "_drop_deny":
            data["permissions"]["deny"] = [d for d in data["permissions"]["deny"] if d != v]
        elif isinstance(v, dict) and isinstance(data.get(k), dict):
            data[k].update(v)
        else:
            data[k] = v
    return json.dumps(data, indent=2)


def make_project(hooks_src):
    root = tempfile.mkdtemp(prefix="hookredteam-").replace("\\", "/")
    for d in ("app-backend/routes", "app-frontend/src", "qa-tools", "qa-evidence", ".memory", ".claude/hooks", ".claude/skills/x"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    for f in os.listdir(hooks_src):
        if f.endswith((".py", ".sh")):
            shutil.copyfile(os.path.join(hooks_src, f), os.path.join(root, ".claude", "hooks", f))
    if os.path.exists(TEMPLATE_SETTINGS):
        shutil.copyfile(TEMPLATE_SETTINGS, os.path.join(root, ".claude", "settings.json"))
    cfg = {
        "memory_root": root + "/.memory",
        "evidence_root": "qa-evidence",
        "allowed_write_globs": [".claude/PROJECT-PROFILE.md", ".claude/settings.json", ".claude/hooks/harness-config.json", ".mcp.json"],
        "protected_repos": ["app-backend", "app-frontend"],
        "owned_repos": ["qa-tools"],
        "gate": {"enforce": False},
    }
    with io.open(os.path.join(root, ".claude", "hooks", "harness-config.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    return root


def run_cases(cases, hooks_src):
    root = make_project(hooks_src)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=root, PYTHONDONTWRITEBYTECODE="1")
    fails = []
    for i, c in enumerate(cases, 1):
        hook = os.path.join(root, ".claude", "hooks", HOOK_FILES.get(c["hook"], ""))
        cid = c.get("id", "case-%d" % i)
        if not c["hook"] in HOOK_FILES or not os.path.exists(hook):
            fails.append((cid, c, "guard script missing: %s" % c["hook"])); continue
        case_env = dict(env, **c.get("env", {}))
        blocked, code, broken, timed_out, out = invoke(hook, build_payload(c, root), case_env)
        if timed_out:
            fails.append((cid, c, "TIMED OUT after %ss - a hung guard blocks nothing" % TIMEOUT)); continue
        if broken:
            fails.append((cid, c, "GUARD DID NOT SPEAK THE PROTOCOL (exit %s; only 0 or 2 are valid) -> non-blocking in production: %s" % (code, out.strip()[:120]))); continue
        if blocked != c["block"]:
            fails.append((cid, c, "ALLOWED but must BLOCK (exit %s)" % code if c["block"] else "BLOCKED but must ALLOW: %s" % out.strip()[:140]))
    shutil.rmtree(root, ignore_errors=True)
    return fails


FAKE = {
    "allow":        "import sys; sys.exit(0)",
    "block_exit2":  "import sys; sys.exit(2)",
    "text_only":    "print('READ-ONLY QA: blocked'); import sys; sys.exit(0)",
    "crash":        "raise SyntaxError('boom')",
    "hang":         "import time; time.sleep(60)",
    "modern_deny":  ("import json,sys; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
                     "'permissionDecision':'deny','permissionDecisionReason':'no'}})); sys.exit(0)"),
    "legacy_deny":  "import json,sys; print(json.dumps({'decision':'block','reason':'no'})); sys.exit(0)",
    "stderr_noise": "import sys; sys.stderr.write('note: decision block appear in this log line'); sys.exit(0)",
    "silent_exit1": "import sys; sys.exit(1)",
    "garbage_out":  "print('decision block but not json'); import sys; sys.exit(0)",
}


def selftest():
    tmp = tempfile.mkdtemp(prefix="hookselftest-")
    paths = {}
    for name, src in FAKE.items():
        p = os.path.join(tmp, name + ".py")
        io.open(p, "w", encoding="utf-8").write(src)
        paths[name] = p
    expect = [
        ("allow        -> not blocked", "allow", dict(blocked=False, broken=False, timed_out=False)),
        ("exit 2       -> blocked", "block_exit2", dict(blocked=True, broken=False, timed_out=False)),
        ("text only    -> NOT blocked (text is not protocol)", "text_only", dict(blocked=False, broken=False)),
        ("crash        -> broken", "crash", dict(broken=True)),
        ("hang         -> timed out AND broken", "hang", dict(timed_out=True, broken=True)),
        ("modern deny  -> blocked (permissionDecision)", "modern_deny", dict(blocked=True, broken=False)),
        ("legacy deny  -> blocked (decision:block)", "legacy_deny", dict(blocked=True, broken=False)),
        ("stderr noise -> NOT blocked (stderr is feedback)", "stderr_noise", dict(blocked=False, broken=False)),
        ("silent exit1 -> broken (neither 0 nor 2)", "silent_exit1", dict(broken=True)),
        ("garbage out  -> NOT blocked (unparseable != deny)", "garbage_out", dict(blocked=False, broken=False)),
    ]
    bad = 0
    print("RUNNER SELF-TEST (fake guards)")
    env = dict(os.environ)
    for label, key, want in expect:
        to = 2 if key == "hang" else TIMEOUT
        blocked, code, broken, timed_out, _ = invoke(paths[key], {"tool_input": {"command": "x"}}, env, timeout=to)
        got = dict(blocked=blocked, broken=broken, timed_out=timed_out)
        ok = all(got[k] == v for k, v in want.items())
        bad += 0 if ok else 1
        print("  %-5s %-52s %s" % ("OK" if ok else "FAIL", label, {k: got[k] for k in want}))
    shutil.rmtree(tmp, ignore_errors=True)
    print("  self-test failures: %d" % bad)
    return bad


def find_sh():
    """A POSIX sh to run the launcher with (Claude Code runs hook commands through one - Git Bash on Windows).

    On Windows the first `bash` on PATH is often C:\\Windows\\System32\\bash.exe, the WSL launcher, which
    cannot see Windows paths (exit 127). Prefer Git for Windows and skip System32 / WindowsApps stubs."""
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


def launcher_tests(hooks_src):
    """run-hook.sh must FAIL CLOSED: a guard that cannot run blocks instead of silently allowing."""
    sh = find_sh()
    if not sh:
        print("LAUNCHER: SKIPPED - no POSIX sh found (Claude Code needs one to run hooks at all)")
        return []
    if not os.path.exists(os.path.join(hooks_src, "run-hook.sh")):
        return [("L0", "run-hook.sh missing from %s" % hooks_src)]
    root = make_project(hooks_src)
    hooks = os.path.join(root, ".claude", "hooks")
    io.open(os.path.join(hooks, "crash.py"), "w", encoding="utf-8").write("raise RuntimeError('boom')\n")
    env = dict(os.environ, CLAUDE_PROJECT_DIR=root, PYTHONDONTWRITEBYTECODE="1")
    me = sys.executable.replace("\\", "/")
    bad = {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}
    good = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    cases = [
        ("L1", "guard + forbidden command -> exit 2", ["block-bash-writes.py"], bad, {}, 2),
        ("L2", "guard + read-only command -> exit 0", ["block-bash-writes.py"], good, {}, 0),
        ("L3", "missing guard script -> exit 2 (fail closed)", ["no-such-guard.py"], good, {}, 2),
        ("L4", "crashing guard -> exit 2 (fail closed)", ["crash.py"], good, {}, 2),
        ("L5", "crashing advisory hook --fail-open -> exit 0", ["crash.py", "--fail-open"], good, {}, 0),
        ("L6", "no usable Python on PATH -> exit 2", ["block-bash-writes.py"], good, {"QA_HOOK_PYTHONS": "no-such-python-xyz"}, 2),
        ("L7", "first name broken, second works -> real decision", ["block-bash-writes.py"], bad, {"QA_HOOK_PYTHONS": "no-such-python-xyz " + me}, 2),
        ("L8", "first name broken, second works -> allow passes", ["block-bash-writes.py"], good, {"QA_HOOK_PYTHONS": "no-such-python-xyz " + me}, 0),
    ]
    fails = []
    print("LAUNCHER (run-hook.sh via %s)" % sh)
    for cid, label, args, payload, extra, want in cases:
        try:
            p = subprocess.run([sh, os.path.join(hooks, "run-hook.sh").replace("\\", "/")] + args, input=json.dumps(payload),
                               capture_output=True, text=True, timeout=TIMEOUT, env=dict(env, **extra))
            got = p.returncode
        except subprocess.TimeoutExpired:
            got = "timeout"
        ok = got == want
        print("  %-5s %-3s %-52s exit %s" % ("OK" if ok else "FAIL", cid, label, got))
        if not ok:
            fails.append((cid, "%s: expected exit %s, got %s" % (label, want, got)))
    shutil.rmtree(root, ignore_errors=True)
    return fails


def main():
    hooks_src = TEMPLATE_HOOKS
    if "--hooks" in sys.argv:
        hooks_src = os.path.abspath(sys.argv[sys.argv.index("--hooks") + 1])
    if "--selftest" in sys.argv:
        sys.exit(1 if selftest() else 0)
    bad = selftest()
    print()
    if bad:
        print("ABORT: the runner itself is broken - its guard results cannot be trusted.")
        sys.exit(1)
    data = json.load(io.open(os.path.join(HERE, "cases.json"), encoding="utf-8"))
    cases = data["cases"]
    fails = run_cases(cases, hooks_src)
    print("GUARD CASES: %d   passed: %d   FAILED: %d   (hooks: %s)" % (len(cases), len(cases) - len(fails), len(fails), hooks_src))
    for cid, c, why in fails:
        tag = " [cwd]" if c.get("cwd") else ""
        print("  %-10s [%-6s]%s %-56s %s" % (cid, c["hook"], tag, c["cmd"][:56], why))
    print()
    lfails = launcher_tests(hooks_src)
    for cid, why in lfails:
        print("  LAUNCHER FAIL %s %s" % (cid, why))
    sys.exit(1 if (fails or lfails) else 0)


if __name__ == "__main__":
    main()
