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
    REC='{"terminals":[{"type":"claude","title":"ROLEX",
          "env":{"NFORMA_ROLE":"ROLEX","NFORMA_GOAL":"goals/role.md"}}]}'
    for v in a b; do mkdir -p .fx-$v/goals .fx-$v/.daintree/recipes
      echo "$REC" > .fx-$v/.daintree/recipes/nforma-fleet.json; done
    { echo '**Repository:** /x -> github.com/nForma-AI/nForma-NEXT'; echo "$SIX"; } > .fx-a/goals/role.md
    { echo 'This goal is for work in nForma-NEXT, the nForma-NEXT repository.';
      echo "$SIX"; } > .fx-b/goals/role.md
    python3 tools/discriminates.py \
      --a "cd $PWD/.fx-a && python3 $PWD/scripts/check-goal-conformance.py" \
      --b "cd $PWD/.fx-b && python3 $PWD/scripts/check-goal-conformance.py"

    -> ✅ DISCRIMINATED   conforming exit=0 · mention-only exit=1

⛔ THE FIXTURES MUST LIVE INSIDE THE REPOSITORY. Outside it, `git remote get-url
origin` fails, scope reads UNVERIFIABLE for BOTH sides, and the comparison reports
NON-DISCRIMINATING for a reason that has nothing to do with the check — an
identical reading from two states that were never actually compared, which is the
exact failure discriminates.py exists to refuse. ⚠ Measured on the first attempt:
it presented as "my check does not work", not as "my harness is misconfigured".

Exit: 0 all conformant · 1 an element is missing OR a file is not scoped to this
      repository · 2 ESTABLISHED NOTHING.
"""
import json, os, re, subprocess, sys

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
# ⚠ Tolerant of MARKUP, strict about the FIELD. Optional list bullet, optional
# bold, colon inside or outside the emphasis. ⛔ Not tolerance for its own sake —
# measured: the original pattern required exactly `**Repository:**` and read FOUR
# of five plainly-declaring forms as MENTION-ONLY, which is a NEGATIVE asserting
# the file merely names the repository. The worst available verdict for a file
# that declares correctly in different markup.
SCOPE = re.compile(r"^\s*(?:[-*]\s+)?\*{0,2}Repository\*{0,2}\s*:\s*\*{0,2}\s*(.+)$",
                   re.M | re.I)

# ⛔ THE VOID PROBE. Its only job is to tell "no declaration here" from "a
# declaration I could not parse". Without it, an unparseable field falls through
# to MENTION-ONLY — an empty extraction reported as a measured absence, which is
# the defect DX traced as the root of #16's false row:
#
#   "An empty extraction means MY EXTRACTOR FOUND NOTHING, never THE FILE CONTAINS
#    NOTHING."
#
# ★ And the reason it read as trustworthy there is the reason it would here: the
# extractor worked on three of four files because those three shared a format.
# A PREDICATE VALIDATED ON A HOMOGENEOUS SAMPLE HAS BEEN VALIDATED ON THE SAMPLE'S
# HOMOGENEITY. All four live goal files write the bold form; this checker's own
# sample cannot exercise the alternative, so the void state is the only thing
# standing between a format miss and a confident wrong verdict.
# ⚠ The COLON is the discriminator between a field and prose, and it was found by
# testing rather than by reasoning: the first version keyed on the word alone and
# read "This repository is where the work happens" as an unparseable declaration —
# a FALSE VOID that masks a genuine MENTION-ONLY. A void is safer than a wrong
# negative and it is still wrong, so the probe has to be a field probe.
DECLARATION_SHAPED = re.compile(r"^\s*(?:[-*]\s+)?\*{0,2}Repositor\w*\*{0,2}\s*:", re.M | re.I)
SLUG = re.compile(r"github\.com[:/]+([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?\s*$")

# ⛔ THE POPULATION IS DECLARED, NOT DETECTED. ARCHITECT's ruling on #16.
#
# An earlier version of this file inferred the population with a threshold: a file
# showing >= N of the six headings was treated as a role goal. ⚠ The number was not
# the defect — ANY number is, and there is a live case on the board proving it:
#
#   goal files present         4  (+ dx-friction-sweep)
#   roles the recipe declares  9  agent panes
#   TEAMLEAD's goal file       ABSENT — zero headings, below EVERY threshold
#   #17                        OPEN, and its subject is that absence
#
# ⇒ A DETECTED population can never report a MISSING member. A nonexistent file has
# zero headings and falls below any threshold by construction, so the check reported
# "4 of 4 conformant" while the role that owns the authorization ceiling had no goal
# at all.
#
# ★ That is this file's own defect one layer further out. The `**Repository:**`
# filter had its VALUE unread; the POPULATION was still inferred — so "this role has
# no goal file" and "this file is not a role goal" collapsed into one value (absence
# from the set) and the collapsed value was reported as success.
#
# The roles are knowable. The recipe declares them. Precedent: fleet-context.py
# treats the fleet as a DECLARED roster for exactly this reason.
RECIPE = os.path.join(".daintree", "recipes", "nforma-fleet.json")

# ⚠ `type` is the agent discriminator, measured: nine panes are "claude" and
# PREFLIGHT is "terminal". Keying on the title would need a name blocklist, which
# is the shape this repository keeps refusing.
AGENT_PANE = "claude"


def declared_roles():
    """[(role, declared_goal_path_or_None)] from the recipe, or None if unreadable.

    ⛔ None is a THIRD state and the caller must not read it as an empty roster —
    an unreadable recipe establishes nothing about conformance.
    """
    try:
        doc = json.load(open(RECIPE, errors="replace"))
    except Exception:
        return None
    out = []
    for t in doc.get("terminals", []):
        if t.get("type") != AGENT_PANE:
            continue
        env = t.get("env") or {}
        role = env.get("NFORMA_ROLE") or t.get("title")
        if role:
            out.append((role, env.get("NFORMA_GOAL")))
    return out or None


HELD_BY = re.compile(r"^\*\*Held by:\*\*\s*(.+)$", re.M)


def resolve_goal(role, declared, goals_dir="goals"):
    """Which file carries this role's goal, and how we know. (path, key) or (None, why).

    ★ Keyed on NFORMA_GOAL first — a substrate value set before the agent exists,
    the same argument prompts/README.md makes for NFORMA_ROLE, applied to the goal.
    ⚠ `Held by:` is the INTERIM key and is measured at 3 of 6 files, so it is a
    fallback rather than the contract. A role with neither is NO-FILE — the verdict
    a detected population cannot express.
    """
    if declared:
        return (declared, "NFORMA_GOAL") if os.path.exists(declared) else (None, f"NFORMA_GOAL names {declared!r}, which does not exist")
    if not os.path.isdir(goals_dir):
        return None, "no goals/ directory"
    for f in sorted(os.listdir(goals_dir)):
        if not f.endswith(".md") or f == "README.md":
            continue
        m = HELD_BY.search(open(os.path.join(goals_dir, f), errors="replace").read(4000))
        if m and re.search(rf"\b{re.escape(role)}\b", m.group(1)):
            return os.path.join(goals_dir, f), "Held by:"
    return None, "no NFORMA_GOAL in the recipe and no `Held by:` line naming this role"


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
    # ⛔ Void before negative. A declaration-shaped line that did not parse is a
    # failure of THIS EXTRACTOR, and must not be reported as a property of the file.
    if DECLARATION_SHAPED.search(text):
        return "UNPARSEABLE-DECLARATION", (
            "a line looks like a Repository declaration and this extractor could not parse it "
            "— ESTABLISHED NOTHING about scope, NOT a mention. Fix the extractor or the line; "
            "do not read this as the file being unscoped")
    if re.search(re.escape(mine[1]), text, re.I):
        return "MENTION-ONLY", (f"the name {mine[1]!r} appears in the body, no Repository "
                                f"declaration in any form — it names this repository without "
                                f"being scoped to it")
    return "NO-DECLARATION", "no Repository declaration in any form, and the name does not appear"


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
    # ⛔ FORMAT VARIANTS ARE CONTROLS, NOT POLISH. All four live goal files write the
    # bold form, so the live sample CANNOT exercise the alternatives — a predicate
    # validated on a homogeneous sample has been validated on the sample's
    # homogeneity (DX, tracing the root of #16's false row). Measured before these
    # existed: four of five plainly-declaring forms read MENTION-ONLY, which is a
    # NEGATIVE asserting the file merely names the repository.
    cases = [
        ("declares this repo, bold — the live format", decl, "FOR-THIS-REPO"),
        ("declares it without bold", "Repository: github.com/nForma-AI/nForma-NEXT\n" + six,
         "FOR-THIS-REPO"),
        ("colon outside the emphasis", "**Repository**: github.com/nForma-AI/nForma-NEXT\n" + six,
         "FOR-THIS-REPO"),
        ("as a list item", "- **Repository:** github.com/nForma-AI/nForma-NEXT\n" + six,
         "FOR-THIS-REPO"),
        ("declares another repo", foreign, "FOREIGN"),
        # ⛔ The void. A field this extractor cannot parse is ITS failure, never a
        # property of the file — "an empty extraction means my extractor found
        # nothing, never the file contains nothing".
        ("field present, value unparseable", "**Repository:** (see the recipe)\n" + six,
         "UNPARSEABLE-DECLARATION"),
        # ⚠ And the void must not swallow a real mention. Found by testing, not by
        # reasoning: the first probe keyed on the word alone and read this as a
        # declaration.
        ("prose beginning 'This repository is…'",
         "This repository is where the work happens for nForma-NEXT.\n" + six, "MENTION-ONLY"),
        ("names it in prose only", mention, "MENTION-ONLY"),
        ("says nothing about any repo", silent, "NO-DECLARATION")]
    ok_scope = True
    for label, text, want in cases:
        got, _ = scope_verdict(text, mine)
        good = got == want
        ok_scope = ok_scope and good
        print(f"  {'known-negative' if want == 'FOR-THIS-REPO' else 'known-positive'}  "
              f"{'✅' if good else '⛔'} {got:<16} {label}")
    # ⛔ THE ROSTER, both directions. The verdict a threshold cannot express is
    # NO-FILE, and it is the one the live board needs — so it gets a control.
    import tempfile
    tmp = tempfile.mkdtemp(prefix="goalconf-")
    os.makedirs(os.path.join(tmp, "goals"))
    open(os.path.join(tmp, "goals", "held.md"), "w").write("**Held by:** ROLEA (single seat)\n" + six)
    cwd = os.getcwd()
    os.chdir(tmp)
    try:
        p_a, k_a = resolve_goal("ROLEA", None)
        p_b, k_b = resolve_goal("ROLEB", None)
        p_c, k_c = resolve_goal("ROLEC", "goals/held.md")
        p_d, _ = resolve_goal("ROLED", "goals/nope.md")
    finally:
        os.chdir(cwd)
    ok_roster = (p_a and k_a == "Held by:") and p_b is None and (p_c and k_c == "NFORMA_GOAL") and p_d is None
    print(f"  known-negative  {'✅' if p_a else '⛔'} resolved via Held by:      a declared role with a file")
    print(f"  known-positive  {'✅' if p_b is None else '⛔'} NO-FILE                   a declared role with none")
    print(f"  known-negative  {'✅' if p_c else '⛔'} resolved via NFORMA_GOAL  the substrate carrier wins")
    print(f"  known-positive  {'✅' if p_d is None else '⛔'} NO-FILE                   NFORMA_GOAL names a missing file")
    if not ok_roster:
        print("  ⛔ the roster resolver cannot report NO-FILE — which is the verdict a "
              "threshold-detected population could not express, and the reason it was "
              "replaced", file=sys.stderr)

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

    ok = ok_full and ok_miss and ok_dec and ok_diff and ok_scope and ok_spam and ok_roster
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def main():
    # ⚠ MEMBERSHIP, NOT EQUALITY, was the bug (#321). `"--self-test" in sys.argv` accepts the
    # flag but does not REJECT anything else: `--zzz-not-a-flag` fell straight through to a
    # normal run and exited 0. ⇒ So a misspelled or renamed self-test flag runs the CHECKER and
    # reports success, and a CI step invoking the control would go green having never run it.
    # A control whose invocation cannot fail is not being invoked. (ARCHITECT's PR #47 fix,
    # applied here at last; check-orientation.py has had it since, this file did not.)
    args = sys.argv[1:]
    if args in (["--self-test"], ["--selftest"]):
        return self_test()
    if args:
        print(f"  VOID  unrecognised argument(s): {' '.join(args)} — established nothing",
              file=sys.stderr)
        return 2
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
    mine = this_repo()
    roster = declared_roles()
    if roster is None:
        print(f"⛔ cannot read {RECIPE} — the role population is UNKNOWN, so this run "
              f"ESTABLISHED NOTHING. It is not 'no roles'.\n"
              f"   ADDABLE — FIXABLE HERE: run from the repository root.", file=sys.stderr)
        return 2

    # ⛔ NAMING THE REV IS NOT ENOUGH — SAY WHETHER IT IS THE ONE THE READER MEANS.
    # Nine panes share one working tree, so `git rev-parse HEAD` is whatever branch
    # the last pane left checked out. Measured live: the tree reported `branch=main`
    # while HEAD was three merges behind origin/main, and a file that DOES exist on
    # origin/main was absent from disk. A conformance verdict "at <rev>" reads as a
    # fact about the repository; it is a fact about a tree other panes control.
    #
    # ⚠ This line already said "working tree, not a cached PR view" — written to
    # guard against reading a DIFF. That guard is still right and it understated a
    # different problem: the working tree may not be the ref anyone means.
    beh = subprocess.run(["git", "rev-list", "--count", "HEAD..origin/main"],
                         capture_output=True, text=True).stdout.strip()
    drift = ""
    if beh.isdigit() and int(beh) > 0:
        drift = (f"  ⛔ {beh} commit(s) BEHIND origin/main — this verdict is about a tree "
                 f"nine panes share, not about the repository. Re-run after `git fetch` "
                 f"and a pinned read if it matters.")
    elif not beh.isdigit():
        drift = "  ⚠ could not compare to origin/main — drift UNMEASURED, not zero."
    print(f"goal conformance at {rev or '?'} (working tree, not a cached PR view){drift}")
    print(f"this repository, from `git remote get-url origin`: "
          f"{mine[0] + '/' + mine[1] if mine else '⛔ UNREADABLE'}")
    print(f"population: {len(roster)} agent roles DECLARED by {RECIPE} "
          f"(not files that look goal-shaped)")

    bad = scoped_here = no_file = 0
    unverifiable = False
    seen = {}
    for role, declared in roster:
        path, key = resolve_goal(role, declared)
        if path is None:
            # ⛔ The verdict a detected population cannot express. TEAMLEAD is the
            # live case: declared as a role, no goal file, and #17 is about that.
            no_file += 1
            bad += 1
            print(f"  FAIL  {role:<10} scope: NO-FILE — {key}")
            continue
        text = open(path, errors="replace").read()
        miss = [l for l, v in check(text) if not v]
        verdict, why = scope_verdict(text, mine)
        ok_scope = verdict == "FOR-THIS-REPO"
        scoped_here += ok_scope
        unverifiable = unverifiable or verdict in ("UNVERIFIABLE", "UNPARSEABLE-DECLARATION")
        bad += bool(miss) or not ok_scope
        seen[path] = seen.get(path, 0) + 1
        mark = "ok  " if not miss and ok_scope else "FAIL"
        print(f"  {mark}  {role:<10} {os.path.basename(path):<38} "
              f"[{key}] elements: {'missing ' + ', '.join(miss) if miss else 'all six'}")
        print(f"        {'    ' if ok_scope else '⛔  '}scope: {verdict} — {why}")

    print(f"\n{len(roster) - bad} of {len(roster)} roles conformant "
          f"(a goal file, six elements, scoped to this repository).", file=sys.stderr)
    print(f"{scoped_here} of {len(roster)} roles resolve to a file declaring THIS repository.",
          file=sys.stderr)
    if no_file:
        print(f"⛔ {no_file} declared role(s) have NO GOAL FILE. A detected population could not "
              f"report this — a nonexistent file has zero headings and falls below every "
              f"threshold by construction, which is how 'all conformant' was reported while a "
              f"role had nothing (#17).", file=sys.stderr)
    # ⚠ Name the many-to-one mapping rather than let a shared file read as N files.
    shared = {p: n for p, n in seen.items() if n > 1}
    for p_, n in sorted(shared.items()):
        print(f"⚠ {os.path.basename(p_)} serves {n} roles — one file, {n} holders. A defect in it "
              f"is a defect for all {n}.", file=sys.stderr)
    print("⛔ A file that merely NAMES this repository in its body is reported MENTION-ONLY "
          "and counted as NOT scoped here — that distinction is #16, and a mention cannot "
          "occupy a `**Repository:**` declaration.", file=sys.stderr)
    # Files present in goals/ that no declared role claims.
    if os.path.isdir("goals"):
        claimed = {os.path.basename(p_) for p_ in seen}
        orphan = [f for f in sorted(os.listdir("goals"))
                  if f.endswith(".md") and f != "README.md" and f not in claimed]
        if orphan:
            print(f"⚠ in goals/ but claimed by NO declared role: {', '.join(orphan)}. Not a "
                  f"failure — they fall out because no role declares them, not because they "
                  f"scored below a threshold.", file=sys.stderr)
    if unverifiable:
        print("⛔ At least one scope verdict was UNVERIFIABLE (no readable origin remote). "
              "That is ESTABLISHED NOTHING, not a pass.", file=sys.stderr)
        return 2
    print("⚠ Presence of a HEADING, not quality of its content. A §1 that is present "
          "and aspirational passes here and should still fail review.", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
