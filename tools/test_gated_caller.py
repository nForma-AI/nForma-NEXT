#!/usr/bin/env python3
"""Gated caller for `tools/gated-caller.py --self-test`. answers which instruments' --self-test CI actually invokes.

⛔ WHY THIS FILE EXISTS AT ALL, and it is criterion 4 as amended on 2026-08-21 (#381):

    "shown to FAIL on real data — BY A CALLER THAT STILL RUNS IT. A demonstration that
     happened once and cannot happen again is a SCREENSHOT. Name the caller and when it
     last ran."

★ `gated-caller.py`'s controls lived behind `--self-test`, and the gate runs
`tools/test_*.py` and `scripts/*.py` — never a `--self-test`. ⇒ Measured 2026-08-21 on
`origin/main`: of 25 instruments carrying a self-test, **13 had no gated caller naming
the tool and the flag.** Those controls were screenshots. THIS FILE IS THE CALLER, and
`.github/workflows/tools.yml`'s `hermetic suites (gating)` step is when it last ran.

⛔ IT DOES NOT RE-IMPLEMENT THE CONTROLS. Copying them here would produce two populations
that drift, and the second copy is the one nobody re-reads. It invokes the real thing and
CLASSIFIES ITS EXIT CODE, which is the only part the gate could not already see.

⚠ THE THREE-WAY SPLIT IS THE POINT, and it is `scripts/exit-code-gate.sh`'s contract:

    self-test 0     every reachable control passed            -> 0  pass
    self-test 3     a control FAILED                          -> 1  a finding
    anything else   crash, bad flag, missing interpreter      -> 2  ESTABLISHED NOTHING

⛔ The third is not tidiness. `python3 <missing-file>` exits 2, argparse exits 2, and this
repository's own convention uses 2 for a refused verdict (#58) — so a wrapper that folded
"could not run" into "failed" would send a reader hunting a defect that may not exist.

⚠ HERMETIC BY MEASUREMENT, NOT BY ASSERTION. Verified 2026-08-21 with a failing `gh` and a
failing `git ls-remote` first on PATH: exit 0 both ways. Where a control needs the forge or
the network it now reports NOT ESTABLISHED and does not fail — fixing two born-red guards
this file's own preparation uncovered.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUBJECT = os.path.join(HERE, "gated-caller.py")


def main():
    if not os.path.isfile(SUBJECT):
        print(f"  VOID  subject missing: {SUBJECT} — established nothing")
        return 2
    r = subprocess.run([sys.executable, SUBJECT, "--self-test"], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.splitlines():
        print(f"  {line}")
    if r.returncode == 0:
        print("  ok    gated-caller --self-test: every reachable control passed")
        return 0
    if r.returncode == 3:
        print("  ⛔ gated-caller --self-test reported a FAILED control (exit 3)")
        return 1
    print(f"  VOID  gated-caller --self-test exited {r.returncode}, which it does not document"
          f" — established nothing. ⛔ NOT 'the controls failed'.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
