#!/usr/bin/env python3
"""Pins branch-census's four states, and the squash collapse it exists to break.

⛔ CRITERION 4 IS THE POINT OF THIS FILE. A classifier that never mis-classifies
anything in test has not been shown able to fail. `test_squash_would_read_as_stranded`
asserts the DEFECT explicitly: it re-runs the ancestry-only rule the tool replaced and
requires that rule to get the answer WRONG on the same fixture. If that assertion ever
passes trivially — because ancestry alone became sufficient — the tool's reason for
existing has gone and this test should fail loudly rather than stay green.

Hermetic: builds its own repository with `git init` in a temp dir and writes
refs/remotes/origin/* with update-ref. No network, no fixture checked in, so it
carries no `# SUITE-DEPENDS:` and the CI glob gates it.
"""
import os, subprocess, sys, tempfile, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bc", os.path.join(HERE, "branch-census.py"))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)

FAILED = 0


def check(label, got, want):
    global FAILED
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
    if not ok:
        FAILED += 1


def g(repo, *a):
    p = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"git {' '.join(a)} -> {p.stderr.strip()}")
    return p.stdout.strip()


def write(repo, name, body):
    with open(os.path.join(repo, name), "w") as f:
        f.write(body)
    g(repo, "add", name)
    g(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", name + body[:8])
    return g(repo, "rev-parse", "HEAD")


def build(repo):
    """A repo with one branch in each of the four states."""
    g(repo, "init", "-q", "-b", "main")
    root = write(repo, "root.txt", "root\n")

    # MERGED: an ancestor of main
    g(repo, "checkout", "-q", "-b", "merged-branch")
    merged = write(repo, "m.txt", "m\n")
    g(repo, "checkout", "-q", "main")
    g(repo, "merge", "-q", "--ff-only", "merged-branch")

    # SQUASH-MERGED: two commits on a branch, landed on main as ONE commit with the
    # same cumulative diff. `git cherry` cannot see this — neither commit matches alone.
    g(repo, "checkout", "-q", "-b", "squashed-branch", root)
    write(repo, "s.txt", "one\n")
    with open(os.path.join(repo, "s.txt"), "w") as f:
        f.write("one\ntwo\n")
    g(repo, "add", "s.txt")
    g(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "s2")
    squashed_tip = g(repo, "rev-parse", "HEAD")
    g(repo, "checkout", "-q", "main")
    g(repo, "checkout", "-q", "squashed-branch", "--", "s.txt")
    g(repo, "add", "s.txt")
    g(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "squash of s")

    # unmerged pair: one will be checked out (LIVE), one will not (STRANDED)
    for name, body in (("live-branch", "L\n"), ("stranded-branch", "S\n")):
        g(repo, "checkout", "-q", "-b", name, root)
        write(repo, name + ".txt", body)
    g(repo, "checkout", "-q", "main")

    for b in ("merged-branch", "squashed-branch", "live-branch", "stranded-branch"):
        g(repo, "update-ref", f"refs/remotes/origin/{b}", g(repo, "rev-parse", b))
    g(repo, "update-ref", "refs/remotes/origin/main", g(repo, "rev-parse", "main"))
    return squashed_tip


def main():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "r"); os.makedirs(repo)
        squashed_tip = build(repo)
        wt = os.path.join(tmp, "wt")
        g(repo, "worktree", "add", "-q", wt, "live-branch")

        rows, why = bc.census(repo)
        state = {b: s for b, s, _ in (rows or [])}
        print("four states, one fixture:")
        check("merged-branch", state.get("merged-branch"), bc.MERGED)
        check("squashed-branch", state.get("squashed-branch"), bc.SQUASH)
        check("live-branch", state.get("live-branch"), bc.LIVE)
        check("stranded-branch", state.get("stranded-branch"), bc.STRANDED)

        print("\n★ criterion 4 — the rule this replaced must get it WRONG here:")
        anc = subprocess.run(
            ["git", "-C", repo, "merge-base", "--is-ancestor",
             "origin/squashed-branch", "origin/main"], capture_output=True).returncode == 0
        check("ancestry alone calls the squashed branch merged", anc, False)
        cherry = subprocess.run(
            ["git", "-C", repo, "cherry", "origin/main", "origin/squashed-branch"],
            capture_output=True, text=True).stdout
        check("git cherry finds an unmatched commit (so it too says unmerged)",
              cherry.strip().startswith("+"), True)

        print("\n★ --touches: two-dot and three-dot must DISAGREE on the fixture,")
        print("  or the flag is guarding a distinction this repo cannot exhibit:")
        # main changes shared.txt AFTER stranded-branch was cut. The branch never
        # touches it; the endpoint form says it does, because main moved.
        g(repo, "checkout", "-q", "main")
        write(repo, "shared.txt", "main-only change\n")
        g(repo, "update-ref", "refs/remotes/origin/main", g(repo, "rev-parse", "main"))
        names = bc.branch_names(repo, "origin", "main")
        three = bc.touching(repo, "origin", "origin/main", "shared.txt", names)
        two = [b for b in names
               if bc.git(repo, "diff", "--name-only",
                         f"origin/main..origin/{b}", "--", "shared.txt").strip()]
        check("merge-base form: no branch changed shared.txt", three, [])
        check("endpoint form names branches anyway", len(two) > 0, True)
        check("the two forms disagree — that IS the defect", two != three, True)

        print("\nexit contract:")
        empty = os.path.join(tmp, "e"); os.makedirs(empty)
        g(empty, "init", "-q", "-b", "main")
        write(empty, "a.txt", "a\n")
        g(empty, "update-ref", "refs/remotes/origin/main", g(empty, "rev-parse", "main"))
        rows2, why2 = bc.census(empty)
        check("no branches besides main -> ESTABLISHED NOTHING", rows2 is None, True)

        one = os.path.join(tmp, "o"); os.makedirs(one)
        g(one, "init", "-q", "-b", "main")
        r0 = write(one, "a.txt", "a\n")
        g(one, "checkout", "-q", "-b", "x1", r0); write(one, "x1.txt", "1\n")
        g(one, "checkout", "-q", "-b", "x2", r0); write(one, "x2.txt", "2\n")
        g(one, "checkout", "-q", "main")
        for b in ("x1", "x2"):
            g(one, "update-ref", f"refs/remotes/origin/{b}", g(one, "rev-parse", b))
        g(one, "update-ref", "refs/remotes/origin/main", g(one, "rev-parse", "main"))
        rows3, _ = bc.census(one)
        check("all branches in one bucket is detectable",
              len({s for _, s, _ in rows3}), 1)

    print(f"\n{FAILED} FAILED" if FAILED else "\nall PASS")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
