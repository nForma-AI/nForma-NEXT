#!/usr/bin/env python3
"""Before a token counts as evidence about ONE record, measure it across ALL of them.

⛔ A TOKEN PRESENT IN EVERY RECORD CARRIES NO INFORMATION ABOUT ANY ONE OF THEM —
and it reads as a finding because it is sitting right next to the thing you are
looking at. Two measured instances, four months apart, same shape:

  1. An Actions log CONTAINS THE STEP'S OWN SCRIPT, so every phrase the workflow
     quotes matches 100% of runs. A skip-census keyed on such a phrase published
     58 skips that were actually 0.

  2. A poll line renders `detail=<free text>, attempts=1, elapsed=247s`. The
     suffix is the LINE FORMAT — measured 7 of 7 lines carry it, INCLUDING lines
     whose `detail=` is empty. It was read as circuit-breaker state and reported
     to a decision-maker; the breaker's own message contains neither field.

★ In both, the reader had the right token, in the right file, next to the right
subject — and the token was a CONSTANT of the format. ⇒ The question is never
"is it there". It is "is it there MORE THAN USUAL".

⚠ AND THE DELIMITER IS WHY #2 IS HARD TO SEE: `detail=<free text>, attempts=…`
puts a comma before the next field that is indistinguishable from a comma INSIDE
the free text, so an embedded field silently annexes everything after it. A human
reads one sentence; the format has three.

⛔ REFUSES ON A POPULATION OF ONE. With n=1, "100% of records carry it" and "the
only record carries it" are the same sentence and neither is evidence. A tool
that answered anyway would manufacture the exact confidence it exists to remove.

⇒ Exits: 0 the token DISCRIMINATES (present in some, absent in others) ·
1 NON-DISCRIMINATING (present in all, or absent from all) · 2 established nothing.

Run: python3 tools/prevalence.py --token 'attempts=' --like '\\[POLL #' run.log
"""
import argparse, re, sys


def population(text, like):
    """The comparable records. `like` is what makes them comparable — without it
    every line in the file is 'comparable', which is rarely what the reader means."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not like:
        return lines
    rx = re.compile(like)
    return [l for l in lines if rx.search(l)]


def prevalence(records, token, literal=True):
    """(carrying, total). Literal by default — a token from a log is full of
    metacharacters and every one of them fails silently toward 'absent'."""
    if literal:
        return sum(1 for r in records if token in r), len(records)
    rx = re.compile(token)
    return sum(1 for r in records if rx.search(r)), len(records)


def verdict(carrying, total):
    if total < 2:
        return "VOID", ("a population of {} cannot distinguish 'every record carries it' "
                        "from 'the only record carries it'".format(total))
    if carrying == total:
        return "NON-DISCRIMINATING", ("every record carries it — this is the FORMAT, "
                                      "not a property of the one you are reading")
    if carrying == 0:
        return "NON-DISCRIMINATING", "no record carries it — it says nothing about any of them"
    return "DISCRIMINATES", "present in some records and absent from others"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="file to read, or - for stdin")
    ap.add_argument("--token", required=True,
                    help="LITERAL text whose prevalence to measure (see --token-re)")
    ap.add_argument("--token-re", action="store_true",
                    help="treat --token as a regex; opt in deliberately")
    ap.add_argument("--like", default=None,
                    help="regex selecting the COMPARABLE records. Without it every "
                         "non-empty line counts, which is rarely the population meant.")
    ap.add_argument("--show", type=int, default=3)
    a = ap.parse_args()

    try:
        text = sys.stdin.read() if a.path == "-" else open(a.path, errors="replace").read()
    except OSError as exc:
        print(f"⛔ ESTABLISHED NOTHING — could not read {a.path}: {exc}")
        return 2
    if not text.strip():
        print("⛔ ESTABLISHED NOTHING — the input is empty. An empty file and a token "
              "that appears nowhere print the same zero.")
        return 2

    recs = population(text, a.like)
    carrying, total = prevalence(recs, a.token, literal=not a.token_re)
    v, why = verdict(carrying, total)

    scope = f"/{a.like}/" if a.like else "every non-empty line"
    print(f"── PREVALENCE ── {a.token!r} over {total} record(s) matching {scope}")
    if v == "VOID":
        print(f"⛔ ESTABLISHED NOTHING — {why}.")
        if a.like:
            print(f"   ⚠ /{a.like}/ selected {total}. Widen it, or drop --like to compare "
                  f"against every line.")
        return 2

    pct = 100.0 * carrying / total
    print(f"  carried by {carrying} of {total}  ({pct:.0f}%)")
    if v == "NON-DISCRIMINATING":
        print(f"⛔ NON-DISCRIMINATING — {why}.")
        print("   ⇒ Do NOT record a conclusion about one record from this token.")
    else:
        print(f"✅ DISCRIMINATES — {why}.")
        print("   ⇒ Its presence on a given record IS informative. The count is still a "
              "count:\n     read the records before concluding what it means.")
        for r in [x for x in recs if (a.token in x)][:a.show]:
            print(f"        + {r.strip()[:100]}")
    return 1 if v == "NON-DISCRIMINATING" else 0


if __name__ == "__main__":
    sys.exit(main())
