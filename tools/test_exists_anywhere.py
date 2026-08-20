#!/usr/bin/env python3
"""Pins the three-state answer, and the control that says why the tool is needed at all.

Why this file exists
--------------------
Four times in one session, by three agents: concluding about a repository from a single
ref. One reached publication as a finding and had to be retracted — a 161-line guard,
WITH ITS OWN TEST FILE, on an unmerged branch, reported as never having existed because
two agents each ran `git ls-files | grep`.

⛔ The load-bearing test here is the LAST one: `git ls-files` cannot separate a shipped
file from an unmerged one. If that ever becomes false, this tool is redundant and should
be deleted rather than maintained.

Run: python3 tools/test_exists_anywhere.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "ea", os.path.join(_HERE, "exists-anywhere.py"))
ea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ea)


def check(name, got, want):
    ok = got == want
    print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
    return ok


def build(td):
    def g(*a):
        subprocess.run(("git",) + a, cwd=td, capture_output=True, text=True)
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@t"); g("config", "user.name", "t")
    open(os.path.join(td, "shipped.py"), "w").write("x = 1\n")
    g("add", "-A"); g("commit", "-qm", "shipped")
    g("checkout", "-qb", "side")
    open(os.path.join(td, "unmerged_guard.py"), "w").write("y = 2\n")
    open(os.path.join(td, "test_unmerged_guard.py"), "w").write("z = 3\n")
    g("add", "-A"); g("commit", "-qm", "guard")
    g("checkout", "-q", "main")


def main():
    f = 0
    with tempfile.TemporaryDirectory() as td:
        build(td)

        # ── the three states ────────────────────────────────────────────────────
        f += not check("shipped file is in the object store",
                       bool(ea.object_hits("shipped.py", td)), True)
        f += not check("unmerged file is ALSO in the object store",
                       bool(ea.object_hits("unmerged_guard.py", td)), True)
        f += not check("a name never committed is not",
                       ea.object_hits("never_written.py", td), [])

        # ⚠ A substring must not silently widen the claim. `guard` matches the guard AND
        # its test file — the real incident had exactly this, and reporting one path when
        # two exist understates an unmerged instrument's footprint.
        f += not check("a substring finds every matching path",
                       len(ea.object_hits("unmerged_guard", td)), 2)

        # ── reachability is the discriminator, not presence ─────────────────────
        _o, on_main_shipped = ea.sh("git", "cat-file", "-e", "main:shipped.py", cwd=td)
        _o, on_main_guard = ea.sh("git", "cat-file", "-e", "main:unmerged_guard.py", cwd=td)
        f += not check("shipped is reachable from main", on_main_shipped, True)
        f += not check("the unmerged guard is NOT reachable from main", on_main_guard, False)

        # ⛔ THE CONTROL THAT JUSTIFIES THE TOOL. If `git ls-files` ever separates these,
        # delete this tool rather than maintain it.
        out, _ = ea.sh("git", "ls-files", cwd=td)
        listed = out.split()
        f += not check("git ls-files sees the shipped file", "shipped.py" in listed, True)
        f += not check("git ls-files is BLIND to the unmerged one",
                       "unmerged_guard.py" in listed, False)

        # ── a failed search is not an absence ───────────────────────────────────
        f += not check("object_hits on a non-repo returns None, not []",
                       ea.object_hits("x", tempfile.gettempdir()), None)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
