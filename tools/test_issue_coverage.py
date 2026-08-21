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
    check("gh issue view is a real contact", dict(ic.contacts(p)[0]), {602: {ic.OPENED}})

    p = write([tool_use("Bash", {"command": "gh issue comment 604 --body x"})])
    check("a comment is OPENED and ACTED", dict(ic.contacts(p)[0]), {604: {ic.OPENED, ic.ACTED}})

    p = write([tool_use("Bash", {"command": "gh api repos/o/r/issues/1115"})])
    check("the api path form counts", dict(ic.contacts(p)[0]), {1115: {ic.OPENED}})

    # ⛔ the known-bad control: a number in PROSE is not a contact
    p = write([{"type": "assistant", "message": {"content": [
        {"type": "text", "text": "we should look at #602 and issues/604 soon"}]}}])
    check("KNOWN-BAD control: a number in prose is NOT a contact", dict(ic.contacts(p)[0]), {})

    # a bulk list dump is not a contact either
    p = write([{"type": "user", "message": {"content": [
        {"type": "tool_result", "content": "#602 #604 #1115 ..."}]}}])
    check("a list dump in a tool_result is NOT a contact", dict(ic.contacts(p)[0]), {})

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


# ── ⛔ A COUNT IS AN ABSENCE CLAIM, SO IT NEEDS A COMPLETENESS WITNESS ────────
#     A witness that certifies PROVENANCE does not certify COMPLETENESS,
#     and every absence claim needs the second one.
#
# This tool's product is "which issues did NOBODY open". An unparseable line was
# silently skipped, so a PARTIAL READ and a GENUINELY QUIET PANE produced the same
# output. The bias runs one way: fewer contacts -> MORE issues read as untouched.
#
# ⚠ MEASURED BEFORE WRITING THIS, and it refuted the reason for looking: 0
# unparseable lines in 170,364 across all 12 role-named transcripts, 0 of 12
# ending on a partial line, including panes writing while they were read. ⇒ The
# COUNT is zero. The COUNTER was missing, and an instrument that cannot report a
# zero cannot report a one. These pins protect the counter, not a live defect.
with tempfile.TemporaryDirectory() as tmp2:
    def tx(name, lines):
        q = os.path.join(tmp2, name)
        with open(q, "w") as f:
            f.write("".join(lines))
        return q

    good = json.dumps(tool_use("Bash", {"command": "gh issue view 777"})) + "\n"
    # ⚠ must contain "issue" or the prefilter drops it BEFORE json.loads —
    # otherwise this fixture would test the prefilter, not the parser.
    # ⚠ I WROTE THE COMMENT ABOVE AND THEN VIOLATED IT ON THE NEXT LINE: the first
    # version of this fixture had no "issue" token, so the PREFILTER dropped it and
    # `skipped` stayed 0. The test failed and was right to. A fixture has to reach
    # the code path it claims to exercise, and "it looks malformed" is not that.
    torn = '{"type":"assistant","content":"gh issue view 888","tool_us\n'

    clean = tx("clean.jsonl", [good])
    partial = tx("partial.jsonl", [good, torn])

    c_clean, s_clean = ic.contacts(clean)
    c_partial, s_partial = ic.contacts(partial)

    check("a clean transcript skips nothing", s_clean, 0)
    check("a torn final line is COUNTED, not swallowed", s_partial, 1)
    check("...and the good line's contact still lands",
          dict(c_partial), {777: {ic.OPENED}})

    # ⛔ KNOWN-BAD CONTROL — the whole reason the counter has to exist.
    # The contacts are IDENTICAL between a complete read and a torn one. Nothing
    # in the primary output can tell them apart; only `skipped` can.
    check("KNOWN-BAD control: contacts are IDENTICAL either way",
          dict(c_clean), dict(c_partial))
    check("...so ONLY the completeness counter separates them",
          (s_clean, s_partial), (0, 1))

    # a torn line that never mentions an issue is dropped by the PREFILTER, not
    # the parser — and that is not a completeness failure, so it must not count.
    prefiltered = tx("pre.jsonl", [good, '{"type":"assistant","con\n'])
    check("a torn line with no 'issue' token is not counted as skipped",
          ic.contacts(prefiltered)[1], 0)

    check("an unreadable transcript is still None, not (…, 0)",
          ic.contacts(os.path.join(tmp2, "absent.jsonl")), None)


# ── ⛔ A COUNT WITHOUT AN INSTANT CANNOT BE RE-DERIVED ────────────────────────
# Measured three times in one night, on three different agents' numbers, and none
# of them was a re-measurement error — the BOARD moved:
#
#     233 open / 81 untouched  ->  237/86  ->  248/92   (one session)
#     107 conflict pairs       ->  measured against a main that then moved
#     +64/-1 vs origin/main    ->  +49/-0, origin/main moved between reads
#
# ★ Every one was quoted back by a second agent as a property of the repository,
# because the output carried no instant and so READ AS TIMELESS.
# ⚠ The failure is not the drift. It is the QUOTABILITY.
import re as _re
_ISO = _re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_stamp = ic.collected_at()
check("the stamp is an ISO-Z instant", bool(_ISO.match(_stamp)), True)
check("...in UTC, not a local naive time", _stamp.endswith("Z"), True)

# ⛔ KNOWN-BAD CONTROL — a constant would satisfy the shape check above. Assert the
# stamp actually ADVANCES, or it is decoration that cannot distinguish two runs.
import time as _time
_a = ic.collected_at(); _time.sleep(1.1); _b = ic.collected_at()
check("KNOWN-BAD control: two readings a second apart DIFFER — it is not a constant",
      _a != _b, True)
check("...and the later one sorts after the earlier (lexical ISO ordering)",
      _b > _a, True)

# the header and the footer must BOTH carry it: a reader who quotes the top line
# and a reader who quotes the bottom one are both quoting a photograph.
# ⛔ Assert on the RENDERED text, not on the source. The first version of this
# check grepped the source for "Quote the instant" and FAILED — the phrase was
# split across a string-literal boundary. Third source-text assertion tonight to
# need converting; the fix is to make the text a constant, not a smarter grep.
_rendered = ic.PHOTOGRAPH.format(when=_stamp)
check("the footer names the reading as a photograph", "PHOTOGRAPH taken at" in _rendered, True)
check("...carries the actual instant", _stamp in _rendered, True)
check("...tells the reader to quote it or re-derive",
      "Quote the instant" in _rendered and "re-derive" in _rendered, True)
check("...and shows a MEASURED drift rather than asserting one",
      "233/81" in _rendered and "248/92" in _rendered, True)
src = open(os.path.join(_here, "issue-coverage.py")).read()
check("the header line carries the instant too", "collected {collected_at()}" in src, True)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
