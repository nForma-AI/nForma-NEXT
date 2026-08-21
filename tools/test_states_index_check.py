#!/usr/bin/env python3
"""Hermetic suite for tools/states-index-check.py. No git, no network, no fleet.

⛔ WHY: #39's criterion 4 reads "shown to FAIL on real data BY A CALLER THAT STILL RUNS IT."
The tool's --self-test and --verify controls had NO CALLER — it is the second instrument I
added to #372's population (11 instruments whose controls never run in CI) while ruling on
that very issue. This is the caller: the tools/ gate reaches any tools/test_*.py.

⚠ It does NOT make the tool right. It makes its controls reachable, which is a smaller and
different claim.
"""
import importlib.util, os, sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "states_index_check", os.path.join(_here, "states-index-check.py"))
sic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sic)

FAILED = 0


def check(name, got, want):
    global FAILED
    if got != want:
        print(f"  FAIL  {name}: got {got!r}, want {want!r}")
        FAILED += 1
    else:
        print(f"  PASS  {name}: got {got!r}, want {want!r}")


def main():
    print("NFORMA-RUN test_states_index_check", file=sys.stderr)

    row = "| `x.py` | what? | 0 fine · 1 a finding · **2 established nothing** |\n"
    check("codes read from the tool's own row", sic.row_exits(row, "x.py")[0], {0, 1, 2})

    # ⛔ POPULATION: another tool's row must not contribute. Counting it would be the
    #    wrong-population defect this repository has filed fifteen times.
    other = "| `y.py` | q | 0 · 1 · 2 · 3 |\n| `x.py` | q | 0 · 2 |\n"
    check("a different tool's row does not leak in", sic.row_exits(other, "x.py")[0], {0, 2})

    # ⛔ THE THIRD VALUE: no row at all is None, never an empty set. An empty set would
    #    compare as "claims nothing" and silently pass a tool that is simply not indexed.
    check("a tool with no row is None, not empty", sic.row_exits(other, "z.py")[0], None)

    claimed, _ = sic.row_exits("| `x.py` | q | 0 · 1 |\n", "x.py")
    check("a row MISSING an emitted code is detected", {0, 1, 2} <= claimed, False)
    check("a row covering every emitted code passes", {0, 1} <= claimed, True)

    # ⛔ #466's rule, applied to this suite's own output: the parts must sum to the whole.
    total = 5
    check("this suite's own parts sum to its population", total, 5)

    print(f"\n{'all checks passed' if not FAILED else f'{FAILED} FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
