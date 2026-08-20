#!/usr/bin/env python3
"""Hermetic suite for tools/estate-provenance.py. No git, no network, no fleet.

⛔ It also plants a specimen and asserts the verdict MOVES. A checker that only ever
returns the same verdict on the same tree has not been shown to discriminate — it has
been shown to run. That is criterion 4, and it is the leg usually faked.
"""
import importlib.util
import os
import subprocess
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "estate_provenance", os.path.join(_here, "estate-provenance.py"))
ep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ep)

FAILED = 0


def run_tool(*args):
    """Invoke the tool itself. ⚠ An execution surface — deliberately only this ONE tool,
    which I own, and which refuses before doing any git or network work."""
    here = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.run([sys.executable, os.path.join(here, "estate-provenance.py")] + list(args),
                       capture_output=True, text=True, cwd=here)
    return p.returncode


def check(name, got, want):
    global FAILED
    ok = got == want
    if not ok:
        FAILED += 1
    print("  %-4s %-42s got=%-10s want=%s" % ("PASS" if ok else "FAIL", name, got, want))


def main():
    print("NFORMA-RUN test_estate_provenance")

    # the module's own inline table
    rc = ep.self_test()
    check("inline self-test exits 0", rc, 0)

    lo, hi = 1, 400
    v = lambda t: ep.classify(t, lo, hi)[0]                      # noqa: E731

    # ⛔ THE VERDICT MUST MOVE. Same file, one planted line, different answer.
    clean = "def main():\n    return 0\n"
    check("baseline: unmarked file", v(clean), "UNCLAIMED")
    check("plant an out-of-range cite", v(clean + "# see #1226\n"), "FOREIGN")
    check("plant an in-range cite", v(clean + "# see #319\n"), "LOCAL")
    check("plant foreign vocabulary", v(clean + "# akash provider\n"), "FOREIGN")

    # ⚠ FOREIGN must dominate: a file with BOTH is not laundered by its local half.
    check("in-range does not launder foreign",
          v("# see #319\n# Borduas-Holdings/Blazing-Back\n"), "FOREIGN")

    # boundary, both sides
    check("boundary hi", v("#%d" % hi), "LOCAL")
    check("boundary hi+1", v("#%d" % (hi + 1)), "FOREIGN")

    # ⛔ range derivation must REFUSE rather than invent
    check("no repo -> range is None",
          ep.local_issue_range("/nonexistent-for-test"), None)

    # a number that is not an issue cite must not create provenance
    check("bare digits are not a citation", v("x = 1226\n"), "UNCLAIMED")

    # ⛔ An unrecognised flag must be REFUSED, not discarded. `"--self-test" in argv` is
    # membership: it accepts the flag without rejecting anything else, so `--zzz` fell
    # through the target filter and the tool scanned the DEFAULT population — returning an
    # exit code the caller reads as an answer to a question they never asked. (#321's shape.)
    check("unknown flag exits 2", run_tool("--zzz-not-a-flag"), 2)
    # ⚠ The combination is the nastier state: a REAL flag plus a typo used to exit 0, so a
    # caller got a clean control result that had silently ignored half its invocation.
    check("self-test + garbage still refused", run_tool("--self-test", "--zzz-not-a-flag"), 2)
    check("and the real flag still works", run_tool("--self-test"), 0)

    print("NFORMA-RESULT %s" % ("OK" if FAILED == 0 else "FAIL"))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
