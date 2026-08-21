#!/usr/bin/env python3
"""Pins landing-rate's cause clause against the two ways it was already WRONG.

⛔ CRITERION 4 IS WHY THIS FILE EXISTS (#381). Both defects below were live, both were
found by an emission arriving that should not have, and both were fixed in a scratchpad
monitor where nothing re-runs the demonstration. That evidence was a screenshot.

  · V1 carried the CONSTANT string "accumulating with no exit" — true during a stall
    where 15 of 15 were mergeable, FALSE during one where every open PR was CONFLICTING
    and no merge was possible.
  · V2 derived the clause from the SPLIT and announced merger-absence on every LANDED
    event, with a ZERO-minute gap, seconds after a merge.

★ The regression tests are therefore the two FALSE verdicts, not the true ones:
  a zero-gap board with mergeable work must NOT read STALLED
  an all-CONFLICTING board must NOT read STALLED at any gap

⚠ And the boundary is asserted directly. `mins == stall` is the first minute the gap
counts; off-by-one there silently moves the alarm and nothing else would notice.

Hermetic by construction: classify() takes counts and returns a verdict. No repository,
no network, no forge — so this carries no `# SUITE-DEPENDS:` and the CI glob gates it.
"""
import importlib.util, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "lr", Path(__file__).resolve().parent / "landing-rate.py")
lr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lr)

FAILED = 0


def check(label, got, want):
    global FAILED
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAILED += 1


def v(total, m, c, u, mins, stall=30):
    return lr.classify(total, m, c, u, mins, stall)[1]


print("★ regression — the two verdicts this gauge got WRONG in production:")
check("zero-gap board with mergeable work is NOT a stall", v(5, 5, 0, 0, 0), "WORKING")
check("all-CONFLICTING is NOT a merger stall, even at 200m",
      v(3, 0, 3, 0, 200), "NO-MERGE-POSSIBLE")

print("\nthe stall it must still catch:")
check("mergeable work, long gap", v(5, 5, 0, 0, 63), "STALLED")
check("exit code is 1, not 0", lr.classify(5, 5, 0, 0, 63)[0], 1)

print("\n★ the boundary, asserted rather than assumed:")
check("one minute below the threshold", v(5, 5, 0, 0, 29), "WORKING")
check("exactly at the threshold", v(5, 5, 0, 0, 30), "STALLED")

print("\n⛔ states that must never be read as calm:")
check("no timestamp is VOID, not clean", v(5, 5, 0, 0, None), "VOID")
check("VOID exits 2", lr.classify(5, 5, 0, 0, None)[0], 2)
check("all-UNKNOWN is a recompute window", v(5, 0, 0, 5, 99), "RECOMPUTE")
check("empty board is not a blocked one", v(0, 0, 0, 0, 500), "EMPTY")

print("\n⚠ a custom threshold must actually move the alarm:")
check("60m gap under a 90m threshold is WORKING", v(5, 5, 0, 0, 60, 90), "WORKING")
check("60m gap under a 30m threshold is STALLED", v(5, 5, 0, 0, 60, 30), "STALLED")

print(f"\n{FAILED} FAILED" if FAILED else "\nall PASS")
sys.exit(1 if FAILED else 0)
