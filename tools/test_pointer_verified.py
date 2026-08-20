#!/usr/bin/env python3
"""Hermetic suite for pointer-verified.py. No network, no fleet, no transcripts on disk.

⛔ WHY THIS EXISTS SEPARATELY FROM `--self-test`. The gate runs LISTED suites. A
control that lives only behind a flag nothing invokes is a control with no
execution record — #2 — and this fleet has already measured that exact failure:
doctrine-watch shipped a known-positive that fired only while the fleet was
broken, and nothing caught it because nothing ran --self-test.

⇒ So the discriminating cases run HERE, where the gate reaches them.
"""
import importlib.util, os, sys

_spec = importlib.util.spec_from_file_location(
    "pv", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pointer-verified.py"))
pv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pv)

fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    if not ok:
        fails += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")


def verdict(records):
    rows = pv.audit(records)
    return rows[0][1] if rows else "NO-ROW"


POINTER = ("DOCTRINE POINTER — read it at the ref, do not take it from me: "
           "git show origin/main:goals/RESERVED-ACTIONS.md | sed -n '1,20p'")

print("★ the defect this tool exists for — a pointer QUOTES the command that would verify it:")
# ⛔ THE LOAD-BEARING CASE. Guaranteed in production, because pointers quote the
# command they want run. A tool that reads the turn text instead of the tool calls
# reports every pointer as self-verifying and can never fail.
check("quoted command, no tool calls -> UNVERIFIED",
      verdict([("in", "t", POINTER)]), "UNVERIFIED")
check("quoted command, and the named artifact actually read -> VERIFIED",
      verdict([("in", "t", POINTER),
               ("cmd", "t", "git show origin/main:goals/RESERVED-ACTIONS.md")]), "VERIFIED")

print("\nreading SOMETHING is not reading the NAMED thing:")
# The whole reason the specific predicate replaced the crude one.
check("a different artifact -> READ-DIFFERENT",
      verdict([("in", "t", POINTER), ("cmd", "t", "git show origin/main:goals/README.md")]),
      "READ-DIFFERENT")
check("an unrelated command -> UNVERIFIED",
      verdict([("in", "t", POINTER), ("cmd", "t", "ls -la")]), "UNVERIFIED")

print("\n★ locally produced text is not an inbound pointer — it measures the pane against itself:")
# Measured: /goal echoes contain "re-read" and a path, and scored two UNVERIFIED
# rows against text the pane generated.
check("<local-command-stdout> naming a path -> not a row",
      verdict([("in", "t", "<local-command-stdout>Goal set: re-read goals/dev-implementation.md "
                           + "at HEAD. " + "x " * 60)]), "NO-ROW")
check("a Stop-hook notice naming a path -> not a row",
      verdict([("in", "t", "A session-scoped Stop hook is now active with condition: re-read "
                           "goals/dev-implementation.md. " + "x " * 60)]), "NO-ROW")

print("\nthe window closes at the next inbound turn:")
check("read AFTER the next inbound turn does not count -> UNVERIFIED",
      verdict([("in", "t", POINTER),
               ("in", "t", "Another long inbound turn that is not a pointer. " + "x " * 60),
               ("cmd", "t", "git show origin/main:goals/RESERVED-ACTIONS.md")]), "UNVERIFIED")

print("\na pointer naming nothing readable establishes nothing:")
check("no ref and no path -> NO-ARTIFACT-NAMED",
      verdict([("in", "t", "DOCTRINE MOVED. Go and re-read your row. " + "x " * 60)]),
      "NO-ARTIFACT-NAMED")

print("\n★ and the tool's own control must still pass under the gate:")
check("--self-test returns 0", pv.self_test_quiet(), True)

print(f"\n{'PASS' if not fails else 'FAIL'} — {fails} failure(s)")
sys.exit(1 if fails else 0)
