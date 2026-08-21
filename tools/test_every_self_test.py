#!/usr/bin/env python3
"""Gated caller for EVERY instrument in tools/ that exposes `--self-test`.

⛔ WHY ONE FILE AND NOT NINETEEN. Criterion 4 as amended (#381) requires a control to be *"shown to
FAIL on real data — BY A CALLER THAT STILL RUNS IT."* ⇒ Measured 2026-08-21 by `gated-caller.py`:
of 25 instruments carrying a `--self-test`, **4 had a caller and 17 were REACHED** — their suites
import them and never pass the flag. Nineteen near-identical wrapper files would fix today's list
and leave the NEXT instrument uncovered, because someone has to remember. ⇒ This DISCOVERS the
population instead of enumerating it: a new instrument with a `--self-test` is gated the moment it
lands, with nobody remembering anything.

★ THAT IS ALSO ITS COST, AND IT IS DELIBERATE. A new instrument whose self-test FAILS reds the gate
immediately. That is the intended behaviour — a control that cannot red the board is the defect
#372 was filed about — but it is a policy change and it is stated here rather than discovered.

⛔ IT DOES NOT RE-IMPLEMENT ANY CONTROL. It invokes each instrument's own `--self-test` and
classifies the exit code, per `scripts/exit-code-gate.sh`'s contract:

    0            every reachable control passed          -> counted PASS
    3            a control FAILED                        -> a FINDING; this suite exits 1
    anything     crash, bad flag, no interpreter         -> ESTABLISHED NOTHING; exits 2 if alone

⚠ The third is not tidiness. `python3 <missing>` exits 2, argparse exits 2, and this repository's
convention uses 2 for a refused verdict (#58). Folding "could not run" into "failed" sends a reader
hunting a defect that may not exist.

⚠ HERMETIC BY MEASUREMENT, NOT BY ASSERTION. Every instrument below was run 2026-08-21 with a
failing `gh` and a failing `git ls-remote` first on PATH — a runner proxy — and all 19 then-REACHED
instruments exited 0 both ways. ⛔ An instrument that is NOT safe in that state must not be gated
here; it would ship the born-red guard `.github/workflows/tools.yml` calls load-bearing in its own
hermetic/fleet split. If one appears, this suite is where it will show, as a FINDING, with its name.

⚠ WHAT THIS DOES NOT ESTABLISH: that any invoked self-test is a GOOD control. It says the flag was
passed and the tool did not report failure. Whether the control could ever fail is
`population-leg.py`'s and `probe-validity.py`'s question, not this one.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ME = os.path.basename(__file__)
# ⛔ NAMED, never silently skipped — an invisible population narrowing is the defect
# check-tools-index.py exists against. gated-caller.py spawns suites; running it from inside a
# suite it would then spawn terminates only by timeout.
SKIP = {"gated-caller.py"}


def exposes_self_test(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return False
    return '"--self-test"' in src or "'--self-test'" in src


def main():
    names = sorted(
        n for n in os.listdir(HERE)
        if n.endswith(".py") and not n.startswith("test_") and n != ME and n not in SKIP
        and exposes_self_test(os.path.join(HERE, n))
    )
    if not names:
        # ⛔ NOT a pass. An empty population means the discovery broke, or the directory moved.
        print("  VOID  no instrument in tools/ exposes --self-test — established nothing.")
        print("        ⛔ This is NOT 'every control passed'.")
        return 2

    failed, void, passed = [], [], []
    for n in names:
        r = subprocess.run([sys.executable, os.path.join(HERE, n), "--self-test"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            passed.append(n)
            print(f"  ok    {n}")
        elif r.returncode == 3:
            failed.append(n)
            print(f"  ⛔ FAIL  {n} — its --self-test reported a failed control (exit 3)")
            for line in (r.stdout or "").splitlines():
                if "FAIL" in line:
                    print(f"           {line.strip()[:150]}")
        else:
            void.append(n)
            print(f"  ⚠ VOID  {n} — exited {r.returncode}, which it does not document."
                  f" ⛔ NOT 'the controls failed'.")
            tail = [l for l in (r.stderr or "").splitlines() if l.strip()]
            if tail:
                print(f"           {tail[-1][:150]}")

    print()
    print(f"  {len(passed)} passed · {len(failed)} FAILED · {len(void)} established nothing"
          f"  ({len(names)} instruments discovered)")
    print("  note  the population is DISCOVERED, not listed — a new instrument exposing"
          " --self-test is gated the moment it lands, with nobody remembering to add it.")
    print("  note  a PASS means the flag was passed and nothing reported failure. It does NOT"
          " mean the control could ever fail — that is population-leg.py's question.")
    if failed:
        return 1
    if void:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
