#!/usr/bin/env python
"""
Completion Gate hook (Stop / SubagentStop) - portable.

MODE: advisory by default. It NEVER blocks unless enforcement is switched on, either with the
environment variable QA_GATE_ENFORCE=1 (settings.json -> env) or with
harness-config.json -> "gate": {"enforce": true}.

Rationale: a Stop hook that blocks wrongly makes every turn feel stuck, and Claude Code overrides it
after 8 consecutive blocks anyway. Earn the enforcement first, then switch it on.

Why this exists: written rules did not prevent three classic verdict mistakes made in one run -
a false BLOCKED ("no fixture" when many fixtures existed), an authoritative source cited from memory
without being read, and a stale ticket status propagated into a recommendation. This hook is the
mechanical backstop for the Verdict Contract / Completion Gate sections of qa-standards.

Check 14 recomputes the run: when the verdict names a run folder (qa-evidence/<run-folder>) that holds a
run.json, the folder is checked with qa-standards/scripts/verdict_check.py - a stated GO that the rows
contradict, an evidence id with no file, or a confidence line that does not add up is reported here.

Checks 15-22 hold a run report to the run skills' own contract (qa-standards -> Verdict Contract):
  15  a NOT YET VERIFIED row names a structural blocker that was tried, not an operational one ("not run");
  16  the turn does not ask whether to run the skill's own steps or the cases still open;
  17  "expected" does not rest on a code comment unless the ticket / AC was quoted or declared silent;
  18  an audited run verdict carries a complete 'Case completeness:' line (full-qa Phase 8a);
  19  ... and a 'Skills loaded:' line whose check marks match the Skill calls in the session transcript;
  20  ... and a 'Core-page sweep: <route>' row with a result for every route of PROJECT-PROFILE.md section 8
      (skipped when the profile says 'Browser: off'; with no route list, at least one sweep row);
  21  a full / regression / bugfix / release run report has 'Regression: <area>' rows that ran;
  22  every run report opens with the Run line 'Run: <skill> | QA mode: <mode> | Audit: AUDIT_PASSED'.
Checks 18-21 fire on an audited run verdict (the Run line says AUDIT_PASSED, or AUDIT_PASSED and a run verdict
stand in plain text); check 22 makes every run report carry the Run line, so leaving AUDIT_PASSED out does not
skip them. An n/a sweep or regression row counts only when it cites the owner's decision or a capability that is
off. The transcript (Stop hook input 'transcript_path') is read only for check 19; unreadable = skipped.

It is deliberately conservative: it only speaks when the turn LOOKS like a QA verdict. Ordinary
conversation is never touched. Lines that QUOTE or EXPLAIN a verdict (code blocks, inline code,
blockquotes, lines tagged "example") are stripped before the checks run.

Configuration (harness-config.json, all optional):
  "gate": {
    "enforce": false,
    "ticket_id_pattern": "\\b[A-Z][A-Z0-9]+-\\d+\\b",
    "extra_concession_phrases": [],
    "extra_example_markers": [],
    "log": true
  }
"""
import io
import json
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "completion-gate.log")


def _load_gate_cfg():
    cfg = {}
    try:
        with io.open(os.path.join(HERE, "harness-config.json"), "r", encoding="utf-8") as fh:
            cfg = json.load(fh).get("gate", {}) or {}
    except Exception:
        cfg = {}
    return {
        "enforce": bool(cfg.get("enforce", False)),
        "ticket_id_pattern": cfg.get("ticket_id_pattern") or r"\b[A-Z][A-Z0-9]+-\d+\b",
        "extra_concession_phrases": [p for p in (cfg.get("extra_concession_phrases") or []) if p],
        "extra_example_markers": [p for p in (cfg.get("extra_example_markers") or []) if p],
        "log": bool(cfg.get("log", True)),
    }


GATE = _load_gate_cfg()
ENFORCE = os.environ.get("QA_GATE_ENFORCE") == "1" or GATE["enforce"]
TICKET_RE = re.compile(GATE["ticket_id_pattern"])

CONCESSION_PHRASES = [r"you are right", r"you.re right", r"i was wrong", r"my mistake",
                      r"i stand corrected"] + [re.escape(p) for p in GATE["extra_concession_phrases"]]
CONCESSION_RE = "|".join(CONCESSION_PHRASES)

# Only engage when the turn actually states a QA verdict (or concedes a point).
VERDICT = re.compile(
    r"(\bGO\b\s*[-\u2014:]|\bNO-GO\b|\bPARTIAL\b|\bAUDIT_(PASSED|FAILED)|\bVerdict\s*:|"
    r"\bCONFIRMED BUG\b|\bNOT A BUG\b|\bCANNOT CONFIRM\b|\bResult\s*:\s*(PASS|FAIL)\b|"
    r"\*\*(PASS|FAIL)\*\*)|" + CONCESSION_RE, re.I)


def strip_quoted(text):
    """Remove text that QUOTES or EXPLAINS a verdict rather than STATING one.

    A turn that discusses verdicts is not a turn that issues one. Stripped, in order:
      - fenced code blocks   ``` ... ```   (test output, fixtures, samples)
      - inline code spans    `GO`          (naming the token, not asserting it)
      - blockquote lines     > "Verdict: GO"
      - explicit example lines (example / e.g. / for instance / would warn / would fire /
        test case / plus any configured extra markers)
    Evidence Ledger and Execution Register TABLES are deliberately NOT stripped -
    a real report needs them and they must still be seen.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    extra = "".join("|(" + re.escape(m) + ")" for m in GATE["extra_example_markers"])
    marker = re.compile(
        r"(^\s*>)|(\bexample\b)|(\be\.g\.)|(\bfor instance\b)|(\bwould (warn|fire|flag|block)\b)"
        r"|(\btest case\b)|(\bexpected=)|(\bblocked=)|(\bwarned=)" + extra, re.I)
    kept = []
    for line in text.splitlines():
        if marker.search(line):
            continue
        kept.append(line)
    return "\n".join(kept)


# The Run line: every run report opens with one plain line
#     Run: <skill> | QA mode: <mode> | Audit: AUDIT_PASSED
# so the gate reads the skill, the mode and the audit result from the report itself, never from the session.
RUN_LINE = re.compile(r"^\W*run\W*:\W*([a-z][a-z:-]*)\W*[|\u00b7]\W*qa mode\W*:\W*([a-z]+)\W*[|\u00b7]\W*audit\W*:\W*"
                      r"(AUDIT_PASSED|AUDIT_FAILED)\b", re.I | re.M)
RUN_SKILLS = ("full-qa", "qa-validate", "release-check", "regression-runner", "bug-verifier", "qa-team")
QA_MODES = ("smoke", "targeted", "regression", "bugfix", "full", "release")
# An n/a sweep or regression row counts only when it cites who decided it, or a capability that is off.
DECIDED = re.compile(r"\b(?:owner|user|product owner)(?:'s)?\s+(?:decision|ruling|approval|approved|scoped|said|ok)\b"
                     r"|\bcapability\s+(?:is\s+)?off\b|\b(?:browser|db|api|admin|reporting)\s*[:=]\s*off\b"
                     r"|PROJECT-PROFILE(?:\.md)?\s*\u00a7\s*(?:2|16)\b", re.I)
PROFILE = os.path.join(HERE, "..", "PROJECT-PROFILE.md")
_PROFILE = {}


def run_line(text):
    """(skill, mode, audit) from the Run line, or None. Read from the stripped text: a Run line in backticks is not one."""
    m = RUN_LINE.search(text)
    return (m.group(1).lower(), m.group(2).lower(), m.group(3).upper()) if m else None


def row_result(ln):
    """The canonical result a table row carries (qa-standards -> Verdict Contract), or None."""
    up = ln.upper()
    for value in ("NOT YET VERIFIED", "NOT APPLICABLE"):
        if value in up:
            return value
    m = re.search(r"\b(PASS|FAIL|BLOCKED)\b", up)
    return m.group(1) if m else None


def _profile_text():
    if "t" not in _PROFILE:
        try:
            with io.open(PROFILE, "r", encoding="utf-8") as fh:
                _PROFILE["t"] = fh.read()
        except Exception:
            _PROFILE["t"] = ""
    return _PROFILE["t"]


def browser_off():
    """True when PROJECT-PROFILE.md section 2 says 'Browser: off': there is no browser to sweep with."""
    return bool(re.search(r"^\s*-\s*Browser\s*:\s*off\b", _profile_text(), re.I | re.M))


def sweep_routes():
    """The core-page routes from PROJECT-PROFILE.md section 8 'Core pages per role', the single source of the page
    list: the sub-bullets under that line (until the next '## ' heading or top-level '- **' bullet), each route in
    backticks. Empty when the profile has no such list: check 20 then asks for at least one sweep row (never guessed)."""
    routes, inside = [], False
    for ln in _profile_text().splitlines():
        if not inside:
            if re.search(r"core pages per role", ln, re.I):
                inside = True
                routes += re.findall(r"`(/[^`\s]*)`", ln)
            continue
        if ln.startswith("## ") or ln.startswith("- **"):
            break
        if ln.strip().startswith("- "):
            routes += re.findall(r"`(/[^`\s]*)`", ln)
    unique = []
    for r in routes:
        if r not in unique:
            unique.append(r)
    return unique


CANON = ("PASS", "FAIL", "BLOCKED", "NOT APPLICABLE", "NOT YET VERIFIED")


def _has_register_rows(text):
    """True only if an Execution Register exists AND carries real rows.

    A bare heading with no rows must not pass: a register that cannot be parsed carries the same
    risk as no register at all.
    """
    if "execution register" not in text.lower():
        return False
    rows = 0
    for ln in text.splitlines():
        s = ln.strip()
        if not s.startswith("|") or s.count("|") < 4:
            continue
        up = s.upper()
        if any(v in up for v in CANON):
            rows += 1
    return rows > 0


def _totals_sane(text):
    """Verified N of M must satisfy 0 < N <= M."""
    m = re.search(r"verified\s+(\d+)\s+of\s+(\d+)", text, re.I)
    if not m:
        return True
    n, tot = int(m.group(1)), int(m.group(2))
    return 0 < n <= tot


def loaded_skills(path):
    """Skill names this session really loaded: Skill tool calls and /slash invocations in the transcript.
    None when the transcript cannot be read - the cross-check is then skipped, never guessed."""
    if not path or not os.path.isfile(path):
        return None
    names = set()
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"Skill"' not in line and "<command-name>" not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                msg = o.get("message") or {}
                content = msg.get("content") if isinstance(msg, dict) else None
                if o.get("type") == "assistant" and isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                            s = str((c.get("input") or {}).get("skill") or "").strip()
                            if s:
                                names.add(s)
                                names.add(s.split(":")[-1])
                elif o.get("type") == "user":
                    if isinstance(content, str):
                        body = content
                    elif isinstance(content, list):
                        body = " ".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
                    else:
                        body = ""
                    for m in re.findall(r"<command-name>/?([^<]+)</command-name>", body):
                        names.add(m.strip())
                        names.add(m.strip().split(":")[-1])
    except Exception:
        return None
    return names


_SEEN = {}


def loaded_skills_cached(path):
    """loaded_skills() read once per gate run."""
    if path not in _SEEN:
        _SEEN[path] = loaded_skills(path)
    return _SEEN[path]


def checks(text, raw=None, transcript=None):
    """Return a list of gate warnings. Each is a concrete, actionable sentence.

    text = the message with quoted / example lines stripped; raw = the unstripped message (table rows may name a
    sweep in backticks); transcript = the session transcript path (check 19)."""
    out = []
    low = text.lower()

    # 1. A verdict with no evidence anywhere.
    if not re.search(r"evidence|ledger|\bE\d\b", text, re.I):
        out.append("Verdict stated with no Evidence Ledger reference. "
                   "qa-standards: no evidence = no finding.")

    # 2. BLOCKED without saying what would unblock it -> the false-blocker anti-pattern.
    if re.search(r"\bBLOCKED\b(?!\s*:?\s*0\b)", text):
        if not re.search(r"unblock|would resolve|would settle|what would|not applicable|cannot be started|"
                         r"no local path|requires .* access|structural", low):
            out.append("A BLOCKED disposition appears without what would unblock it. "
                       "Operational != structural: is this a setup step you skipped? "
                       "(A missing fixture is a setup step, not a structural blocker.)")

    # 3. Ticket state asserted -> was it re-read live this run?
    if TICKET_RE.search(text) and re.search(
            r"ready for release|verified|to do|in testing|reopen|transition|closed|resolved", low):
        if not re.search(r"getjiraissue|issue_read|read live|re-read live|checked directly|fresh read", low):
            out.append("A ticket state is asserted. Fresh-vs-Historical is bidirectional: a REMEMBERED "
                       "ticket status is not evidence a ticket is still open. Re-read it live from the tracker.")

    # 4. Coverage gaps must be named, never implied.
    if re.search(r"(?<!NO-)\bGO\b", text) and not re.search(r"gap|not applicable|n/?a\b|out of scope", low):
        out.append("GO stated without naming coverage gaps. An untested dimension is never an implied PASS.")

    # 5. bug-verifier: CANNOT CONFIRM is the false-blocker pattern in disguise.
    if re.search(r"cannot confirm", low):
        if not re.search(r"escalat|next step|would confirm|would settle|retry|flaky|repeat|more data", low):
            out.append("CANNOT CONFIRM stated with no escalation path. Same anti-pattern as a "
                       "false BLOCKED: say what WOULD confirm it, or that it is genuinely "
                       "unreproducible.")

    # 6. Dismissing a bug needs a source, exactly like asserting one does.
    if re.search(r"not a bug|expected behaviou?r|as designed|by[- ]design|working as intended|known behaviou?r", low):
        if not re.search(r"acceptance criteri|\bac\b|spec|ticket|column_comment|code comment|:\d+|ruling|documented", low):
            out.append("A bug is dismissed as expected behaviour with no source quoted. "
                       "Verdict Integrity #2 cuts both ways: quote the AC / spec / code "
                       "contract that defines this as correct, or withdraw the dismissal.")

    # 7. A run verdict (GO / NO-GO / PARTIAL) with no Execution Register -> silent areas.
    if re.search(r"\b(GO|NO-GO|PARTIAL)\b", text) and not _has_register_rows(text):
        out.append("Run verdict stated without an Execution Register. Every in-scope area needs a row "
                   "(PASS/FAIL/BLOCKED/NOT APPLICABLE/NOT YET VERIFIED) - qa-standards: Verdict Contract.")
    # 8. Run verdict without the mandatory confidence line.
    if re.search(r"\b(GO|NO-GO|PARTIAL)\b", text) and not re.search(r"verified \d+ of \d+", low):
        out.append("Run verdict stated without the confidence line 'Verified N of M in-scope areas; "
                   "BLOCKED k; NOT YET VERIFIED j' - qa-standards: Verdict Contract.")

    # 9. Impossible confidence arithmetic.
    if not _totals_sane(text):
        out.append("The confidence line does not add up (Verified N of M requires 0 < N <= M). "
                   "Recount the Execution Register rows.")

    # 10. An anomaly may only end as a TICKET or as expected WITH A SOURCE (anomaly-disposition Rule 1).
    if re.search(r"by[- ]design|workaround adopted|deploy .{0,40}individually|unresolved (w\/?o|without)|"
                 r"first[- ]ever|route around|known behaviou?r", low):
        if not TICKET_RE.search(text) and not re.search(r"\bBUG-\d+", text) and not re.search(
                r"schema|scalar fk|acceptance criteri|\bac\b|spec\b|code comment|ruling|documented|decision", low):
            out.append("Dissolved-anomaly language (by design / workaround / unresolved / first-ever / known "
                       "behaviour) with no ticket id and no cited source. anomaly-disposition.md Rule 1: an "
                       "anomaly ends as a TICKET or as expected WITH A CITED SOURCE - nothing else.")

    # 11. A PASS proven only by a success toast is validation-green, not feature-green (Rule 5).
    if re.search(r"\bPASS\b", text) and re.search(r"toast|saved successfully|success message|success flash", low):
        if not re.search(r"network|request|\bpost\b|read-?back|db row|database|select |persist", low):
            out.append("A PASS cites a success toast/message with no network log or DB read-back. "
                       "anomaly-disposition.md Rule 5: validation green is not feature green - prove the WRITE path.")

    # 12. A fix reported verified without checking it touched the root-cause location.
    if re.search(r"fix (is|was) (verified|confirmed|deployed|live|working)|verified fixed", low) and TICKET_RE.search(text):
        if not re.search(r"root[- ]cause|touch(ed|es)|name-only|:\d+", low):
            out.append("A fix is reported verified without stating whether it touched the ROOT-CAUSE file:line named in "
                       "the ticket. A symptom fix leaves the root cause live.")

    # 13. Folding under pushback without a NEW fact is forbidden - rules/pushback-protocol.md.
    if re.search(CONCESSION_RE, low):
        if not re.search(r"re-?checked|re-?ran|re-?read|verified|here is the proof|the new fact|\bE\d+\b|:\d+|"
                         r"select |query|git |screenshot|network", low):
            out.append("A concession (you are right / I was wrong) with no new evidence beside it. "
                       "pushback-protocol.md: re-run the check and quote the fact that changed your answer, or hold the position.")

    # 14. The run record must agree with itself (references/run-record.md).
    out.extend(run_record_warnings(text))

    # 15. NOT YET VERIFIED is not a parking place: the row names a STRUCTURAL blocker that was tried.
    #     (illustrative: a run parked a dozen rows as "not run" / "needs a DB without the table" / "no server shell";
    #     every one of them ran the same day on a local harness, with timings, or with test doubles.)
    nyv_rows = [ln for ln in text.splitlines()
                if ln.strip().startswith("|") and "NOT YET VERIFIED" in ln.upper()]
    structural = re.compile(r"refused|denied|permission|classifier|owner (decision|ruling|approval|must)|needs the owner"
                            r"|cannot be started|no local path|requires .{0,40}access|structural|unblock|waiting for"
                            r"|not deployed|undeployed|out of scope|capability (is )?off|:\s*off\b", re.I)
    weak_rows = [ln for ln in nyv_rows if not structural.search(ln)]
    nyv_count = re.search(r"not yet verified\s+(\d+)", low)
    if weak_rows or (nyv_count and int(nyv_count.group(1)) > 0 and not nyv_rows):
        out.append("NOT YET VERIFIED without a structural blocker that was attempted ('not run', 'needs a DB without "
                   "the table', 'no shell', 'no timings' are operational, not structural). Run the case: live -> local "
                   "harness / container copy -> the real component with test doubles -> code read; or name the "
                   "blocker, what you tried and what would unblock it (rules/testing.md).")

    # 16. A QA run goes end to end: it never asks whether to run its own steps or the cases still open.
    if re.search(r"(should i|shall i|do you want me to|want me to)\s+(run|execute|do|continue|start|finish)\b", low) and \
            re.search(r"step 1b|phase \d|test-cases-generator|open (checks|cases|rows)|not yet verified|remaining (checks|cases)"
                      r"|the \d+ (checks|cases|rows)", low):
        out.append("The turn asks whether to run the skill's own steps or the cases still open. A QA run goes end to "
                   "end (rules/testing.md): run them now; ask only for decisions that are the owner's (filing, a "
                   "permission the harness refuses, a product ruling).")

    # 17. A code comment cannot overrule the ticket (anomaly-disposition.md Rule 1: the ticket comes first).
    #     (illustrative: a row was closed as "expected (code comment)" while the story's AC said the opposite.)
    if re.search(r"(=\s*|\bis\s+|\bmarked\s+|\bclosed as\s+|\bdisposition:?\s*)(expected|by[- ]design|as designed"
                 r"|intended|working as intended|not a bug)\b", low) and \
            re.search(r"code comment|comment in the code|the code says", low):
        if not re.search(r"\b(ticket|story|epic|ac|acceptance criteria)\s+(says|said|line|text|reads|quote)"
                         r"|\b(ticket|story|epic|ac)( and (the )?(ticket|story|epic|ac))?\s+(is|are)\s+silent"
                         r"|\bsilent on (it|this)", low):
            out.append("An anomaly is closed as expected on a code comment. A code comment cannot overrule the "
                       "ticket: quote the ticket / AC line that covers this behaviour, or say that they are silent "
                       "on it (anomaly-disposition.md Rule 1).")

    # 18-21 share one trigger: the Run line says AUDIT_PASSED, or (older reports) AUDIT_PASSED and a run verdict
    # stand in plain text. Check 22 makes every run report carry the Run line.
    run = run_line(text)
    run_skill = run[0] if run else None
    audit_run = bool((run and run[2] == "AUDIT_PASSED") or
                     (re.search(r"\bAUDIT_PASSED\b", text) and re.search(r"\b(GO|NO-GO|PARTIAL)\b", text)))
    src = raw if raw is not None else text

    # 18. Running every written case finds nothing in a case that was never written (escape class E15). An audit
    #     that passes a run verdict carries the case-completeness line (full-qa Phase 8a), every count full.
    if audit_run:
        line = re.search(r"case[- ]completeness[^\n]*", src, re.I)
        if not line:
            out.append("AUDIT_PASSED without the case-completeness line ('Case completeness: AC sentences a/A - roles x "
                       "actions b/B - branches c/C - Step 1c classes d/D - UI controls e/E - silent-story questions q', "
                       "full-qa Phase 8a), or 'Case completeness: n/a (<why>)' for a skill that writes no cases.")
        else:
            short = ["%s/%s" % (a, b) for a, b in re.findall(r"(\d+)\s*/\s*(\d+)", line.group(0)) if int(a) < int(b)]
            if short:
                out.append("The case-completeness line shows missing cases (%s). Write and run them before "
                           "AUDIT_PASSED (full-qa Phase 8a)." % ", ".join(short))

    # 19. An orchestrator LOADS its phase skills; a phase run from a one-line summary has not run. An audit that
    #     passes a run verdict names the skills it loaded, and every check mark must match a Skill call in the
    #     session transcript.
    if audit_run:
        sl = re.search(r"skills[- ]loaded\s*:([^\n]*)", src, re.I)
        if not sl:
            out.append("AUDIT_PASSED without the 'Skills loaded:' line (full-qa -> Phase skill map): each phase skill "
                       "with \u2713 (loaded by the Skill tool in this run) or n/a (<why>); a skill that loads no other "
                       "skill writes 'Skills loaded: n/a (<why>)'.")
        else:
            body = sl.group(1)
            if re.search(r"\u2717|\u2718|\bnot loaded\b|\bskipped\b|\bmissing\b", body, re.I):
                out.append("The 'Skills loaded:' line names a phase skill that was not loaded and has no n/a reason. "
                           "Load it with the Skill tool and run its checklist (full-qa -> Phase skill map).")
            claimed = re.findall(r"([A-Za-z][\w:.-]*)\s*[\u2713\u2714]", body)
            seen = loaded_skills_cached(transcript)
            if claimed and seen is not None:
                fake = [c for c in claimed if c not in seen and c.split(":")[-1] not in seen]
                if fake:
                    out.append("Skills marked \u2713 that this session never loaded (no Skill call in the transcript): "
                               "%s. Load them with the Skill tool, or mark them n/a with a reason." % ", ".join(fake))

    # 20. A run report covers the core-page sweep: the build carries every merged change, so the story's own screens
    #     are not the only ones it can break (illustrative: a shared text key gained a placeholder for one page; two
    #     other pages showed the raw placeholder for a week behind ticket-scoped smokes). Every route of
    #     PROJECT-PROFILE.md section 8 needs a row 'Core-page sweep: <route>' with a canonical result. A bug-verifier
    #     verdict is exempt; 'Browser: off' skips the check.
    if audit_run and run_skill != "bug-verifier" and not browser_off():
        rows = [ln for ln in src.splitlines() if ln.strip().startswith("|") and "core-page sweep" in ln.lower()]
        good = [ln for ln in rows if row_result(ln) and (row_result(ln) != "NOT APPLICABLE" or DECIDED.search(ln))]
        routes = sweep_routes()
        blanket = any(row_result(ln) == "NOT APPLICABLE" and not any(r in ln for r in routes) for ln in good)
        if routes and not blanket:
            missing = [r for r in routes
                       if not any(re.search(r"(?<![\w/-])" + re.escape(r) + r"(?![\w/-])", ln) for ln in good)]
        else:
            missing = [] if good else ["every page"]
        if missing:
            out.append("Core-page sweep incomplete: no row with a canonical result for %s. qa-standards -> Core-page "
                       "sweep: per role run .claude/skills/browser-test/scripts/core-page-sweep.js (or raw-text-scan.js "
                       "page by page) and add one Execution Register row 'Core-page sweep: <route>' per page with its "
                       "result and evidence id; 'skipped' or 'not run' is not a result, and an n/a row counts only when "
                       "it quotes the owner's decision or a capability that is off (PROJECT-PROFILE.md \u00a72)."
                       % ", ".join(missing))

    # 21. A full / regression / bugfix / release report shows the regression it ran (full-qa Phase 7b,
    #     regression-runner): at least one 'Regression: <area>' row with a canonical result that is not n/a (an n/a
    #     row counts when it cites the owner's decision), and no Regression row without a result. The mode comes
    #     from the Run line, never from the session.
    if audit_run and run and run_skill != "bug-verifier" and run[1] in ("full", "regression", "bugfix", "release"):
        rows = [ln for ln in src.splitlines() if ln.strip().startswith("|") and "regression:" in ln.lower()]
        ran = [ln for ln in rows if row_result(ln) and (row_result(ln) != "NOT APPLICABLE" or DECIDED.search(ln))]
        if not ran or any(not row_result(ln) for ln in rows):
            out.append("Regression rows missing or without a result in a %s-mode run report. full-qa Phase 7b: one "
                       "Execution Register row 'Regression: <area>' per area of the Step 0b map, Impact Analysis 1b and "
                       "the code review's Possibly affected list, each with a canonical result and an evidence id; "
                       "'skipped' or 'not run' is not a result, and an n/a row counts only when it quotes the owner's "
                       "decision." % run[1])

    # 22. Every run report carries the Run line; without it checks 18-21 would never run on that report.
    #     A run report = Execution Register rows + a verdict word.
    if _has_register_rows(text) and (re.search(r"\b(GO|NO-GO|PARTIAL)\b|\bAUDIT_(PASSED|FAILED)\b", text) or
                                     re.search(r"\bverdict\s*:", text, re.I)):
        if not run:
            out.append("Run report without the Run line. Put this plain line (not in backticks) above the verdict: "
                       "'Run: <skill> | QA mode: <mode> | Audit: AUDIT_PASSED', skill = %s, mode = %s "
                       "(qa-standards -> Verdict Contract)." % (" / ".join(RUN_SKILLS), " / ".join(QA_MODES)))
        elif run[0] not in RUN_SKILLS or run[1] not in QA_MODES:
            out.append("The Run line names an unknown skill or QA mode (%s, %s). Skills: %s; modes: %s."
                       % (run[0], run[1], ", ".join(RUN_SKILLS), ", ".join(QA_MODES)))
        elif run[2] == "AUDIT_FAILED" and re.search(r"\b(GO|NO-GO|PARTIAL)\b", text):
            out.append("The Run line says AUDIT_FAILED next to a run verdict. full-qa Phase 8a: resolve every audit "
                       "challenge with evidence and re-audit before the verdict is reported.")

    return out


def _project_root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _evidence_root():
    ev = "qa-evidence"
    try:
        with io.open(os.path.join(HERE, "harness-config.json"), "r", encoding="utf-8") as fh:
            ev = json.load(fh).get("evidence_root") or ev
    except Exception:
        pass
    return ev if os.path.isabs(ev) else os.path.join(_project_root(), ev)


def run_record_warnings(text):
    names = sorted(set(re.findall(r"qa-evidence[/\\]([A-Za-z0-9][A-Za-z0-9._-]*)", text)))
    if not names:
        return []
    states_verdict = bool(re.search(r"\b(GO|NO-GO|PARTIAL)\b", text))
    vc_path = os.path.join(_project_root(), ".claude", "skills", "qa-standards", "scripts", "verdict_check.py")
    out = []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("verdict_check", vc_path)
        vc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vc)
    except Exception:
        return []
    for name in names[:3]:
        rd = os.path.join(_evidence_root(), name)
        if not os.path.isdir(rd):
            continue
        if not os.path.isfile(os.path.join(rd, "run.json")):
            if states_verdict:
                out.append("The verdict names %s but that folder has no run.json, so the verdict cannot be "
                           "recomputed (qa-standards references/run-record.md)." % name)
            continue
        try:
            data = vc.load(rd)
            err, _, rc = vc.check(data, rd, partial=not states_verdict)
        except Exception as e:
            out.append("run.json in %s could not be checked (%s)." % (name, type(e).__name__))
            continue
        if err:
            out.append("run.json in %s contradicts itself (%d issue(s)); first: %s. Recomputed: %s. "
                       "Run verdict_check.py on the folder and fix the record or the verdict."
                       % (name, len(err), err[0], rc["confidence_line"]))
    return out


def _log(line):
    if not GATE["log"]:
        return
    try:
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), line))
    except Exception:
        pass


def main():
    try:
        # Read bytes and decode UTF-8: sys.stdin uses the console code page on Windows, which garbles every
        # non-ASCII character (configured concession phrases in other languages, the check marks of check 19).
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        # A gate that cannot read its input must SAY so, not wave the turn through silently.
        msg = ("COMPLETION GATE could not parse its hook input (%s). No checks ran - "
               "treat this turn as UNVERIFIED by the gate." % type(e).__name__)
        _log("parse-error  %s" % type(e).__name__)
        if ENFORCE:
            sys.stderr.write(msg + "\n")
            sys.exit(2)
        print(json.dumps({"systemMessage": msg}))
        sys.exit(0)

    # Claude Code sets stop_hook_active when it is already continuing because of THIS hook.
    # Re-blocking there is what creates the loop the docs warn about (override after 8).
    if data.get("stop_hook_active"):
        sys.exit(0)

    raw = data.get("last_assistant_message") or ""
    # A turn that QUOTES or EXPLAINS a verdict is not a turn that issues one.
    text = strip_quoted(raw)
    if not text or not VERDICT.search(text):
        sys.exit(0)                      # not a verdict turn - stay silent

    warnings = checks(text, raw, data.get("transcript_path"))
    if not warnings:
        sys.exit(0)

    _log("%s  %s" % (data.get("agent_type", "main"), " | ".join(warnings)))

    msg = ("COMPLETION GATE - " + ("BLOCKING" if ENFORCE else "advisory") + ":\n- " +
           "\n- ".join(warnings) +
           "\nResolve these or state explicitly why each does not apply.")

    if ENFORCE:
        sys.stderr.write(msg + "\n")
        sys.exit(2)                      # exit 2 = block, ask Claude to continue
    print(json.dumps({"systemMessage": msg}))
    sys.exit(0)


if __name__ == "__main__":
    main()
