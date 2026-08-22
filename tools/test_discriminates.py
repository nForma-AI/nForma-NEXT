#!/usr/bin/env python3
"""Pins discriminates.py against its own docstring, including the half it was missing.

Written from the DOCSTRING, not from the code — a test derived from the implementation
cannot disagree with it, which is how two other tools in this directory carried a comment
asserting a restriction the code never enforced.

The claims under test:
  - it never reports "same": only DIFFER or NON-DISCRIMINATING
  - exit 0 discriminated · 2 non-discriminating · 3 control failed · 4 a state is unstable
  - a reading is (status, stdout), so equal stdout with a different status is a difference
  - the control runs BEFORE the comparison and refuses when it cannot show a difference

⛔ The missing half, measured on the shipped tool:

    discriminates.py --a 'date +%N' --b 'date +%N'   ->  ✅ DISCRIMINATED, exit 0

One state against itself with a noise check. It had a known-DIFFERENT control and no
known-SAME one, so it could refuse a false "same" and not a false "differ".

Run: python3 tools/test_discriminates.py
"""
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discriminates.py")


def run(*args):
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0

    print("★ the missing control — one state, a noisy check, must NOT read as a difference:")
    rc, out = run("--a", "date +%N", "--b", "date +%N")
    f += not check("exit", rc, 4)
    f += not check("says UNSTABLE", "UNSTABLE" in out, True)
    f += not check("does not claim discrimination", "DISCRIMINATED" in out, False)

    print("a real difference still discriminates:")
    rc, out = run("--a", "echo alpha", "--b", "echo beta")
    f += not check("exit", rc, 0)
    f += not check("says DISCRIMINATED", "DISCRIMINATED" in out, True)

    print("identical readings are refused, and never called 'same':")
    rc, out = run("--a", "echo same", "--b", "echo same")
    f += not check("exit", rc, 2)
    f += not check("says NON-DISCRIMINATING", "NON-DISCRIMINATING" in out, True)

    print("status is part of the reading — equal stdout, different exit:")
    rc, out = run("--a", "true", "--b", "false")
    f += not check("exit", rc, 0)

    print("a known-different control that does NOT differ fails the harness:")
    rc, out = run("--control-a", "echo x", "--control-b", "echo x",
                  "--a", "echo p", "--b", "echo q")
    f += not check("exit", rc, 3)
    f += not check("says CONTROL FAILED", "CONTROL FAILED" in out, True)

    print("★ a control half that is itself noise cannot prove anything:")
    # Its 'difference' may be the noise. Caught before the real comparison runs.
    rc, out = run("--control-a", "date +%N", "--control-b", "echo x",
                  "--a", "echo p", "--b", "echo q")
    f += not check("exit", rc, 3)
    f += not check("says CONTROL UNUSABLE", "CONTROL UNUSABLE" in out, True)

    print("a good control lets a real comparison through:")
    rc, out = run("--control-a", "echo 1", "--control-b", "echo 2",
                  "--a", "echo p", "--b", "echo q")
    f += not check("exit", rc, 0)
    f += not check("states what the control did NOT establish", "does NOT establish" in out, True)

    print("half a control pair is a usage error, not a silent skip:")
    rc, out = run("--control-a", "echo 1", "--a", "echo p", "--b", "echo q")
    f += not check("nonzero", rc != 0, True)
    f += not check("did not silently run", "DISCRIMINATED" in out, False)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
