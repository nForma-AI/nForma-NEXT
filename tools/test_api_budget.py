#!/usr/bin/env python3
"""Pins that a failed quota read is not a full pool, and a mention is not a call.

⛔ The two ways this tool could lie, both of which read as good news:
  - `rate_limit` fails and the tool prints a healthy pool. The endpoint is EXEMPT
    from the quota it reports, so a failure there is network or auth — reporting
    a number would blame the wrong thing.
  - a `gh` string inside an echo or a heredoc counts as a call, inflating the
    attribution of whoever happened to be DISCUSSING the quota.

Run: python3 tools/test_api_budget.py
"""
import json, os, sys, tempfile, types, glob

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
_here = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    mod = types.ModuleType(name); mod.__file__ = path
    exec(compile(open(path).read(), path, "exec"), mod.__dict__)
    return mod


ab = load(os.path.join(_here, "api-budget.py"), "ab")
fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'✅' if ok else '❌'} {name}")
    if not ok:
        print(f"     got  {got!r}\n     want {want!r}")
        fails.append(name)


def n(cmd):
    return len(ab.GH.findall(cmd))


# ── a call is at a command position ──────────────────────────────────────────
check("bare invocation", n("gh pr view 12"), 1)
check("after && ", n("cd /x && gh issue list"), 1)
check("in a pipeline", n("echo x | gh api foo"), 1)
check("in $( )", n("x=$(gh pr list --json number)"), 1)
check("two on one line", n("gh pr view 1; gh pr view 2"), 2)

# ⛔ KNOWN-BAD CONTROL: the naive `"gh " in cmd` counts all of these
for mention in ('echo "run gh pr view next"',
                'printf "the gh api call is expensive\\n"',
                'grep -c "gh issue" notes.md'):
    check(f"MENTION not counted: {mention[:34]}", n(mention), 0)
    check("  ...and the naive substring WOULD have", "gh " in mention, True)

# ── multi-call flags ─────────────────────────────────────────────────────────
for cmd, want in (("gh pr list --limit 200", True), ("gh run view 1 --log", True),
                  ("gh api graphql -f q=x", True), ("gh pr view 3", False)):
    check(f"multi-call flag detected: {cmd[:28]}",
          any(m in cmd for m in ab.MULTI), want)

# ── a failed quota read is None, never a number ──────────────────────────────
real = ab.subprocess.run
class Fake:
    def __init__(s, rc, out=""): s.returncode, s.stdout, s.stderr = rc, out, ""
ab.subprocess.run = lambda *a, **k: Fake(1)
check("rate_limit failing is None, NOT a full pool", ab.quota(), None)
ab.subprocess.run = lambda *a, **k: Fake(0, "")
check("rate_limit returning empty is None too", ab.quota(), None)
ab.subprocess.run = lambda *a, **k: Fake(0, "0\t5000\t99\n")
check("an EXHAUSTED pool is a real reading, not an error", ab.quota(), (0, 5000, 99))
ab.subprocess.run = real

# ── an empty corpus establishes nothing ──────────────────────────────────────
with tempfile.TemporaryDirectory() as t:
    per, subs, multi, files, unread, _how = ab.scan(os.path.join(t, "*.jsonl"), 9)
    check("no transcripts -> zero invocations and zero files",
          (sum(per.values()), files), (0, 0))
    d = os.path.join(t, "p"); os.makedirs(d)
    # ⚠ THE BOOTSTRAP LINE IS NOW LOAD-BEARING, and this test found that out.
    # Selection is by IDENTITY: a transcript that never declares a role is not read
    # at all. Without the line below this fixture scans to ZERO — which is correct
    # behaviour and a broken fixture. ⇒ A fixture standing in for a PANE must now
    # look like one; "it contains a gh call" is no longer enough to be counted.
    with open(os.path.join(d, "aaaaaaaa-x.jsonl"), "w") as f:
        f.write(json.dumps({"type": "user", "message":
                            {"content": "You are DEVOPS. go."}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "gh pr view 9 && echo 'gh pr view mentioned'"}}]}}) + "\n")
    per, subs, multi, files, unread, _how = ab.scan(os.path.join(d, "*.jsonl"), 9)
    check("one real call plus one mention counts ONE", sum(per.values()), 1)


# ── ⛔ SELECTION BY IDENTITY, NOT RECENCY — the SAME defect fixed in
#    issue-coverage.py, which lived on unfixed in this sibling ────────────────
# Measured 2026-08-21 with the SAME parser, one variable changed:
#
#   CODER2 +948 · CODER4 +439 · CODER3 +91 · IMPLEMENTER +2 · CODER +1
#   b00d725a -959 · a8090f6b -179 · 86f48924 -157 · ef1ad25e -152 · ...
#   total: identity 11,703   recency 11,709
#
# ★ THE TOTALS AGREED WITHIN 0.05% AND EVERY ATTRIBUTION WAS WRONG. This tool's
# product is a pane's SHARE of one pool, so attribution IS the answer — and 1,481
# invocations belonged to five named panes that recency counted as ZERO.
#
# ⚠ The bias is worse here than in issue-coverage: a pane that is idle (thinking,
# blocked, waiting on the meter) leaves the window, so the tool under-reports
# consumption exactly when the pool is exhausted and everyone is idle waiting for
# it — the only moment anyone reads it.
with tempfile.TemporaryDirectory() as d:
    def pane(sid, role, calls):
        q = os.path.join(d, sid + ".jsonl")
        recs = [{"type": "user", "message": {"content":
                 f"You are {role}. go." if role else "hello, go."}}]
        for _ in range(calls):
            recs.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash",
                 "input": {"command": "gh pr view 1"}}]}})
        with open(q, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        return q

    roled = [pane(f"r{i}", r, 3) for i, r in enumerate(["ARCHITECT", "DEVOPS", "DX"])]
    anon = [pane(f"a{i}", None, 5) for i in range(3)]
    root = os.path.join(d, "*.jsonl")

    def stamp(order):
        for k, path in enumerate(order):
            os.utime(path, (1_700_000_000 - k * 60,) * 2)

    stamp(anon + roled)          # anonymous panes are the FRESHEST
    sel, note = ab.select_panes(root, 64)
    check("identity ignores mtime entirely — only the role-named are read",
          set(sel), set(roled))
    check("...and an anonymous session is never read", set(sel) & set(anon), set())

    stamp(roled + anon)          # flip the freshness order completely
    check("reversing every mtime does not move the set",
          set(ab.select_panes(root, 64)[0]), set(roled))

    # ⛔ KNOWN-BAD CONTROL — without it the checks above would also pass against a
    # selector that ignored mtime by accident. The OLD selection must MOVE.
    stamp(anon + roled)
    old_a = sorted(glob.glob(root), key=lambda q: -os.path.getmtime(q))[:3]
    stamp(roled + anon)
    old_b = sorted(glob.glob(root), key=lambda q: -os.path.getmtime(q))[:3]
    check("KNOWN-BAD control: the OLD recency selection DOES move", set(old_a) != set(old_b), True)
    check("KNOWN-BAD control: ...and it picks up the anonymous panes", set(old_a), set(anon))

    # the attribution consequence, end to end through the real parser
    per, _s, _m, files, _u, how = ab.scan(root, 64)
    check("every named role is attributed", sorted(per), ["ARCHITECT", "DEVOPS", "DX"])
    check("...and the counts are the real ones", sum(per.values()), 9)
    check("the note names the selection", "selection: identity" in how, True)

    # a bound limit must announce itself and say what it costs
    _sel, note = ab.select_panes(root, 2)
    check("a bound --limit says BOUND", "BOUND" in note, True)
    check("...and says the dropped panes count as ZERO", "counted as ZERO" in note, True)
    check("an unbound limit claims no ceiling", "BOUND" in ab.select_panes(root, 64)[1], False)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
