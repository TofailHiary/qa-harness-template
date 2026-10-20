#!/usr/bin/env python3
"""Validate the template (or an installed copy) for portability, consistency and privacy.

  python scripts/validate.py              # template mode: run from the template repo
  python scripts/validate.py --installed  # installed mode: run inside a project that has the harness
  python scripts/validate.py --fix-catalog-doc   # regenerate docs/catalog.md from catalog.json

Template mode checks:
  * skill frontmatter (name == folder, description starts with "Use ", <= 1024 chars), agents frontmatter
  * every Skill(x) / Agent(x) / subagent_type reference resolves to a shipped skill / agent
  * catalog.json <-> .claude/skills and .claude/agents agree; listed files exist; docs/catalog.md is current
  * JSON files parse; hooks compile (python -m py_compile, node --check); settings.json hook commands exist
  * harness-config.json is the shipped default (no widened allow-globs, no repos, gate advisory)
  * relative markdown links resolve; no CRLF / BOM in text files; .gitignore covers the secret-bearing files
  * no tracked symlink / junction; no node_modules or evidence output tracked
  * privacy: shape-based scan (credentials, keys, tokens, non-example hostnames and emails, non-generic
    ticket keys, workstation paths, loopback tunnel ports) plus an optional git-ignored private list
Exit 1 on any ERROR; warnings do not fail.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ERR, WARN = [], []

TEXT_EXT = {".md", ".py", ".js", ".json", ".sh", ".template", ".html", ".txt", ".yml", ".yaml", ".gitignore", ".gitattributes", ""}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "qa-evidence", "out", ".playwright-mcp"}
PRIVATE_FILE = os.path.join(HERE, "private-patterns.json")   # git-ignored; never shipped

# ---------------------------------------------------------------------------------------------------
# Privacy scan - the mechanism
#
# The template must never carry anything that ties it to the machine, organisation or product it was
# generalized from. Two layers:
#
#   1. SHAPE-BASED rules (below, shipped): they describe what private data LOOKS like - credentials,
#      API keys and tokens, user-home paths, e-mail addresses and hostnames outside the documented
#      example domains, ticket keys outside the documented generic forms, loopback tunnel ports.
#      They name no product, person or host, so the scanner itself stays generic.
#   2. An OPTIONAL git-ignored file scripts/private-patterns.json, kept only on the maintainer's
#      machine, holding the literals and regexes specific to the source setup (product names, people,
#      ticket prefixes, hostname fragments, fixture accounts). When present it is merged into the scan
#      AND the scanner self-checks: none of its literals may appear anywhere in the tracked repo text,
#      this file included. Shape: {"literals": ["..."], "patterns": [{"pattern": "...", "why": "..."}]}.
#
# Allow-lists are the documented generic examples only (example.com, localhost, APP-nnn, BUG-ids, the
# SM-/TC- case ids used in skill examples). Add to them deliberately, never to silence a real hit.
# ---------------------------------------------------------------------------------------------------
GENERIC_EMAIL_DOMAINS = ("example.com",)                       # any sub-domain of these is fine
GENERIC_HOST_SUFFIXES = ("example.com", "localhost", "127.0.0.1")
KNOWN_TOOLING_HOSTS = ("json.schemastore.org", "github.com", "anthropic.com", "claude.com", "claude.ai", "npmjs.com",
                       "nodejs.org", "python.org", "playwright.dev")   # referenced by docs/config on purpose
GENERIC_TICKET_PREFIXES = ("APP", "BUG", "SM", "TC")           # APP-nnn, BUG-YYYYMMDD-HHMMSS, smoke/test case ids
GENERIC_LOOPBACK_PORTS = ()                                    # docs write 127.0.0.1:<port>, never a real port

SHAPE_PATTERNS = [
    (r"AIza[0-9A-Za-z_-]{20,}", "Google / Firebase API key"),
    (r"eyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{10,}", "JWT-like token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"\b(gh[pousr])_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"(?i)[A-Z]:[\\/]Users[\\/](?!<)", "workstation path"),
    (r"c--Users-[A-Za-z]", "encoded workstation path"),
    (r"(?i)(?:password|passwd|pwd)\s*[:=]\s*[\"']?(?![\"']?\s*[$<\[{\u2026.])[^\s\"',;)]{4,}", "credential assignment"),
    (r"(?i)\b[A-Z0-9_]*_PASS(?:WORD)?\s*=\s*(?![$<\[{])[^\s\"']{4,}", "credential assignment (env style)"),
    (r"(?i)sshpass\s+-p\s+\S+", "credential on the command line"),
    (r"127\.0\.0\.1:(\d{4,5})\b", "loopback tunnel port"),
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
HOST_RE = re.compile(r"\b((?:[a-z0-9-]+\.)+(?:com|net|org|io|co|dev|app|cloud|ai))\b")   # lowercase on purpose: real hostnames are; `System.IO` is not one
TICKET_RE = re.compile(r"\b([A-Z]{2,6})-\d{2,}\b")


def load_private():
    """The maintainer-only list. Absent on a clean clone; that is the expected state for users."""
    if not os.path.exists(PRIVATE_FILE):
        return [], []
    data = json.loads(read(PRIVATE_FILE))
    lits = [str(x) for x in data.get("literals", []) if str(x).strip()]
    pats = [(p["pattern"], p.get("why", "private pattern")) for p in data.get("patterns", []) if p.get("pattern")]
    return lits, pats


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = os.path.join(dirpath, f)
            if os.path.abspath(p) == os.path.abspath(PRIVATE_FILE) or f.endswith(".new"):
                continue
            yield p


def is_text(p):
    _, ext = os.path.splitext(p)
    return ext in TEXT_EXT or os.path.basename(p) in (".gitignore", ".gitattributes")


def read(p):
    with io.open(p, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def frontmatter(text):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip()
    return fm


def check_skills(catalog):
    skills_dir = os.path.join(ROOT, ".claude", "skills")
    on_disk = sorted(d for d in os.listdir(skills_dir) if os.path.isfile(os.path.join(skills_dir, d, "SKILL.md")))
    in_catalog = sorted(catalog["skills"].keys())
    for s in on_disk:
        if s not in in_catalog:
            ERR.append("catalog.json: skill folder not listed: %s" % s)
    for s in in_catalog:
        if s not in on_disk:
            ERR.append("catalog.json: listed skill has no folder: %s" % s)
        for f in catalog["skills"][s].get("files", []):
            if not os.path.exists(os.path.join(skills_dir, s, f)):
                ERR.append("catalog.json: %s lists missing file %s" % (s, f))
    agents = catalog["agents"]
    for a, meta in agents.items():
        if not os.path.exists(os.path.join(ROOT, meta["file"])):
            ERR.append("catalog.json: agent file missing: %s" % meta["file"])
    agent_files = {os.path.basename(m["file"]) for m in agents.values()}
    for f in os.listdir(os.path.join(ROOT, ".claude", "agents")):
        if f.endswith(".md") and f not in agent_files:
            ERR.append("agent file not in catalog.json: %s" % f)
    for s in on_disk:
        text = read(os.path.join(skills_dir, s, "SKILL.md"))
        fm = frontmatter(text)
        if not fm:
            ERR.append("%s: no frontmatter" % s); continue
        if fm.get("name") != s:
            ERR.append("%s: frontmatter name %r != folder" % (s, fm.get("name")))
        d = fm.get("description", "")
        if not d.lower().startswith("use "):
            ERR.append("%s: description must start with 'Use ...' (triggering conditions)" % s)
        if len(d) > 1024:
            ERR.append("%s: description longer than 1024 chars (%d)" % (s, len(d)))
        if re.search(r"<[^>]*PROJECT-PROFILE", d):
            ERR.append("%s: description carries a profile placeholder; keep descriptions plain" % s)
        for m in re.findall(r"Skill\(([A-Za-z0-9_:-]+)\)", text):
            if ":" in m:
                continue  # plugin skill, optional
            if m not in on_disk:
                ERR.append("%s: references Skill(%s) which is not shipped" % (s, m))
        for a, b in re.findall(r"Agent\(([A-Za-z0-9_-]+)\)|subagent_type:\s*\"([A-Za-z0-9_-]+)\"", text):
            an = a or b
            if an not in agents:
                ERR.append("%s: references agent %r which is not shipped" % (s, an))
    for a, meta in agents.items():
        fm = frontmatter(read(os.path.join(ROOT, meta["file"])))
        if not fm or fm.get("name") != a:
            ERR.append("%s: agent frontmatter name must be %r" % (meta["file"], a))
        if fm and "model" in fm:
            WARN.append("%s: pins a model; the template inherits the session model" % meta["file"])
    return on_disk


def check_json_and_hooks():
    for j in [".claude/settings.json", ".mcp.json.template", ".claude/hooks/harness-config.json", "catalog.json",
              ".claude/skills/prompt-generator/evals/evals.json", ".claude/skills/demo-creator/templates/steps.example.json"]:
        p = os.path.join(ROOT, j)
        if not os.path.exists(p):
            ERR.append("missing: %s" % j); continue
        try:
            json.loads(read(p))
        except Exception as e:
            ERR.append("%s: invalid JSON (%s)" % (j, e))
    hooks = os.path.join(ROOT, ".claude", "hooks")
    for f in os.listdir(hooks):
        p = os.path.join(hooks, f)
        if f.endswith(".py"):
            r = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True, text=True)
            if r.returncode != 0:
                ERR.append("%s: py_compile failed: %s" % (f, (r.stderr or r.stdout).strip()[:200]))
        if f.endswith(".js"):
            r = subprocess.run(["node", "--check", p], capture_output=True, text=True, shell=(os.name == "nt"))
            if r.returncode != 0:
                ERR.append("%s: node --check failed: %s" % (f, (r.stderr or r.stdout).strip()[:200]))
    for p in [".claude/skills/demo-creator/scripts", ".claude/skills/test-together/scripts", ".claude/skills/demo-creator/templates"]:
        d = os.path.join(ROOT, p)
        for f in os.listdir(d):
            if f.endswith(".js"):
                r = subprocess.run(["node", "--check", os.path.join(d, f)], capture_output=True, text=True, shell=(os.name == "nt"))
                if r.returncode != 0:
                    ERR.append("%s/%s: node --check failed" % (p, f))
    settings = json.loads(read(os.path.join(ROOT, ".claude", "settings.json")))
    for event, groups in settings.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                m = re.search(r"\$CLAUDE_PROJECT_DIR/([^\"']+)", h.get("command", ""))
                if m and not os.path.exists(os.path.join(ROOT, m.group(1))):
                    ERR.append("settings.json %s: hook file missing: %s" % (event, m.group(1)))
    cfg = json.loads(read(os.path.join(ROOT, ".claude", "hooks", "harness-config.json")))
    expected_globs = [".claude/PROJECT-PROFILE.md", ".claude/settings.json", ".claude/hooks/harness-config.json", ".mcp.json"]
    if sorted(cfg.get("allowed_write_globs", [])) != sorted(expected_globs):
        ERR.append("harness-config.json: allowed_write_globs is not the shipped default %s" % expected_globs)
    if cfg.get("protected_repos") or cfg.get("owned_repos"):
        ERR.append("harness-config.json: ships with repos configured; the template must ship empty lists")
    if (cfg.get("gate") or {}).get("enforce"):
        ERR.append("harness-config.json: gate.enforce must ship false")
    if cfg.get("memory_root"):
        ERR.append("harness-config.json: memory_root must ship empty")
    for k in ("_session_note",):
        if k in cfg:
            ERR.append("harness-config.json: stray key %s" % k)


def check_text_hygiene():
    gi = read(os.path.join(ROOT, ".gitignore")) if os.path.exists(os.path.join(ROOT, ".gitignore")) else ""
    for needed in (".mcp.json", "qa-evidence/", "node_modules/", "completion-gate.log", "*.new", "scripts/private-patterns.json"):
        if needed not in gi:
            ERR.append(".gitignore must contain %s" % needed)
    for p in files():
        if not is_text(p):
            continue
        r = rel(p)
        raw = open(p, "rb").read()
        if raw.startswith(b"\xef\xbb\xbf"):
            ERR.append("%s: UTF-8 BOM" % r)
        if b"\r\n" in raw:
            ERR.append("%s: CRLF line endings (template files are LF; see .gitattributes)" % r)
    r = subprocess.run(["git", "ls-files", "-s"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode == 0:
        for line in r.stdout.splitlines():
            mode, _, _, path = line.split(None, 3)
            if mode == "120000":
                ERR.append("tracked symlink: %s" % path)
            if "/node_modules/" in path or path.startswith("qa-evidence/") or path.endswith(".pyc"):
                ERR.append("tracked artifact: %s" % path)
            if path == "scripts/private-patterns.json":
                ERR.append("scripts/private-patterns.json is TRACKED; it must stay git-ignored")


def check_links():
    link_re = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(#[^)]*)?\)")
    for p in files():
        if not p.endswith(".md"):
            continue
        text = read(p)
        for target, _ in link_re.findall(text):
            if re.match(r"^[a-z]+:", target) or target.startswith("<"):
                continue
            if "<" in target or "{" in target:
                continue
            cand = os.path.normpath(os.path.join(os.path.dirname(p), target))
            if not os.path.exists(cand):
                WARN.append("%s: link target not found: %s" % (rel(p), target))


def _host_ok(host):
    h = host.lower().rstrip(".")
    for suf in GENERIC_HOST_SUFFIXES + KNOWN_TOOLING_HOSTS:
        if h == suf or h.endswith("." + suf):
            return True
    return False


def _email_ok(domain):
    d = domain.lower()
    return any(d == g or d.endswith("." + g) for g in GENERIC_EMAIL_DOMAINS)


def check_privacy():
    lits, pats = load_private()
    patterns = SHAPE_PATTERNS + [(p, "private pattern: " + why) for p, why in pats]
    for p in files():
        if not is_text(p):
            continue
        r = rel(p)
        text = read(p)
        low = text.lower()
        for pat, why in patterns:
            for m in re.finditer(pat, text):
                if why == "loopback tunnel port" and m.group(1) in GENERIC_LOOPBACK_PORTS:
                    continue
                line = text.count("\n", 0, m.start()) + 1
                ERR.append("%s:%d: %s: %r" % (r, line, why, m.group(0)[:40]))
        for m in EMAIL_RE.finditer(text):
            if not _email_ok(m.group(1)):
                ERR.append("%s:%d: e-mail outside the example domains: %r" % (r, text.count("\n", 0, m.start()) + 1, m.group(0)))
        for m in HOST_RE.finditer(text):
            if not _host_ok(m.group(1)):
                ERR.append("%s:%d: hostname outside the example/tooling domains: %r" % (r, text.count("\n", 0, m.start()) + 1, m.group(1)))
        for m in TICKET_RE.finditer(text):
            if m.group(1) not in GENERIC_TICKET_PREFIXES:
                ERR.append("%s:%d: ticket key outside the generic forms (APP-nnn / BUG-...): %r" % (r, text.count("\n", 0, m.start()) + 1, m.group(0)))
        # self-check against the maintainer's private list: its literals may appear NOWHERE in the repo text
        for lit in lits:
            i = low.find(lit.lower())
            if i >= 0:
                ERR.append("%s:%d: literal from scripts/private-patterns.json found in tracked text: %r" % (r, text.count("\n", 0, i) + 1, lit))
    if lits or pats:
        print("privacy: merged %d literal(s) and %d pattern(s) from scripts/private-patterns.json (git-ignored)" % (len(lits), len(pats)))
    else:
        print("privacy: shape-based rules only (scripts/private-patterns.json not present)")


def catalog_doc(catalog):
    lines = ["# Component catalog", "",
             "Generated from `catalog.json` by `python scripts/validate.py --fix-catalog-doc`. Do not edit by hand.", "",
             "## Skills", "", "| Skill | Group | Capability rule | What it does |", "|---|---|---|---|"]
    for name, meta in catalog["skills"].items():
        lines.append("| `%s` | %s | %s | %s |" % (name, meta["category"], meta["capability"], meta["summary"]))
    lines += ["", "## Agents", "", "| Agent (dispatch name) | File | Capability |", "|---|---|---|"]
    for name, meta in catalog["agents"].items():
        lines.append("| `%s` | `%s` | %s |" % (name, meta["file"], meta["capability"]))
    lines += ["", "## Groups", "", "| Group | Skills |", "|---|---|"]
    for g, members in catalog["groups"].items():
        lines.append("| `%s` | %s |" % (g, ", ".join("`%s`" % m for m in members)))
    lines += ["", "## Core files (installed with every project-level install)", ""]
    for f in catalog["core"]["files"]:
        lines.append("- `%s`" % f)
    lines += ["", "## Optional external components", ""]
    for name, meta in catalog["external_optional"].items():
        lines.append("- **%s** — %s%s" % (name, meta.get("kind", ""), ("; " + meta["notes"]) if meta.get("notes") else ""))
    return "\n".join(lines) + "\n"


def check_catalog_doc(catalog, fix):
    p = os.path.join(ROOT, "docs", "catalog.md")
    want = catalog_doc(catalog)
    have = read(p) if os.path.exists(p) else ""
    if fix:
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(want)
        print("wrote docs/catalog.md")
    elif have != want:
        ERR.append("docs/catalog.md is out of date: run python scripts/validate.py --fix-catalog-doc")


def check_installed():
    """Light checks for a project that has the harness installed."""
    for f in [".claude/CLAUDE.md", ".claude/PROJECT-PROFILE.md", ".claude/settings.json", ".claude/hooks/harness-config.json",
              ".claude/skills/qa-standards/SKILL.md"]:
        if not os.path.exists(os.path.join(ROOT, f)):
            ERR.append("missing: %s" % f)
    mcp = os.path.join(ROOT, ".mcp.json")
    if os.path.exists(mcp):
        t = read(mcp)
        if "${PROJECT_ROOT}" in t:
            ERR.append(".mcp.json still contains ${PROJECT_ROOT}; run /configure-project")
        try:
            json.loads(t)
        except Exception as e:
            ERR.append(".mcp.json invalid JSON: %s" % e)
    else:
        WARN.append(".mcp.json not generated yet (run /configure-project)")
    hooks = os.path.join(ROOT, ".claude", "hooks")
    for f in os.listdir(hooks):
        if f.endswith(".py"):
            r = subprocess.run([sys.executable, "-m", "py_compile", os.path.join(hooks, f)], capture_output=True, text=True)
            if r.returncode != 0:
                ERR.append("%s: py_compile failed" % f)
    prof = read(os.path.join(ROOT, ".claude", "PROJECT-PROFILE.md")) if os.path.exists(os.path.join(ROOT, ".claude", "PROJECT-PROFILE.md")) else ""
    caps = dict(re.findall(r"^- ([A-Za-z-]+): (on|off)", prof, re.M))
    if not caps:
        WARN.append("PROJECT-PROFILE.md §2 has no capability lines yet")
    else:
        print("capabilities:", ", ".join("%s=%s" % kv for kv in caps.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--installed", action="store_true")
    ap.add_argument("--fix-catalog-doc", action="store_true")
    args = ap.parse_args()
    if args.installed:
        check_installed()
    else:
        catalog = json.loads(read(os.path.join(ROOT, "catalog.json")))
        check_skills(catalog)
        check_json_and_hooks()
        check_text_hygiene()
        check_links()
        check_privacy()
        check_catalog_doc(catalog, args.fix_catalog_doc)
    for w in WARN:
        print("WARN ", w)
    for e in ERR:
        print("ERROR", e)
    print("%d error(s), %d warning(s)" % (len(ERR), len(WARN)))
    sys.exit(1 if ERR else 0)


if __name__ == "__main__":
    main()
