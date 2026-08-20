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

ID = en.Identity("nForma-NEXT", "-Users-o-code-nForma-NEXT", "nForma-NEXT")
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
    check("code-dir", kinds("p = '/Users/o/code/Fabrikam-Ledger/x'"), ["code-dir"])
    check("project-slug", kinds("'~/.claude/projects/-Users-o-code-Fabrikam-Ledger/a.jsonl'"),
          ["project-slug"])
    check("forge-url", kinds("'https://github.com/Fab-Corp/Fabrikam-Ledger.git'"), ["forge-repo"])

    print("\nand OUR OWN names in the same shapes do not — the flood control:")
    # ⛔ Without these rows the predicate is indistinguishable from one matching every
    # path in the tree. A detector with no known-negative is not a detector.
    check("our code dir", kinds("p = '/Users/o/code/nForma-NEXT/tools/x.py'"), [])
    check("our slug", kinds("'~/.claude/projects/-Users-o-code-nForma-NEXT/a.jsonl'"), [])
    check("our forge repo", kinds("'https://github.com/nForma-AI/nForma-NEXT.git'"), [])
    check("case differs, same estate", kinds("p = '~/code/nforma-next/x'"), [])

    print("\na bare relative path is NOT a forge ref:")
    # `tools/README.md` is exactly `X/Y`. Matching that shape anywhere floods the tree.
    check("bare dir/file", kinds("'tools/README.md'"), [])
    check("bare owner/repo alone", kinds("'Fab-Corp/Fabrikam-Ledger'"), [])

    print("\nadjacency: gh -R arrives as SEPARATE literals, and only for gh:")
    gh = ["gh", "issue", "list", "-R", "Fab-Corp/Fabrikam-Ledger"]
    check("gh argv list", [k for k, _, _ in en.scan_strings(gh, ID)], ["forge-flag"])
    check("our own repo via -R",
          en.scan_strings(["gh", "-R", "nForma-AI/nForma-NEXT"], ID), [])
    # ⛔ -R is also grep's recursive flag.
    check("grep -R is not a forge ref",
          en.scan_strings(["grep", "-R", "docs/README.md"], ID), [])

    print("\nan incomplete identity establishes NOTHING — it never reads clean:")
    # With no comparand every string is trivially "not ours"; returning [] here is the
    # only safe answer, and the CALLER must treat it as VOID, not as absence.
    check("no identity -> no claim", en.foreign_in("p='/Users/o/code/Anything/x'",
                                                   en.Identity(None, None, None)), [])
    check("incomplete is not complete", en.Identity("a", "b", None).complete(), False)
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
