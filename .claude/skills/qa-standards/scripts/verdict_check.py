#!/usr/bin/env python3
"""Recompute a QA run from its run record (qa-evidence/<run-folder>/run.json) and check it agrees with itself.

    python verdict_check.py <run-folder>              final check: exit 0 consistent, exit 1 contradictions
    python verdict_check.py <run-folder> --partial    mid-run check (no verdict yet, open rows allowed)
    python verdict_check.py <run-folder> --package    also write package.md for the qa-verdict-auditor
    python verdict_check.py <run-folder> --json       print the recomputed numbers as JSON
    python verdict_check.py --summary <evidence-root> one line per run folder that holds a run.json

The shape and the rules are in ../references/run-record.md. The canonical words are the ones in
qa-standards -> Verdict Contract; this script enforces them, it does not define them.
Standard library only. Read-only, except --package, which writes package.md into the run folder.
"""
import io
import json
import os
import re
import sys

RESULTS = ("PASS", "FAIL", "BLOCKED", "NOT APPLICABLE", "NOT YET VERIFIED")
FINDING_STATUS = ("CONFIRMED BUG", "NOT A BUG", "CANNOT CONFIRM", "DUPLICATE")
RUN_VERDICTS = ("GO", "NO-GO", "PARTIAL")


def load(run_dir):
    p = os.path.join(run_dir, "run.json")
    with io.open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _is_ref(ev):
    f = (ev.get("file") or "").strip()
    t = (ev.get("type") or "").lower()
    return ("://" in f or re.search(r"[^\\/]:\d+(?:-\d+)?$", f) is not None
            or any(k in t for k in ("code", "git", "contract", "commit", "diff")))


def recompute(data):
    reg = data.get("register") or []
    in_scope = [r for r in reg if r.get("result") != "NOT APPLICABLE"]
    n = sum(1 for r in in_scope if r.get("result") in ("PASS", "FAIL"))
    k = sum(1 for r in in_scope if r.get("result") == "BLOCKED")
    j = sum(1 for r in in_scope if r.get("result") == "NOT YET VERIFIED")
    m = len(in_scope)
    bugs = [f for f in (data.get("findings") or []) if f.get("status") == "CONFIRMED BUG"]
    if bugs:
        verdict = "NO-GO"
    elif k or j:
        verdict = "PARTIAL"
    else:
        verdict = "GO"
    risk = ((data.get("verdict") or {}).get("remaining_risk") or "none").strip()
    line = "Verified %d of %d in-scope areas; BLOCKED %d; NOT YET VERIFIED %d; Remaining Risk: %s" % (n, m, k, j, risk)
    return {"N": n, "M": m, "k": k, "j": j, "confirmed_bugs": len(bugs), "verdict": verdict, "confidence_line": line}


def check(data, run_dir, partial=False):
    err, warn = [], []
    if data.get("schema") != "qa-run/1":
        err.append("schema must be 'qa-run/1' (got %r)" % data.get("schema"))
    for key in ("run_id", "skill", "mode", "env", "register", "ledger"):
        if key not in data:
            err.append("missing top-level field %r" % key)
    ledger = {e.get("id"): e for e in (data.get("ledger") or [])}
    findings = {f.get("id"): f for f in (data.get("findings") or [])}

    for e in data.get("ledger") or []:
        eid = e.get("id") or "?"
        for k in ("env", "commit", "captured_at"):
            if not e.get(k):
                err.append("ledger %s: provenance field %r is empty (qa-standards: Evidence provenance)" % (eid, k))
        f = (e.get("file") or "").strip()
        if not f:
            err.append("ledger %s: no file / URL / path:line" % eid)
        elif not _is_ref(e) and not os.path.exists(os.path.join(run_dir, f)):
            err.append("ledger %s: file %r is not in the run folder" % (eid, f))

    covered = set()
    for r in data.get("register") or []:
        rid = r.get("id") or "?"
        res = r.get("result")
        ev = r.get("evidence") or []
        covered.update(r.get("cells") or [])
        if res not in RESULTS:
            err.append("register %s: result %r is not one of %s" % (rid, res, " / ".join(RESULTS)))
            continue
        for x in ev:
            if x not in ledger:
                err.append("register %s: evidence id %s is not in the ledger" % (rid, x))
        if res == "PASS" and not ev:
            err.append("register %s: PASS with no evidence (no evidence = no finding)" % rid)
        if res == "FAIL":
            if not r.get("expected_source"):
                err.append("register %s: FAIL without expected_source (Verdict Contract: FAIL needs an authoritative source)" % rid)
            if not ev:
                err.append("register %s: FAIL without reproduction evidence" % rid)
            if not r.get("finding"):
                err.append("register %s: FAIL row names no finding id" % rid)
            elif r.get("finding") not in findings:
                err.append("register %s: finding %s is not in findings[]" % (rid, r.get("finding")))
        if res == "BLOCKED":
            if not r.get("reason"):
                err.append("register %s: BLOCKED without a reason" % rid)
            if not r.get("unblock"):
                err.append("register %s: BLOCKED without what would unblock it" % rid)
        if res == "NOT APPLICABLE" and not r.get("reason"):
            err.append("register %s: NOT APPLICABLE without the scope predicate (reason)" % rid)
        if res == "NOT YET VERIFIED" and not partial:
            warn.append("register %s: NOT YET VERIFIED - listed, so the run cannot be GO" % rid)
        if res == "PASS" and r.get("path_exercised") == "write":
            types = " ".join((ledger.get(x) or {}).get("type", "").lower() for x in ev)
            if not re.search(r"api|network|request", types) or not re.search(r"\bdb\b|database|query", types):
                err.append("register %s: write-path PASS needs a network/API row AND a DB row "
                           "(validation green is not feature green)" % rid)

    matrix = data.get("matrix") or {}
    excluded = {x.get("cell") if isinstance(x, dict) else x for x in (matrix.get("excluded") or [])}
    for x in matrix.get("excluded") or []:
        if isinstance(x, dict) and not x.get("reason"):
            err.append("matrix: excluded cell %r has no reason" % x.get("cell"))
    for cell in matrix.get("cells") or []:
        if cell not in excluded and cell not in covered:
            err.append("matrix: cell %r has no register row (add one, NOT YET VERIFIED if it was not run)" % cell)

    for fid, f in findings.items():
        if f.get("status") not in FINDING_STATUS:
            err.append("finding %s: status %r is not one of %s" % (fid, f.get("status"), " / ".join(FINDING_STATUS)))
        if f.get("status") == "CONFIRMED BUG":
            ev = f.get("evidence") or []
            if not ev:
                err.append("finding %s: CONFIRMED BUG without evidence (no reproduction = no confirmed bug)" % fid)
            for x in ev:
                if x not in ledger:
                    err.append("finding %s: evidence id %s is not in the ledger" % (fid, x))

    rc = recompute(data)
    v = data.get("verdict") or {}
    stated = v.get("run")
    strict = (data.get("verdict_policy") or "strict-binary") == "strict-binary"
    if partial:
        if stated and stated not in RUN_VERDICTS:
            err.append("verdict.run %r is not one of %s" % (stated, " / ".join(RUN_VERDICTS)))
    else:
        if stated not in RUN_VERDICTS:
            err.append("verdict.run %r is not one of %s" % (stated, " / ".join(RUN_VERDICTS)))
        elif stated != rc["verdict"]:
            msg = "verdict.run is %s but the rows give %s (confirmed bugs %d, BLOCKED %d, NOT YET VERIFIED %d)" % (
                stated, rc["verdict"], rc["confirmed_bugs"], rc["k"], rc["j"])
            (err if strict else warn).append(msg + ("" if strict else " - severity-weighted policy: state the threshold"))
        line = (v.get("confidence_line") or "").strip()
        want = rc["confidence_line"].split("; Remaining Risk:")[0]
        if not line:
            err.append("verdict.confidence_line is empty; it must read: %s" % rc["confidence_line"])
        elif line.split("; Remaining Risk:")[0] != want:
            err.append("confidence line does not match the register: stated %r, recomputed %r" % (line.split("; Remaining Risk:")[0], want))
        if v.get("audit") not in ("AUDIT_PASSED", "AUDIT_FAILED", "not-run", None):
            err.append("verdict.audit %r is not AUDIT_PASSED / AUDIT_FAILED / not-run" % v.get("audit"))
    return err, warn, rc


def _md_table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        cells = []
        for c in cols:
            val = r.get(c)
            if isinstance(val, list):
                val = ", ".join(str(x) for x in val)
            cells.append(str(val if val not in (None, "") else "").replace("|", "/").replace("\n", " "))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def package(data, rc):
    v = data.get("verdict") or {}
    scope = data.get("scope") or {}
    lines = ["# Audit package - %s" % data.get("run_id", "?"), "",
             "Generated from run.json by verdict_check.py --package. It carries the findings, the acceptance-criteria",
             "source, the register, the ledger and the proposed verdict - and no reasoning. Audit it against the",
             "files in this folder and the live systems; try to refute every row.", "",
             "- Skill / mode: %s / %s" % (data.get("skill"), data.get("mode")),
             "- Subject: %s" % data.get("subject", ""),
             "- Env: %s" % data.get("env"),
             "- Commits: %s" % ", ".join("%s = %s" % kv for kv in (data.get("commits") or {}).items()),
             "- AC source: %s" % scope.get("ac_source", ""),
             "- In scope: %s" % "; ".join(scope.get("in") or []),
             "- Out of scope: %s" % "; ".join("%s (%s)" % (o.get("item"), o.get("reason")) if isinstance(o, dict) else str(o)
                                             for o in (scope.get("out") or [])),
             "", "## Execution register", "",
             _md_table(data.get("register") or [], ["id", "area", "requirement", "check", "result", "expected_source",
                                                     "evidence", "path_exercised", "finding", "reason", "unblock"]),
             "", "## Evidence ledger", "",
             _md_table(data.get("ledger") or [], ["id", "type", "file", "env", "commit", "captured_at", "proves"]),
             "", "## Findings", "",
             _md_table(data.get("findings") or [], ["id", "title", "layer", "severity", "status", "evidence", "ticket"]),
             "", "## Proposed verdict", "",
             "- Stated: %s" % v.get("run"),
             "- Recomputed from the rows: %s" % rc["verdict"],
             "- Confidence line (recomputed): %s" % rc["confidence_line"], ""]
    return "\n".join(lines)


def summary(root):
    rows = []
    for d in sorted(os.listdir(root)):
        rd = os.path.join(root, d)
        if not os.path.isfile(os.path.join(rd, "run.json")):
            continue
        try:
            data = load(rd)
            err, _, rc = check(data, rd, partial=not (data.get("verdict") or {}).get("run"))
            phases = data.get("phases") or []
            skipped = sum(1 for p in phases if p.get("status") == "skipped")
            rows.append((d, data.get("skill", "?"), data.get("mode", "?"), (data.get("verdict") or {}).get("run") or "-",
                         "%d/%d" % (rc["N"], rc["M"]), str(rc["k"]), str(rc["j"]), str(skipped),
                         "OK" if not err else "INCONSISTENT(%d)" % len(err), data.get("updated_at", "")))
        except Exception as e:
            rows.append((d, "?", "?", "?", "?", "?", "?", "?", "UNREADABLE(%s)" % type(e).__name__, ""))
    hdr = ("run", "skill", "mode", "verdict", "N/M", "blocked", "nyv", "skipped", "record", "updated")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    for r in rows:
        print("| " + " | ".join(r) + " |")
    return 0


def main(argv):
    if "--summary" in argv:
        i = argv.index("--summary")
        root = argv[i + 1] if len(argv) > i + 1 else "qa-evidence"
        return summary(root)
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    run_dir = args[0]
    try:
        data = load(run_dir)
    except Exception as e:
        print("ERROR cannot read %s/run.json: %s" % (run_dir, e))
        return 1
    err, warn, rc = check(data, run_dir, partial="--partial" in argv)
    if "--json" in argv:
        print(json.dumps(dict(rc, errors=err, warnings=warn), indent=2))
    else:
        for w in warn:
            print("WARN ", w)
        for e in err:
            print("ERROR", e)
        print("recomputed: %s | %s" % (rc["verdict"], rc["confidence_line"]))
        print("%s: %d contradiction(s), %d warning(s)" % ("CONSISTENT" if not err else "INCONSISTENT", len(err), len(warn)))
    if "--package" in argv:
        p = os.path.join(run_dir, "package.md")
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(package(data, rc))
        print("wrote %s" % p)
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))