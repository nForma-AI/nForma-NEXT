#!/usr/bin/env python3
"""Pins that unfetched heads are UNKNOWN, and that overlap is not compatibility.

⛔ The defect this suite exists for: the first run of `pr-stack.py` could not
resolve 2 of 4 PR heads, skipped them, and printed a conflict count derived from
the half it could see. **A smaller conflict count looks like better news**, so a
reader with no reason to doubt it takes the reassuring number.

★ The git fixtures are REAL repositories, not stubs. `merge-tree`'s behaviour is
the thing under test, and a stub would test the stub.

Run: python3 tools/test_pr_stack.py
"""
import os, subprocess, sys, tempfile, types

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name)
    mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


ps = load(os.path.join(_here, "pr-stack.py"), "ps")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def git(d, *a):
    return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)


with tempfile.TemporaryDirectory() as d:
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.email", "t@t"); git(d, "config", "user.name", "t")
    # ⚠ 40 lines, not 3. A three-line file puts every edit inside every other edit's
    # context window, so "different lines" and "the same line" both conflict — the
    # fixture would have tested its own size. Found by this suite failing on it.
    open(os.path.join(d, "shared.txt"), "w").write("".join(f"line{i}\n" for i in range(40)))
    open(os.path.join(d, "solo.txt"), "w").write("x\n")
    git(d, "add", "-A"); git(d, "commit", "-qm", "base")

    def branch(name, edits):
        git(d, "checkout", "-q", "-B", name, "main")
        for f, text in edits.items():
            open(os.path.join(d, f), "w").write(text)
        git(d, "add", "-A"); git(d, "commit", "-qm", name)

    # two branches editing the SAME line of the same file
    def lines(**edits):
        out = [f"line{i}\n" for i in range(40)]
        for k, v in edits.items():
            out[int(k[1:])] = v + "\n"
        return "".join(out)
    branch("alpha", {"shared.txt": lines(n20="ALPHA")})
    branch("beta",  {"shared.txt": lines(n20="BETA")})
    # a branch editing a DIFFERENT file entirely
    branch("gamma", {"solo.txt": "y\n"})
    # a branch editing a DIFFERENT line of the SAME file — overlap, no conflict
    branch("delta", {"shared.txt": lines(n2="DELTA")})   # 18 lines away from alpha
    git(d, "checkout", "-q", "main")

    cwd = os.getcwd()
    os.chdir(d)
    try:
        kind, files = ps.relation("alpha", "beta")
        check("same line of the same file is a CONFLICT", kind, "CONFLICTS")
        check("...and the file is named", files, ["shared.txt"])

        check("disjoint files: no textual conflict", ps.relation("alpha", "gamma")[0], None)

        # ⛔ THE DANGEROUS CASE the tool must not call 'independent'
        check("different lines of the SAME file: no conflict",
              ps.relation("alpha", "delta")[0], None)
        check("...but the file sets OVERLAP, which is the whole point of that verdict",
              bool(ps.files_of("alpha", "main") & ps.files_of("delta", "main")), True)
        check("...whereas a genuinely disjoint pair does not overlap",
              bool(ps.files_of("alpha", "main") & ps.files_of("gamma", "main")), False)

        check("files_of reads the merge-base diff, not two dots",
              ps.files_of("alpha", "main"), {"shared.txt"})
    finally:
        os.chdir(cwd)

# ⛔ a failed query is not an empty board
check("a repo that cannot be queried is None, never []",
      ps.open_prs("nForma-AI/this-repo-does-not-exist-xyzzy"), None)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
