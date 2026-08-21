#!/usr/bin/env python3
"""Pins that an UNDATED check is not an old one, and a failed query is not a green board.

⛔ The three ways this tool could hand back reassurance:
  - a check with no `completedAt` treated as STALE, quietly enlarging the "safe to
    ignore" pile
  - a failed GraphQL query printed as an empty board
  - no required contexts found — every check then counts as optional, which is a
    verdict about the QUERY, not about the repository

Run: python3 tools/test_check_freshness.py
"""
import json, os, sys, types
from datetime import datetime, timezone

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    with open(path) as fh:
        src = fh.read()
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


cf = load(os.path.join(_here, "check-freshness.py"), "cf")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


SINCE = datetime(2026, 8, 20, 22, 0, 0, tzinfo=timezone.utc)

check("after the boundary is CURRENT",
      cf.classify("2026-08-20T23:28:49Z", SINCE), cf.CURRENT)
check("before it is STALE",
      cf.classify("2026-08-20T21:59:59Z", SINCE), cf.STALE)
check("exactly at the boundary counts as CURRENT",
      cf.classify("2026-08-20T22:00:00Z", SINCE), cf.CURRENT)

# ⛔ THE ONE THAT MATTERS: a missing date is not an old date.
check("no completedAt is UNDATED, never STALE", cf.classify(None, SINCE), cf.UNDATED)
check("an empty string is UNDATED too", cf.classify("", SINCE), cf.UNDATED)
check("an unparseable date is UNDATED, not silently old",
      cf.classify("yesterday-ish", SINCE), cf.UNDATED)
# KNOWN-BAD control: the naive reading buckets all three of those as old
check("KNOWN-BAD control: `not completed_at` is truthy for every undated case",
      [bool(not x) for x in (None, "", "yesterday-ish")], [True, True, False])

# ── a failed query is not a green board ──────────────────────────────────────
real = cf.subprocess.run


def fake(rc, out=""):
    class R:
        returncode, stdout, stderr = rc, out, ""
    return lambda *a, **k: R()


cf.subprocess.run = fake(1)
check("a failed query is None", cf.fetch("o", "n", 5), None)
cf.subprocess.run = fake(0, "")
check("empty stdout is None", cf.fetch("o", "n", 5), None)
cf.subprocess.run = fake(0, "not json")
check("unparseable output is None", cf.fetch("o", "n", 5), None)
cf.subprocess.run = fake(0, '{"data":{"repository":null}}')
check("a null repository is None, not an empty board", cf.fetch("o", "n", 5), None)
cf.subprocess.run = real


# ── ⛔ EVERY `first:N` WINDOW IS A SILENT TRUNCATION UNTIL COMPARED TO totalCount ──
# Both windows in this tool's query were unchecked. Measured 2026-08-21 on
# Borduas-Holdings/Blazing-Back: branchProtectionRules totalCount 1 (window 5),
# contexts totalCount 56-57 (window 100). Neither bound — but 57 of 100 is not
# margin, and NOTHING would have said so when it did.
#
# ★ The two truncations are NOT the same severity, and the code treats them
# differently on purpose:
#   branchProtectionRules -> decides WHICH contexts are required. A dropped rule
#                            does not shrink the answer, it REDEFINES THE QUESTION.
#                            ⇒ fatal, exit 2.
#   contexts              -> loses rows from one PR's verdict. A missing red check
#                            reads as a green PR. ⇒ named, counts become LOWER bounds.
check("the query asks for totalCount on the protection rules",
      "branchProtectionRules(first:5){totalCount" in cf.QUERY, True)
check("...and on the context list", "contexts(first:100){totalCount" in cf.QUERY, True)

# ⛔ KNOWN-BAD CONTROL: without totalCount in the RESPONSE the check cannot run at
# all, and its absence would read as "not truncated". Assert the field is consumed.
src = open(os.path.join(_here, "check-freshness.py")).read()
check("the rules totalCount is COMPARED, not merely requested",
      'bp["totalCount"] > len(bp["nodes"])' in src, True)
check("the contexts totalCount is COMPARED too",
      'ctx_conn["totalCount"] > len(ctx_conn["nodes"])' in src, True)
check("a truncated required-set is FATAL (exit 2), not a warning",
      "The required set is " in src and "return 2" in src, True)
check("a truncated context list is NAMED, not fatal",
      "truncated_prs.append" in src, True)
check("...and turns the counts into LOWER bounds in the output",
      "LOWER bounds" in src, True)
check("the no-truncation line prints on SUCCESS too — never only on failure",
      "no truncation" in src, True)


# ── ⛔ THE ABOVE ARE SOURCE-TEXT ASSERTIONS AND WOULD PASS AGAINST A COMMENT ──
# So drive the real thing: hand main() a response whose totalCount EXCEEDS its
# nodes and assert the EXIT CODE, which is what a caller acts on.
import io, contextlib

def _resp(rule_total, rule_nodes, ctx_total, ctx_nodes):
    return json.dumps({"data": {"repository": {
        "branchProtectionRules": {"totalCount": rule_total, "nodes": [
            {"pattern": "main", "requiredStatusCheckContexts": ["A1"]}] * rule_nodes},
        "pullRequests": {"nodes": [{"number": 1, "title": "t", "commits": {"nodes": [
            {"commit": {"statusCheckRollup": {"contexts": {
                "totalCount": ctx_total,
                "nodes": [{"__typename": "CheckRun", "name": "A1",
                           "conclusion": "FAILURE",
                           "completedAt": "2026-08-20T23:00:00Z"}] * ctx_nodes}}}}]}}]}}}})

def _run(resp):
    cf.subprocess.run = fake(0, resp)
    buf = io.StringIO()
    argv = sys.argv[:]
    sys.argv = ["check-freshness.py", "--repo", "o/n", "--since", "2026-08-20T22:00:00Z"]
    try:
        with contextlib.redirect_stdout(buf):
            rc = cf.main()
    finally:
        sys.argv = argv
        cf.subprocess.run = real
    return rc, buf.getvalue()

rc, out = _run(_resp(9, 1, 1, 1))
check("BEHAVIOUR: a truncated required-set EXITS 2", rc, 2)
check("...and says the required set is incomplete", "required set is INCOMPLETE" in out, True)
check("...and prints NO verdict table — the question was wrong, not the sample",
      "required context(s)" in out, False)

rc, out = _run(_resp(1, 1, 40, 1))
check("BEHAVIOUR: a truncated context list does NOT exit 2", rc in (0, 1), True)
check("...but names the PR and the shortfall", "#1 40>1" in out, True)
check("...and downgrades the counts to LOWER bounds", "LOWER bounds" in out, True)

rc, out = _run(_resp(1, 1, 1, 1))
check("BEHAVIOUR: an untruncated read says so explicitly", "no truncation" in out, True)
check("...and does NOT claim a truncation", "LOWER bounds" in out, False)

# ⛔ KNOWN-BAD CONTROL — without this the three checks above would also pass
# against a tool that exits 2 unconditionally.
check("KNOWN-BAD control: the healthy case does NOT exit 2", rc != 2, True)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
