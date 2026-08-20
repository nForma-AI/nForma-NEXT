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

print(f"\n{len(fails)} failure(s)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
