#!/usr/bin/env python3
"""Are the six required elements present in each goal file?

⛔ WHY A CHECKER AND NOT A CLEARER STANDARD. `goals/README.md` §1-6 is durable,
delivered, correct and unambiguous — and four of four goal files omitted §5 and §6,
then a fifth, written by an author who had read the standard, satisfied five of six
and omitted a DIFFERENT one. That distribution is the evidence: the template is not
the problem, NOTHING CHECKS COMPLETENESS. Six required headings is the most
mechanically checkable rule in the standard and it is the one being missed.

⛔ AND THE MANUAL CHECK IT REPLACES PRODUCED A FALSE FAIL. A reviewer ran
`gh pr diff <n> | grep -i "desired state"`, got no output, and ruled a goal file
non-conformant for a section that was present — the same command reproduced minutes
later returns it at line 55. `gh` lags the remote ref; it has been measured lagging
three times in one session.

⇒ So this reads THE FILE, at a named revision, and prints the revision it read.
A conformance verdict that cannot say what it inspected is not a verdict.

Exit: 0 all conformant · 1 an element is missing · 2 ESTABLISHED NOTHING.
"""
import os, re, subprocess, sys

# The six, from goals/README.md "What a role goal must contain". Each entry is
# (label, regex over headings). ⚠ Matched on HEADINGS, not on body text: a file
# that merely discusses "reserved actions" in prose has not stated them where every
# agent they bind will read them.
REQUIRED = [
    ("1 Desired state",      r"desired state"),
    ("2 Reserved actions",   r"reserved"),
    ("3 Self-dispatch order", r"self-dispatch"),
    ("4 Standing calibrations", r"calibration"),
    ("5 Does NOT own",       r"not own"),
    ("6 Channel contract",   r"channel contract"),
]

# ⛔ Deliberately permissive on decoration and strict on the noun. Headings here
# carry ⚠ ⛔ ★ prefixes and em-dash suffixes; a checker keyed on exact text would
# fail every file in the directory. The reviewer's own manual extraction dropped
# `## Desired state` — the ONE heading with no suffix — which is the failure mode
# an exact-match rule reproduces.
HEADING = re.compile(r"^#{2,3}\s+(.*)$", re.M)


def headings(text):
    return [h.strip() for h in HEADING.findall(text)]


def check(text):
    hs = " || ".join(headings(text)).lower()
    return [(label, bool(re.search(rx, hs))) for label, rx in REQUIRED]


def self_test():
    """Both directions. A checker that has only ever passed is not a checker."""
    full = "\n".join(f"## {lbl.split(' ', 1)[1]}" for lbl, _ in REQUIRED)
    missing = "\n".join(f"## {lbl.split(' ', 1)[1]}" for lbl, _ in REQUIRED[1:])
    decorated = ("## ⚠ Desired state — and how to tell\n## ⛔ Reserved to TEAMLEAD\n"
                 "## ★ Self-dispatch order — must return EMPTY\n## Standing calibrations\n"
                 "## What this role does NOT own\n## Channel contract")
    ok_full = all(v for _, v in check(full))
    ok_miss = [l for l, v in check(missing) if not v] == ["1 Desired state"]
    ok_dec = all(v for _, v in check(decorated))
    print(f"  known-negative  all six present      : {'pass' if ok_full else 'FAIL'}")
    print(f"  known-positive  §1 removed           : {'detected' if ok_miss else 'MISSED'}")
    print(f"  known-negative  decorated headings   : {'pass' if ok_dec else 'FAIL'}")
    print("  ⇒ the decorated case is the one that matters: the manual check this "
          "replaces dropped the only heading with no suffix.", file=sys.stderr)
    ok = ok_full and ok_miss and ok_dec
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def main():
    if "--self-test" in sys.argv:
        return self_test()
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    files = sorted(f for f in os.listdir("goals")
                   if f.endswith(".md") and f != "README.md") if os.path.isdir("goals") else []
    if not files:
        print("⛔ no goal files found under goals/ — ESTABLISHED NOTHING, not conformant.\n"
              "   ADDABLE — FIXABLE HERE: run from the repository root.", file=sys.stderr)
        return 2
    bad = 0
    print(f"goal conformance at {rev or '?'} (working tree, not a cached PR view)")
    for f in files:
        text = open(os.path.join("goals", f), errors="replace").read()
        res = check(text)
        miss = [l for l, v in res if not v]
        bad += bool(miss)
        print(f"  {'FAIL' if miss else 'ok  '}  {f:<40} {'missing: ' + ', '.join(miss) if miss else 'all six'}")
    print(f"\n{len(files) - bad} of {len(files)} conformant.", file=sys.stderr)
    print("⚠ Presence of a HEADING, not quality of its content. A §1 that is present "
          "and aspirational passes here and should still fail review.", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
