#!/usr/bin/env python3
"""Pins that a docstring claiming a MEASUREMENT names the day, and that the check
does not flag things that are not claims.

⛔ Written by the author of the offending lines. On 2026-08-21 I changed
`issue-coverage.py` to stamp every count with its collection instant — because
three agents' numbers had been quoted as properties of the repository when they
were photographs — and then wrote, the same night, in two tool docstrings:

    "Two measured instances, FOUR MONTHS APART"     apart from when?
    "MEASURED TWICE IN ONE NIGHT"                   which night?

★ Both true when written, unverifiable afterwards.

Run: python3 tools/test_dated_claims.py
"""
import contextlib, io, os, sys, tempfile, types

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


dc = load(os.path.join(_here, "dated-claims.py"), "dc")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


# ── what IS a claim ──────────────────────────────────────────────────────────
u, r = dc.violations("MEASURED 2026-08-21: 7 of 7 lines carry it.")
check("a dated claim is clean", (u, r), ([], []))

u, r = dc.violations("MEASURED TWICE IN ONE NIGHT, both near-misses.")
check("an undated claim is caught", len(u), 1)
check("...and 'in one night' is ALSO caught — one line, two defects", len(r), 1)

u, r = dc.violations("Two measured instances, four months apart.")
check("'four months apart' is a rotting phrase", len(r), 1)
# ⚠ ...but a date on the SAME LINE resolves it. Flagging a qualified phrase would
# repeat the over-strictness the anaphora fix removed, one rule later.
u, r = dc.violations("MEASURED 2026-08-20/21, twice in one night, both near-misses.")
check("a rot phrase QUALIFIED by a date is not rot", (len(u), len(r)), (0, 0))
check("KNOWN-BAD control: the same phrase WITHOUT the date is still caught",
      len(dc.violations("MEASURED twice in one night, both near-misses.")[1]), 1)

# ⛔ KNOWN-BAD CONTROLS — a check that flagged everything would pass the tests above.
u, r = dc.violations("The threshold is 100000 uACT per block, and 5 of 9 legs are gated.")
check("KNOWN-BAD control: bare numbers are NOT claims", (u, r), ([], []))
u, r = dc.violations("This tool refuses when the window is full.")
check("KNOWN-BAD control: ordinary prose is not flagged", (u, r), ([], []))

# ── anaphora: a date EARLIER in the same docstring satisfies a later claim ────
# ⛔ The first predicate used a ±2-line window and flagged 35 claims across tools/,
# of which 11 were anaphoric — "Measured the same day" pointing back at a date in
# the paragraph above. 31% of its own findings were false.
# ★ A detector whose predicate is tighter than the thing it detects produces
# findings that are not.
far = "Run on 2026-08-21.\n" + "\n" * 8 + "Measured the same day: 88%."
check("a date FAR earlier still satisfies the claim", dc.violations(far), ([], []))
check("KNOWN-BAD control: the same sentence with NO date IS caught",
      len(dc.violations("Measured the same day: 88%.")[0]), 1)
after = "Measured the same day: 88%.\n\n\n\n\n\n\n\n\nRun on 2026-08-21."
# ⚠ THE LABEL AND THE ASSERTION CONTRADICTED EACH OTHER in the first version: the
# label said the date does NOT satisfy the claim (⇒ it IS a violation, count 1) and
# I asserted 0. The suite caught my expectation, not the code. ★ A test name is a
# claim too, and it can disagree with the number beside it.
check("a date only AFTER the claim does NOT satisfy it — a measurement cannot "
      "forward-reference its own date", len(dc.violations(after)[0]), 1)

# ── the three ways to print a clean scan are not all exit 0 ──────────────────
with tempfile.TemporaryDirectory() as tmp:
    def run(d):
        argv = sys.argv[:]
        sys.argv = ["dated-claims.py", "--dir", d]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = dc.main()
        finally:
            sys.argv = argv
        return rc, buf.getvalue()

    rc, out = run(os.path.join(tmp, "nope"))
    check("⛔ a missing directory is exit 2", rc, 2)

    empty = os.path.join(tmp, "empty"); os.makedirs(empty)
    rc, out = run(empty)
    check("⛔ a directory with no .py files is exit 2, not clean", rc, 2)
    check("...saying zero files and zero violations print the same line",
          "print the same clean line" in out, True)

    good = os.path.join(tmp, "good"); os.makedirs(good)
    open(os.path.join(good, "a.py"), "w").write('"""Fine. MEASURED 2026-08-21: 3 of 4."""\n')
    rc, out = run(good)
    check("a clean directory is exit 0", rc, 0)
    check("...and says so explicitly", "carries an ISO date" in out, True)

    open(os.path.join(good, "b.py"), "w").write('"""MEASURED last week: 3 of 4."""\n')
    rc, out = run(good)
    check("one violation makes the scan exit 1", rc, 1)
    check("...naming the file", "b.py" in out, True)
    check("...and stating what it CANNOT tell you",
          "cannot tell whether a date is CORRECT" in out, True)

    # ⚠ a file that will not parse must not be silently skipped as clean
    open(os.path.join(good, "c.py"), "w").write("def (\n")
    check("an unparseable file yields no docstring, not a false clean",
          dc.docstring(os.path.join(good, "c.py")), None)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
