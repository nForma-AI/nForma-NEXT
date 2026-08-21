#!/usr/bin/env python3
"""Does a refusal NAME a disposition, or only report that it established nothing?

⛔ WHY THIS EXISTS — #73. `tools/README.md` carries a three-state refusal form: a refusal must say
which KIND it is, because *a correctly-reported absence and an unfixable one arrive as the same
value* -- so the first is never fixed and the second is re-investigated forever.

    ADDABLE — <who>: <what>                      a remedy exists; name it AND its owner
    ADDABLE — <who>: <what> — DECLINED: <why>    the owner weighed it; cost exceeds the absence
    NO REMEDY — the refusal is the verdict       the states genuinely do not differ
    neither of the above                         <- the defect this scans for

★ MEASURED 2026-08-21 at origin/main: the form is adopted by 1 of the 41 tools that refuse.
   2.4%. That is ESTABLISHED-vs-IN-FORCE on a form its own author wrote.

⛔ THIS NEVER GATES AND ALWAYS EXITS 0 ON A COMPLETED SCAN, DELIBERATELY. A gating check fails 40
   files on its first run; a red naming 40 pre-existing files is reverted or ignored, which is worse
   than absent because it teaches that the gate is noise. ⇒ The shape that fits is a RATCHET keyed on
   the count -- proven on #39 -- and 39 of the 40 files are not this author's, so committing other
   roles to a floor is not this tool's call. It reports; someone else decides.

⚠ STATIC BY CONSTRUCTION, AND THAT IS NOT A PROXY HERE. The proposition is textual -- *does this
   refusal NAME a disposition* -- so the source IS the population. ★ Forcing a refusal at RUNTIME
   would mean running each tool's main path, which for a forge-touching instrument PERFORMS the
   action (#506). That hazard is why this reads rather than runs.

⛔ WHAT IT CANNOT DO, and #73 states it against itself: *a check could pass while every refusal names
   a remedy nobody can act on.* ⇒ PRESENCE of a disposition is not USEFULNESS of one. This counts the
   first and says nothing about the second.

⇒ EXIT CODES
    0  scan completed -- see the counts. NEVER a pass/fail verdict.
    2  ESTABLISHED NOTHING -- no tools readable at that path. ⛔ never "all clear".
"""
import argparse
import glob
import os
import re
import sys

REFUSAL = re.compile(r'(VOID|ESTABLISHED NOTHING|established nothing)', re.I)
EMITS = re.compile(r'\bprint\(|file=sys\.stderr')
# ⛔ The disposition must appear in the PRINTED REFUSAL, never merely in the file. A first version
# fell back to "anywhere in the source" and credited THREE files that only MENTION the form in a
# docstring -- use-versus-mention, in the predicate written to find dispositions. Caught by a plant,
# not by reading it back.
DISPO = re.compile(r'ADDABLE\s*[—-]|NO REMEDY')

NO_PATH, NAMED, UNNAMED = "NO-REFUSAL-PATH", "NAMED", "UNNAMED"


def classify(src):
    """-> NO-REFUSAL-PATH / NAMED / UNNAMED. Pure, so the suite can drive every branch."""
    printed = [l for l in src.splitlines() if REFUSAL.search(l) and EMITS.search(l)]
    if not printed:
        return NO_PATH
    return NAMED if any(DISPO.search(l) for l in printed) else UNNAMED


def scan(root, out=sys.stdout):
    tools = sorted(t for t in glob.glob(os.path.join(root, "tools", "*.py"))
                   if not os.path.basename(t).startswith("test_"))
    if not tools:
        print("⛔ VOID — no instruments readable at that path. ESTABLISHED NOTHING, not 'all named'.",
              file=out)
        return 2
    buckets = {NO_PATH: [], NAMED: [], UNNAMED: []}
    for t in tools:
        with open(t, errors="ignore") as fh:
            buckets[classify(fh.read())].append(os.path.basename(t))
    for kind in (NAMED, UNNAMED, NO_PATH):
        print(f"  {kind:<17} {len(buckets[kind]):>3}", file=out)
        if kind == UNNAMED:
            for n in buckets[kind]:
                print(f"      {n}", file=out)
    total = sum(len(v) for v in buckets.values())
    print(f"  {'PARTITION':<17} {total:>3}  = sum of the three buckets above", file=out)
    if total != len(tools):
        print(f"⛔ VOID — buckets sum to {total} against {len(tools)} instruments. ESTABLISHED NOTHING.",
              file=out)
        return 2
    refusing = len(buckets[NAMED]) + len(buckets[UNNAMED])
    me = os.path.basename(__file__)
    mine = me in buckets[NAMED]
    print(f"\n  ⇒ {len(buckets[NAMED])} of {refusing} refusals name a disposition.", file=out)
    if mine:
        # ⛔ This instrument is itself an instrument in tools/, and its own refusals name
        # dispositions -- so SHIPPING THE MEASUREMENT RAISED THE NUMBER IT REPORTS, by one, on the
        # day it landed. Stated rather than quietly enjoyed.
        print(f"  ⚠ {len(buckets[NAMED]) - 1} of {refusing - 1} EXCLUDING this tool, which counts"
              f"\n     itself: adding the instrument raised the figure it reports.", file=out)
    print("⚠ THIS IS NOT A VERDICT AND EXITS 0 EITHER WAY. A gate that reds on 40 pre-existing files"
          "\n   teaches that the gate is noise; a RATCHET on this count is the shape that fits (#39),"
          "\n   and committing other roles' files to a floor is not this tool's call.", file=out)
    print("⛔ PRESENCE of a disposition is not USEFULNESS of one — #73's own proxy test, unaddressed"
          "\n   here and stated so it is not read as covered.", file=out)
    return 0


def self_test(out=sys.stdout):
    """⚠ Four planted cases, and case 3 is the one that caught the first version."""
    cases = [
        ('print("⛔ VOID: cannot read. ADDABLE — DEVOPS: grant read access")', NAMED,
         "names it IN the refusal"),
        ('print("⛔ VOID: cannot read — established nothing")', UNNAMED,
         "refuses and names nothing"),
        ('"""We use ADDABLE — OWNER: what, elsewhere."""\nprint("⛔ VOID: established nothing")',
         UNNAMED, "MENTIONS the form in a docstring; the refusal is bare"),
        ('print("all good")', NO_PATH, "no refusal path at all"),
        ('print("⛔ VOID: no discriminator. NO REMEDY — the refusal is the verdict")', NAMED,
         "NO REMEDY counts as named"),
    ]
    bad = 0
    for src, want, label in cases:
        got = classify(src)
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} {label:<48} want={want:<16} got={got}", file=out)
    seen = {classify(s) for s, _, _ in cases}
    if seen != {NAMED, UNNAMED, NO_PATH}:
        print(f"  FAIL not every bucket exercised: {seen}", file=out)
        bad += 1
    else:
        print("  ok  every bucket exercised — the classifier can return each answer", file=out)
    print("PASS" if not bad else f"{bad} FAILED", file=out)
    return 0 if not bad else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--states", action="store_true")
    a = ap.parse_args(argv)
    if a.states:
        for kind, code, meaning in (
                ("VERDICT", "NAMED", "the printed refusal names ADDABLE or NO REMEDY"),
                ("VERDICT", "UNNAMED", "it refuses and names no disposition -- #73's defect"),
                ("VERDICT", "NO-REFUSAL-PATH", "no printed refusal to classify"),
                ("EXIT", "0", "scan completed -- counts only, never a pass/fail verdict"),
                ("EXIT", "2", "established nothing: no instruments readable, or the buckets did not sum")):
            print(f"{kind}\t{code}\t{meaning}")
        return 0
    if a.self_test:
        return self_test()
    return scan(a.root)


if __name__ == "__main__":
    sys.exit(main())
