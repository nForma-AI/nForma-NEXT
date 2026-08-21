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


def self_test():
    """⛔ A known-POSITIVE and a known-NEGATIVE, because a checker that always refused
    would pass a suite made only of positives.

    The positive is this tool's own founding case: a suffix on EVERY record. The
    negative is a token that genuinely varies across the same records. If the two do
    not come out differently, the verdict function is not discriminating and no
    result it produces means anything."""
    recs = ["[POLL #1] status=QUEUED, detail=, attempts=0, elapsed=0s",
            "[POLL #2] status=RUNNING, detail=, attempts=1, elapsed=183s",
            "[POLL #3] status=FAILED, detail=boom, attempts=1, elapsed=247s"]
    cases = [
        ("attempts=", recs, "NON-DISCRIMINATING", "a suffix on EVERY record is FORMAT"),
        ("status=FAILED", recs, "DISCRIMINATES", "KNOWN-NEGATIVE: a varying token informs"),
        ("nowhere", recs, "NON-DISCRIMINATING", "absent from all is equally uninformative"),
        ("attempts=", recs[:1], "VOID", "a population of ONE cannot distinguish"),
    ]
    ok = True
    for token, population, want, label in cases:
        carrying, total = prevalence(population, token)
        got, _ = verdict(carrying, total)
        good = got == want
        print(f"{'✅' if good else '❌'} {label}: {carrying}/{total} -> {got}")
        if not good:
            print(f"     want {want}")
            ok = False
    # ⛔ the two verdicts must actually DIFFER on the same population, or the
    # function is constant and every check above is vacuous.
    a1, t1 = prevalence(recs, "attempts=")
    a2, t2 = prevalence(recs, "status=FAILED")
    differ = verdict(a1, t1)[0] != verdict(a2, t2)[0]
    print(f"{'✅' if differ else '❌'} the two verdicts DIFFER on the same records "
          f"— the function is not constant")
    ok = ok and differ
    print("\nall checks passed" if ok else "\nFAILED")
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # ⛔ nargs="?" so `--self-test` is reachable BARE. A control you cannot invoke
    # without also supplying the thing under test is not a control the gate can run —
    # measured: the repo's gate-selftests counts exactly that as UNESTABLISHED.
    ap.add_argument("path", nargs="?", help="file to read, or - for stdin")
    # ⛔ NOT required=True. argparse rejects `--self-test` alone before main() runs,
    # so a required flag makes the control UNREACHABLE — which the repo's gate counts
    # as UNESTABLISHED, correctly: "that is not 'has no self-test'; it is a limit of
    # the invocation." The requirement is enforced below, where it can be explained.
    ap.add_argument("--token", default=None,
                    help="LITERAL text whose prevalence to measure (see --token-re)")
    ap.add_argument("--token-re", action="store_true",
                    help="treat --token as a regex; opt in deliberately")
    ap.add_argument("--like", default=None,
                    help="regex selecting the COMPARABLE records. Without it every "
                         "non-empty line counts, which is rarely the population meant.")
    ap.add_argument("--show", type=int, default=3)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if not a.path or not a.token:
        missing = " and ".join(x for x, v in (("a path", a.path), ("--token", a.token)) if not v)
        print(f"⛔ ESTABLISHED NOTHING — {missing} not given. Pass a file (or - for "
              f"stdin) and --token, or --self-test.")
        return 2
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
