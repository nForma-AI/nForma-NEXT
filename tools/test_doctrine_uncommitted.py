#!/usr/bin/env python3
"""Pins that "the fleet reads what landed" and "I could not check" are two results.

⛔ The defect this exists for: CLAUDE.md loads from the WORKING COPY, so an
uncommitted edit is fleet doctrine the moment it is written. Measured 2026-08-21 —
44 lines of an OPEN PR's content were being read as doctrine by four agents, from a
checkout with an unresolved merge nobody had committed.

★ The clean result and the could-not-check result must never share an exit code:
a doctrine checker that says nothing when it read nothing is the same failure it
exists to detect, one level up.

Run: python3 tools/test_doctrine_uncommitted.py
"""
import contextlib, io, os, subprocess, sys, tempfile, types

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


du = load(os.path.join(_here, "doctrine-uncommitted.py"), "du")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)


def run(repo, *extra):
    """Drive main() and return (exit code, rendered output) — behaviour, not source text."""
    argv = sys.argv[:]
    sys.argv = ["doctrine-uncommitted.py", "--repo-path", repo, "--ref", "base", *extra]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = du.main()
    finally:
        sys.argv = argv
    return rc, buf.getvalue()


with tempfile.TemporaryDirectory() as tmp:
    # ── a repo whose "base" ref carries a known CLAUDE.md ──────────────────
    repo = os.path.join(tmp, "r"); os.makedirs(repo)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
    def write(text):
        with open(os.path.join(repo, "CLAUDE.md"), "w") as f:
            f.write(text)
    write("alpha\nbeta\ngamma\n")
    git(repo, "add", "CLAUDE.md"); git(repo, "commit", "-qm", "base")
    git(repo, "branch", "base")

    rc, out = run(repo)
    check("identical working copy and ref -> exit 0", rc, 0)
    check("...and it SAYS so rather than printing nothing",
          "what the fleet reads is what landed" in out, True)

    # ⛔ the core case: text being READ that no ref carries
    write("alpha\nbeta\ngamma\nDELTA-UNCOMMITTED\n")
    rc, out = run(repo)
    check("a working-only line is READ BUT NOT COMMITTED", rc, 1)
    check("...named in that direction", "READ BUT NOT COMMITTED" in out, True)
    check("...and quoted verbatim so the reader can recognise it",
          "DELTA-UNCOMMITTED" in out, True)
    check("...and NOT reported as the opposite direction",
          "COMMITTED BUT NOT READ" in out, False)

    # ⚠ the inverse: a checkout that HIDES landed doctrine
    write("alpha\ngamma\n")
    rc, out = run(repo)
    check("a missing committed line is COMMITTED BUT NOT READ", rc, 1)
    check("...named in that direction", "COMMITTED BUT NOT READ" in out, True)
    check("...and 'beta' is shown as the hidden line", "beta" in out, True)

    # a path absent from the ref entirely is the strongest form
    write("alpha\nbeta\ngamma\n")
    with open(os.path.join(repo, "AGENTS.md"), "w") as f:
        f.write("ENTIRELY-UNCOMMITTED-FILE\n")
    rc, out = run(repo)
    check("a file absent from the ref is wholly read-but-not-committed",
          "ENTIRELY-UNCOMMITTED-FILE" in out, True)
    os.remove(os.path.join(repo, "AGENTS.md"))

    # ── ⛔ THE THREE WAYS TO PRINT A CLEAN RESULT ARE THREE EXITS ──────────
    # A doctrine checker that says nothing when it READ nothing is the same
    # failure it exists to detect, one level up.
    rc, out = run(repo, "--path", "does-not-exist.md")
    check("⛔ no doctrine file present -> exit 2, NOT a clean 0", rc, 2)
    check("...and it says zero drift and zero files print the same result",
          "print the same clean result" in out, True)

    argv = sys.argv[:]
    sys.argv = ["x", "--repo-path", repo, "--ref", "no-such-ref"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = du.main()
    sys.argv = argv
    check("⛔ an unresolvable ref -> exit 2, not 'everything is uncommitted'", rc, 2)
    check("...and it blames the REF, not the files",
          "verdict about the REF" in buf.getvalue(), True)

    plain = os.path.join(tmp, "notarepo"); os.makedirs(plain)
    with open(os.path.join(plain, "CLAUDE.md"), "w") as f:
        f.write("x\n")
    rc, out = run(plain)
    check("⛔ not a git checkout -> exit 2", rc, 2)

    # ⛔ KNOWN-BAD CONTROL — without it every refusal check above would also pass
    # against a tool that ALWAYS exits 2. The healthy case must still be 0.
    write("alpha\nbeta\ngamma\n")
    check("KNOWN-BAD control: the healthy case still exits 0, so 2 means something",
          run(repo)[0], 0)

    # ── the checkout's own state is reported as the EXPLANATION ────────────
    open(os.path.join(repo, ".git", "MERGE_HEAD"), "w").write("deadbeef\n")
    rc, out = run(repo)
    check("an in-progress merge is surfaced, because it EXPLAINS the drift",
          "MERGE IN PROGRESS" in out, True)
    os.remove(os.path.join(repo, ".git", "MERGE_HEAD"))

    # the stated bound must travel with every result, including the clean one
    rc, out = run(repo)
    check("⚠ the one-checkout bound is printed even on a CLEAN run",
          "ONE CHECKOUT ONLY" in out, True)


# ── ⛔ THE THIRD STATE: COMMITTED ON A BRANCH, NOT ON MAIN ────────────────────
# The first version of this tool asserted "no ref carries them" about text that
# THREE COMMITS on branch `pr1136` carried. False claim, wrong remedy: "commit
# your work" is useless to someone whose work is committed and awaiting review,
# and it sends a reviewer after unsaved edits that do not exist.
# ★ This is not an anomaly — it is what an open docs PR looks like from the
# working copy, every time.
with tempfile.TemporaryDirectory() as tmp2:
    repo2 = os.path.join(tmp2, "r"); os.makedirs(repo2)
    git(repo2, "init", "-q")
    git(repo2, "config", "user.email", "t@t"); git(repo2, "config", "user.name", "t")
    def w2(text):
        with open(os.path.join(repo2, "CLAUDE.md"), "w") as f:
            f.write(text)
    w2("alpha\nbeta\n")
    git(repo2, "add", "CLAUDE.md"); git(repo2, "commit", "-qm", "base")
    git(repo2, "branch", "base")
    # a docs PR: committed on a branch, absent from `base`
    git(repo2, "checkout", "-q", "-b", "docs/pr")
    w2("alpha\nbeta\nSECTION-ON-A-BRANCH\n")
    git(repo2, "add", "CLAUDE.md"); git(repo2, "commit", "-qm", "docs: add the section")

    def run2(*extra):
        argv = sys.argv[:]
        sys.argv = ["x", "--repo-path", repo2, "--ref", "base", *extra]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = du.main()
        finally:
            sys.argv = argv
        return rc, buf.getvalue()

    rc, out = run2()
    check("branch-committed text is NOT called uncommitted",
          "READ BUT NOT COMMITTED" in out, False)
    check("...it is reported as COMMITTED ON <branch>, NOT ON <ref>",
          "COMMITTED ON docs/pr, NOT ON base" in out, True)
    check("...with LAND THE PR as the remedy", "LAND THE PR" in out, True)
    check("...and the commit that carries it, so a reviewer can act",
          "docs: add the section" in out, True)
    check("...and it explicitly warns against the wrong remedy",
          "sends them after edits that do not exist" in out, True)

    # ⛔ KNOWN-BAD CONTROL — the two states must remain DISTINGUISHABLE. Add a
    # genuinely uncommitted line on top and assert BOTH are reported separately.
    w2("alpha\nbeta\nSECTION-ON-A-BRANCH\nTRULY-UNSAVED\n")
    rc, out = run2()
    check("KNOWN-BAD control: a truly uncommitted line IS still called that",
          "READ BUT NOT COMMITTED" in out, True)
    check("...and the branch state is reported ALONGSIDE it, not instead of it",
          "COMMITTED ON docs/pr" in out, True)
    check("...the uncommitted line is quoted", "TRULY-UNSAVED" in out, True)
    check("...and the branch line is NOT in the uncommitted list",
          out.split("READ BUT NOT COMMITTED")[1].split("⚠")[0].count("SECTION-ON-A-BRANCH"), 0)

    # ⚠ and a checkout sitting exactly on the ref must report neither.
    # ⛔ THE FIXTURE HAD A BUG HERE AND THE TEST WAS RIGHT TO FAIL: `git checkout`
    # with a DIRTY tree CARRIES the modification across, so the file still held
    # both extra lines and the tool correctly reported them. Restore the content
    # explicitly — a fixture must reach the state it claims to test.
    git(repo2, "checkout", "-q", "base")
    w2("alpha\nbeta\n")
    rc, out = run2()
    check("on the ref itself, with a clean file, nothing is reported and exit is 0", rc, 0)
    check("...and it SAYS reads == landed rather than printing nothing",
          "what the fleet reads is what landed" in out, True)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
