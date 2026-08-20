#!/usr/bin/env python3
"""Pins the completeness test, and the shapes where completeness cannot be established.

⛔ `gh api …/check-runs` returns 30 of 54 by default. It is not an error — the response
carries `total_count: 54`, and a filter over `.check_runs[]` evaluates the thirty it
received and answers about a set it never saw. It once **hid a required-check failure**.

⚠ `per_page=100` is the reflex and it is not the check: it fails the same way past 100.
The check is comparing the count the API states against the array it sent.

★ Verified live while building this, on three real endpoints:

    check-runs on a df-wiki commit        9 of 9      -> exit 0
    search/issues, 775 merged PRs         30 of 775   -> exit 1, TRUNCATED
    repos/…/pulls (a BARE ARRAY)          no total    -> exit 2, VOID

⛔ That third one matters most and is the tool's limit rather than its feature: the
endpoint most people reach for returns a bare array with **no stated total**, so
completeness cannot be established from it at all. Refusing is the honest answer, and it
means this cannot rescue every call.

Run: python3 tools/test_gh_complete.py
"""
import importlib.util
import os
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
TOOL = os.path.join(_here, "gh-complete.py")
_spec = importlib.util.spec_from_file_location("ghc", TOOL)
ghc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ghc)


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def raises(fn, needle):
    try:
        fn()
        return False, "did not raise"
    except RuntimeError as exc:
        return (needle in str(exc)), str(exc)[:70]


def main():
    f = 0

    print("★ the measured defect — 30 sent, 54 stated:")
    doc = {"total_count": 54, "check_runs": [{} for _ in range(30)]}
    complete, stated, received, key = ghc.assess(doc)
    f += not check("complete", complete, False)
    f += not check("stated", stated, 54)
    f += not check("received", received, 30)
    f += not check("key derived, not assumed", key, "check_runs")

    f += link_checks()

    print("a whole reading passes:")
    doc = {"total_count": 9, "check_runs": [{} for _ in range(9)]}
    f += not check("complete", ghc.assess(doc)[0], True)

    print("an empty-but-complete list is complete, not suspicious:")
    f += not check("0 of 0", ghc.assess({"total_count": 0, "check_runs": []})[0], True)

    print("★ shapes where completeness CANNOT be established — refuse, never assume:")
    ok, msg = raises(lambda: ghc.assess([{"a": 1}]), "bare array")
    f += not check("a bare array", ok, True)
    ok, msg = raises(lambda: ghc.assess({"check_runs": [1, 2]}), "no total_count")
    f += not check("no stated total", ok, True)
    ok, msg = raises(lambda: ghc.assess({"total_count": 2, "a": [1], "b": [2]}),
                     "cannot tell which key")
    f += not check("two candidate arrays -> refuses to guess", ok, True)

    print("--key resolves the ambiguity, and only to a real list:")
    doc = {"total_count": 1, "a": [1], "b": [2, 3]}
    f += not check("explicit key", ghc.assess(doc, key="b")[3], "b")
    ok, _ = raises(lambda: ghc.assess({"total_count": 1, "a": 5}, key="a"), "is not a list")
    f += not check("--key must name a list", ok, True)

    print("⚠ the count key is read, not inferred from length:")
    # A response whose array is LONGER than the stated count is also not whole —
    # it means the total is stale or the page overlapped, and either way the two
    # disagree. Equality is the test, not `received < stated`.
    f += not check("over-long array is not complete",
                   ghc.assess({"total_count": 2, "x": [1, 2, 3]})[0], False)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


def link_checks():
    """⛔ Registered explicitly, because main() lists its checks and does not discover
    them. The first version of these tests was appended as bare defs and NEVER RAN —
    a sabotage run exited 0 and I read the zero as a pass. A test file that discovers
    nothing turns every added test into decoration."""
    f = 0
    print("Link-header completeness — the second checkable signal:")
    f += not check("no Link at all == complete", ghc.link_complete({}), True)
    f += not check('rel="last" only == complete',
                   ghc.link_complete({"link": '<...>; rel="last"'}), True)
    f += not check('rel="next" == prefix',
                   ghc.link_complete({"link": '<...>; rel="next", <...>; rel="last"'}), False)
    ok, stated, received, _ = ghc.assess([1, 2, 3], headers={})
    f += not check("bare array + complete Link passes", (ok, stated, received), (True, 3, 3))
    for label, hdrs in (("bare array + rel=next refuses", {"link": '<>; rel="next"'}),
                        ("bare array + NO headers refuses", None)):
        try:
            ghc.assess([1, 2, 3], headers=hdrs)
            f += not check(label, "passed", "refused")
        except RuntimeError:
            f += not check(label, "refused", "refused")
    return f


if __name__ == "__main__":
    sys.exit(main())

# --- Link-header completeness, added with the path it exercises -----------------
# ⛔ The bare-array refusal was read as "completeness cannot be established for list
# endpoints", and that conclusion recommended a bare `--limit` instead. Measured:
# the list endpoints state no COUNT and DO state COMPLETENESS. A different input,
# not no input.

def test_link_absent_means_complete():
    assert ghc.link_complete({}) is True
    assert ghc.link_complete({"link": '<...page=3>; rel="last"'}) is True


def test_link_next_means_prefix():
    assert ghc.link_complete({"link": '<...page=2>; rel="next", <...>; rel="last"'}) is False


def test_bare_array_passes_only_with_a_complete_link():
    # complete: no rel=next
    ok, stated, received, key = ghc.assess([1, 2, 3], headers={})
    assert ok and stated == 3 and received == 3
    # prefix: refuses rather than assuming
    try:
        ghc.assess([1, 2, 3], headers={"link": '<...>; rel="next"'})
    except RuntimeError:
        pass
    else:
        raise AssertionError("a bare array WITH rel=next must refuse, not pass")
    # ⚠ no headers at all is still a refusal — absence of evidence, not evidence
    try:
        ghc.assess([1, 2, 3])
    except RuntimeError:
        pass
    else:
        raise AssertionError("a bare array with NO headers must refuse")

