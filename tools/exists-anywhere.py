#!/usr/bin/env python3
"""Does this name exist in this repository — at ANY ref, not just the one checked out?

⛔ FOUR TIMES IN ONE SESSION, BY THREE AGENTS, THE SAME MISTAKE: concluding about a
repository from a single ref. The costliest was published as a finding and had to be
retracted.

    ci_guard_closing_keywords    git ls-files | grep -c   ->  0    "it never existed"
                                 rev-list --all --objects ->  6    161 lines, unmerged branch
    iter_console_backends        rev-list --all --objects ->  0    genuinely absent

★ THE OBJECT-STORE COUNT IS THE DISCRIMINATOR AND IT IS ONE COMMAND. Two agents each
searched `git ls-files` — the index of ONE branch — and reported a built-and-unmerged guard
as a phantom reference. `git grep`, `git ls-files` and a working-tree scan **cannot tell
those apart**, and all three read as authoritative.

⇒ *"Never existed"* and *"exists on a ref you did not search"* are different defects with
different remedies — **a wrong sentence versus an unmerged branch** — and only the second is
fixed by merging something.

⚠ WHY A TOOL AND NOT A GUARD. A `PreToolUse` rule firing on every `git grep` would fire on
the correct use, which is the failure this repository already shipped once (`two-dot-diff`
fired on the three-dot form). The wrong reading is not a wrong COMMAND, it is a correct
command answering a narrower question than the one asked. ⇒ So this is a thing to reach
for, not a thing that nags.

Exit: 0 present on the default ref · 1 present only on other refs · 2 absent everywhere
      · 3 established nothing.
"""
import argparse, os, re, subprocess, sys


def sh(*args, cwd=None):
    """⛔ Returns (stdout, ok). A non-zero git is NOT an empty result — the whole subject
    of this file is refusing to read a failed search as an absence."""
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return "", False
    return p.stdout, p.returncode == 0


def object_hits(name, repo):
    """Every path in the object store whose name matches. The widest population git has."""
    out, ok = sh("git", "rev-list", "--all", "--objects", cwd=repo)
    if not ok:
        return None
    return [ln.split(" ", 1)[1] for ln in out.splitlines()
            if " " in ln and name in ln.split(" ", 1)[1]]


def refs_containing(path, repo, limit=800):
    """Which refs carry this path. Bounded, and it SAYS when it truncated."""
    out, ok = sh("git", "for-each-ref", "--format=%(refname:short)", "refs/remotes", cwd=repo)
    if not ok:
        return [], False
    refs = [r for r in out.splitlines() if r and not r.endswith("/HEAD")]
    truncated = len(refs) > limit
    found = []
    for r in refs[:limit]:
        o, ok2 = sh("git", "cat-file", "-e", f"{r}:{path}", cwd=repo)
        if ok2:
            found.append(r)
    return found, truncated


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="A zero here means absent from the OBJECT STORE, which is the strongest "
               "absence git can report. A zero from git ls-files or git grep means absent "
               "from ONE REF and is not the same claim.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?", help="a filename or identifier fragment")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref", default="origin/main", help="the ref that counts as 'shipped'")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.name:
        print("⛔ need a name — ESTABLISHED NOTHING.", file=sys.stderr)
        return 3

    inside, ok = sh("git", "rev-parse", "--is-inside-work-tree", cwd=args.repo)
    if not ok or inside.strip() != "true":
        print(f"⛔ {args.repo} is not a git work tree. This is a fact about the PATH, "
              "not about the name. ESTABLISHED NOTHING.", file=sys.stderr)
        return 3

    hits = object_hits(args.name, args.repo)
    if hits is None:
        print("⛔ `git rev-list --all --objects` failed — ESTABLISHED NOTHING. A failed "
              "search is not an absence.", file=sys.stderr)
        return 3

    if not hits:
        print(f"ABSENT  {args.name}")
        print(f"  0 objects in the whole store. This is the strongest absence git reports:\n"
              f"  it was never committed on any ref this clone has fetched.", file=sys.stderr)
        print("  ⚠ It can still exist on a ref you have never fetched. Run `git fetch --all` "
              "first if that matters.", file=sys.stderr)
        return 2

    paths = sorted(set(hits))
    on_ref = []
    for p in paths:
        _o, ok2 = sh("git", "cat-file", "-e", f"{args.ref}:{p}", cwd=args.repo)
        if ok2:
            on_ref.append(p)

    if on_ref:
        print(f"PRESENT on {args.ref}")
        for p in on_ref:
            print(f"  {p}")
        return 0

    print(f"⛔ EXISTS BUT NOT ON {args.ref} — {len(paths)} path(s) in the object store")
    for p in paths[:10]:
        refs, truncated = refs_containing(p, args.repo)
        where = ", ".join(r.replace("origin/", "") for r in refs[:4]) or "no remote ref"
        print(f"  {p}\n      on: {where}{'  (ref scan truncated)' if truncated else ''}")
    print(f"\n⇒ This is an UNMERGED INSTRUMENT, not a phantom reference. The remedy is a "
          f"merge, not a correction to whatever sentence names it.", file=sys.stderr)
    return 1


def self_test():
    """⛔ Known positives from the incident, in a tree built here — not from this machine's
    repositories, which would make the test a fact about this checkout."""
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        def g(*a):
            subprocess.run(("git",) + a, cwd=td, capture_output=True, text=True)
        g("init", "-q", "-b", "main")
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        open(os.path.join(td, "shipped.py"), "w").write("x = 1\n")
        g("add", "-A"); g("commit", "-qm", "shipped")
        g("checkout", "-qb", "side")
        open(os.path.join(td, "unmerged_guard.py"), "w").write("y = 2\n")
        g("add", "-A"); g("commit", "-qm", "guard")
        g("checkout", "-q", "main")

        h1 = object_hits("shipped.py", td)
        h2 = object_hits("unmerged_guard.py", td)
        h3 = object_hits("never_written.py", td)
        ok &= _c("a shipped file is in the store", bool(h1), True)
        ok &= _c("an UNMERGED file is also in the store", bool(h2), True)
        ok &= _c("a file that never existed is not", h3, [])

        # ⛔ The discriminating pair: both are "present in the store", and only one is on main.
        _o, on_main_1 = sh("git", "cat-file", "-e", "main:shipped.py", cwd=td)
        _o, on_main_2 = sh("git", "cat-file", "-e", "main:unmerged_guard.py", cwd=td)
        ok &= _c("shipped is reachable from main", on_main_1, True)
        ok &= _c("the unmerged guard is NOT", on_main_2, False)

        # ⚠ And the control that matters: git ls-files, the command that caused the incident,
        # cannot separate them. If this ever starts separating them, the tool is redundant.
        out, _ = sh("git", "ls-files", cwd=td)
        listed = out.split()
        ok &= _c("git ls-files sees the shipped file", "shipped.py" in listed, True)
        ok &= _c("git ls-files is BLIND to the unmerged one",
                 "unmerged_guard.py" in listed, False)

    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 3


def _c(name, got, want):
    good = got == want
    print(f"  {'ok  ' if good else 'FAIL'} {name}: got {got!r} want {want!r}")
    return good


if __name__ == "__main__":
    sys.exit(main())
