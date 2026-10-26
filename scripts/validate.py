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
  * conventions: description length / no workflow words (warn), an ARGUMENTS + STOP block for every skill
    that takes arguments, a complete Post-Session memory block, known tool names only, skill size
    (warn > 16 KB, error > 24 KB), one confidence-line template and one result vocabulary everywhere
  * versions and counts: catalog.json version == newest CHANGELOG heading; README / catalog counts == reality
  * guards: every Python hook in settings.json runs through run-hook.sh; the launcher fails closed
    (scripts/hook-redteam launcher tests); deny list keeps Read(.mcp.json)
  * MCP template: no @latest, no Windows-only `cmd /c` wrapper (render_mcp.py adds it on Windows)
  * run records: verdict_check.py accepts the consistent fixture and rejects the tampered one
  * capability matrix lists every skill exactly once; every evals/evals.json parses
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
                       "nodejs.org", "python.org", "playwright.dev",
                       "opencode.ai", "kilo.ai")   # referenced by docs/config on purpose (opencode.ai / app.kilo.ai: config schemas)
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
    for p in [".claude/skills/demo-creator/scripts", ".claude/skills/test-together/scripts", ".claude/skills/demo-creator/templates",
              ".claude/skills/perf-test/scripts"]:
        d = os.path.join(ROOT, p)
        if not os.path.isdir(d):
            ERR.append("missing folder: %s" % p)
            continue
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
             "## Skills", "", "| Skill | Group | Capability rule | Profile sections read | What it does |", "|---|---|---|---|---|"]
    for name, meta in catalog["skills"].items():
        lines.append("| `%s` | %s | %s | %s | %s |" % (name, meta["category"], meta["capability"], profile_sections(name), meta["summary"]))
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


# ---------------------------------------------------------------------------------------------------
# Conventions, versions, guards, run records (2.1)
# ---------------------------------------------------------------------------------------------------
KNOWN_TOOLS = {"Bash", "PowerShell", "Read", "Write", "Edit", "MultiEdit", "Grep", "Glob", "Agent", "WebFetch",
               "WebSearch", "AskUserQuestion", "SendUserFile", "NotebookEdit", "TodoWrite", "Skill"}
WORKFLOW_WORDS = re.compile(r"\b(then|runs|produces|synthesi[sz]es|phase \d|step \d)\b", re.I)
NO_ARGS_BY_DESIGN = {"env-health": "health check of the whole environment", "sync-repos": "syncs every repo when no name is given",
                     "configure-project": "the bootstrap interviews the user itself"}
NO_MEMORY_RITUAL = {"configure-project": "writes the profile and config, not QA memory",
                    "automation-writer": "code-generation utility, no QA verdict",
                    "qa-standards": "defines the ritual itself",
                    "qa-verdict-auditor": "a judge in a fresh context; the orchestrator records its result",
                    "evidence-manager": "a helper other skills call; the calling skill records memory"}
CANON_RESULTS = ("PASS", "FAIL", "BLOCKED", "NOT APPLICABLE", "NOT YET VERIFIED")
CONF_TEMPLATE = "Verified N of M in-scope areas; BLOCKED k; NOT YET VERIFIED j; Remaining Risk:"
SIZE_WARN, SIZE_ERR = 16 * 1024, 24 * 1024


def _skill_files():
    d = os.path.join(ROOT, ".claude", "skills")
    for s in sorted(os.listdir(d)):
        p = os.path.join(d, s, "SKILL.md")
        if os.path.isfile(p):
            yield s, p


def _agent_files():
    d = os.path.join(ROOT, ".claude", "agents")
    for f in sorted(os.listdir(d)):
        if f.endswith(".md"):
            yield f[:-3], os.path.join(d, f)


def _post_session(text):
    m = re.search(r"^##+ [^\n]*(Post-Session|Memory Ritual)[^\n]*\n(.*?)(?=^##? [^#]|\Z)", text, re.M | re.S)
    return m.group(2) if m else None


def check_conventions():
    for s, p in _skill_files():
        text = read(p)
        fm = frontmatter(text) or {}
        d = fm.get("description", "")
        if len(d) > 500:
            WARN.append("%s: description is %d chars (> 500); state triggers only, move workflow into the body" % (s, len(d)))
        if WORKFLOW_WORDS.search(d):
            WARN.append("%s: description narrates workflow (%r); descriptions state WHEN to use, not HOW" % (s, WORKFLOW_WORDS.search(d).group(0)))
        size = len(text.encode("utf-8"))
        if size > SIZE_ERR:
            ERR.append("%s: SKILL.md is %d bytes (> %d); move reference material into references/" % (s, size, SIZE_ERR))
        elif size > SIZE_WARN:
            WARN.append("%s: SKILL.md is %d bytes (> %d)" % (s, size, SIZE_WARN))
        if fm.get("argument-hint") and s not in NO_ARGS_BY_DESIGN:
            if "## ARGUMENTS" not in text:
                ERR.append("%s: takes arguments but has no '## ARGUMENTS' block" % s)
            elif not re.search(r"(?is)if no arguments.{0,400}\bSTOP\b", text):
                ERR.append("%s: no 'If no arguments provided ... STOP' sentence (an agent would guess the scope)" % s)
        for tok in re.findall(r'"([^"]+)"', (re.search(r"^allowed-tools:(.*)$", text, re.M) or [None, ""])[1] if re.search(r"^allowed-tools:", text, re.M) else ""):
            if tok.startswith("mcp__") or re.match(r"^(Skill|Agent|Bash|Read|Write|Edit)\(", tok):
                continue
            if tok not in KNOWN_TOOLS:
                ERR.append("%s: allowed-tools names unknown tool %r" % (s, tok))
    for name, p in list(_skill_files()) + list(_agent_files()):
        if name in NO_MEMORY_RITUAL:
            continue
        body = _post_session(read(p))
        if body is None:
            ERR.append("%s: no Post-Session (memory) block - memory updates are mandatory (CLAUDE.md)" % name)
            continue
        for need, why in (("<memory folder: PROJECT-PROFILE.md §12>", "memory-folder placeholder"),
                          ("ls -la", "verify line"), ("SUPERSEDED", "mark disproved facts SUPERSEDED")):
            if need not in body:
                ERR.append("%s: Post-Session block lacks the %s (%r)" % (name, why, need))
    for p in files():
        if not p.endswith(".md"):
            continue
        r = rel(p)
        if r.startswith("docs/maintainers/"):
            continue
        text = read(p)
        for m in re.finditer(r"Verified N of M[^`\n|]*", text):
            if not m.group(0).startswith(CONF_TEMPLATE):
                ERR.append("%s:%d: confidence line drifts from the Verdict Contract template: %r"
                           % (r, text.count("\n", 0, m.start()) + 1, m.group(0)[:70]))
        for m in re.finditer(r"\bPASS\s*/\s*FAIL\s*/\s*BLOCKED(?:\s*/\s*[A-Z][A-Z ]*[A-Z])*", text):
            line_txt = text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.end())]
            if all(c in line_txt for c in CANON_RESULTS):
                continue        # a mapping row that translates a foreign word INTO the five canonical values
            toks = [t.strip() for t in m.group(0).split("/")]
            bad = [t for t in toks if t not in CANON_RESULTS]
            if bad:
                ERR.append("%s:%d: result list uses non-canonical word(s) %s" % (r, text.count("\n", 0, m.start()) + 1, bad))


def check_versions_and_counts(catalog):
    ch = read(os.path.join(ROOT, "CHANGELOG.md"))
    m = re.search(r"^## (\d+\.\d+\.\d+)", ch, re.M)
    if not m:
        ERR.append("CHANGELOG.md: no '## x.y.z' heading")
    elif m.group(1) != catalog.get("version"):
        ERR.append("catalog.json version %s != newest CHANGELOG heading %s" % (catalog.get("version"), m.group(1)))
    n_sk, n_ag = len(catalog["skills"]), len(catalog["agents"])
    n_hooks = len([f for f in os.listdir(os.path.join(ROOT, ".claude", "hooks"))
                   if f.endswith((".py", ".js", ".sh")) and f not in ("harness_config.py", "run-hook.sh")])
    n_rules = len([f for f in os.listdir(os.path.join(ROOT, ".claude", "rules")) if f.endswith(".md")])
    for f in ("README.md", "catalog.json", "AGENTS.md", "SETUP.md"):
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            continue
        t = read(p)
        for num, what in re.findall(r"\b(\d+) (skills|sub-agents|agents|hooks|rules)\b", t):
            want = {"skills": n_sk, "sub-agents": n_ag, "agents": n_ag, "hooks": n_hooks, "rules": n_rules}[what]
            if int(num) != want:
                ERR.append("%s says %s %s; the template ships %d" % (f, num, what, want))


def check_guards_and_mcp():
    settings = json.loads(read(os.path.join(ROOT, ".claude", "settings.json")))
    for event, groups in settings.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                if re.search(r"\.py\b", cmd) and "run-hook.sh" not in cmd:
                    ERR.append("settings.json %s: %r runs a Python hook without run-hook.sh (a missing interpreter "
                               "would silently disable it)" % (event, cmd[:70]))
                m = re.search(r"run-hook\.sh[\"']?\s+([A-Za-z0-9_.-]+\.py)", cmd)
                if m and not os.path.exists(os.path.join(ROOT, ".claude", "hooks", m.group(1))):
                    ERR.append("settings.json %s: hook script missing: %s" % (event, m.group(1)))
    if "Read(.mcp.json)" not in settings.get("permissions", {}).get("deny", []):
        ERR.append("settings.json: deny list must keep Read(.mcp.json) (secrets may live there)")
    t = read(os.path.join(ROOT, ".mcp.json.template"))
    if "@latest" in t:
        ERR.append(".mcp.json.template: '@latest' makes installs drift; pin the tested version")
    tpl = json.loads(t)
    for name, srv in (tpl.get("mcpServers") or {}).items():
        if srv.get("command") == "cmd":
            ERR.append(".mcp.json.template: %s uses the Windows-only 'cmd /c' wrapper; .claude/scripts/render_mcp.py adds it on Windows" % name)
    runner = os.path.join(ROOT, "scripts", "hook-redteam", "runner.py")
    if os.path.exists(runner):
        import importlib.util
        spec = importlib.util.spec_from_file_location("hook_runner", runner)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fails = mod.launcher_tests(os.path.join(ROOT, ".claude", "hooks"))
        if "SKIPPED" in buf.getvalue():
            WARN.append("launcher self-test skipped: no POSIX sh found")
        for cid, why in fails:
            ERR.append("run-hook.sh launcher test %s failed: %s" % (cid, why))


def check_run_records_and_evals():
    vc = os.path.join(ROOT, ".claude", "skills", "qa-standards", "scripts", "verdict_check.py")
    fx = os.path.join(ROOT, ".claude", "skills", "qa-standards", "scripts", "fixtures")
    if not os.path.exists(vc):
        ERR.append("missing: .claude/skills/qa-standards/scripts/verdict_check.py")
    else:
        for name, want in (("consistent-run", 0), ("tampered-run", 1)):
            r = subprocess.run([sys.executable, vc, os.path.join(fx, name)], capture_output=True, text=True)
            if r.returncode != want:
                ERR.append("verdict_check.py on fixtures/%s exited %s, expected %s" % (name, r.returncode, want))
    for dirpath, _, filenames in os.walk(os.path.join(ROOT, ".claude", "skills")):
        for f in filenames:
            if f == "evals.json":
                p = os.path.join(dirpath, f)
                try:
                    data = json.loads(read(p))
                    if not data.get("evals"):
                        ERR.append("%s: no evals" % rel(p))
                except Exception as e:
                    ERR.append("%s: invalid JSON (%s)" % (rel(p), e))
    for f in ("references/run-record.md",):
        pass
    for py in (".claude/scripts/doctor.py", ".claude/scripts/rebind.py", ".claude/scripts/render_mcp.py",
               ".claude/skills/qa-standards/scripts/verdict_check.py"):
        r = subprocess.run([sys.executable, "-m", "py_compile", os.path.join(ROOT, py)], capture_output=True, text=True)
        if r.returncode != 0:
            ERR.append("%s: py_compile failed" % py)
    for f in ("references/run-record.md",):
        if not os.path.exists(os.path.join(ROOT, ".claude", "skills", "qa-standards", f)):
            ERR.append("missing: qa-standards/%s" % f)


def check_docs_consistency(catalog):
    p = os.path.join(ROOT, "docs", "capability-matrix.md")
    t = read(p) if os.path.exists(p) else ""
    for s in catalog["skills"]:
        n = len(re.findall(r"^\|\s*`%s`\s*\|" % re.escape(s), t, re.M))
        if n != 1:
            ERR.append("docs/capability-matrix.md lists `%s` %d times (must be exactly once)" % (s, n))


def profile_sections(skill):
    t = read(os.path.join(ROOT, ".claude", "skills", skill, "SKILL.md"))
    secs = sorted({int(x) for x in re.findall(r"§(\d+)", t)})
    return ", ".join("§%d" % x for x in secs) or "-"


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
    doctor = os.path.join(ROOT, ".claude", "scripts", "doctor.py")
    if os.path.exists(doctor):
        r = subprocess.run([sys.executable, doctor, "--json"], capture_output=True, text=True,
                           env=dict(os.environ, CLAUDE_PROJECT_DIR=ROOT))
        try:
            for c in json.loads(r.stdout).get("checks", []):
                if c["status"] == "FAIL":
                    ERR.append("doctor: %s - %s" % (c["check"], c["detail"]))
        except Exception:
            ERR.append("doctor.py did not return its JSON report (exit %s)" % r.returncode)
    else:
        WARN.append(".claude/scripts/doctor.py missing - guards cannot be self-tested")
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
        check_conventions()
        check_versions_and_counts(catalog)
        check_guards_and_mcp()
        check_run_records_and_evals()
        check_docs_consistency(catalog)
        check_catalog_doc(catalog, args.fix_catalog_doc)
    for w in WARN:
        print("WARN ", w)
    for e in ERR:
        print("ERROR", e)
    print("%d error(s), %d warning(s)" % (len(ERR), len(WARN)))
    sys.exit(1 if ERR else 0)


if __name__ == "__main__":
    main()
