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

⇒ SCOPE, added under #16: a goal file written FOR this repository vs one that
merely NAMES it. See the SCOPE block below for the measurements that motivated it.

★ PROVEN DISCRIMINATING END-TO-END, not just in the unit self-test. Reproduce:

    SIX=$'## Desired state\n## Reserved actions\n## Self-dispatch order\n'\
        $'## Standing calibrations\n## What this role does NOT own\n## Channel contract'
    mkdir -p .fx-a/goals .fx-b/goals .fx-empty/goals
    { echo '**Repository:** /x -> github.com/nForma-AI/nForma-NEXT'; echo "$SIX"; } > .fx-a/goals/role.md
    { echo 'This goal is for work in nForma-NEXT, the nForma-NEXT repository.';
      echo "$SIX"; } > .fx-b/goals/role.md
    python3 tools/discriminates.py \
      --a "cd $PWD/.fx-a && python3 $PWD/scripts/check-goal-conformance.py" \
      --b "cd $PWD/.fx-b && python3 $PWD/scripts/check-goal-conformance.py" \
      --control-a "cd $PWD/.fx-a && python3 $PWD/scripts/check-goal-conformance.py" \
      --control-b "cd $PWD/.fx-empty && python3 $PWD/scripts/check-goal-conformance.py"

    -> ✅ DISCRIMINATED   conforming exit=0 · mention-only exit=1

⛔ THE FIXTURES MUST LIVE INSIDE THE REPOSITORY. Outside it, `git remote get-url
origin` fails, scope reads UNVERIFIABLE for BOTH sides, and the comparison reports
NON-DISCRIMINATING for a reason that has nothing to do with the check — an
identical reading from two states that were never actually compared, which is the
exact failure discriminates.py exists to refuse.

Exit: 0 all conformant · 1 an element is missing OR a file is not scoped to this
      repository · 2 ESTABLISHED NOTHING.
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

# ⛔ THE SCOPE DISCRIMINATOR — written FOR this repository vs merely NAMING it.
#
# The original defect (#16): a grep matched *mentions* of the repository name and
# reported 3 of 4 files scoped here when the true count was 4 of 4 vendored. One
# file carried no `Repository:` line at all and its body merely mentioned the repo.
#
# ⚠ And this checker inherited the same shape from the other side. Measured before
# the fix, on two constructed files:
#
#   role goal, NO Repository: line, body names this repo 3x  -> exit 2, "no goal
#                                                               files found"  (INVISIBLE)
#   role goal declaring Borduas-Holdings/Blazing-Back        -> exit 0, "1 of 1
#                                                               conformant"   (⛔ PASSES)
#
# ⇒ The line was used as a POPULATION FILTER and its VALUE was never read. So the
# checker discriminated "has a Repository line" from "has none", and never "names
# THIS repository" from "names another" — which is the only question #16 asks.
#
# ★ A mention cannot produce a structural field. `**Repository:** … → github.com/o/r`
# is a declaration at a fixed position in a fixed form; prose saying "for work in
# nForma-NEXT" cannot occupy it. Same rule as #36: match on something a mention
# cannot produce.
SCOPE = re.compile(r"^\*\*Repository:\*\*\s*(.+)$", re.M)
SLUG = re.compile(r"github\.com[:/]+([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?\s*$")

# How many of the six a file must show before "no Repository: line" is read as a
# DEFECT rather than as "not a role goal". ⛔ Without this, a role goal missing its
# scope declaration falls out of the population and is reported as skipped — which
# is the exact case that produced the false 3-of-4, and skipped reads as benign.
GOAL_SHAPED = 4


def this_repo():
    """The repository this checkout actually is, from the remote. Not a constant."""
    out = subprocess.run(["git", "remote", "get-url", "origin"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    m = SLUG.search(out.stdout.strip())
    return (m.group(1).lower(), m.group(2).lower()) if m else None


def declared_scope(text):
    """(owner, repo) declared by the structural field, or None if absent/unparseable."""
    m = SCOPE.search(text)
    if not m:
        return None
    m2 = SLUG.search(m.group(1).strip())
    return (m2.group(1).lower(), m2.group(2).lower()) if m2 else None


def scope_verdict(text, mine):
    """FOR-THIS-REPO · FOREIGN · MENTION-ONLY · NO-DECLARATION · UNVERIFIABLE.

    ⚠ MENTION-ONLY is reported separately from NO-DECLARATION on purpose. Both fail,
    and they fail for different reasons a reader must be able to act on: one file is
    a goal that forgot to say where it applies; the other reads as though it says so
    and does not. Collapsing them is how the original 3-of-4 was produced.
    """
    if mine is None:
        return "UNVERIFIABLE", "cannot read origin remote — scope ESTABLISHED NOTHING"
    got = declared_scope(text)
    if got:
        if got == mine:
            return "FOR-THIS-REPO", f"declares {got[0]}/{got[1]}"
        return "FOREIGN", f"declares {got[0]}/{got[1]}, this repo is {mine[0]}/{mine[1]}"
    shaped = sum(v for _, v in check(text))
    names_it = re.search(re.escape(mine[1]), text, re.I) is not None
    if shaped >= GOAL_SHAPED and names_it:
        return "MENTION-ONLY", (f"{shaped}/6 role-goal headings and the name {mine[1]!r} in the "
                                f"body, but NO `**Repository:**` declaration — it names this "
                                f"repository without being scoped to it")
    if shaped >= GOAL_SHAPED:
        return "NO-DECLARATION", f"{shaped}/6 role-goal headings and no `**Repository:**` line"
    return "NOT-A-ROLE-GOAL", f"only {shaped}/6 role-goal headings"


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

    # ⛔ THE SCOPE DISCRIMINATOR, both directions. #16 is a false NEGATIVE about
    # scoping produced by matching mentions; the control must show the check
    # separates a declaration from a mention, and must show it does not simply
    # fail everything.
    mine = ("nforma-ai", "nforma-next")
    six = "\n".join(f"## {lbl.split(' ', 1)[1]}" for lbl, _ in REQUIRED)
    decl = "**Repository:** /x → github.com/nForma-AI/nForma-NEXT\n" + six
    foreign = "**Repository:** /x → github.com/Borduas-Holdings/Blazing-Back\n" + six
    mention = "This goal is for work in nForma-NEXT, the nForma-NEXT repository.\n" + six
    silent = six
    cases = [("declares this repo", decl, "FOR-THIS-REPO"),
             ("declares another repo", foreign, "FOREIGN"),
             ("names it in prose only", mention, "MENTION-ONLY"),
             ("role-goal shaped, says nothing", silent, "NO-DECLARATION"),
             ("not a role goal at all", "## Unrelated", "NOT-A-ROLE-GOAL")]
    ok_scope = True
    for label, text, want in cases:
        got, _ = scope_verdict(text, mine)
        good = got == want
        ok_scope = ok_scope and good
        print(f"  {'known-negative' if want == 'FOR-THIS-REPO' else 'known-positive'}  "
              f"{'✅' if good else '⛔'} {got:<16} {label}")
    # ⛔ And the property #16 is actually about: the MENTION case must not be
    # reachable from the same verdict as the DECLARATION case, no matter how many
    # times the name appears in the body.
    spammed, _ = scope_verdict(("nForma-NEXT " * 40) + "\n" + six, mine)
    ok_spam = spammed == "MENTION-ONLY"
    print(f"  known-positive  {'✅' if ok_spam else '⛔'} {spammed:<16} "
          f"the name 40 times in the body, still no declaration")
    if not ok_scope or not ok_spam:
        print("  ⛔ the scope check does not separate a DECLARATION from a MENTION — which is "
              "the false 3-of-4 in #16, reproduced", file=sys.stderr)

    ok = ok_full and ok_miss and ok_dec and ok_diff and ok_scope and ok_spam
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
    # ⛔ POPULATION CHANGED, AND THE OLD RULE WAS THE DEFECT. Selecting on "carries a
    # `**Repository:**` line" made a role goal that OMITS the line invisible rather
    # than failing — measured: such a file produced "no goal files found", exit 2.
    # A file is now in scope if it carries the declaration OR is role-goal SHAPED
    # (>= GOAL_SHAPED of the six headings), so a missing declaration is a verdict
    # rather than an exclusion.
    mine = this_repo()
    files, skipped = [], []
    for f in sorted(os.listdir("goals")) if os.path.isdir("goals") else []:
        if not f.endswith(".md") or f == "README.md":
            continue
        text = open(os.path.join("goals", f), errors="replace").read()
        if re.search(r"^\*\*Repository:\*\*", text, re.M) or sum(v for _, v in check(text)) >= GOAL_SHAPED:
            files.append(f)
        else:
            skipped.append(f)
    if not files:
        print("⛔ no goal files found under goals/ — ESTABLISHED NOTHING, not conformant.\n"
              "   ADDABLE — FIXABLE HERE: run from the repository root.", file=sys.stderr)
        return 2
    bad = 0
    scoped_here = 0
    unverifiable = False
    print(f"goal conformance at {rev or '?'} (working tree, not a cached PR view)")
    print(f"this repository, from `git remote get-url origin`: "
          f"{mine[0] + '/' + mine[1] if mine else '⛔ UNREADABLE'}")
    for f in files:
        text = open(os.path.join("goals", f), errors="replace").read()
        miss = [l for l, v in check(text) if not v]
        verdict, why = scope_verdict(text, mine)
        ok_scope = verdict == "FOR-THIS-REPO"
        scoped_here += ok_scope
        unverifiable = unverifiable or verdict == "UNVERIFIABLE"
        bad += bool(miss) or not ok_scope
        mark = "ok  " if not miss and ok_scope else "FAIL"
        print(f"  {mark}  {f:<40} elements: "
              f"{'missing ' + ', '.join(miss) if miss else 'all six'}")
        print(f"        {'    ' if ok_scope else '⛔  '}scope: {verdict} — {why}")
    print(f"\n{len(files) - bad} of {len(files)} conformant "
          f"(six elements AND scoped to this repository).", file=sys.stderr)
    print(f"{scoped_here} of {len(files)} declare THIS repository structurally.", file=sys.stderr)
    print("⛔ A file that merely NAMES this repository in its body is reported "
          "MENTION-ONLY and counted as NOT scoped here — that distinction is #16, "
          "and a mention cannot occupy a `**Repository:**` declaration.", file=sys.stderr)
    if unverifiable:
        print("⛔ At least one scope verdict was UNVERIFIABLE (no readable origin remote). "
              "That is ESTABLISHED NOTHING, not a pass.", file=sys.stderr)
        return 2
    # ⛔ Name what was skipped. A population that silently excludes files is how
    # "all conformant" gets believed — and the exclusion rule here is a heuristic
    # on a header line, not a fact about the file.
    if skipped:
        print(f"⚠ NOT CHECKED (no `**Repository:**` declaration AND fewer than {GOAL_SHAPED} of "
              f"the six role-goal headings): {', '.join(skipped)}. ⛔ Both conditions must hold to "
              f"be excluded — a file with the headings and no declaration is now reported "
              f"MENTION-ONLY or NO-DECLARATION rather than skipped, because the old "
              f"declaration-only filter made exactly that file invisible.", file=sys.stderr)
    print("⚠ Presence of a HEADING, not quality of its content. A §1 that is present "
          "and aspirational passes here and should still fail review.", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
