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

⛔⛔ MEASURED PRECISION, 2026-09-07: 7 candidates read by hand, 2 TRUE, 5 FALSE.

    #300  TRUE   the refuted figure was in the TITLE ("measured on 4 of my own
                 captures"); the author's comment says the verified floor is 1
    #431  TRUE   "⛔ RETRACTING FINDING 1 OF THIS ISSUE" — and the body still
                 carried FINDING 1 under a heading, 0 markers, for 17 days
    #338  FALSE  silent adoption — the body was REWRITTEN, not struck
    #58   FALSE  corrects a COMMENT; its author says so in the artifact:
                 "This issue's body has it right. My routing comment drifted."
    #173  FALSE  "Correction to this comment, made one minute after posting it"
    #347  FALSE  "The claim in the body STANDS" — the correction was about the
                 author's own retraction-HANDLING, not the issue's claim
    #93   FALSE  a QUOTED claim at ten spaces of indent — a regex defect, fixed

⇒ THE STATED BOUND IS THE LARGEST SINGLE CAUSE. THREE of the five false positives
(#58, #173, #347) are "the comment corrects something other than the issue's
claim", which is exactly what this tool says it cannot separate. The other two are
different defects: #338 is silent adoption, #93 was a regex fault since fixed.

⚠ THIS PARAGRAPH SAID "FOUR" AND "a measured hit rate near 2/7" UNTIL REVIEW
CAUGHT BOTH, 2026-09-07. The four was arithmetic its own case list above refutes.
The "hit rate" contradicted the "not a rate" warning three lines below it — in the
change whose entire purpose was publishing an honest figure. ⇒ Recorded rather
than quietly corrected, because a document refuted by its own later text is the
defect this tool detects.

⇒ So the candidate count is an UPPER BOUND. Of the 7 opened by hand, 2 were real.
A reader must open the named comments before believing any of the rest.

⚠ NOT A RATE. Seven is a small sample and I chose them — two were the headline
cases and five were picked as ones I had not already touched. Do not divide.

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
    try:
        gh(["--zzz-not-a-real-subcommand"])
    except Void:
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
    print(f"\n  {len(cases) + 1}/{len(cases) + 1} controls passed — including the "
          "use-vs-mention negative and the fail-closed fetch.")
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

    if not nums:
        print("⛔ VOID — zero open issues read. An empty board and a failed query are "
              "byte-identical here.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2
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
