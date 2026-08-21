#!/usr/bin/env python3
"""A docstring that says MEASURED must say WHEN. Relative time rots; an instant does not.

⛔ WHY THIS EXISTS, and the author of the offending lines wrote this check.

`tools/issue-coverage.py` was changed on 2026-08-21 to stamp every count with its
collection instant, because three agents' numbers had been quoted back as
properties of the repository when they were photographs: 233/81 became 237/86
became 248/92 within ONE session. ⇒ Then the same author wrote, in two tool
docstrings, on the same night:

    "Two measured instances, FOUR MONTHS APART"        <- apart from when?
    "MEASURED TWICE IN ONE NIGHT"                      <- which night?

★ Both are true at the moment of writing and unverifiable afterwards. A reader in
March cannot tell whether "one night" is last week or last year, whether the API
still behaves that way, or which of two conflicting notes is newer.

⇒ THE RULE, and it is narrow on purpose: a docstring that CLAIMS A MEASUREMENT
must carry an ISO date. It does not police numbers — a threshold, a byte count, an
exit code are not measurements of a world that moves. It fires only on the words
that assert an observation was made.

⚠ WHAT IT DELIBERATELY DOES NOT DO. It cannot tell whether the date is CORRECT, or
whether the measurement still holds. A wrong date passes. ⇒ It converts "no way to
check" into "a claim you can check", which is the whole of the improvement and is
worth saying rather than overselling.

⛔ AND IT REFUSES ON AN EMPTY SCAN. Zero files read and zero violations print the
same clean line otherwise, which is the defect this repository names most often.

Exits: 0 clean · 1 undated measurement claims found · 2 established nothing.
"""
import argparse, ast, os, re, sys

# The words that ASSERT AN OBSERVATION. Deliberately not "N of M" or a bare number:
# a docstring full of thresholds is not making a claim about a moment.
CLAIM = re.compile(r"\b(MEASURED|Measured|measured on|observed|Observed)\b")
ISO = re.compile(r"\b20\d\d-\d\d-\d\d\b")
# Relative phrases that read as precision and carry none.
ROT = re.compile(r"\b(?:four|three|two|five|six|ten)\s+months?\s+apart\b"
                 r"|\bin\s+one\s+night\b|\blast\s+(?:night|week|month)\b"
                 r"|\b(?:yesterday|today|tonight)\b", re.I)


def docstring(path):
    """The module docstring, or None if the file will not parse."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            tree = ast.parse(fh.read(), path)
    except (OSError, SyntaxError):
        return None
    return ast.get_docstring(tree)


def violations(doc):
    """(claims_without_a_date, rotting_phrases) for one docstring."""
    if not doc:
        return [], []
    lines = doc.splitlines()
    undated, rotting = [], []
    for i, l in enumerate(lines):
        if CLAIM.search(l):
            # ⛔ A DATE ANYWHERE EARLIER IN THE SAME DOCSTRING COUNTS. The first version
            # used a ±2-line window and flagged 35 claims; 11 of them were ANAPHORIC —
            # "Measured the same day" referring back to a date stated in the paragraph
            # above. Measured 2026-08-21: the narrow window made 31% of its own findings
            # false. ★ A detector whose predicate is tighter than the thing it detects
            # produces findings that are not.
            if not (ISO.search("\n".join(lines[:i + 3]))):
                undated.append(l.strip()[:88])
        m = ROT.search(l)
        # ⛔ A ROT PHRASE ACCOMPANIED BY A DATE IS NOT ROT — the date resolves it.
        # "MEASURED 2026-08-20/21, twice in one night" is exact. Flagging it would
        # repeat, one rule later, the over-strictness the anaphora fix removed above:
        # a predicate tighter than the thing it detects produces findings that are not.
        if m and not ISO.search(l):
            rotting.append((m.group(0), l.strip()[:88]))
    return undated, rotting


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="tools")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    root = a.dir
    if not os.path.isdir(root):
        print(f"⛔ ESTABLISHED NOTHING — {root!r} is not a directory.")
        return 2
    files = sorted(f for f in os.listdir(root)
                   if f.endswith(".py") and not f.startswith("test_"))
    if not files:
        print(f"⛔ ESTABLISHED NOTHING — no .py files in {root!r}. Zero files read and "
              f"zero violations print the same clean line.")
        return 2

    bad = []
    for f in files:
        doc = docstring(os.path.join(root, f))
        u, r = violations(doc)
        if u or r:
            bad.append((f, u, r))

    print(f"── DATED CLAIMS ── {len(files)} module docstring(s) in {root}/")
    if not bad:
        print("  every MEASURED claim carries an ISO date, and no relative-time phrase "
              "stands in for one.")
        return 0
    for f, u, r in bad:
        print(f"\n  {f}")
        for l in u:
            print(f"    ⛔ claims a measurement with no ISO date nearby:\n        {l}")
        for phrase, l in r:
            print(f"    ⚠ relative time {phrase!r} — true when written, unverifiable after:"
                  f"\n        {l}")
    print(f"\n⇒ {len(bad)} file(s). Add the date the measurement was taken.")
    print("⚠ This cannot tell whether a date is CORRECT or whether the measurement still "
          "holds.\n   It converts 'no way to check' into 'a claim you can check'.")
    return 1


def self_test():
    """⛔ A known-POSITIVE and a known-NEGATIVE. Without the negative, a check that
    flagged everything would pass its own suite."""
    cases = [
        ("MEASURED 2026-08-21: 7 of 7 lines carry it.", ([], []), "dated claim is clean"),
        # ⚠ 2, not 1 — and the self-test caught my expectation, not the code. This line
        # trips BOTH rules: it claims a measurement with no date AND says "in one night".
        # A phrase can be two defects, and asserting the count I predicted would have
        # hidden that the second rule fired at all.
        ("MEASURED TWICE IN ONE NIGHT, both near-misses.", 2,
         "one line can be BOTH an undated claim and a rotting phrase"),
        ("Two measured instances, four months apart.", 1, "relative phrase is caught"),
        ("The threshold is 100000 uACT per block.", ([], []), "a bare number is NOT a claim"),
        ("Measured on the board.\nSee 2026-08-21 for the run.", ([], []),
         "a date two lines away still counts"),
        ("Run on 2026-08-21.\n\n\n\n\n\nMeasured the same day: 88%.", ([], []),
         "ANAPHORA: a date far EARLIER in the docstring satisfies the claim"),
        ("Measured the same day: 88%.", 1,
         "KNOWN-BAD control: with NO date anywhere it is still caught"),
    ]
    ok = True
    for doc, want, label in cases:
        u, r = violations(doc)
        got = (u, r) if want == ([], []) else len(u) + len(r)
        good = (got == want)
        print(f"{'✅' if good else '❌'} {label}")
        if not good:
            print(f"     got {got!r} want {want!r}")
            ok = False
    print("\nall checks passed" if ok else "\nFAILED")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
