#!/usr/bin/env python3
r"""Pins the echoed-`run:`-block stripper, and the order that cannot be reversed.

⛔ The defect: `grep -c FAILED` returned 4 on a job whose conclusion was SUCCESS. All four
hits were the echoed script, which declares `FAILED_FILES`. Real output: zero.

★ The order is the whole point. The cyan-bold escape is the ONLY thing separating the echoed
block from real output — the words are identical. Strip ANSI first and the discriminator is
gone irrecoverably. The test below proves that by doing it and watching the tool refuse.

⚠ And the escape is not what a reader expects. Measured on a real 153 KB log from
`gh run view --log`: **0** real `\x1b` bytes, **218** literal `^[` pairs. A reader stripping
`\x1b\[[0-9;]*m` removes nothing and believes the log is clean.

Run: python3 tools/test_ci_log_clean.py
"""
import importlib.util
import os
import re
import subprocess
import sys

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE, and the dangerous
# class is the COMMON one: Python invalidates a .pyc on mtime + SIZE, so a
# SIZE-PRESERVING mutation (==/!=, a flag flip, a token swap) applied in the same
# second leaves both unchanged and the cache is served. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

_here = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(_here, "ci-log-clean.py")
_spec = importlib.util.spec_from_file_location("clc", TOOL)
clc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clc)

# Shaped like the real thing: gh prefixes job/step/timestamp, and renders ESC as `^[`.
P = "job\tstep\t2026-08-20T05:09:51.7Z "
LOG = "\n".join([
    P + "##[group]Run FAILED_FILES=$(grep -c FAILED out.txt)",
    P + "^[[36;1mFAILED_FILES=$(grep -c FAILED out.txt)^[[0m",
    P + '^[[36;1mecho "FAILED count: $FAILED_FILES"^[[0m',
    P + "shell: /usr/bin/bash --noprofile --norc -e -o pipefail {0}",
    P + "##[endgroup]",
    P + "FAILED count: 0",
    P + "^[[32mall tests passed^[[0m",
])


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0

    print("★ the defect — counting FAILED before and after:")
    # ⚠ 7, not 3 — `FAILED_FILES` contains the token too, and my first expectation
    # here was simply wrong arithmetic. It failed loudly; had it happened to match,
    # the assertion would have been vacuous and I would not have known.
    f += not check("raw log contains FAILED 7x", LOG.count("FAILED"), 7)
    out, stats = clc.clean(LOG)
    body = "\n".join(out)
    f += not check("cleaned log contains it once (the real output line)",
                   body.count("FAILED"), 1)
    f += not check("and that line is the command's output", "FAILED count: 0" in body, True)

    print("ANSI is stripped from what survives, both forms:")
    f += not check("no literal ^[ left", "^[" in body, False)
    f += not check("no real ESC left", "\x1b" in body, False)
    f += not check("the surviving text is intact", "all tests passed" in body, True)

    print("★ THE ORDER — strip ANSI first and the tool must REFUSE, not guess:")
    pre_stripped = re.sub(r"(?:\x1b|\^\[)\[[0-9;]*m", "", LOG)
    # The envelope survives an ANSI strip, so remove it too — this is the
    # `--log-failed` shape, where group markers are absent as well.
    pre_stripped = "\n".join(l for l in pre_stripped.split("\n") if "##[" not in l)
    try:
        clc.clean(pre_stripped)
        f += not check("refused", False, True)
    except ValueError as exc:
        f += not check("refused", True, True)
        f += not check("says why", "destroyed the marker" in str(exc), True)

    print("the envelope alone is enough when the marker is gone but groups remain:")
    envelope_only = re.sub(r"(?:\x1b|\^\[)\[[0-9;]*m", "", LOG)
    out2, _ = clc.clean(envelope_only)
    f += not check("script still dropped", "\n".join(out2).count("FAILED"), 1)

    print("empty input is VOID, never a clean log:")
    try:
        clc.clean("   \n  \n")
        f += not check("refused", False, True)
    except ValueError:
        f += not check("refused", True, True)

    print("exit codes, over stdin:")
    p = subprocess.run([sys.executable, TOOL], input=LOG, capture_output=True, text=True)
    f += not check("clean exits 0", p.returncode, 0)
    p = subprocess.run([sys.executable, TOOL], input="nothing here\n",
                       capture_output=True, text=True)
    f += not check("no discriminator exits 2", p.returncode, 2)
    f += not check("and emits nothing on stdout", p.stdout, "")

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
