#!/usr/bin/env python3
"""Are the six required elements present in each goal file?

⛔ WHY A CHECKER AND NOT A CLEARER STANDARD. `goals/README.md` §1-6 is durable,
delivered, correct and unambiguous — and four of four goal files omitted §5 and §6,
then a fifth, written by an author who had read the standard, satisfied five of six
and omitted a DIFFERENT one. That distribution is the evidence: the template is not
the problem, NOTHING CHECKS COMPLETENESS. Six required headings is the most
mechanically checkable rule in the standard and it is the one being missed.

⛔ THE LOAD-BEARING PROPERTY: READ THE FILE AT A REVISION, NEVER A DIFF.

The manual check this replaces produced a FALSE FAIL, and the cause is not what it
first looked like. A reviewer ruled a goal file non-conformant for a missing
`## Desired state`, evidenced by a grep filtered to ADDED lines:

    git show <ref> -- <file> | grep -c "^+## Desired state"   ->  0
    git show <ref> -- <file> | grep -c "^ ## Desired state"   ->  1   (context, unchanged)
    git log -S"## Desired state"                              ->  present since 13:15

The section had been in the file for hours. The re-scope preserved it byte-identical,
so it appears as an ADDED line exactly zero times.

★ AND THE DIRECTION IS PERVERSE, WHICH IS WHY IT NEEDS A GUARD AND NOT A NOTE:
conformance is a property of the FILE; a diff answers *what did this change add*.
Different propositions — and the second is SILENT ABOUT EVERY ELEMENT A CHANGE
CORRECTLY LEFT ALONE. **The better a re-scope is at preserving what already
conformed, the less of it a diff-based review can see.** A file that satisfied all
six and changed nothing would read as satisfying none.

⇒ So: never `gh pr diff`, never `git show <ref> -- <file>`, never `^+`. Read the
file, at a named revision, and print the revision read. ⚠ A future maintainer
optimising this toward a diff for speed reintroduces exactly this defect, and it
will present as a confident FAIL on the most conservative changes.

⚠ Two other explanations were offered for the same failure and BOTH WERE WRONG:
`gh` lag (measured: the commit landed thirty minutes before the review, no race)
and a separator-keyed heading extractor (the reviewer's grep keyed on `## `, not on
an em-dash). Recorded because a checker built against a plausible-but-wrong
diagnosis guards a door nothing came through — the decoration-tolerant matching
below is still right, and it is not what went wrong.

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
    # ⛔ THE PROPERTY ITSELF, MADE EXECUTABLE. A docstring saying "never a diff"
    # does not stop a maintainer optimising toward one. This asserts that the
    # diff-based method FAILS on a case the file-based method passes — so if
    # anyone rewrites check() to read a diff, this control goes red rather than
    # the tool going quietly wrong on the most conservative changes.
    #
    # The view a diff gives of a conformant file that was NOT modified: no added
    # lines at all. Faithful to the real incident — the heading was preserved
    # byte-identical, so it appeared as an added line exactly zero times.
    diff_view = "\n".join(l for l in full.splitlines() if l.startswith("+"))
    diff_missing = [l for l, v in check(diff_view) if not v]
    file_missing = [l for l, v in check(full) if not v]
    ok_diff = len(diff_missing) == 6 and file_missing == []
    print(f"  known-positive  diff view of an UNCHANGED conformant file : "
          f"{len(diff_missing)}/6 read as missing")
    print(f"  known-negative  same content read as a FILE               : "
          f"{len(file_missing)}/6 missing")
    if not ok_diff:
        print("  ⛔ the file/diff distinction is not being enforced — if check() now reads "
              "a diff, it will report a confident FAIL on any change that correctly left "
              "a conforming section alone", file=sys.stderr)

    ok = ok_full and ok_miss and ok_dec and ok_diff
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def main():
    if "--self-test" in sys.argv:
        return self_test()
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    # ⛔ NOT "every .md that is not README". That population is wrong and it fired
    # the moment this checker got a caller: `goals/RESERVED-ACTIONS.md` is a shared
    # reference, not a role goal, and it was reported as missing five of six.
    # A checker whose population is "everything in the directory" measures the
    # directory's naming discipline, not the thing it claims to check.
    #
    # A role goal declares a Repository line — the standard's own header form.
    # ⚠ Files that carry it and nothing else are still checked, which is correct:
    # a file claiming to be a role goal must satisfy the six.
    files, skipped = [], []
    for f in sorted(os.listdir("goals")) if os.path.isdir("goals") else []:
        if not f.endswith(".md") or f == "README.md":
            continue
        head = open(os.path.join("goals", f), errors="replace").read(2000)
        (files if re.search(r"^\*\*Repository:\*\*", head, re.M) else skipped).append(f)
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
    # ⛔ Name what was skipped. A population that silently excludes files is how
    # "all conformant" gets believed — and the exclusion rule here is a heuristic
    # on a header line, not a fact about the file.
    if skipped:
        print(f"⚠ NOT CHECKED (no `**Repository:**` header, so not treated as a role goal): "
              f"{', '.join(skipped)}. That is a heuristic — if one of these IS a role goal, "
              f"this run missed it.", file=sys.stderr)
    print("⚠ Presence of a HEADING, not quality of its content. A §1 that is present "
          "and aspirational passes here and should still fail review.", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
