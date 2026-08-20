#!/usr/bin/env python3
"""Did this pane READ the artifact a pointer named, before acting on the pointer?

⛔ THE GAP. "Verify at the artifact, never the message" is this fleet's mitigation
for #3 — substrate-generated text is untrusted input — and TEAMLEAD recorded that
it is DOCTRINE WITH NO EXECUTION RECORD. That is #2's shape: a check whose
execution rate is memory, unrecorded and unqueryable.

⚠ AND THE OBVIOUS VERSION OF THIS TOOL IS #26. A predicate asking "did ANY
artifact command run after the pointer" scores 21 of 23 on this author's own
transcript — and would score any LIVE pane clean, because a working pane always
runs `git` for some other reason. A control that passes whenever the pane is alive
has no reachable failing state. That measurement establishes only that the
measurement is possible.

★ SO THE PREDICATE IS SPECIFIC: did a command read THE ref-and-path THE POINTER
NAMED. That is reachable — a pane can read a different artifact, or none.

⛔⛔ AND THE FAILURE MODE IS GUARANTEED, NOT HYPOTHETICAL. A pointer's text
CONTAINS the command that would verify it:

    DOCTRINE POINTER … get the tool:
    git show origin/main:tools/doctrine-watch.py > /tmp/dw.py

⇒ Any scan over the whole turn finds `git show origin/main:tools/doctrine-watch.py`
INSIDE THE POINTER and reports the pointer as self-verifying. **The population of
false positives is created by the pointer format itself** (#36) — so this tool
reads NAMED artifacts from the inbound turn and EVIDENCE only from assistant
`tool_use` command fields. Two different keys in the same record; a quotation
cannot occupy a tool call.

Exit: 0 every named artifact was read · 1 at least one was not · 2 ESTABLISHED
      NOTHING (no transcript, or no pointer named an artifact) · 3 control failed.
"""
import argparse, glob, json, os, re, sys

PROJECTS = os.path.expanduser("~/.claude/projects")

# `<ref>:<path>` as a pointer writes it, and bare doctrine paths named in prose.
REF_PATH = re.compile(r"\b([0-9a-f]{7,40}|origin/[A-Za-z0-9_.-]+|HEAD)"
                      r":([A-Za-z0-9_./-]+\.(?:md|py|json|sh|yml|yaml))")
BARE_PATH = re.compile(r"\b((?:goals|prompts|tools|scripts|docs)/[A-Za-z0-9_.-]+"
                       r"\.(?:md|py|json|sh|yml|yaml))")
ISSUE_REF = re.compile(r"gh issue view (\d+)|gh pr view (\d+)")

# A turn is pointer-shaped if it announces moved doctrine or names a ref to read.
# Locally generated, never inbound: slash-command echoes, their stdout, hook notices.
LOCAL_OUTPUT = re.compile(r"<command-name>|<local-command-stdout>|A session-scoped Stop hook")

POINTER = re.compile(r"DOCTRINE|POINTER|read (?:it|them|yours) at|at the (?:ref|artifact)|"
                     r"re-read|read your row", re.I)


def named_artifacts(text):
    """Paths this pointer TELLS the reader to go and read."""
    out = set()
    for _ref, path in REF_PATH.findall(text):
        out.add(path)
    for path in BARE_PATH.findall(text):
        out.add(path)
    return out


def reads_of(cmd):
    """Paths this COMMAND actually reads. Evidence, never prose."""
    out = set()
    for _ref, path in REF_PATH.findall(cmd):
        out.add(path)
    # `gh issue view N --comments`, `cat goals/x.md`, `sed -n … goals/x.md`
    for path in BARE_PATH.findall(cmd):
        out.add(path)
    return out


def walk(path):
    """Ordered [(kind, timestamp, text)] — kind is 'in' or 'cmd'."""
    out = []
    for ln in open(path, errors="replace"):
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        t = rec.get("type")
        if t == "user":
            c = (rec.get("message") or {}).get("content")
            if isinstance(c, str):
                out.append(("in", rec.get("timestamp", ""), c))
        elif t == "assistant":
            for b in (rec.get("message") or {}).get("content") or []:
                # ⛔ ONLY the command field. Assistant TEXT discussing a command is
                # a mention; this is the same key discipline use-not-mention.py
                # applies to source, applied to a transcript.
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    cmd = (b.get("input") or {}).get("command")
                    if isinstance(cmd, str):
                        out.append(("cmd", rec.get("timestamp", ""), cmd))
    return out


def audit(records):
    """[(ts, verdict, named, read_in_window)] for each pointer-shaped inbound turn."""
    rows = []
    for i, (kind, ts, text) in enumerate(records):
        # ⛔ LOCAL COMMAND OUTPUT IS NOT AN INBOUND POINTER. `/goal` echoes and Stop-hook
        # activations contain "re-read" and a path, so the pointer predicate matched them
        # and scored two UNVERIFIED rows against text this pane GENERATED. Measured on
        # this author's own transcript: 2 of 5 failures were that class. ⇒ A predicate
        # that matches locally-produced text is measuring the pane against itself.
        if kind != "in" or LOCAL_OUTPUT.match(text.lstrip()):
            continue
        if not POINTER.search(text) or len(text) < 120:
            continue
        named = named_artifacts(text)
        if not named:
            rows.append((ts, "NO-ARTIFACT-NAMED", set(), set()))
            continue
        seen = set()
        for k2, _ts2, txt2 in records[i + 1:]:
            if k2 == "in" and len(txt2) >= 120:
                break                      # window closes at the next inbound turn
            if k2 == "cmd":
                seen |= reads_of(txt2)
        missing = named - seen
        if not missing:
            rows.append((ts, "VERIFIED", named, seen & named))
        elif seen:
            rows.append((ts, "READ-DIFFERENT", named, seen & named))
        else:
            rows.append((ts, "UNVERIFIED", named, set()))
    return rows


def self_test():
    """⛔ The load-bearing control is the SELF-SATISFACTION guard: a pointer whose
    own text contains the verifying command, followed by NO commands, must read
    UNVERIFIED. That case is guaranteed in production — pointers quote the command
    they want run — so a tool that passes it is reading evidence, and one that
    fails it is reading the pointer back to itself."""
    ptr = ("DOCTRINE POINTER — read it at the ref, do not take it from me: "
           "git show origin/main:goals/RESERVED-ACTIONS.md | sed -n '1,20p'")
    cases = [
        ("pointer, then a read of the NAMED artifact",
         [("in", "t", ptr), ("cmd", "t", "git show origin/main:goals/RESERVED-ACTIONS.md")],
         "VERIFIED"),
        ("⛔ pointer quoting the command, then NO commands at all",
         [("in", "t", ptr)], "UNVERIFIED"),
        ("pointer, then a read of a DIFFERENT artifact",
         [("in", "t", ptr), ("cmd", "t", "git show origin/main:goals/README.md")],
         "READ-DIFFERENT"),
        ("pointer naming nothing readable",
         [("in", "t", "DOCTRINE MOVED. Go and re-read your row somewhere." + " x" * 60)],
         "NO-ARTIFACT-NAMED"),
    ]
    ok = True
    for label, recs, want in cases:
        got = audit(recs)
        v = got[0][1] if got else "NO-ROW"
        good = v == want
        ok = ok and good
        kind = "known-negative" if want == "VERIFIED" else "known-positive"
        print(f"  {kind}  {'✅' if good else '⛔'} {v:<18} {label}")
    if not ok:
        print("  ⛔ the audit either self-satisfies from the pointer's own text, or cannot "
              "separate reading the NAMED artifact from reading any artifact", file=sys.stderr)
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", help="transcript sessionId prefix (default: every session found)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("Pointer verification — did the pane read the artifact the pointer NAMED?\n")
    if not self_test_quiet():
        print("⛔ CONTROL FAILED — the audit self-satisfies from the pointer's own text. "
              "No verdict below would mean anything.", file=sys.stderr)
        return 3

    files = sorted(glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")))
    if args.session:
        files = [f for f in files if os.path.basename(f).startswith(args.session)]
    if not files:
        print("⛔ no transcripts found — ESTABLISHED NOTHING.", file=sys.stderr)
        return 2
    bad = total = 0
    for f in files:
        rows = audit(walk(f))
        rows = [r for r in rows if r[1] != "NO-ARTIFACT-NAMED"]
        if not rows:
            continue
        print(f"  {os.path.basename(f)[:8]}")
        for ts, v, named, read in rows:
            total += 1
            bad += v != "VERIFIED"
            mark = "ok  " if v == "VERIFIED" else "FAIL"
            print(f"    {mark} [{ts[11:19]}Z] {v:<16} named={sorted(named)}"
                  + (f" read={sorted(read)}" if v == "READ-DIFFERENT" else ""))
    if not total:
        print("⛔ no pointer named a readable artifact — ESTABLISHED NOTHING, not compliance.",
              file=sys.stderr)
        return 2
    print(f"\n{total - bad} of {total} pointers had their NAMED artifact read in-window.",
          file=sys.stderr)
    print("⚠ Reads EVIDENCE from tool_use command fields only. A pointer quotes the command "
          "it wants run, so a scan over the turn text would report every pointer as "
          "self-verifying.", file=sys.stderr)
    print("⛔ In-window means before the next inbound turn. A read AFTER that is real "
          "verification this tool cannot see — the count is a LOWER bound on compliance.",
          file=sys.stderr)
    print("⛔ READ-DIFFERENT OVER-REPORTS, and the reason is not a bug. A doctrine pointer "
          "names every file in a role's row, including files whose targeted delta is +0/-0. "
          "Reading only the CHANGED ones is correct and scores FAIL here. ⇒ This tool "
          "measures 'was every NAMED artifact read', which is not the same proposition as "
          "'did the pane verify what it acted on'. Stated rather than tuned away: narrowing "
          "the predicate to guess which named file mattered would replace a visible "
          "over-report with an invisible under-report.", file=sys.stderr)
    return 1 if bad else 0


def self_test_quiet():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return self_test() == 0


if __name__ == "__main__":
    sys.exit(main())
