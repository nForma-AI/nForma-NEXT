#!/usr/bin/env python3
"""Hermetic checks for the derived estate predicate. No git, no network, no fleet."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estatenames as en                                     # noqa: E402
try:
    from runmarker import result, run                         # noqa: E402
except ImportError:                                           # pragma: no cover
    def run(n): print("NFORMA-RUN %s" % n, file=sys.stderr)
    def result(ok): print("NFORMA-RESULT %s" % ("OK" if ok else "FINDING"), file=sys.stderr)

# ⛔ SHAPE, NEVER OWNER. Assembled at runtime so that NO substring of this file matches the
# predicate this file tests. A literal foreign path here would make the suite trip the
# detector it exercises — and would BURN the name as a future control the moment it landed,
# because a committed name is already in the vocabulary of the thing under test.
EST = "-".join(("fixture", "estate", "not", "an", "owner"))
OWN = "-".join(("fixture", "owner", "not", "real"))
# ⚠ The fixture's OWN slug has to be assembled too, and the reason is less obvious: a
# hermetic suite must construct a synthetic identity, and any synthetic identity differs
# from the real repo's — so `-Users-o-code-nForma-NEXT` reads FOREIGN to the live detector
# even though it is this fixture's idea of LOCAL. Assembling costs nothing and removes it.
SLUG_PRE = "-Users" + "-o" + "-code-"

ID = en.Identity("nForma-NEXT", SLUG_PRE + "nForma-NEXT", "nForma-NEXT")
F = 0


def check(name, got, want):
    global F
    ok = got == want
    F += not ok
    print("  %s  %s: got %r, want %r" % ("PASS" if ok else "FAIL", name, got, want))


def kinds(text, ident=ID):
    return sorted({k for k, _, _ in en.foreign_in(text, ident)})


def main():
    run("estatenames")
    print("the three single-string shapes fire on a foreign estate:")
    check("code-dir", kinds("p = '/Users/o/code/%s/x'" % EST), ["code-dir"])
    check("project-slug", kinds("'~/.claude/projects/%s%s/a.jsonl'" % (SLUG_PRE, EST)),
          ["project-slug"])
    check("forge-url", kinds("'https://github.com/%s/%s.git'" % (OWN, EST)), ["forge-repo"])

    print("\nand OUR OWN names in the same shapes do not — the flood control:")
    # ⛔ Without these rows the predicate is indistinguishable from one matching every
    # path in the tree. A detector with no known-negative is not a detector.
    check("our code dir", kinds("p = '/Users/o/code/nForma-NEXT/tools/x.py'"), [])
    check("our slug", kinds("'~/.claude/projects/%snForma-NEXT/a.jsonl'" % SLUG_PRE), [])
    check("our forge repo", kinds("'https://github.com/nForma-AI/nForma-NEXT.git'"), [])
    check("case differs, same estate", kinds("p = '~/code/nforma-next/x'"), [])

    print("\na bare relative path is NOT a forge ref:")
    # `tools/README.md` is exactly `X/Y`. Matching that shape anywhere floods the tree.
    check("bare dir/file", kinds("'tools/README.md'"), [])
    check("bare owner/repo alone", kinds("'%s/%s'" % (OWN, EST)), [])

    print("\nthe argv shape is an UNCOVERED GAP, asserted so it is not assumed:")
    # ⛔ NOT a bug — a stated gap. The adjacency leg that once caught this was removed:
    # ast.walk is breadth-first, so literals from unrelated statements sort before a call's
    # own arguments, and the leg passed by luck. DEVOPS measured 12 of 12 real estate hits
    # matching a SINGLE literal, so it never fired for a genuine detection.
    # ⚠ This row FAILS if someone reintroduces adjacency without the per-call population —
    # which is the point: the gap must stay visible until it is closed properly.
    gh = ["gh", "issue", "list", "-R", "%s/%s" % (OWN, EST)]
    check("argv list is NOT detected", en.scan_strings(gh, ID), [])
    # ⇒ And the SHELL-STRING form still is, which is what keeps the gap narrow.
    check("shell string form still caught",
          [k for k, _, _ in en.scan_strings(["gh issue list -R %s/%s" % (OWN, EST)], ID)],
          ["forge-repo"])   # one kind: the flag form is not distinguished from the URL form
    # ⛔ -R is also grep's recursive flag; the single-string leg must not read a path as a repo.
    check("grep -R is not a forge ref",
          en.scan_strings(["grep -R docs/README.md"], ID), [])

    print("\nan incomplete identity establishes NOTHING — it never reads clean:")
    # With no comparand every string is trivially "not ours"; returning [] here is the
    # only safe answer, and the CALLER must treat it as VOID, not as absence.
    check("no identity -> no claim", en.foreign_in("p='/Users/o/code/%s/x'" % EST,
                                                   en.Identity(None, None, None)), [])
    check("incomplete is not complete", en.Identity("a", "b", None).complete(), False)
    # ⛔ THE REAL TRIGGER, not a constructed one. A directory that is not a git repo
    # yields an incomplete identity — which is how the derived leg silently vanished
    # inside a self-test fixture while every plant in the real tree still worked.
    check("non-repo dir -> incomplete", en.local_identity("/").complete(), False)
    check("complete is complete", ID.complete(), True)

    print()
    result(F == 0)
    if F:
        print("%d FAILED" % F)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
