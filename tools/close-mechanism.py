#!/usr/bin/env python3
"""What does closing this issue REQUIRE? -- derived from each issue's own words.

⛔ THE DEFECT. A board of 108 open issues offers no way to answer "what can move
today?" The obvious remedy is to group them, and the obvious axis -- defect class --
is measured WRONG here twice over:

  #296 §5  "'wrong proposition' is a GENUS, not a species -- ~19 instances across 6
           sub-shapes. Ruling on it as one class would itself have been an instance,
           and a remedy attaches to a sub-shape, never to the genus."
  #87      CLOSED for exactly this: "a signature spanning six mechanisms is a symptom,
           not a class, and a register organised by symptom will keep growing without
           becoming actionable, because no single remedy addresses six mechanisms."

★ THE AXIS THAT WORKS is CLOSE MECHANISM, and the board has already written it down:
91 of 108 open issues carry their own `Done when` block, and those blocks state what
closing requires. So this tool REPORTS WHAT EACH ISSUE SAYS ABOUT ITSELF. It does not
impose a scheme.

⛔⛔ AND THAT DISTINCTION IS THE WHOLE DESIGN, because the alternative is measured and
merged. #165 PART 2c: a reviewer's four-state taxonomy became a CONSTRAINT ON WHAT THE
MEASURER REPORTED -- "I bent two measurements to fit a taxonomy rather than reporting
that the taxonomy was short ... it is in a merged artifact."

    ⇒ A taxonomy too short to hold a real state makes the measurer disagree with the
      world instead. A DERIVED reading cannot do that: an issue that fits no bucket
      lands in the residual and the residual is reported as untrustworthy.

⛔ PRIOR ART, CHECKED BEFORE WRITING (#405: "a second implementation is the defect").
Three instruments already live in this family and this tool DELEGATES to the first
rather than re-implementing it:

    close-condition-scan.py   is a condition PRESENT, and is it in the BODY?
                              ⇒ imported. `classify()`, `fetch()` and `stated_total()`
                                are CALLED here, not copied. Its truncation guard is
                                therefore this tool's truncation guard.
    runnable-condition.py     can the condition be RUN, or only agreed with?
                              ⇒ adjacent and NOT subsumed. Run it separately.
    issue-coverage.py         has anybody OPENED the issue?
                              ⇒ a different question entirely.

⚠ WHY THIS IS A NEW FILE AND NOT AN EXTENSION, stated because #164 §2 says three
instruments answering one question are one instrument. The question here is not
"is there a condition" but "who can act on it", and the verdict space shares no
member with close-condition-scan's. ⛔ If a reviewer judges that wrong, the correct
outcome is to fold this INTO close-condition-scan, not to keep both.

## The verdicts -- OVERLAPPING BY CONSTRUCTION, and that is not a defect

An issue may be a capture AND operator-terminal AND lack an instrument. A partition
would have to pick one and would hide the other two.

    #355  "a classifier that cannot separate its population must SAY SO rather than
           emit a confident smaller number" -- a name-keyed watch collapsed 34
           sessions into 9 and discarded 25 silently.

⇒ Tags are emitted as a SET per issue. Counts sum to more than the population and the
output says so on every run.

    NO-CONDITION    no `Done when` anywhere            ⇒ nobody can tell when it closes
    BURIED          a condition, but only in a COMMENT ⇒ a closer reading the body
                    sees none. A DIFFERENT repair from NO-CONDITION (#58, #189, #300)
    DISCHARGE       self-declared CAPTURE / residue / RECORD / ASK ⇒ cannot be
                    "fixed", only discharged by recording a destination per item
    OPERATOR        closing is reserved to the operator ⇒ NO PANE CAN CLOSE IT
    NO-CALLER       the condition names an instrument with no caller that runs
    NO-INSTRUMENT   the condition specifies a tool that DOES NOT EXIST YET
    ACTIONABLE      ⚠ RESIDUAL -- defined by the ABSENCE of every tag above.

⛔⛔ THE RESIDUAL IS THE LEAST TRUSTWORTHY ROW AND IS LABELLED SO IN THE OUTPUT.
It is not a measurement of actionability; it is "no blocker matched". A blocker
phrased in words these patterns do not carry lands here and looks ready to work.
⇒ #452: "a predicate matching almost everything discriminates nothing." The controls
below therefore include a case that MUST NOT be ACTIONABLE.

## What this does NOT check -- ask the instrument what it did not look at

  · It does not read whether a condition is FALSIFIABLE. That is close-condition-scan's
    stated bound and it is inherited here whole.
  · It does not verify that a named instrument is the RIGHT one, or that a named
    operator action is one the operator agrees with.
  · It reads the BODY and (for BURIED only) the comments. ⛔ A retraction that lives in
    a comment leaves the body asserting the retracted claim (#300), so a tag derived
    from the body may describe a position its author has since withdrawn.
  · It cannot see an issue whose blocker was never written down. Silence is not a
    reachable close path; it is an unmeasured one.

Exit: 0 the census is answering · 1 a FINDING -- at least one issue has no close path
reachable by any pane · 2 VOID, established nothing.
"""
import argparse
import importlib.util
import re
import sys
from pathlib import Path

# ⛔ Windows: the FAIL branches carry ⛔/⚠ and stdout defaults to cp1252, so a checker
# runs clean when all is well and dies with UnicodeEncodeError exactly when it finds
# something -- and a crashed checker reports nothing at all. (#502 B4)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DEFAULT_REPO = "nForma-AI/nForma-NEXT"


def _load(stem):
    """Import a hyphenated sibling module. ⛔ Not a copy -- the point is that this tool
    has no second implementation of fetch, truncation or condition-presence."""
    path = HERE / f"{stem}.py"
    if not path.exists():
        raise Void(f"prior art missing: {path} -- cannot delegate, and will not re-implement")
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Void(Exception):
    """Established nothing. ⇒ exit 2, never a verdict."""


# ── The predicates ────────────────────────────────────────────────────────────
# ⚠ Each is ANCHORED to phrasing this board actually uses. A looser matcher would
# start reporting issues DISCUSSING a blocker as issues HAVING one -- use-vs-mention,
# which is the error three instruments here exist to catch.

DISCHARGE = re.compile(
    r"(?im)\*\*This is a CAPTURE"
    r"|\bresidue report\b"
    r"|only be DISCHARGED"
    r"|\*\*This is an? (?:ASK|RECORD)"
    r"|is a RECORD, NOT A GRANT"
    r"|closes by (?:DISPOSITION|EXTRACTION)")

OPERATOR = re.compile(
    r"(?im)ADDABLE\s*[—-]\s*OPERATOR"
    r"|OPERATOR (?:DISPOSITION|RULING)"
    r"|reserved to the operator"
    r"|operator-only"
    r"|not TEAMLEAD'?s to grant"
    r"|is the operator'?s(?: alone| call| to)")

# ⛔ SPLIT DELIBERATELY. An earlier exploratory pass folded these together with a bare
# /DOES NOT EXIST/, which fires on prose about missing tools generally -- a loose
# matcher reported as a count. They are different repairs: wire a caller vs build a
# tool. Reporting them apart is the whole lesson of #58's three-cause split.
NO_CALLER = re.compile(
    r"(?im)\bNO CALLER\b"
    r"|CALLER:?\s*\*{0,2}\s*none"
    r"|none that runs unattended"
    r"|none is possible"
    r"|nothing (?:invokes|re-?runs|re-?reads) it")

NO_INSTRUMENT = re.compile(
    r"(?im)tools/[\w./-]+\.py[^\n]{0,60}?DOES NOT EXIST"
    r"|DOES NOT EXIST[^\n]{0,40}?(?:that is the point|this clause specifies)"
    r"|NO SUCH CHECK EXISTS")

BLOCKERS = ("NO-CONDITION", "BURIED", "DISCHARGE", "OPERATOR", "NO-CALLER", "NO-INSTRUMENT")
# Tags meaning NO PANE CAN CLOSE THIS -- the finding this tool exists for, and the one
# close-condition-scan structurally cannot see.
UNREACHABLE = ("NO-CONDITION", "OPERATOR", "NO-INSTRUMENT")


def tags_for(issue, presence):
    """Derive the tag SET. `presence` is close-condition-scan's own verdict."""
    body = issue.get("body") or ""
    tags = []
    if presence == "NONE":
        tags.append("NO-CONDITION")
    elif presence == "BURIED":
        tags.append("BURIED")
    if DISCHARGE.search(body):
        tags.append("DISCHARGE")
    if OPERATOR.search(body):
        tags.append("OPERATOR")
    if NO_CALLER.search(body):
        tags.append("NO-CALLER")
    if NO_INSTRUMENT.search(body):
        tags.append("NO-INSTRUMENT")
    return tags or ["ACTIONABLE"]


# ── Controls ──────────────────────────────────────────────────────────────────

def self_test():
    """⛔ TWO-SIDED AND NAMED, both directions printed. Measured: only 9 of 46
    instruments in this repository do that (#405), and a control that only ever fires
    positive cannot distinguish a working predicate from one that matches everything.

    ★ Fixtures are LITERALS, so the control survives a repair to the patterns."""
    ok = True

    # Each row: (name, body, tag, must_fire)
    cases = [
        # ── KNOWN-POSITIVES: the predicate MUST fire ──
        ("DISCHARGE +", "## Done when\n⚠ **This is a CAPTURE, not a defect report.**", "DISCHARGE", True),
        ("DISCHARGE +", "## Done when\nResidue report -- closes by DISPOSITION.", "DISCHARGE", True),
        ("OPERATOR +", "## Done when\n⛔ **ADDABLE — OPERATOR.** ~/.claude/hooks/ is harness config.", "OPERATOR", True),
        ("OPERATOR +", "## Done when\nIt is reserved to the operator and not TEAMLEAD's to grant.", "OPERATOR", True),
        ("NO-CALLER +", "## Done when\n⛔ **CALLER THAT STILL RUNS IT:** none is possible.", "NO-CALLER", True),
        ("NO-CALLER +", "## Done when\n⚠ **CALLER:** none that runs unattended.", "NO-CALLER", True),
        ("NO-INSTRUMENT +", "## Done when\n⛔ `tools/merge-guard.py` DOES NOT EXIST. That is the point of leg 4.", "NO-INSTRUMENT", True),

        # ── KNOWN-NEGATIVES: the predicate MUST NOT fire. ⛔ These are the leg that
        # decides it. Without them "the matcher works" and "the matcher matches
        # everything" are the same reading -- the 13-of-13 defect (#56).
        ("DISCHARGE −", "## Done when\nThe fix lands on main and the control fires.", "DISCHARGE", False),
        ("OPERATOR −", "## Done when\nDEVOPS wires the caller; routing, not assigning.", "OPERATOR", False),
        # use-vs-mention: an issue DISCUSSING callers must not read as HAVING no caller
        ("NO-CALLER − (mention)", "## Done when\n★ **CALLER: `tools/index-watch.py`, gated, last run on every PR.**", "NO-CALLER", False),
        ("NO-INSTRUMENT − (mention)", "## Done when\n`tools/landing-rate.py` exists and is the worked example.", "NO-INSTRUMENT", False),
    ]

    print("── controls ── (a predicate that fires on every fixture discriminates nothing)")
    for name, body, tag, must in cases:
        got = tag in tags_for({"body": body}, "BODY")
        good = (got == must)
        ok &= good
        arrow = "fires" if got else "silent"
        print(f"  {'✅' if good else '⛔'} {name:26s} expected {'fires ' if must else 'silent'} · got {arrow}")

    # ── The residual must be reachable in BOTH directions ──
    plain = tags_for({"body": "## Done when\nThe fix lands on main and the control fires."}, "BODY")
    blocked = tags_for({"body": "## Done when\n⛔ **CALLER:** none is possible."}, "BODY")
    r1, r2 = plain == ["ACTIONABLE"], "ACTIONABLE" not in blocked
    ok &= r1 and r2
    print(f"  {'✅' if r1 else '⛔'} residual +               a clean condition IS ACTIONABLE · got {plain}")
    print(f"  {'✅' if r2 else '⛔'} residual −               a blocked condition is NOT · got {blocked}")

    # ── Presence is DELEGATED: prove the delegation, do not re-implement it ──
    try:
        ccs = _load("close-condition-scan")
        pos = ccs.classify({"body": "## Done when\nsomething", "comments": []})
        neg = ccs.classify({"body": "no clause here", "comments": []})
        d1, d2 = pos == "BODY", neg == "NONE"
        ok &= d1 and d2
        print(f"  {'✅' if d1 else '⛔'} delegation +             close-condition-scan.classify -> {pos!r} (expect 'BODY')")
        print(f"  {'✅' if d2 else '⛔'} delegation −             close-condition-scan.classify -> {neg!r} (expect 'NONE')")
    except Exception as exc:
        ok = False
        print(f"  ⛔ delegation VOID          {exc}")

    print(f"\n{'✅ controls pass' if ok else '⛔ CONTROLS FAILED'} — "
          f"{len(cases) + 4} legs, both directions named")
    return 0 if ok else 1


# ── Report ────────────────────────────────────────────────────────────────────

def run(repo, label, limit):
    ccs = _load("close-condition-scan")

    try:
        stated = ccs.stated_total(repo, label)
        issues = ccs.fetch(repo, label, limit)
    except ccs.Void as exc:
        raise Void(str(exc))

    # ⛔ An empty result is NOT a clean board. A mistyped label returns exit 0 with
    # ZERO BYTES on stdout AND stderr -- byte-identical to an empty queue (#317).
    if stated == 0:
        raise Void(f"population is EMPTY for repo={repo} label={label!r}. "
                   f"A nonexistent label produces this exact reading -- verify the label exists "
                   f"before reading this as 'no issues'.")
    if len(issues) < stated:
        raise Void(f"TRUNCATED: search/issues states {stated}, the list returned {len(issues)}. "
                   f"`--limit` clamps silently; raise it. A clean answer about a set this tool "
                   f"never saw is the defect it exists against.")

    rows = []
    for i in issues:
        rows.append((i["number"], tags_for(i, ccs.classify(i)), i.get("title", "")))

    # ⛔ A census with ONE bucket has relabelled the population, not discriminated it
    # -- branch-census.py's rule (#331), and it is the honest VOID here too.
    distinct = {tuple(sorted(t)) for _, t, _ in rows}
    if len(distinct) < 2:
        raise Void(f"every one of {len(rows)} issues classified identically as "
                   f"{sorted(distinct)[0]}. A census with one bucket has relabelled the "
                   f"population; it has not discriminated it.")

    print(f"POPULATION  {len(rows)} open issues · repo={repo}" + (f" label={label}" if label else ""))
    print(f"PREDICATE   what does each issue's OWN `Done when` block say closing requires")
    print(f"CHANNEL     issue BODY (and comments for BURIED only) -- via close-condition-scan")
    print(f"⚠ stated_total={stated}, received={len(issues)} — equal, so the reading is not a prefix\n")

    counts = {}
    for _, tags, _ in rows:
        for t in tags:
            counts[t] = counts.get(t, 0) + 1

    print("── tags ── ⚠ OVERLAPPING: an issue may carry several, so these SUM TO MORE "
          f"THAN {len(rows)}")
    for t in ("ACTIONABLE",) + BLOCKERS:
        if t in counts:
            note = ""
            if t == "ACTIONABLE":
                note = "  ⚠ RESIDUAL — defined by ABSENCE of a blocker, not by readiness"
            elif t in UNREACHABLE:
                note = "  ⛔ no pane can close these"
            print(f"  {counts[t]:4d}  {t:14s}{note}")

    unreachable = [n for n, t, _ in rows if set(t) & set(UNREACHABLE)]
    print(f"\n── the finding ──")
    print(f"  {len(unreachable)} issues have NO close path reachable by any pane:")
    print("  " + " ".join(f"#{n}" for n in sorted(unreachable)) if unreachable else "  (none)")

    print(f"\n⛔ NOT CHECKED, and the bound is inherited whole from close-condition-scan:")
    print(f"   whether any condition is FALSIFIABLE. `## Done when: it feels done` scores")
    print(f"   ACTIONABLE here. Presence is checkable; quality is a reading.")
    print(f"⚠  A tag is derived from the BODY. A claim withdrawn only in a COMMENT still")
    print(f"   reads as live here (#300).")

    return 1 if unreachable else 0


def main():
    ap = argparse.ArgumentParser(
        description="What does closing each open issue REQUIRE? Derived from its own Done-when block.")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--label", default=None, help="restrict to one label")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--self-test", action="store_true",
                    help="run the two-sided controls and exit; makes no network call")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    try:
        return run(args.repo, args.label, args.limit)
    except Void as exc:
        print(f"⛔ VOID — established nothing: {exc}", file=sys.stderr)
        return 2



# ⛔ `guard()` ALONE SHIPS HALF THE MARKER CONVENTION. It emits NFORMA-RESULT only on
# the argparse SystemExit path, so a SUCCESSFUL run emitted NFORMA-RUN and no RESULT --
# which reads as started-and-never-finished, the exact collapse #58 exists to prevent.
# Measured 2026-09-06: 2 of the 13 instruments importing runmarker shipped it this way.
# #234 §4 named the defect and prescribed this remedy: wrap the entry so every return
# from main() carries a terminal marker.
#
# ⚠ #234 §4's second warning, honoured: "check for a SECOND emission -- my first
# injection produced TWO RESULT lines for one process." Neither of these files calls
# result() anywhere else, and the fix is verified by COUNTING the lines, not by reading
# the patch.
_STATE = {0: "CLEAN", 1: "FINDINGS", 2: "ESTABLISHED-NOTHING", 3: "CONTROL-FAILED"}


def _entry():
    rc = main()
    if "--self-test" in sys.argv or "--selftest" in sys.argv:
        runmarker.result("SELF-TEST-PASS" if rc == 0 else _STATE.get(rc, f"EXIT-{rc}"))
    else:
        runmarker.result(_STATE.get(rc, f"EXIT-{rc}"))
    return rc

if __name__ == "__main__":
    try:
        import runmarker
        sys.exit(runmarker.guard("close-mechanism", _entry))
    except ImportError:
        sys.exit(main())
