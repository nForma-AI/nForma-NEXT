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
import os, sys, types
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

# ── ⛔ "no current reds" vs "nothing re-ran" — two states, one output ─────────
# Found by USING the tool: with --since set to a recent push it printed
# "0 CURRENT" and exited 0, which reads as clean. Nothing had re-run yet.
def _rollup(contexts):
    return {"data": {"repository": {
        "branchProtectionRules": {"nodes": [
            {"pattern": "main", "requiredStatusCheckContexts": ["A1"]}]},
        "pullRequests": {"nodes": [{"number": 1, "title": "t", "commits": {"nodes": [
            {"commit": {"statusCheckRollup": {"contexts": {"nodes": contexts}}}}]}}]}}}}


def _run(contexts, since_iso):
    import json as _j
    cf.subprocess.run = fake(0, _j.dumps(_rollup(contexts)))
    cf.sys.argv = ["x", "--repo", "o/n", "--since", since_iso]
    try:
        return cf.main()
    finally:
        cf.subprocess.run = real


OLD = [{"__typename": "CheckRun", "name": "A1", "conclusion": "FAILURE",
        "completedAt": "2026-08-20T10:00:00Z"}]
NEWPASS = OLD + [{"__typename": "CheckRun", "name": "A1", "conclusion": "SUCCESS",
                  "completedAt": "2026-08-21T02:00:00Z"}]

check("stale red only, nothing re-ran -> ESTABLISHED NOTHING (exit 2)",
      _run(OLD, "2026-08-21T00:00:00Z"), 2)
check("a required check DID complete after the boundary -> real reading (exit 0)",
      _run(NEWPASS, "2026-08-21T00:00:00Z"), 0)
check("KNOWN-BAD control: both cases have ZERO current reds",
      (len([c for c in OLD if c["completedAt"] > "2026-08-21T00:00:00Z"]),
       len([c for c in NEWPASS if c["conclusion"] == "FAILURE"
            and c["completedAt"] > "2026-08-21T00:00:00Z"])), (0, 0))
check("a CURRENT red still reports as one (exit 1)",
      _run([{"__typename": "CheckRun", "name": "A1", "conclusion": "FAILURE",
             "completedAt": "2026-08-21T02:00:00Z"}], "2026-08-21T00:00:00Z"), 1)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
