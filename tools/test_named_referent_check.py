#!/usr/bin/env python3
"""Pins the referent check against the two ways it was measurably wrong before shipping.

Why this file exists
--------------------
This tool went 126 candidates -> 8 -> 1 on the same 1,559-file repository, and only the
last number is usable. Both narrowings were forced by hand-verification, not by reading:

  126  every identifier-shaped token in a binding sentence. `GIT_COMMIT_SHA`,
       `cpu_per_vcpu_second`, pricing keys — config names mentioned in prose.
    8  code-marked only (``x``, `x`, x()). Then hand-checking found **7 of 8 false**:
       `allow_degraded_mesh`, `ci_only`, `AKASH_CONSOLE_2`, `provisioning_type` all
       exist — as STRING LITERALS and kwargs, which no `ast.Name` node carries. The
       tool was calling real config keys phantoms, with 4, 4, 12 and 2 occurrences
       respectively in the tree.
    1  the one true positive.

⛔ A guard that calls a config key a phantom is worse than no guard: it teaches its reader
to dismiss the output, and the true positive dies with the seven. Both narrowings are
pinned below, because either could regress silently and the symptom is a longer list that
still contains the right answer.

Run: python3 tools/test_named_referent_check.py
"""
import importlib.util
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "nrc", os.path.join(_HERE, "named-referent-check.py"))
nrc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nrc)


def check(name, got, want):
    ok = got == want
    print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
    return ok


def hits(files, target=None):
    """Write {name: source} into a temp tree, return the names flagged in `target`."""
    with tempfile.TemporaryDirectory() as td:
        for fn, src in files.items():
            open(os.path.join(td, fn), "w").write(src)
        universe, _f, _u = nrc.build_universe(td)
        t = target or next(iter(files))
        return [n for n, _line in nrc.scan_file(os.path.join(td, t), universe)]


def main():
    f = 0

    # ── the founding incident, structurally ──────────────────────────────────────
    f += not check("undefined referent in a MUST docstring fires",
                   hits({"a.py": '"""Reads must iterate ``iter_console_backends``."""\n'}),
                   ["iter_console_backends"])

    # ── narrowing 1: code-marked only. Was 126 candidates without this. ──────────
    f += not check("bare config key in a MUST sentence is NOT a referent claim",
                   hits({"a.py": '"""Each manifest must contain SENTRY_DSN env var."""\n'}),
                   [])
    f += not check("backticked call form fires",
                   hits({"a.py": "# Writers must call `flush_pending()` first.\n"}),
                   ["flush_pending"])

    # ── narrowing 2: string literals and kwargs ARE referents. Was 7/8 false. ────
    f += not check("string-literal referent is not a phantom",
                   hits({"a.py": '"""``allow_degraded_mesh`` must be read."""\n',
                         "b.py": 'CFG = {"allow_degraded_mesh": True}\n'}, "a.py"),
                   [])
    f += not check("kwarg-name referent is not a phantom",
                   hits({"a.py": '"""The helper must pass ``filter_hostname``."""\n',
                         "b.py": "def q(**kw):\n    return kw\n\nq(filter_hostname='x')\n"},
                        "a.py"),
                   [])
    f += not check("cross-module definition is not a phantom",
                   hits({"a.py": '"""Callers must use ``safe_read_all``."""\n',
                         "c.py": "def safe_read_all():\n    return []\n"}, "a.py"),
                   [])

    # ── a sentence with no requirement is not a claim ────────────────────────────
    f += not check("descriptive prose does not fire",
                   hits({"a.py": '"""We could add ``some_missing_helper`` later."""\n'}),
                   [])

    # ── population: tracked files, and an empty tree establishes NOTHING ─────────
    with tempfile.TemporaryDirectory() as td:
        _u, files, _ = nrc.build_universe(td)
        f += not check("empty tree yields no files (caller must exit 2)", files, [])

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
