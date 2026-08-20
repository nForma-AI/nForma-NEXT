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
import json, os, sys, tempfile, types

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
ab.subprocess.run = lambda *a, **k: Fake(0, "not json")
check("unparseable rate_limit is None", ab.quota(), None)

# ⛔ IT IS NOT ONE POOL. core can be EXHAUSTED while graphql is two-thirds free,
# and reporting only core turns "one bucket is empty" into "we are rate limited".
payload = json.dumps({"resources": {
    "core":    {"remaining": 0,    "limit": 5000, "reset": 99},
    "graphql": {"remaining": 3508, "limit": 5000, "reset": 99},
    "search":  {"remaining": 30,   "limit": 30,   "reset": 99}}})
ab.subprocess.run = lambda *a, **k: Fake(0, payload)
q = ab.quota()
check("all three buckets are read", sorted(q), ["core", "graphql", "search"])
check("an EXHAUSTED bucket is a real reading, not an error", q["core"], (0, 5000, 99))
check("...and a FREE bucket is reported alongside it", q["graphql"][0], 3508)
check("KNOWN-BAD control: reading core alone calls this 'rate limited'",
      q["core"][0] == 0 and q["graphql"][0] > 0, True)

# a payload with no recognised bucket is None, never an empty-but-healthy reading
ab.subprocess.run = lambda *a, **k: Fake(0, json.dumps({"resources": {"weird": {}}}))
check("no recognised bucket is None, not {}", ab.quota(), None)
ab.subprocess.run = real

# ── an empty corpus establishes nothing ──────────────────────────────────────
with tempfile.TemporaryDirectory() as t:
    per, subs, multi, files, unread = ab.scan(os.path.join(t, "*.jsonl"), 9)
    check("no transcripts -> zero invocations and zero files",
          (sum(per.values()), files), (0, 0))
    d = os.path.join(t, "p"); os.makedirs(d)
    with open(os.path.join(d, "aaaaaaaa-x.jsonl"), "w") as f:
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "gh pr view 9 && echo 'gh pr view mentioned'"}}]}}) + "\n")
    per, subs, multi, files, unread = ab.scan(os.path.join(d, "*.jsonl"), 9)
    check("one real call plus one mention counts ONE", sum(per.values()), 1)

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
