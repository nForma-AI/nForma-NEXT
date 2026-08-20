#!/usr/bin/env python3
"""Pins `match_step`'s verdict vocabulary — and the slash rule that swallowed absolute paths.

⛔ Why this file exists at all. `bootstrap-audit.py` was the ONE tool in this directory I
audited and could not fault. Its row in `dx-measurement-register` says so, and states the
falsifier that seemed likeliest to fire:

    "a tool with a real control suite that still carried a defect, **or a defect I missed in
     the one I passed**"

⇒ It fired, within the hour. The step classifier read `cmd.lstrip().startswith("/")` as
"names a built-in slash command", which is true of `/rename DEV2` and false of every
absolute path. Measured 2026-08-20:

    /rename DEV2                              -> UNEXECUTABLE   correct
    /usr/bin/git rev-parse --abbrev-ref HEAD  -> UNEXECUTABLE   ⛔ WRONG
    /opt/homebrew/bin/python3 x.py            -> UNEXECUTABLE   ⛔ WRONG

★ And the verdict is not a shrug. `UNEXECUTABLE` asserts *"no execution record CAN exist"* —
the strongest claim in this file's vocabulary — about a step that both can run and, in the
first case, **did: a matching call was in the very list passed to the function.** The evidence
sat one argument away and the rule never looked.

A slash command is a single bare word. A path has a separator inside it. That is the whole
discriminator, and it is what the audit of the other twelve tools would have found here: a
restriction asserted in prose (`names a built-in`) that the code implements as something
broader (`starts with a slash`).

Run: python3 tools/test_bootstrap_audit.py
"""
import importlib.util
import os
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
TOOL = os.path.join(_here, "bootstrap-audit.py")
_spec = importlib.util.spec_from_file_location("ba", TOOL)
ba = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ba)

# A call list containing a real execution of the absolute-path step.
CALLS = [("Bash", "/usr/bin/git rev-parse --abbrev-ref HEAD", False),
         ("Bash", "cat prompts/DX.md", False),
         ("Bash", "echo 'cat prompts/DEVOPS.md'", False)]


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0
    v = lambda c: ba.match_step(c, CALLS)[0]

    print("★ a slash command is a bare word — these are genuinely unreachable:")
    f += not check("/rename", v("/rename DEV2"), "UNEXECUTABLE")
    f += not check("/compact alone", v("/compact"), "UNEXECUTABLE")

    print("★ an ABSOLUTE PATH is not a slash command — and this one was executed:")
    f += not check("/usr/bin/git …", v("/usr/bin/git rev-parse --abbrev-ref HEAD"), "EXECUTED")
    print("  (a path with no matching call is UNDECIDED — honest, not 'cannot exist')")
    f += not check("/opt/homebrew/bin/python3 …", v("/opt/homebrew/bin/python3 x.py"),
                   "UNDECIDED")
    f += not check("a bare slash", v("/"), "UNDECIDED")
    f += not check("a path fragment", v("/x/y"), "UNDECIDED")

    print("the rest of the vocabulary still discriminates:")
    f += not check("a step genuinely run", v("cat prompts/DX.md"), "EXECUTED")
    f += not check("a step only echoed", v("cat prompts/DEVOPS.md"), "MENTIONED-ONLY")
    f += not check("a step absent from the window", v("terraform apply -auto-approve"),
                   "UNEXECUTED")
    print("  (a PARTIAL anchor match is UNDECIDED, never folded into either neighbour)")
    f += not check("partial anchors", v("cat prompts/DX.md --with-a-flag-nobody-ran"),
                   "UNDECIDED")

    print("the tool's own 28 controls still pass:")
    p = subprocess.run([sys.executable, TOOL, "--self-test"], capture_output=True, text=True,
                       cwd=os.path.dirname(_here))
    f += not check("exit", p.returncode, 0)
    f += not check("every control discriminated",
                   "every control discriminated" in (p.stdout + p.stderr), True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
