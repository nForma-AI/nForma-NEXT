#!/usr/bin/env python3
"""Pins the two failures apart, because they have opposite remedies.

⛔ An ORPHAN is fixed by ADDING an index line. OVERSIZE is made WORSE by adding one. A tool
reporting them as one number sends its reader to the wrong remedy half the time — which is
the two-states-one-output collapse this fleet spent a night cataloguing, and which
TEAMLEAD found five instances of in its own toolchain (#1279).

Measured on this machine when the tool was written: 348 files, 232 indexed, 115 orphans,
index 42.5 KB against a recalled ~25 KB load budget. Both failures live, at once.

Run: python3 tools/test_memory_index_check.py
"""
import importlib.util, os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "mic", os.path.join(_HERE, "memory-index-check.py"))
mic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mic)


def check(name, got, want):
    ok = got == want
    print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
    return ok


def main():
    f = 0
    idx = "- [a](a.md) — x\n- [b](b.md) — y\n"

    r = mic.analyse(idx, ["a.md", "b.md", "c.md", "MEMORY.md"], 10_000)
    f += not check("an unlinked file is an orphan", r["orphans"], ["c.md"])
    f += not check("MEMORY.md is not its own orphan", "MEMORY.md" in r["orphans"], False)
    f += not check("linked counts only files that exist", r["linked"], 2)

    # ⛔ The other direction: an index line whose file is gone. Not an orphan — the opposite.
    # Left uncounted it makes the index claim coverage it does not have.
    r2 = mic.analyse(idx + "- [gone](gone.md)\n", ["a.md", "b.md"], 10_000)
    f += not check("a link to an absent file is DANGLING", r2["dangling"], ["gone.md"])
    f += not check("dangling is not counted as coverage", r2["linked"], 2)
    f += not check("dangling is not an orphan", r2["orphans"], [])

    # ⚠ Oversize must be independent of coverage, or the reader cannot tell which to fix.
    r3 = mic.analyse("x" * 30_000, ["a.md"], 25 * 1024)
    f += not check("oversize detected", r3["oversize"], True)
    f += not check("and reported separately from orphans", r3["orphans"], ["a.md"])
    r4 = mic.analyse(idx, ["a.md", "b.md"], 10)
    f += not check("a COVERED index can still be oversize",
                   (r4["orphans"], r4["oversize"]), ([], True))

    f += not check("a fully covered, small index is clean",
                   (lambda r: (r["orphans"], r["dangling"], r["oversize"]))(
                       mic.analyse(idx, ["a.md", "b.md"], 10_000)), ([], [], False))
    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
