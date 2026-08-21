#!/usr/bin/env python3
"""Can this close condition be RUN, or only agreed with?

⛔ THE GAP THIS FILLS, stated by the tool that found it: `close-condition-scan.py` checks
PRESENCE ONLY. `## Done when: it feels done` scores BODY. So does "when the file cools",
which ARCHITECT wrote into docs/DEFECT-CLASSES.md and could not evaluate three minutes
after merging it.

⚠ THIS DOES NOT CHECK FALSIFIABILITY. Falsifiability is not a string match and no tool
here claims to test it. This matches a PROXY that is HARDER TO FAKE than prose:

    does the condition name a COMMAND, and state the RESULT that would satisfy it?

⇒ A clause you can RUN has a reachable other answer. A clause you can only AGREE WITH does
not. That is #214's question -- "could this method have produced the other answer?" -- asked
of a close condition instead of a probe.

⛔ PRESENCE OF A HARDER FEATURE IS STILL PRESENCE. A condition can name a command that does
not test the thing, or an expected result nobody will check. This tool cannot see either,
and says so on every run so the number is not quoted without the limit.

⛔⛔⛔ AND `RUNNABLE` IS NOT `READABLE`. MEASURED BY RUNNING THE CONDITIONS THIS TOOL SCORED.

A condition can name a command and a result and still produce output that CANNOT DISTINGUISH
"not met" from "the check itself failed". Two of four run on 2026-08-21:

    #29   grep -rn 'doctrine-version' .github/workflows/ scripts/  ->  SILENCE
          which reads as BOTH "no invocation exists" AND "the grep found no files".
          Repaired to print `files=N hits=N`: files>0 & hits=0 is a readable NOT MET;
          files=0 is VOID.
    #345  a bare grep whose 0 hits and whose unreadable-file case are the same output.

⇒ THAT IS DEV3's ABSENT-PROBE RULE APPLIED TO CLOSE CONDITIONS. A command whose negative and
whose failure are one value has the collapse this repository has spent an evening filing, and
THIS TOOL SCORES IT `RUNNABLE`. ⚠ So `RUNNABLE = N` is not N usable conditions -- it is N
conditions that name a command. TEAMLEAD said as much as a caveat; this is the mechanism.

⛔⛔ AND `ASSERTED` IS NOT AUTOMATICALLY A DEFECT. Some conditions close on a judgement no
command can make -- "a hop is caught prospectively by someone who did not write the form"
has no invocation and is still the right bar. ⇒ ASSERTED means AGREEMENT IS THE ONLY ROUTE,
which is a fact about the condition, not a verdict on its author. Treating every ASSERTED
as a fault would manufacture commands that test nothing -- #73's warning against #73's own
remedy, one register over.

★ MEASURED ON ITS FIRST RUN, AGAINST ITS AUTHOR: 17 of 19 role:ARCHITECT issues scored
ASSERTED, including ALL TWELVE conditions ARCHITECT wrote an hour earlier using the full
population/predicate/channel/caller standard. Those conditions name the right things IN
PROSE. ⇒ Naming a population is not naming the command that draws it, and stating "CALLER
still runs: <doctrine>" is not an invocation. The standard was met and the conditions still
cannot be run.

Verdicts:
    RUNNABLE      names a command AND the result that satisfies it
    ASSERTED      a condition exists; agreement is the only way to satisfy it
    NO-CONDITION  nothing to judge -- close-condition-scan.py owns that finding
    VOID          could not read the issue

Exit codes:
    0  every condition read is RUNNABLE          (and both controls fired)
    1  at least one ASSERTED
    2  ESTABLISHED NOTHING -- unreadable, empty population, or truncated
       ⚠ never "all clear"
    3  CONTROL FAILED -- the positive did not fire, or the negative did
"""
import argparse, json, re, subprocess, sys

CONDITION = re.compile(
    r"^[ ]{0,3}(?:[-*+][ ]+)?(?:#{1,6}[ ]*)?(?:[⇒★⚠⛔→][ ]*)*(?:#{1,6}[ ]*)?"
    r"(?:\*\*|__)?[ ]*(?:done[ ]when|close[ ]when|closes[ ]when|acceptance[ ]criteria)",
    re.I | re.M)

# ⚠ An invocation, not a word, and NOT A CLOSED LIST OF COMMAND NAMES.
#
# ⛔ The first version of this enumerated gh|git|python3|bash|sh|make|./|tools/|scripts/ and
#    therefore could not see `grep`, `sed`, `diff`, `jq`, `curl` -- so it scored a condition
#    carrying `grep -c ... -> 0` as ASSERTED. That is a CLOSED LIST OVER AN OPEN-ENDED NOUN,
#    the same defect ARCHITECT ruled against in #348's FOREIGN_VOCAB three hours earlier,
#    committed inside the tool built to catch conditions that cannot fail.
#
# ⇒ Structural instead: a lowercase bare first token followed by a FLAG, a PATH, a REDIRECT
#   or a further token -- the shape of a command line, not a vocabulary of them. Prose that
#   MENTIONS a command does not match, because prose does not start a fenced line with one.
INVOCATION = re.compile(
    r"^[ ]{0,4}(?:\$[ ]*)?"
    r"(?:\./|[a-z][a-z0-9_.-]*/)?"                    # ./x  or  tools/x.py
    r"[a-z][a-z0-9_.+-]*[ ]+"                          # a lowercase command word, then
    r"(?=[^\n]*(?:-{1,2}[A-Za-z]|[/<>|'\"]))"          # SOMETHING ONLY A COMMAND CARRIES
    r"\S",
    re.M)
# ⛔ THE LOOKAHEAD IS LOAD-BEARING and exists because the first widening was too loose:
#    "the count must be zero." matched as `the` + an argument, and the live board went from
#    ASSERTED 10 to a FALSELY CONFIDENT RUNNABLE 11. ⇒ A second word is not a command line.
#    A FLAG, a PATH, a REDIRECT or a QUOTE is. Caught by the known-negative in self_test()
#    before the number left this pane.

# ⚠ A stated result: an arrow to a value, an exit code, or an explicit expectation.
RESULT = re.compile(
    r"(?:->|→|=>)\s*\S|exit(?:s|[ ]code)?[ ]*[0-9]|\bempty\b|\breturns\b|\bmust\b[ ]\S+|"
    r"\bzero\b|\bnon-zero\b", re.I)

FENCE = re.compile(r"```.*?```", re.S)


def classify(body):
    """⇒ Only text INSIDE the condition block is judged. A command elsewhere in the issue
    is not the condition, and counting it would be the wrong-population defect this
    repository has spent a night filing."""
    m = CONDITION.search(body or "")
    if not m:
        return "NO-CONDITION", ""
    block = body[m.start():]
    fences = FENCE.findall(block)
    hay = "\n".join(fences) if fences else block
    has_cmd = bool(INVOCATION.search(hay))
    has_res = bool(RESULT.search(hay))
    if has_cmd and has_res:
        return "RUNNABLE", ""
    why = []
    if not has_cmd:
        why.append("no invocation")
    if not has_res:
        why.append("no stated result")
    return "ASSERTED", " + ".join(why)


def fetch(repo, label, limit):
    args = ["gh", "issue", "list", "-R", repo, "--state", "open", "--limit", str(limit),
            "--json", "number,title,body"]
    if label:
        args += ["--label", label]
    p = subprocess.run(args, capture_output=True, text=True, timeout=180)
    if p.returncode != 0 or not p.stdout.strip():
        return None, f"gh exited {p.returncode}"
    try:
        rows = json.loads(p.stdout)
    except ValueError:
        return None, "unparseable JSON"
    if len(rows) >= limit:
        return None, f"returned exactly the limit ({limit}) — TRUNCATED, population unknown"
    return rows, None


def controls():
    """⛔ TWO-SIDED (DEV2, #353): a probe must demonstrate ON THIS RUN that it can return the
    answer it did not return. A one-sided control is blind to a predicate that says RUNNABLE
    for everything."""
    pos = classify("## Done when\n\n```\npython3 tools/x.py --self-test   ->   exit 0\n```")[0]
    neg = classify("## Done when\n\nthe fleet agrees the situation has improved.")[0]
    nothing = classify("A body with no clause at all.")[0]
    return (pos == "RUNNABLE", neg == "ASSERTED", nothing == "NO-CONDITION"), (pos, neg, nothing)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--repo", default="nForma-AI/nForma-NEXT")
    ap.add_argument("--label")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--states", action="store_true")
    a = ap.parse_args()

    print("NFORMA-RUN runnable-condition", file=sys.stderr)
    if a.states:
        for k, v in (("RUNNABLE", "names a command AND the result that satisfies it"),
                     ("ASSERTED", "a condition exists; agreement is the only way to satisfy it"),
                     ("NO-CONDITION", "nothing to judge — close-condition-scan.py owns it"),
                     ("VOID", "could not read")):
            print(f"VERDICT\t{k}\t{v}")
        for k, v in ((0, "every condition RUNNABLE"), (1, "at least one ASSERTED"),
                     (2, "established nothing"), (3, "control failed")):
            print(f"EXIT\t{k}\t{v}")
        return 0
    if a.self_test:
        return self_test()

    (p_ok, n_ok, z_ok), got = controls()
    if not (p_ok and n_ok and z_ok):
        print(f"⛔ CONTROL FAILED before reading anything: positive={got[0]} negative={got[1]} "
              f"empty={got[2]}", file=sys.stderr)
        return 3

    rows, err = fetch(a.repo, a.label, a.limit)
    if rows is None:
        print(f"⛔ VOID  {err} — ESTABLISHED NOTHING, not zero", file=sys.stderr)
        return 2
    if not rows:
        print("⛔ VOID  empty population — ESTABLISHED NOTHING", file=sys.stderr)
        return 2

    buckets = {"RUNNABLE": [], "ASSERTED": [], "NO-CONDITION": []}
    for r in rows:
        v, why = classify(r.get("body"))
        buckets[v].append((r["number"], r["title"], why))

    print(f"open issues read: {len(rows)} of {len(rows)} stated"
          + (f"   label={a.label}" if a.label else ""))
    for v in ("ASSERTED", "RUNNABLE", "NO-CONDITION"):
        print(f"\n{v}  ({len(buckets[v])})")
        for n, t, why in buckets[v][:40]:
            print(f"    #{n:<5} {t[:62]}" + (f"   [{why}]" if why else ""))

    print("\n⚠ ASSERTED IS NOT AUTOMATICALLY A DEFECT. Some conditions close on a judgement"
          "\n   no command can make. ASSERTED means agreement is the only route — a fact about the"
          "\n   condition, not a verdict on its author.")
    print("⛔ RUNNABLE IS NOT READABLE. A named command whose NOT-MET and whose OWN FAILURE"
          "\n   produce the same output is scored RUNNABLE here and cannot be acted on. Measured on"
          "\n   2 of 4 of this tool's author's own conditions.")
    print("⚠ PRESENCE OF A HARDER FEATURE IS STILL PRESENCE. A condition can name a command"
          "\n   that does not test the thing, or a result nobody will check. This does not test"
          "\n   FALSIFIABILITY and no count here should be quoted as if it did.")
    print("⚠ And these conditions are UNTESTED AGAINST A REAL CLOSURE ATTEMPT. The first pane"
          "\n   that tries to close one and finds it unusable has found a defect in the CONDITION,"
          "\n   not in their reading of it.")
    print("NFORMA-RESULT FINDINGS" if buckets["ASSERTED"] else "NFORMA-RESULT CLEAN", file=sys.stderr)
    return 1 if buckets["ASSERTED"] else 0


def self_test():
    ok = True

    def check(name, got, want):
        nonlocal ok
        if got != want:
            print(f"⛔ FAIL  {name}: got {got!r}, want {want!r}"); ok = False
        else:
            print(f"  PASS  {name}: {got!r}")

    check("command + arrow result is RUNNABLE",
          classify("## Done when\n```\ngh pr list -R x --json number  ->  empty\n```")[0], "RUNNABLE")
    check("command + exit code is RUNNABLE",
          classify("**Done when:**\n```\npython3 tools/x.py --self-test   exit 0\n```")[0], "RUNNABLE")
    # known-negative: prose that SOUNDS like a condition must not pass
    check("prose agreement is ASSERTED",
          classify("## Done when\nthe file cools and everyone agrees.")[0], "ASSERTED")
    check("a command with no stated result is ASSERTED",
          classify("## Done when\n```\ngh issue list\n```")[0], "ASSERTED")
    # ⛔ the closed-list regression: grep/sed/diff were invisible to the first predicate
    check("grep with a stated result is RUNNABLE",
          classify("## Done when\n```\ngrep -c \'x\' file.js   ->   0\n```")[0], "RUNNABLE")
    check("diff with a stated result is RUNNABLE",
          classify("## Done when\n```\ndiff a b   ->   empty\n```")[0], "RUNNABLE")
    # ⛔ regressions from widening the predicate away from a closed list of command names
    check("grep with a stated result is RUNNABLE",
          classify("## Done when\n```\ngrep -c 'x' file.js   ->   0\n```")[0], "RUNNABLE")
    check("diff over paths is RUNNABLE",
          classify("## Done when\n```\ndiff /tmp/a /tmp/b   ->   empty\n```")[0], "RUNNABLE")
    check("a two-word sentence is NOT an invocation",
          classify("## Done when\nthe count must be zero.")[0], "ASSERTED")
    check("a stated result with no command is ASSERTED",
          classify("## Done when\nthe count must be zero.")[0], "ASSERTED")
    check("no clause at all is NO-CONDITION",
          classify("just a body.")[0], "NO-CONDITION")
    # ⛔ use vs mention: a body that TALKS about running something, outside a fence
    check("a mention of gh in prose does not make it runnable",
          classify("## Done when\nsomeone runs gh issue list and is satisfied.")[0], "ASSERTED")
    # ⛔ population: a command elsewhere in the issue is not the condition
    check("a command ABOVE the clause does not count",
          classify("```\ngh pr list -> empty\n```\n\n## Done when\nwe are happy.")[0], "ASSERTED")
    (p, n, z), got = controls()
    check("the run-time controls themselves fire", (p, n, z), (True, True, True))
    print("all checks passed" if ok else "⛔ self-test FAILED")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
