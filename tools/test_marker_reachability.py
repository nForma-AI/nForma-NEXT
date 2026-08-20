#!/usr/bin/env python3
"""Pins the reachability check against the three defects that shipped a CLEAN WRONG answer.

Why this file exists
--------------------
The first working version reported **870 test files, 0 unreachable** on a 50-workflow
estate, and missed a guard that two agents had already reported as never collected. Three
compounding defects, each of which alone would have been survivable:

  1. THE MATCHER FOUND ITS TOKEN IN THE PROSE ABOUT THE TOKEN. `pytest` was matched
     anywhere on a line, so comments (`# the runner only hosts lint / unit-tests (pytest`)
     and `echo "... pytest workers"` parsed as invocations.
  2. FAIL-OPEN DEFAULT. Those mis-parses yielded `paths=[] -m=None`, which the rule reads
     as *collects everything* — so ONE COMMENT marked the whole repository reachable.
  3. THE RIGHT ANSWER TO THE WRONG QUESTION. After fixing 1 and 2 it flagged 11 e2e files
     as unreachable. True — pytest does not collect them — and irrelevant: they are run as
     `python3 e2e/test_x.py` in their own workflows. A true answer to the wrong question
     survives review, which makes it the harder failure of the three.

Plus a narrower one: `pytest.mark.skipif` was counted as a selection marker. It changes
what happens once a test is collected and says nothing about `-m`.

Run: python3 tools/test_marker_reachability.py
"""
import importlib.util
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "mr", os.path.join(_HERE, "marker-reachability.py"))
mr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mr)


def check(name, got, want):
    ok = got == want
    print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
    return ok


def main():
    f = 0

    # ── 1. prose is not an invocation ────────────────────────────────────────────
    f += not check("a comment is not an invocation",
                   mr.invocations("      # the runner only hosts unit-tests (pytest\n"), [])
    f += not check("an echo mentioning pytest is not an invocation",
                   mr.invocations('      - run: echo "using 4 pytest workers"\n'), [])
    f += not check("pip install pytest is not an invocation",
                   mr.invocations("      - run: pip install pytest\n"), [])
    f += not check("a real invocation still parses",
                   mr.invocations('      - run: pytest tests/ -m "not e2e"\n'),
                   [(["tests/"], "not e2e", False)])

    # ── 2. the fail-open default, pinned end to end ──────────────────────────────
    # A comment alone must not make a marked file reachable. This is the exact shape
    # that produced 870/0.
    with tempfile.TemporaryDirectory() as td:
        wfd = os.path.join(td, ".github", "workflows"); os.makedirs(wfd)
        os.makedirs(os.path.join(td, "tests"))
        open(os.path.join(wfd, "ci.yml"), "w").write(
            "jobs:\n  a:\n    steps:\n      - run: |\n"
            "          # we used to run pytest here\n"
            '          pytest tests/ -m "not e2e and not network"\n')
        open(os.path.join(td, "tests", "test_m.py"), "w").write(
            "import pytest\npytestmark = pytest.mark.network\n")
        invs = mr.invocations(open(os.path.join(wfd, "ci.yml")).read())
        f += not check("only the real invocation is counted", len(invs), 1)
        f += not check("and it is not the bare/fail-open shape", invs[0][0], ["tests/"])

    # ── 3. directly-run scripts are run ──────────────────────────────────────────
    f += not check("python3 e2e/x.py counts as run",
                   mr.directly_run("      - run: python3 e2e/test_z.py 2>&1 | tee log\n"),
                   {"e2e/test_z.py"})
    f += not check("a commented direct run does not count",
                   mr.directly_run("      # python3 e2e/test_z.py\n"), set())

    # ── 4. skipif is not a selector ──────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "test_s.py")
        open(p, "w").write("import pytest\npytestmark = pytest.mark.skipif(True, reason='x')\n")
        f += not check("skipif is not a selection marker", mr.module_markers(p), set())
        p2 = os.path.join(td, "test_n.py")
        open(p2, "w").write("import pytest\npytestmark = pytest.mark.network\n")
        f += not check("a real selector still counts", mr.module_markers(p2), {"network"})

    # ── 5. the marker algebra ────────────────────────────────────────────────────
    f += not check("excluded", mr.admits("not e2e and not network", {"network"}), False)
    f += not check("admitted", mr.admits("not e2e and not network", set()), True)
    f += not check("no -m admits everything", mr.admits(None, {"network"}), True)
    f += not check("unparseable is UNKNOWN, not a verdict",
                   mr.admits("network and (", {"network"}), None)

    # ── 6. defects found AFTER the PR was opened, by pulling one thread ──────────
    # Each was a confident wrong answer, and they alternate direction — which is the
    # thing to notice: fixing fail-open produced fail-closed, and fixing fail-closed
    # produced fail-SILENT. Every intermediate version looked correct in isolation.

    # 6a. only attributes under `pytest.mark` are markers. `pytest.mark.skipif(os.getenv(..))`
    # yielded `getenv` — a fabricated marker name in a tool whose subject is markers.
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "test_g.py")
        open(p, "w").write("import os, pytest\n"
                           "pytestmark = pytest.mark.skipif(os.getenv('X'), reason='y')\n")
        f += not check("os.getenv is not a marker", mr.module_markers(p), set())
        p2 = os.path.join(td, "test_h.py")
        open(p2, "w").write("import pytest\npytestmark = pytest.mark.network\n")
        f += not check("pytest.mark.network still is", mr.module_markers(p2), {"network"})

    # 6b. `if ! pytest ...` is a command position. Omitting it made the per-file loop
    # INVISIBLE rather than unresolved, so the 243 files it runs fell through to
    # "no invocation covers this path".
    f += not check("if ! pytest is an invocation",
                   len(mr.invocations('          if ! pytest "${f}" -m "not e2e"; then\n')), 1)

    # 6c. a `cd X` + `find Y` loop resolves to X/Y. Without this the conservative rule
    # applied repo-wide and the tool reported ZERO findings — including its own known
    # positive. Fail-silent is not a fix for fail-closed.
    block = ("          cd control-plane/api\n"
             "          for testfile in $(find tests -name 'test_*.py' | sort); do\n"
             '          if ! pytest "${testfile}" -m "not e2e"; then\n')
    invs = mr.invocations(block)
    f += not check("cd+find resolves the loop path",
                   invs[0][0] if invs else None, ["control-plane/api/tests"])
    f += not check("and it is no longer flagged as variable",
                   invs[0][2] if invs else None, False)

    # 6d. an UNRESOLVABLE variable path must still be UNKNOWN, not resolved to something.
    f += not check("a bare variable path stays unknown",
                   mr.invocations('          pytest "${TESTFILE}" -m "not e2e"\n')[0][2], True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
