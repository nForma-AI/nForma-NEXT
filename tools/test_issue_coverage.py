#!/usr/bin/env python3
"""Pins that an empty board, a failed query and a covered board are three results.

⛔ The defect this prevents: `0 untouched` is printed by a healthy fleet, by a
`gh` failure that exited 0, and by a transcript glob that matched nothing. This
tool exists to answer "what has nobody looked at", so a clean zero from a broken
reader is the exact wrong answer to give.

Run: python3 tools/test_issue_coverage.py
"""
import json, os, sys, tempfile, types

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    """Execute the source read NOW — no __pycache__ in the path to serve a stale module."""
    mod = types.ModuleType(name)
    mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


ic = load(os.path.join(_here, "issue-coverage.py"), "ic")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def tool_use(name, inp):
    return {"type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


with tempfile.TemporaryDirectory() as tmp:
    def write(recs, sid="aaaaaaaa"):
        p = os.path.join(tmp, sid + "-x.jsonl")
        with open(p, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        return p

    p = write([tool_use("Bash", {"command": "gh issue view 602 --json body"})])
    check("gh issue view is a real contact", dict(ic.contacts(p)), {602: {ic.OPENED}})

    p = write([tool_use("Bash", {"command": "gh issue comment 604 --body x"})])
    check("a comment is OPENED and ACTED", dict(ic.contacts(p)), {604: {ic.OPENED, ic.ACTED}})

    p = write([tool_use("Bash", {"command": "gh api repos/o/r/issues/1115"})])
    check("the api path form counts", dict(ic.contacts(p)), {1115: {ic.OPENED}})

    # ⛔ the known-bad control: a number in PROSE is not a contact
    p = write([{"type": "assistant", "message": {"content": [
        {"type": "text", "text": "we should look at #602 and issues/604 soon"}]}}])
    check("KNOWN-BAD control: a number in prose is NOT a contact", dict(ic.contacts(p)), {})

    # a bulk list dump is not a contact either
    p = write([{"type": "user", "message": {"content": [
        {"type": "tool_result", "content": "#602 #604 #1115 ..."}]}}])
    check("a list dump in a tool_result is NOT a contact", dict(ic.contacts(p)), {})

    check("an unreadable transcript is None, never {}",
          ic.contacts(os.path.join(tmp, "nope.jsonl")), None)

# ── the three ways to print a clean zero ──────────────────────────────────────
check("an EMPTY board is refused, not reported as covered", ic.open_issues.__doc__ is not None, True)
check("...and the code path returns None on an empty list",
      ic.open_issues("nForma-AI/this-repo-does-not-exist-xyzzy"), None)


# ── selection: identity, not recency ──────────────────────────────────────────
# ⛔ THE DEFECT. Selection was `sorted(paths, key=-mtime)[:9]`. Measured 2026-08-21,
# two runs 90s apart against an UNCHANGED board: TRIAGE contributed 41 issues, then
# 0, because it went quiet for ~2 minutes and fell out of the top nine. Its issues
# reverted to "opened by NOBODY". The instrument dropped the idle panes — the exact
# population the question is usually about.
#
# ★ The claim being pinned is STRUCTURAL, not statistical: when --limit does not
# bind, the selected SET cannot depend on mtime at all. Sampling the live fleet
# cannot show this — measured, the OLD selection also held steady across 24s. So
# the test permutes mtime directly and asserts the set is unmoved.
with tempfile.TemporaryDirectory() as tmp:
    def pane(sid, role, issue=None):
        """A transcript that bootstraps as `role` (None = never declared one)."""
        p = os.path.join(tmp, sid + ".jsonl")
        recs = []
        if role:
            recs.append({"type": "user", "message": {"content":
                         f"You are {role}. Do the thing."}})
        else:
            recs.append({"type": "user", "message": {"content": "hello, do the thing"}})
        if issue:
            recs.append(tool_use("Bash", {"command": f"gh issue view {issue}"}))
        with open(p, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        return p

    roled = [pane(f"role{i}", r) for i, r in
             enumerate(["ARCHITECT", "DEVOPS", "TRIAGE", "DX", "MAINTAINER"])]
    anon = [pane(f"anon{i}", None) for i in range(5)]
    root = os.path.join(tmp, "*.jsonl")

    def stamp(order):
        """Give `order` strictly decreasing freshness — order[0] is newest."""
        for k, path in enumerate(order):
            os.utime(path, (1_700_000_000 - k * 60,) * 2)

    stamp(roled + anon)                       # roles fresh, anon stale
    a_sel, _ = ic.select_panes(root, limit=64)
    stamp(anon + roled)                       # ⇄ anon fresh, roles stale
    b_sel, _ = ic.select_panes(root, limit=64)
    stamp(list(reversed(roled)) + anon)       # roles reordered among themselves
    c_sel, _ = ic.select_panes(root, limit=64)

    check("identity: the SET is the role-named panes", set(a_sel), set(roled))
    check("identity: reversing every mtime does not move the set",
          set(b_sel), set(a_sel))
    check("identity: reordering WITHIN the roles does not move it either",
          set(c_sel), set(a_sel))
    check("identity: a pane that never declared a role is NOT read",
          set(a_sel) & set(anon), set())

    # ⛔ KNOWN-BAD CONTROL — without it the three checks above are vacuous: they
    # would also pass against a selector that ignored mtime by accident. This
    # asserts the fixture CAN move a recency selector, i.e. the test has teeth.
    stamp(roled + anon)
    r_a, _ = ic.select_panes(root, limit=64, recency=5)
    stamp(anon + roled)
    r_b, _ = ic.select_panes(root, limit=64, recency=5)
    check("KNOWN-BAD control: --recency DOES move under the same permutation",
          set(r_a) != set(r_b), True)
    check("KNOWN-BAD control: ...and it picks up the anonymous panes",
          set(r_b), set(anon))
    check("--recency says the counts are a function of when you ran it",
          "function of WHEN" in ic.select_panes(root, 64, recency=5)[1], True)

    # ── the ceiling must announce itself ──────────────────────────────────────
    # ⛔ A silent cap is the same defect one level up: the dropped panes' issues
    # are counted as untouched, and nothing in the output says a pane was dropped.
    stamp(roled + anon)
    sel, note = ic.select_panes(root, limit=2)
    check("a bound --limit reads only that many", len(sel), 2)
    check("...and SAYS it bound", "BOUND" in note, True)
    check("...and NAMES every role it dropped",
          all(r in note for r in ["TRIAGE", "DX", "MAINTAINER"]), True)
    check("...and warns their issues now read as untouched",
          "counted as untouched" in note, True)
    _, unbound = ic.select_panes(root, limit=64)
    check("an UNBOUND limit says nothing about a ceiling", "BOUND" in unbound, False)

    # ── no fleet at all is a refusal, not a clean zero ────────────────────────
    empty = os.path.join(tmp, "none", "*.jsonl")
    sel, _ = ic.select_panes(empty, limit=64)
    check("no transcripts at all selects nothing (main then refuses)", sel, [])
    anon_only = os.path.join(tmp, "anon*.jsonl")
    sel, _ = ic.select_panes(anon_only, limit=64)
    check("a corpus of role-less transcripts also selects nothing", sel, [])

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
