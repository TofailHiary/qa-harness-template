#!/usr/bin/env python3
"""Runtime adapters for scripts/install.py --runtime <codex|opencode|cline|kilo>.

The harness itself always installs in its Claude Code layout (.claude/...), because every skill refers to
paths inside it. An adapter ADDS what another runtime needs to find the same files and to run with the
strongest read-only policy that runtime can express. Facts per runtime were checked against each runtime's
own documentation on 2026-10-26 (Cline's .agents/skills scan was confirmed in its source code, not its docs):

  runtime   instructions  skills it scans (project)                    MCP config (project)          policy it can enforce
  codex     AGENTS.md     .agents/skills                               .codex/config.toml (trusted)  sandbox_mode + approval_policy + .codex/rules (experimental)
  opencode  AGENTS.md     .opencode/skills, .claude/skills, .agents/skills  opencode.json            "permission" (edit / bash patterns / webfetch)
  cline     AGENTS.md     .cline/skills, .clinerules/skills, .claude/skills  GLOBAL only              none per project (UI auto-approve settings)
  kilo      AGENTS.md     .kilo/skills, .agents/skills (.claude/skills only with Claude compatibility)  kilo.jsonc  "permission" (most tools default to allow)

None of these runtimes runs the harness's Claude Code hooks, so the guards, the fail-closed launcher and the
completion gate are NOT active there. Each adapter prints exactly what is enforced and what is advisory.
Existing runtime config files are never overwritten: the new version is written next to them as <name>.new.
"""
import importlib.util
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ROOT = os.path.abspath(os.path.join(HERE, ".."))
RUNTIMES = ("codex", "opencode", "cline", "kilo")
PLACEHOLDER = re.compile(r"^\$\{([A-Z0-9_]+)\}$")

READ_ONLY_GIT = ["git status", "git log", "git diff", "git show", "git rev-parse", "git branch --show-current",
                 "git fetch", "git pull", "git ls-files", "git blame"]
DENY_CMDS = ["git commit", "git push", "git reset", "git checkout", "git switch", "git merge", "git rebase",
             "git stash", "git add", "git rm", "git mv", "git clean", "git restore", "git cherry-pick",
             "git am", "git apply", "git worktree", "git tag", "npm publish", "npm version", "rm -rf"]


def _render_module():
    p = os.path.join(TEMPLATE_ROOT, ".claude", "scripts", "render_mcp.py")
    spec = importlib.util.spec_from_file_location("render_mcp", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def enabled_servers(dest):
    """The MCP servers enabled by the target project's profile, with ${PROJECT_ROOT} substituted."""
    rm = _render_module()
    with io.open(os.path.join(TEMPLATE_ROOT, ".mcp.json.template"), encoding="utf-8") as fh:
        tpl = json.load(fh)
    prof = os.path.join(dest, ".claude", "PROJECT-PROFILE.md")
    caps = rm.capabilities(io.open(prof, encoding="utf-8").read()) if os.path.exists(prof) else {}
    rendered, _, _ = rm.render(tpl, caps, dest, "linux")      # plain npx: these runtimes launch commands themselves
    out = {}
    for name, srv in rendered["mcpServers"].items():
        if srv.get("disabled"):
            continue
        out[name] = {k: v for k, v in srv.items() if not k.startswith("_") and k != "disabled"}
    return out


def _write(path, text, dry, log):
    rel = path
    if os.path.exists(path):
        path = path + ".new"
        log.append("kept existing %s; wrote %s" % (os.path.basename(rel), os.path.basename(path)))
    if dry:
        log.append("would write %s" % path)
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    log.append("wrote %s" % path)
    return path


def _frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        mm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip()
    return fm


def pointer_skills(dest, skills, dry, log):
    """.agents/skills/<name>/SKILL.md stubs that send the runtime to the one real copy in .claude/skills."""
    n = 0
    for s in skills:
        src = os.path.join(dest, ".claude", "skills", s, "SKILL.md")
        if not os.path.exists(src) and not dry:
            continue
        fm = _frontmatter(io.open(src, encoding="utf-8").read()) if os.path.exists(src) else {"name": s, "description": ""}
        desc = fm.get("description", "")
        text = ("---\nname: %s\ndescription: %s\n---\n\n# %s (pointer)\n\n"
                "The QA harness keeps ONE copy of this skill: `.claude/skills/%s/SKILL.md`. Read that file now and follow\n"
                "it exactly. Its `references/` and `scripts/` paths are relative to `.claude/skills/%s/`. Read `AGENTS.md`\n"
                "first if you have not done so this session.\n") % (s, desc, s, s, s)
        p = os.path.join(dest, ".agents", "skills", s, "SKILL.md")
        if dry:
            n += 1
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        n += 1
    log.append("%s %d pointer skill(s) in .agents/skills" % ("would write" if dry else "wrote", n))


def _toml_str(v):
    return json.dumps(v, ensure_ascii=True)


def codex(dest, servers, skills, dry, log):
    lines = ["# Generated by scripts/install.py --runtime codex (QA harness). Project config is loaded only when the",
             "# project is trusted in ~/.codex/config.toml. Policy: read-only sandbox; Codex asks before anything else.",
             'sandbox_mode = "read-only"', 'approval_policy = "on-request"', ""]
    notes = []
    names_seen = {}
    exported = []
    for name, srv in servers.items():
        env = srv.get("env") or {}
        forward = [k for k, v in env.items() if isinstance(v, str) and PLACEHOLDER.match(v)]
        literal = {k: v for k, v in env.items() if k not in forward}
        clash = [k for k in forward if k in names_seen]
        if clash:
            notes.append("server %s skipped: Codex forwards variables by name and %s is already used by %s - add it to "
                         "~/.codex/config.toml by hand with its own values" % (name, ", ".join(clash), names_seen[clash[0]]))
            continue
        for k in forward:
            names_seen[k] = name
            exported.append(k)
        lines.append("[mcp_servers.%s]" % name)
        lines.append("command = %s" % _toml_str(srv["command"]))
        lines.append("args = [%s]" % ", ".join(_toml_str(a) for a in srv.get("args", [])))
        if forward:
            lines.append("env_vars = [%s]" % ", ".join(_toml_str(k) for k in forward))
            renames = ["%s<-%s" % (k, PLACEHOLDER.match(env[k]).group(1)) for k in forward if PLACEHOLDER.match(env[k]).group(1) != k]
            if renames:
                notes.append("server %s: Codex forwards variables by NAME - export %s under these names "
                             "(not the template names)" % (name, ", ".join(k for k in forward)))
        if literal:
            lines.append("[mcp_servers.%s.env]" % name)
            for k, v in literal.items():
                lines.append("%s = %s" % (k, _toml_str(v)))
        lines.append("")
    _write(os.path.join(dest, ".codex", "config.toml"), "\n".join(lines).rstrip("\n") + "\n", dry, log)
    rules = ["# Generated by scripts/install.py --runtime codex. Codex command rules are experimental; the read-only",
             "# sandbox above is the primary control. Loaded only for trusted projects."]
    rules += ['prefix_rule(pattern=[%s], decision="forbidden")' % ", ".join(_toml_str(p) for p in c.split()) for c in DENY_CMDS]
    _write(os.path.join(dest, ".codex", "rules", "qa-readonly.rules"), "\n".join(rules) + "\n", dry, log)
    pointer_skills(dest, skills, dry, log)
    return {"enforced": ["read-only sandbox (sandbox_mode)", "approval before leaving the sandbox (approval_policy)",
                         "forbidden git/npm write prefixes (.codex/rules, experimental)"],
            "advisory": ["the harness guards and the completion gate (Claude Code hooks) are not wired for Codex",
                         "evidence and memory writes need your approval each time under the read-only sandbox"],
            "steps": ["trust the project in ~/.codex/config.toml ([projects.\"<path>\"] trust_level = \"trusted\") so "
                      ".codex/ is loaded", "export the variables listed below, then run: codex mcp list"],
            "notes": notes, "variables": exported}


def _permission():
    bash = {"*": "ask"}
    for g in READ_ONLY_GIT:
        bash[g + "*"] = "allow"
    for d in DENY_CMDS:
        bash[d + "*"] = "deny"
    return {"edit": "ask", "bash": bash, "webfetch": "ask"}


def _local_mcp(servers):
    out = {}
    for name, srv in servers.items():
        env = {}
        for k, v in (srv.get("env") or {}).items():
            m = PLACEHOLDER.match(v) if isinstance(v, str) else None
            env[k] = "{env:%s}" % m.group(1) if m else v
        entry = {"type": "local", "command": [srv["command"]] + list(srv.get("args", [])), "enabled": True}
        if env:
            entry["environment"] = env
        out[name] = entry
    return out


def opencode(dest, servers, skills, dry, log):
    cfg = {"$schema": "https://opencode.ai/config.json", "mcp": _local_mcp(servers), "permission": _permission()}
    _write(os.path.join(dest, "opencode.json"), json.dumps(cfg, indent=2) + "\n", dry, log)
    log.append("skills: OpenCode scans .claude/skills directly - no copies made")
    return {"enforced": ["edit asks; bash asks by default; read-only git allowed; git/npm write prefixes denied (permission)"],
            "advisory": ["the harness guards and the completion gate are not wired for OpenCode (its plugins could host them; "
                         "not shipped)"], "steps": ["export the variables listed below"], "notes": []}


def kilo(dest, servers, skills, dry, log):
    cfg = {"$schema": "https://app.kilo.ai/config.json", "mcp": _local_mcp(servers), "permission": _permission()}
    _write(os.path.join(dest, "kilo.jsonc"), "// Generated by scripts/install.py --runtime kilo (QA harness).\n"
           + json.dumps(cfg, indent=2) + "\n", dry, log)
    pointer_skills(dest, skills, dry, log)
    return {"enforced": ["edit asks; bash asks by default; read-only git allowed; git/npm write prefixes denied (permission) - "
                         "Kilo allows most tools by default, so these rules matter"],
            "advisory": ["the harness guards and the completion gate are not wired for Kilo",
                         "if Kilo's Claude Code compatibility is on, skills appear twice (.claude/skills and .agents/skills): "
                         "turn it off or delete .agents/skills"],
            "steps": ["reload the VS Code window so Kilo reads kilo.jsonc", "export the variables listed below"], "notes": []}


def cline(dest, servers, skills, dry, log):
    snippet = {"mcpServers": {n: dict(s, disabled=False, autoApprove=[]) for n, s in servers.items()}}
    _write(os.path.join(dest, ".agents", "cline-mcp-settings.snippet.json"), json.dumps(snippet, indent=2) + "\n", dry, log)
    log.append("skills: Cline scans .claude/skills directly - no copies made")
    return {"enforced": ["nothing per project: Cline has no project policy file"],
            "advisory": ["turn OFF auto-approve for edits and commands in Cline's settings for this workspace",
                         "the harness guards and the completion gate are not wired for Cline"],
            "steps": ["merge .agents/cline-mcp-settings.snippet.json into Cline's GLOBAL MCP settings file "
                      "(Cline has no project-level MCP config); replace each ${VAR} with its value there or keep it if your "
                      "Cline build expands variables"], "notes": []}


def apply(runtime, dest, skills, dry=False):
    servers = enabled_servers(dest)
    log = []
    res = {"codex": codex, "opencode": opencode, "cline": cline, "kilo": kilo}[runtime](dest, servers, skills, dry, log)
    variables = sorted({PLACEHOLDER.match(v).group(1) for s in servers.values() for v in (s.get("env") or {}).values()
                        if isinstance(v, str) and PLACEHOLDER.match(v)})
    print("\nRuntime adapter: %s" % runtime)
    for line in log:
        print("  " + line)
    print("  MCP servers enabled by the profile: %s" % (", ".join(servers) or "none (fill PROJECT-PROFILE.md §2 first)"))
    print("  Enforced by %s: %s" % (runtime, "; ".join(res["enforced"])))
    print("  NOT enforced (follow AGENTS.md by discipline): %s" % "; ".join(res["advisory"]))
    for s in res["steps"]:
        print("  Next: " + s)
    for n in res["notes"]:
        print("  Note: " + n)
    variables = res.get("variables", variables)
    if variables:
        print("  Variables to export before starting %s (names only): %s" % (runtime, ", ".join(variables)))
    return res