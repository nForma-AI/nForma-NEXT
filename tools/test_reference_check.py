#!/usr/bin/env python3
"""Pins the reference register's parser and the three states it must keep apart.

⛔ Why the register exists: a 249-line root-cause investigation of a failure this fleet spent
a night re-deriving had been on this machine since **2026-07-20**. The rule "check just-akash
first" existed, in a memory index, and nobody opened its `docs/`.

⚠ And search is not the remedy — measured: **304 repos**, **14,517 markdown files mention
"exec"**. So the register is curated, and this tool answers the one question a curated list
cannot answer about itself: has any of it moved?

★ Three states, and collapsing any two is the defect: **current**, **MOVED** (adopt-or-not is a
judgement), **MISSING** (established nothing — a repo not on this machine is not "unchanged").

Run: python3 tools/test_reference_check.py
"""

import importlib.util
import os
import shutil
import subprocess
import tempfile
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
TOOL = os.path.join(_here, "reference-check.py")
_spec = importlib.util.spec_from_file_location("rc", TOOL)
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

SHA = "f4f3e9db392ac526cf204ba9ec7a71dd6139d545"
ROW = f"| `just-akash` | `docs/x.md` | authoritative for things | `{SHA}` |"


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0

    print("the parser reads a well-formed row:")
    f += not check("one entry", rc.parse(ROW), [("just-akash", "docs/x.md", SHA)])

    print("★ and refuses rows that only LOOK like entries:")
    f += not check("header row", rc.parse("| repo | artifact | for | blob |"), [])
    f += not check("separator", rc.parse("| --- | --- | --- | --- |"), [])
    f += not check("a short sha is not a blob",
                   rc.parse("| `r` | `p` | x | `f4f3e9d` |"), [])
    f += not check("prose mentioning a sha", rc.parse(f"see {SHA} for details"), [])

    print("⛔ a register that parses to nothing is VOID, not clean:")
    # A table rename would otherwise read as "no references to adopt".
    p = subprocess.run([sys.executable, "-c",
                        f"import importlib.util,sys;s=importlib.util.spec_from_file_location('rc',{TOOL!r});"
                        f"m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                        f"m.REGISTER={os.devnull!r};sys.exit(m.main())"],
                       capture_output=True, text=True)
    f += not check("empty register exits 2", p.returncode, 2)

    print("MISSING is distinguished from unchanged:")
    got, why = rc.blob("definitely-not-a-repo-here", "x.md")
    f += not check("no sha", got, None)
    f += not check("says why", "not on this machine" in (why or ""), True)
    # ⛔ HERMETIC FROM HERE, and the reason is #280. These three legs used to resolve against
    # a `just-akash` checkout at ROOT/just-akash — ANOTHER ESTATE'S REPO, present on the
    # machine that wrote them and on no other. They had been red for 17 days behind a
    # `# SUITE-DEPENDS: ... network` marker that named the wrong cause: no amount of network
    # produces a sibling checkout, and the hardcoded blob sha was not an object in THIS repo
    # at all (`git cat-file -t f4f3e9db` -> "Not a valid object name").
    # ⇒ A register test must not require another estate to be checked out beside it. Build the
    # repo, compute the sha at test time, and the legs measure the SAME PROPERTY with nothing
    # borrowed.
    _tmp = tempfile.mkdtemp()
    _repo = os.path.join(_tmp, "sibling-repo")
    os.makedirs(os.path.join(_repo, "docs"))
    _doc = os.path.join(_repo, "docs", "x.md")
    with open(_doc, "w", encoding="utf-8") as fh:
        fh.write("authoritative for things\n")
    for _cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                 ["git", "-c", "user.email=t@t", "-c", "user.name=t",
                  "commit", "-q", "-m", "seed"]):
        subprocess.run(_cmd, cwd=_repo, capture_output=True)
    _real = subprocess.run(["git", "-C", _repo, "rev-parse", "HEAD:docs/x.md"],
                           capture_output=True, text=True).stdout.strip()
    _saved_root, rc.ROOT = rc.ROOT, _tmp

    got, why = rc.blob("sibling-repo", "no/such/path.md")
    f += not check("path absent -> no sha", got, None)
    # ⚠ THE LEG THIS REPAIRS. It asserts "not at HEAD" — a path missing from a repo that
    # EXISTS. Against an absent checkout the reason was "repo not on this machine", so the
    # test was failing on a DIFFERENT branch of blob() than the one it names.
    f += not check("says why", "not at HEAD" in (why or ""), True)

    print("★ a real entry resolves, and a wrong sha would read as MOVED:")
    got, why = rc.blob("sibling-repo", "docs/x.md")
    f += not check("resolves to a blob", bool(got) and len(got) == 40, True)
    # ⚠ Compared against a sha COMPUTED FROM THE REPO JUST BUILT, not a literal. A hardcoded
    # sha is a claim about someone else's disk; this is a claim about the object under test.
    f += not check("and it is the recorded one", got, _real)

    print("⛔ and a WRONG sha still reads as MOVED — the known-negative:")
    f += not check("a different sha is not this blob", got == "0" * 40, False)

    rc.ROOT = _saved_root
    shutil.rmtree(_tmp, ignore_errors=True)

    print("the register on disk parses to at least one entry:")
    f += not check("entries", len(rc.parse(open(rc.REGISTER).read())) >= 1, True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
