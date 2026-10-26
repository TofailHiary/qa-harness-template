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


def checks(text):
    """Return a list of gate warnings. Each is a concrete, actionable sentence."""
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
        raw = sys.stdin.read()
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

    text = data.get("last_assistant_message") or ""
    text = strip_quoted(text)
    if not text or not VERDICT.search(text):
        sys.exit(0)                      # not a verdict turn - stay silent

    warnings = checks(text)
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
