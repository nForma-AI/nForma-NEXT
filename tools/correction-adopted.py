#!/usr/bin/env python3
"""Which issues announce a correction in a COMMENT while the BODY still asserts the claim?

⛔ THE DEFECT, measured. #235 §1: "a correction delivered to one reader is the
reservation-locality defect, applied to a fact." #580 §4: "retraction goes in the
ARTIFACT, not the thread." Both are right and both stop one grade short.

★ "IN THE ARTIFACT" HAS TWO GRADES, AND ONLY THE BODY IS MACHINE-VISIBLE. Every
scanner this fleet owns reads the body. close-condition-scan.py scores a
comment-only clause BURIED for exactly this reason, and #620 found the sharper
case: its remedy said "take the clause from the LAST comment carrying one", and a
correction almost never restates what it corrects, so that rule is blind to
precisely the comments it exists to protect against.

⇒ A correction is ADOPTED when the body stops asserting the refuted thing.
Anything short of that is a correction FILED -- which #338 already named, and
which this counts.

Worked instance (#96, repaired 2026-09-06):

    BODY      "31 minutes" x2, both live · correction markers: 0
    COMMENT   "⛔ CORRECTION -- the '31 minutes' in this issue is WRONG ...
               ⇒ 41m 48s"          filed 2026-08-20
    ⇒ 17 days, on a CLOSED issue, behind 9 comments and 28KB.

⛔⛔ THE BOUND, AND IT IS THE WHOLE DESIGN. This CANNOT tell a comment that
corrects THE ISSUE'S CLAIM from one that corrects AN EARLIER COMMENT. Both are
"⛔ Correcting ..." at line start. A first attempt at discriminating them --
does the comment name a comment as its target ("my comment above", "my own
sweep") -- was measured on 2026-09-06 and FAILED ON BOTH ANCHORS:

    #300  hand-verified TRUE  -> misclassified as false, because "my own sweep"
                                names the issue's own content, not a comment
    #338  hand-verified TRUE  -> silently DROPPED, because the fetch helper
                                returned "" on failure and the caller read that
                                as "no correcting comments"

⇒ So this reports CANDIDATES and NAMES THE COMMENTS, and refuses to make the
call. A reader settles it by opening the comments this prints. Reporting a
number as if the call had been made is the error the tool exists to catch.

⛔⛔ MEASURED PRECISION, updated 2026-09-07: 13 candidates read by hand, 3 TRUE,
10 FALSE. (7/2, then 11/2, now 13/3 — it has moved once in three samples.)

    #300  TRUE   the refuted figure was in the TITLE; the author's comment says
                 the verified floor is 1
    #431  TRUE   "⛔ RETRACTING FINDING 1 OF THIS ISSUE" — and the body still
                 carried FINDING 1 under a heading, 0 markers, 17 days
    #258  TRUE   a DIFFERENT shape: the body is not WRONG, it is SUPERSEDED. Its
                 title and body assert "0 landings in 114 minutes"; the author's
                 comment says "the premise is falsified; the finding is not". A
                 reader arriving later takes a historical measurement for a live
                 condition. Repaired by marking the premise historical and leaving
                 the finding untouched.

    #58 #173 #347 #19 #489 #65   FALSE — the comment corrects AN EARLIER COMMENT,
                 and several say so in their first line ("CORRECTION to my own
                 comment above", "to the rung-2 audit above"). #58's author is
                 explicit: "This issue's body has it right."
    #338  FALSE  silent adoption — the body was REWRITTEN, not struck
    #203  FALSE  silent adoption IN THE TITLE. Its title already reads the
                 corrected "12 of 13"; the comment corrects "9 of 10". Adopted,
                 by a rewrite that leaves no marker anywhere.
    #93   FALSE  a QUOTED claim at ten spaces of indent (regex fault, fixed #627)

⇒ THE STATED BOUND IS THE LARGEST SINGLE CAUSE, and more so at 11 than at 7: SIX
of the nine falses are "the comment corrects something other than the issue's
claim", which is exactly what this tool says it cannot separate. Two more are
silent adoption, which it also cannot see. Only one was a defect in the tool.

⚠ NOT A RATE. Eleven is still small and I CHOSE them -- the first two were the
headline cases and the rest were picked as ones I had not already touched. What
the trend does say is that the number did not improve as the sample grew: 2 of 7
became 2 of 11. Do not divide, and do not extrapolate the remaining 14 either.

⚠ It also cannot tell an ADOPTED correction from a body that merely contains the
word "FALSE". Presence of a marker is not correctness of one.

⛔⛔ SILENT ADOPTION -- THE FALSE-POSITIVE CLASS, NAMED AFTER IT BIT THIS TOOL.
Measured on #338, 2026-09-06, hours after this file first reported 25 candidates:

    comment  "the disposition on defect 1 was wrong ... it read
              `ADDABLE — ARCHITECT: wire defect 1's fix ...`"
    body:90  "**ADDABLE — OPERATOR:** a `PreToolUse` lint on `for x in $unquoted`"
    ⇒ occurrences of the refuted "ARCHITECT" disposition in the body: 0
      (its one ARCHITECT is the author's byline)

The correction WAS adopted -- by REWRITING the line rather than striking it. That
is arguably the better repair for a reader, and it leaves NO MARKER, so this tool
calls it a candidate.

⇒ CANDIDATE therefore means "announced, and the body shows no sign of it", NOT
"unrepaired". A rewritten body and a never-touched one are byte-indistinguishable
here, because the evidence of the repair is in the DIFF and this reads the file.
⚠ Detecting it would need the body's edit history, which `gh issue view` does not
carry. Until something reads that, EVERY candidate needs a human read, and the
count is an upper bound on the defect rather than a measure of it.

Exit: 0 no candidates · 1 at least one candidate · 2 established nothing.
⛔ 2 is not a pass. A failed query, an empty board, or a reading shorter than the
population the API states all mean nothing was measured -- and a fetch failure
must NEVER become "this issue has no corrections", which is how #338 vanished.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runmarker import guard, result  # noqa: E402

import argparse
import io
import json
import re
import subprocess

# ⛔ Anchored at line start, like close-condition-scan.py's CONDITION and for the
# same reason: a sentence ABOUT corrections is not a correction. "we should
# correct this someday" must not fire.
ANNOUNCES = re.compile(
    r"^[ ]{0,3}"
    r"(?:[-*+][ ]+)?"
    r"(?:#{1,6}[ ]*)?"
    r"(?:[⇒★⚠⛔→][ ]*)*"
    r"(?:#{1,6}[ ]*)?"
    # ⛔ THE TRAILING `[ ]*` DEFEATED THE `^[ ]{0,3}` ANCHOR. Measured 2026-09-07:
    # this fired on a line indented TEN spaces -- a QUOTED claim inside another
    # comment's block -- because after `[ ]{0,3}` consumed three, the `[ ]*` after
    # the bold marker consumed the rest. The anchor is the whole design ("a
    # STRUCTURAL element of the document, not a phrase inside a sentence"), and an
    # unbounded run of spaces makes any indent structural.
    # ⇒ Found by READING a flagged issue (#93), not by re-reading the pattern.
    r"(?:\*\*|__)?[ ]{0,2}"
    r"(?:correcting|correction\b|corrected\b|withdraw|retract|"
    r"i was wrong|i got .{0,20}wrong)",
    re.IGNORECASE | re.MULTILINE,
)

# A body that shows a reader something was corrected. Deliberately generous:
# a false NEGATIVE here (missing a marker that exists) invents a candidate and
# costs a read; a false POSITIVE clears a real defect silently.
ADOPTED = re.compile(
    r"~~|⛔[ ]*CORRECTION|\bFALSE\b|\bWRONG\b|\bWITHDRAWN\b|"
    r"STALE AS OF|\bINVERTED\b|\bREFUTED\b|\bSUPERSEDED\b"
)


# ⛔ THE PUBLISHED PRECISION, AS DATA. The docstring describes it in prose; this is
# what the control checks, because prose cannot be checked without parsing it and
# three attempts at parsing it failed on cross-references (`fixed #627`) and on a
# different section of the same docstring that also says "TRUE".
#
# ⇒ Prose that restates a number drifts from it (#345, and #628 where a summary said
#   "four of the five" over a list of three). So the numbers live here, once.
# ⚠ Update this when a candidate is read. The docstring's wording may lag; these
#   counts may not, and the self-test enforces that they add up.
PRECISION = {
    "read_by_hand": 13,
    "true": ["#300", "#431", "#258"],
    "false": {
        "corrects an earlier COMMENT, not the issue's claim":
            ["#58", "#173", "#347", "#19", "#489", "#65"],
        "silent adoption — the body or title was REWRITTEN, leaving no marker":
            ["#338", "#203"],
        "a defect in this tool, since fixed (#627)":
            ["#93"],
        "an UPDATE or an adoption, not a correction of the issue's claim":
            ["#397"],
    },
}


class Void(Exception):
    """Established nothing. ⛔ Never collapse into a verdict."""


def gh(args):
    """⛔ RAISES on failure. It must never return a value a caller can mistake for
    an empty result -- a helper that returned "" on error is exactly how #338 left
    the population without a word on 2026-09-06."""
    try:
        p = subprocess.run(["gh"] + args, capture_output=True, text=True)
    except OSError as exc:
        raise Void(f"cannot run gh: {exc}")
    if p.returncode != 0:
        raise Void(f"gh exited {p.returncode}: {(p.stderr or '').strip()[:200]}")
    return p.stdout


def stated_total(repo):
    """The population as the API STATES it. Counting what we received tells us
    nothing about what we did not."""
    out = gh(["api", "-X", "GET", "search/issues", "-f",
              f"q=repo:{repo} is:issue is:open", "--jq", ".total_count"])
    try:
        return int(out.strip())
    except ValueError:
        raise Void(f"search/issues did not return a count: {out[:100]!r}")


def announcing_comments(comments):
    """1-based positions of comments that ANNOUNCE a correction."""
    return [i + 1 for i, c in enumerate(comments) if ANNOUNCES.search(c or "")]


def classify(body, comments, title=""):
    """(state, comment positions, unmarked surfaces).

    ⛔ THE TITLE IS A THIRD GRADE, and it is the one a triager reads. Found on #300,
    2026-09-06: its comment says "the verified floor of 4 is 1", and the refuted 4 is
    in the TITLE -- "measured on 4 of my own captures" -- not in the body at all. The
    body's own "4"s are unrelated quantities. A body-only check reports that issue
    CLEAN while the sentence every list-reader sees still asserts the refuted number.

    ⚠ And the repair differs by surface. A body takes a strikethrough; GitHub does not
    render ~~ in a title, so a title must be EDITED. Reporting them together would
    prescribe the wrong fix for one of them.
    """
    where = announcing_comments(comments)
    if not where:
        return "NO-CORRECTION", [], []
    # ⛔ THE VERDICT IS BODY-ONLY, AND THE TITLE LEG WAS MEASURED AND WITHDRAWN.
    # Requiring a marker in the TITLE too was implemented on 2026-09-06 and refuted
    # by its own live run: ADOPTED went 14 -> 0, because GitHub titles do not carry
    # `~~` or "FALSE" by convention -- nobody writes them there and they barely
    # render. It would have reported 14 issues whose bodies ARE repaired as defects.
    # ⇒ The title is reported as INFORMATION, never as a verdict.
    title_clear = bool(ADOPTED.search(title or ""))
    if ADOPTED.search(body or ""):
        return "ADOPTED", where, []
    return "CANDIDATE", where, (["body"] if title_clear else ["body", "title"])


def self_test():
    failures = []
    # ⇒ counts the controls that run OUTSIDE `cases`; see the summary below.
    _extra = 0
    cases = [
        ("body with no marker", ["⛔ Correcting my earlier number: it is 43."], "plain title",
         ("CANDIDATE", [1], ["body", "title"]), "the defect: announced, body unmarked"),
        ("body says ~~31 minutes~~ [FALSE]", ["## Correction — the figure is wrong"],
         "title ~~4~~ [FALSE — 1]",
         ("ADOPTED", [1], []), "both surfaces marked is the repaired state"),
        # ⛔ THE TITLE LEG. A body-only check calls this ADOPTED and it is not: the
        # sentence every list-reader sees still asserts the refuted claim (#300).
        # ⛔ THE WITHDRAWN LEG, PINNED. A repaired body is ADOPTED even when the title
        # carries no marker -- titles do not carry them. Asserting CANDIDATE here took
        # the live ADOPTED count from 14 to 0.
        ("body says ~~31 minutes~~ [FALSE]", ["## Correction — the figure is wrong"],
         "measured on 4 of my own captures",
         ("ADOPTED", [1], []), "a repaired body is ADOPTED; an unmarked title is NOT a defect"),
        ("plain body", ["nice write-up", "agreed"], "t",
         ("NO-CORRECTION", [], []), "no announcement anywhere"),
        # ⛔ THE LOAD-BEARING NEGATIVE, same shape as close-condition-scan's.
        ("plain body", ["we should correct this someday, a correction is overdue"], "t",
         ("NO-CORRECTION", [], []), "use-vs-mention: prose ABOUT correcting is not one"),
        ("plain body", ["ok", "⛔ Corrected: the number is 43.", "thanks"], "t",
         ("CANDIDATE", [2], ["body", "title"]), "the `corrected` inflection, POSITION named"),
        ("plain body", ["⛔ Correcting A", "noise", "⛔ Retracting B"], "t",
         ("CANDIDATE", [1, 3], ["body", "title"]), "every announcement located, not just the last"),
        ("", [], "", ("NO-CORRECTION", [], []), "an empty issue establishes nothing"),
        # ⛔ THE INDENT ANCHOR. Measured on #93, 2026-09-07: a QUOTED claim inside
        # another comment's block, indented ten spaces, fired the predicate because
        # a trailing `[ ]*` after the bold marker ate the indent the `^[ ]{0,3}`
        # anchor was there to bound. A deep indent is a quotation, not a heading.
        ("plain body", ['          WITHDRAWN and replaced"'], "t",
         ("NO-CORRECTION", [], []),
         "KNOWN-NEGATIVE: a 10-space-indented QUOTED claim is not an announcement"),
        ("plain body", ["      withdraw the finding"], "t",
         ("NO-CORRECTION", [], []),
         "KNOWN-NEGATIVE: a 6-space indent is not a structural element"),
        ("plain body", ["  ⇒ **Correcting** the record"], "t",
         ("CANDIDATE", [1], ["body", "title"]),
         "KNOWN-POSITIVE: normal markdown indent still fires"),
    ]
    for body, comments, title, expected, why in cases:
        got = classify(body, comments, title)
        mark = "ok  " if got == expected else "FAIL"
        if got != expected:
            failures.append((why, expected, got))
        print(f"  {mark} {why}")

    # ⛔ The fetch helper must RAISE, never return a falsy value. This is the #338
    # defect as a control: a helper that returned "" made a failed fetch read as
    # "no corrections", and the issue left the population silently.
    # ⛔ THE PUBLISHED PRECISION MUST CHECK ITS OWN ARITHMETIC. On #628 a summary
    # said "four of the five" over a list of three; review caught it, and a shell
    # one-liner is not a caller. This checks PRECISION, which is data — three
    # attempts to parse the equivalent prose failed, on a cross-reference and on a
    # different section of the docstring that also contains the word TRUE.
    t = PRECISION["true"]
    f = [n for group in PRECISION["false"].values() for n in group]
    if len(t) + len(f) != PRECISION["read_by_hand"]:
        failures.append(("read_by_hand must equal true + false",
                         PRECISION["read_by_hand"], f"{len(t)}+{len(f)}"))
    elif len(set(t + f)) != len(t + f):
        dupes = sorted({n for n in t + f if (t + f).count(n) > 1})
        failures.append(("no issue may appear twice", "unique", dupes))
    else:
        # ⛔ Review asked for `len(t) == 2` and `len(f) == 9` as LITERALS. DECLINED:
        # a literal 2 in the control is a second copy of the datum the dict exists to
        # hold once, and it would red on every legitimate reclassification.
        # ⇒ The real exposure is the PROSE, which restates "11 … 2 TRUE, 9 FALSE" and
        #   was checked by nobody. ONE anchored line compared to the dict — not the
        #   enumeration, which three earlier attempts proved unparseable.
        m = re.search(r"(\d+)\s+candidates read by hand,\s*(\d+)\s+TRUE,\s*(\d+)\s+FALSE",
                      __doc__ or "")
        if not m:
            failures.append(("the docstring must state the precision in the checked form",
                             "a match", "none"))
        elif [int(g) for g in m.groups()] != [PRECISION["read_by_hand"], len(t), len(f)]:
            failures.append(("the docstring numbers must match PRECISION",
                             f"{PRECISION['read_by_hand']}/{len(t)}/{len(f)}",
                             "/".join(m.groups())))
        else:
            _extra += 1
            print(f"  ok   published precision is self-consistent: "
                  f"{PRECISION['read_by_hand']} read = {len(t)} true + {len(f)} false, "
                  f"across {len(PRECISION['false'])} named causes, no duplicates, "
                  f"and the docstring agrees")

    # ⛔ AND tools/README.md RESTATES THESE NUMBERS TOO. The docstring is checked
    # above; the README was not, and it drifted THREE times in one day — "seven is a
    # small sample" beside an 11, "six of the nine" beside a 10, and a claim about
    # #338 that I had WITHDRAWN a day earlier and left standing here.
    # ⇒ One anchored sentence, same shape as the docstring check. ⚠ If the README is
    #   unreadable this is UNCHECKED, not passing — it says so rather than skipping.
    _readme = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
    try:
        _txt = io.open(_readme, encoding="utf-8").read()
    except OSError as exc:
        failures.append(("tools/README.md must be readable to check it", "readable", exc))
    else:
        # ⚠ `.*?` not `[^,]*`: the README names the TRUE issues in a parenthetical
        # ("3 TRUE (#300, #431, #258), 10 FALSE") and a comma-excluding class cannot
        # cross it. The first version failed loudly here rather than passing, which
        # is the only reason it was a two-minute fix.
        _m = re.search(r"(\d+)\s+candidates read by hand\s*—\s*(\d+)\s+TRUE.*?,\s*(\d+)\s+FALSE",
                       _txt, re.S)
        if not _m:
            failures.append(("tools/README.md must state the precision in the checked form",
                             "a match", "none"))
        elif [int(g) for g in _m.groups()] != [PRECISION["read_by_hand"], len(t), len(f)]:
            failures.append(("tools/README.md's numbers must match PRECISION",
                             f"{PRECISION['read_by_hand']}/{len(t)}/{len(f)}",
                             "/".join(_m.groups())))
        else:
            _extra += 1
            print("  ok   tools/README.md's published precision matches PRECISION too")

    try:
        gh(["--zzz-not-a-real-subcommand"])
    except Void:
        _extra += 1
        print("  ok   a failed gh raises Void — a fetch failure cannot read as 'no corrections'")
    except Exception as exc:                      # noqa: BLE001
        failures.append(("gh must raise Void, not %s" % type(exc).__name__, "Void", exc))
    else:
        failures.append(("gh must RAISE on failure", "Void", "returned normally"))

    if failures:
        print("\n⛔ the classifier is broken; no verdict it produces can be trusted:")
        for why, exp, got in failures:
            print(f"     {why}: expected {exp}, got {got}")
        result("CONTROL-FAILED")
        return 3
    # ⛔ THIS COUNT HAS NOW BEEN WRONG TWICE. It read +1 and reported 12/12 while 13
    # ran (review caught it); then +2 reported 13/13 while 14 ran, after the README
    # control was added — and I caught that only by counting the `ok` lines before
    # committing. A hand-maintained count of controls is the same defect as a
    # hand-maintained count of anything else.
    # ⇒ DERIVED: `_extra` is incremented at each control that runs outside `cases`,
    #   at the point it runs, so the summary cannot drift from what executed.
    _n = len(cases) + _extra
    print(f"\n  {_n}/{_n} controls passed — including the use-vs-mention negative, "
          "the fail-closed fetch, and the precision self-consistency check.")
    result("SELF-TEST-PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default="nForma-AI/nForma-NEXT")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--self-test", action="store_true", help="run the controls; no network")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        total = stated_total(args.repo)
        nums = [i["number"] for i in json.loads(gh(
            ["issue", "list", "--repo", args.repo, "--state", "open",
             "--limit", str(args.limit), "--json", "number"]))]
    except Void as exc:
        print(f"⛔ VOID — {exc}", file=sys.stderr)
        print("   Established NOTHING about the board. Exit 2, not a clean run.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    # ⛔ THIS SAID "an empty board and a failed query are byte-identical here" AND
    # RETURNED 2. Measured 2026-09-07, that justification is FALSE for this call:
    #     q=… is:issue is:open          -> 102     the real board
    #     q=… label:zzz-no-such         -> 0       ⚠ silent — a malformed query CAN
    #     q=repo:owner/zzz-no-such-repo -> HTTP 422, which gh() RAISES
    # ⇒ The query here is FIXED and its only user-supplied part (--repo) fails 422
    #   and raises. So total == 0 means the search SUCCEEDED and the board is empty,
    #   which is a COMPLETE population and therefore CLEAN, not "established
    #   nothing". Returning 2 refused a reading that was in fact complete.
    # ⇒ Found by review on #629 against the sibling tool; the same guard and the
    #   same false comment were here, so it is corrected in the same change.
    if total == 0:
        print("⚠ the board is EMPTY (0 open issues, and the search agrees). No "
              "correction can be unpropagated because there is nothing to carry one.",
              file=sys.stderr)
    if len(nums) < total:
        print(f"⛔ VOID — read {len(nums)} of {total} stated. A truncated reading cannot "
              f"support 'no candidates'.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    print(f"POPULATION  {len(nums)} open issues of {total} stated · repo={args.repo}")
    print("PREDICATE   a COMMENT announces a correction AND the BODY carries no marker")
    print("CHANNEL     issue body + every comment, via gh\n")

    buckets = {"CANDIDATE": [], "ADOPTED": [], "NO-CORRECTION": []}
    for n in nums:
        try:
            d = json.loads(gh(["issue", "view", str(n), "--repo", args.repo,
                               "--json", "body,comments,title"]))
        except Void as exc:
            # ⛔ ONE unreadable issue voids the RUN. It must not be skipped: a skipped
            # issue is indistinguishable from a clean one, which is #338 exactly.
            print(f"⛔ VOID — issue #{n} unreadable: {exc}", file=sys.stderr)
            print("   Skipping it would make an unread issue look clean. Exit 2.",
                  file=sys.stderr)
            result("ESTABLISHED-NOTHING")
            return 2
        state, where, unmarked = classify(
            d.get("body") or "",
            [c.get("body") or "" for c in (d.get("comments") or [])],
            d.get("title") or "")
        buckets[state].append((n, where, unmarked, (d.get("title") or "")[:52]))

    print(f"  NO-CORRECTION  {len(buckets['NO-CORRECTION']):3d}  no comment announces one")
    print(f"  ADOPTED        {len(buckets['ADOPTED']):3d}  announced, and the body shows it")
    print(f"  ⛔ CANDIDATE    {len(buckets['CANDIDATE']):3d}  announced in a comment, body unmarked\n")

    both = sum(1 for _, _, u, _ in buckets["CANDIDATE"] if len(u) == 2)
    print(f"     of those, {both} also have a title carrying no marker — INFORMATION,\n"
          f"     not a finding: a title is repaired by EDITING it, and #300's refuted\n"
          f"     figure lives in its title rather than its body.\n")
    for n, where, unmarked, title in sorted(buckets["CANDIDATE"]):
        seen = ", ".join(f"#{w}" for w in where)
        print(f"    #{n:<5} comment(s) {seen:<14} unmarked: {'+'.join(unmarked):<11} {title}")

    if buckets["CANDIDATE"]:
        print("""
    ⇒ CANDIDATES, NOT FINDINGS. This cannot tell a comment correcting THE ISSUE'S
      CLAIM from one correcting AN EARLIER COMMENT — both are "⛔ Correcting …" at
      line start. Open the comments named above; that is why they are named rather
      than counted. ⚠ A discriminator for this was tried on 2026-09-06 and got BOTH
      hand-verified anchors wrong (#300 misclassified, #338 silently dropped), so
      the honest output is a location and not a verdict.
    ⇒ THE REPAIR is a MOVE, not a rewrite: strike the refuted text in the BODY and
      point at the comment. Nothing new is claimed by doing so.""")
    result("FINDINGS" if buckets["CANDIDATE"] else "CLEAN")
    return 1 if buckets["CANDIDATE"] else 0


if __name__ == "__main__":
    sys.exit(guard("correction-adopted", main))
