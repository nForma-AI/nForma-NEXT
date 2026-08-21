#!/usr/bin/env python3
"""Hermetic suite for tools/architect-sweeps/*.py. No git, no network, no fleet.

⛔ WHY IT LIVES HERE AND NOT BESIDE ITS SUBJECTS. The tools/ gate globs `tools/test_*.py`
and does not recurse, so a suite inside architect-sweeps/ would never be reached. ⇒ I
first concluded that made those tools uncallable without DEVOPS changing the subdirectory
contract. THAT WAS WRONG, by five minutes: only the CALLER must be reachable. A test at
this level can import a tool from the subdirectory, and nothing about the contract moves.

⚠ These two tools are the last of four I shipped in one session with no caller — the
population #372 counted, which I added to three times while ruling on it.
"""
import importlib.util, os, sys

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_here, "architect-sweeps", fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


pa = _load("prior_art", "prior-art.py")
kn = _load("known_negative", "known-negative.py")

FAILED = 0


def check(name, got, want):
    global FAILED
    if got != want:
        print(f"  FAIL  {name}: got {got!r}, want {want!r}")
        FAILED += 1
    else:
        print(f"  PASS  {name}: got {got!r}, want {want!r}")


def main():
    print("NFORMA-RUN test_architect_sweeps", file=sys.stderr)
    import json

    rows = json.dumps([{"number": 7, "title": "Widen the noun", "body": "",
                        "files": [{"path": "goals/README.md"}]}])

    # --- prior-art: the VOID paths are the whole point of the tool
    check("prior-art: a title hit is found", pa._scan(0, rows, "widen", "PR")[1] != [], True)
    check("prior-art: a term in neither is not found", pa._scan(0, rows, "zzz", "PR")[1], [])
    # ⛔ a failed channel must be VOID, never "no hits" — "found nothing" vs "there was nothing"
    check("prior-art: rc!=0 is VOID", pa._scan(2, rows, "widen", "PR")[0], False)
    check("prior-art: empty stdout is VOID", pa._scan(0, "", "widen", "PR")[0], False)
    check("prior-art: unparseable stdout is VOID", pa._scan(0, "nope", "widen", "PR")[0], False)
    # ⛔ the positive term must come FROM the population, so a row with no usable word is VOID
    check("prior-art: no drawable positive is None", pa._first_word(0, json.dumps([{"title": "a b"}])), None)

    # --- known-negative: mutate the ANALYSER, never the dispatch
    src = ("def analyse(n):\n    if n == 3:\n        return 'HIT'\n    return 'MISS'\n"
           "def main():\n    if len('x') == 1:\n        return 0\n")
    sites = kn.Sites(); import ast; sites.visit(ast.parse(src))
    fns = {f for _, _, _, f in sites.sites}
    check("known-negative: main() is NOT a mutation site", "main" in fns, False)
    check("known-negative: the analyser IS a mutation site", "analyse" in fns, True)
    muts = list(kn.mutants(src, 5))
    check("known-negative: the comparison is inverted", "n != 3" in (muts[0][1] if muts else ""), True)

    # --- known-negative: #466's accounting, and BOTH directions by execution.
    # ⛔ The assertion cannot fire on today's control flow -- every pair appends exactly one row --
    # so it was split into account() precisely so this caller can reach the failing state. An
    # invariant no test can reach is decoration, and asserting it inline was the first draft's bug.
    import io as _io
    buf = _io.StringIO()
    check("known-negative: a sound partition returns 0",
          kn.account(4, 3, 1, 2, out=buf), 0)
    check("known-negative: it prints the subset OFF the bucket line",
          "a SUBSET, not a third bucket" in buf.getvalue(), True)
    buf2 = _io.StringIO()
    check("known-negative: buckets that do NOT sum REFUSE with 2",
          kn.account(9, 3, 1, 0, out=buf2), 2)
    check("known-negative: and the refusal says so, not 'no finding'",
          "VOID" in buf2.getvalue() and "established nothing" in buf2.getvalue().lower(), True)

    print(f"\n{'all checks passed' if not FAILED else f'{FAILED} FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
