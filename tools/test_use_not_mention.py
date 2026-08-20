#!/usr/bin/env python3
"""Hermetic suite for use-not-mention.py. No network, no repo state, no fixtures on disk.

⛔ WHY IT EXISTS. That tool shipped with `--self-test` and the gate runs LISTED
suites, so its controls have never executed in CI. A control living behind a flag
nothing invokes has NO EXECUTION RECORD — #2 — and this fleet measured that exact
failure when doctrine-watch carried a known-positive that fired only while the
fleet was broken and nothing noticed.

★ The cases below are the ones the tool was BUILT from — two real false positives
from a live sweep, and the under-report its own control caught during development.
"""
import importlib.util, os, sys, tempfile

_spec = importlib.util.spec_from_file_location(
    "uvm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "use-not-mention.py"))
u = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(u)

fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    if not ok:
        fails += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")


TMP = tempfile.mkdtemp(prefix="uvm-suite-")


def verdicts(src, pattern="gh pr list"):
    p = os.path.join(TMP, f"m{abs(hash(src))}.py")
    open(p, "w").write(src)
    rows = u.classify_file(p, pattern)
    if rows is None:
        return None
    return [v for _, v, _, _ in u.strongest_per_line(rows)]


print("★ the two REAL false positives this tool was built from:")
# stranded-branches.py:258 — a print() warning about the very defect being scanned
# for. ⛔ It tripped the original grep BECAUSE it handles truncation correctly.
check("print() warning containing the pattern -> no CALL",
      "CALL" in (verdicts('print("⛔ TRUNCATED SWEEP — `gh pr list` returned exactly N rows")') or []),
      False)
# test_wake_yield.py:62 — a fixture string passed to a local helper that classifies
# rather than executes.
check("fixture string into a non-executing local -> no CALL",
      "CALL" in (verdicts('def classify(c):\n    return len(c)\n'
                          'def bash(c):\n    return classify(c)\n'
                          'bash("gh pr list --limit 1")\n') or []), False)

print("\nand the real call in the SAME file must still read as one:")
check("local wrapper reaching subprocess -> CALL",
      "CALL" in (verdicts('import subprocess\ndef sh(*a):\n    return subprocess.run(a)\n'
                          'sh("gh", "pr", "list", "--state", "merged")\n') or []), True)
check("a direct stdlib sink -> CALL",
      "CALL" in (verdicts('import subprocess\nsubprocess.run("gh pr list", shell=True)\n') or []),
      True)

print("\n⛔ the UNDER-REPORT its own control caught during development:")
# One-level resolution read outer -> inner -> subprocess.run as MENTION, asserting
# "reaches no execution sink" about a chain that reaches one. That is the unsafe
# direction for a rate. The fixpoint must resolve it.
check("TWO wrappers deep, resolved by fixpoint -> CALL",
      "CALL" in (verdicts('import subprocess\ndef inner(*a):\n    return subprocess.run(a)\n'
                          'def outer(*a):\n    return inner(*a)\n'
                          'outer("gh", "pr", "list")\n') or []), True)

print("\nan unresolvable callee is UNKNOWN, never 'no sink':")
check("callee imported from elsewhere -> not MENTION",
      "MENTION" in (verdicts('from somewhere import run_it\n'
                             'def wrap(*a):\n    return run_it(*a)\n'
                             'wrap("gh", "pr", "list")\n') or []), False)

print("\n⛔ an unparseable file is VOID — established nothing, never 'no calls':")
bad = os.path.join(TMP, "notpython.sh")
open(bad, "w").write("gh pr list --limit 1\n")
check("shell script -> None (VOID)", u.classify_file(bad, "gh pr list"), None)

print(f"\n{'PASS' if not fails else 'FAIL'} — {fails} failure(s)")
sys.exit(1 if fails else 0)
