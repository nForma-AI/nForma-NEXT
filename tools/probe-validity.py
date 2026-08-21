#!/usr/bin/env python3
"""Can this probe return the answer it did NOT return?

⛔ THE DEFECT, six instances in one evening across three roles, on questions
nobody actually got wrong:

    grep a COMMIT SUBJECT as though it were file content   -> ABSENT (it was present)
    grep -c a phrase that WRAPS ACROSS LINES               -> 0      (it was present)
    an estate regex missing the encoded ~/.claude/ form    -> 0 hits (40 were there)
    a waiter matching '"status": "404"' against COMPACT    -> silence for two hours
    an AST predicate excluding docstrings that never matched -> 13 OF 13
    POST an APPROVE over a channel that returns 403 for everything

★ EVERY ONE WAS A BROKEN PROBE, NOT A WRONG ANSWER. And a broken probe's output is
not wrong-looking: `0 occurrences` from a pattern that cannot match is byte-identical
to `0 occurrences` from a thing that is not there.

    > A probe must demonstrate, ON THIS RUN, that it can return the answer it did
    > NOT return.                                                     -- DEV2, #353

⇒ TWO-SIDED, AND THE SECOND HALF IS NOT DECORATION. A probe that reports ABSENT
needs a known-present case. A probe that reports PRESENT FOR EVERYTHING needs a
known-absent one -- and that failure is HARDER to notice, because its answer looks
like a finding. `13 of 13` is its own tell: a discriminator that discriminated
nothing.

★ WHY THIS EXISTS WHEN discriminates.py ALREADY DOES THE COMPARISON CASE. That tool
asks *do these two states differ*, and its own header records shipping with a
KNOWN-DIFFERENT control and no KNOWN-SAME one -- `--a 'date +%N' --b 'date +%N'`
returned ✅ DISCRIMINATED. It learned both-halves the hard way and `exit 4 UNSTABLE`
exists because of it. ⇒ But it is tooled for COMPARISONS. **All six probes above
were EXISTENCE readings -- did I find it -- and had nowhere to go even if anyone had
remembered the rule.** This is the missing half.

⛔ AND IT CLOSES ONE HOLE discriminates.py DOCUMENTS AND CANNOT FIX. Its header:
*"the control pair is NOT verified to use the same check as --a/--b."* Here there is
ONE `--probe` template, substituted with each corpus. The controls cannot use a
different check than the real reading, BY CONSTRUCTION rather than by discipline.

⚠⚠ THE HONEST LIMIT, AND IT IS WHY exit 2 IS THE DEFAULT. A known-positive control
requires a case whose answer you already know, and **for a genuinely new question
there may not be one.** This tool cannot manufacture that case and does not pretend
to: with no controls it reports UNESTABLISHED and refuses. ⇒ *Refusing to validate a
probe is not the same as the probe being wrong* -- and that distinction is the whole
convention (#58).

★ The case for this tool in one sentence, from the instance that motivated it:
**"Had you not named it in advance I would have closed the estate question as CLEAN.
Being handed the answer is not a method."** An operator supplying the fact your probe
missed is not validation; it is luck, and 40 hits were one regex away from zero.

Usage:
    probe-validity.py --probe 'grep -qE "PATTERN" {}' \
                      --present-case fixtures/has-it.txt \
                      --absent-case  fixtures/lacks-it.txt \
                      [--target the/real/corpus]

    {} is substituted with each corpus path. A probe with no {} is rejected: a
    command that ignores its corpus is not reading one.

Exit: 0 VALIDATED   -- both controls fired; a target reading, if given, is reportable
      1 INVALID     -- a control did not fire; this probe CANNOT return that answer
      2 UNESTABLISHED -- controls absent or unconstructible; ⛔ never a verdict
      3 the known-positive control of THIS tool failed
"""
import argparse
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from runmarker import begin, result  # noqa: E402

PLACEHOLDER = "{}"


class Void(Exception):
    """Established nothing. ⛔ Never collapse into a verdict."""


def reading(probe, corpus):
    """(rc, stdout) — status is PART of the reading, deliberately.

    ⛔ A probe exiting 1 with empty output is not the same reading as one exiting 0
    with empty output, and collapsing them is how a FAILED COMMAND reads as a
    NEGATIVE RESULT. That collapse is three of the six motivating instances."""
    cmd = probe.replace(PLACEHOLDER, corpus)
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    except OSError as exc:
        raise Void(f"cannot run the probe: {exc}")
    return p.returncode, p.stdout


def verdict_of(rc, out):
    """PRESENT / ABSENT / ERROR.

    ⚠ The convention is grep's — exit 0 means found, exit 1 means not found, and
    anything else is the COMMAND failing rather than answering. ⛔ ERROR is a third
    value on purpose: a probe that crashed did not report ABSENT, and treating it as
    ABSENT is the exact defect this tool exists for."""
    if rc == 0:
        return "PRESENT"
    if rc == 1:
        return "ABSENT"
    return "ERROR"


def validate(probe, present_case, absent_case):
    """(ok, rows). Runs BOTH controls through the SAME probe template."""
    rows = []
    ok = True
    for corpus, expect, why in (
        (present_case, "PRESENT",
         "a case KNOWN to contain the thing — proves the probe can say YES"),
        (absent_case, "ABSENT",
         "a case KNOWN not to — proves the probe can say NO (the 13-of-13 half)"),
    ):
        rc, out = reading(probe, corpus)
        got = verdict_of(rc, out)
        good = got == expect
        ok = ok and good
        rows.append((corpus, expect, got, rc, good, why))
    return ok, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", help="command template; {} is the corpus path")
    ap.add_argument("--present-case", help="corpus KNOWN to contain the thing")
    ap.add_argument("--absent-case", help="corpus KNOWN not to contain it")
    ap.add_argument("--target", help="the corpus you actually want to read")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        rc = self_test()
        result("SELF-TEST-PASS" if rc == 0 else "SELF-TEST-FAILED")
        return rc

    # ⛔ This tool's own known-positive, run before every real validation. A tool
    # that only checks itself when asked is one whose caller never asks — and the
    # subject of this tool is exactly that failure.
    if not _control_fires():
        print("⛔ this tool's own known-positive failed — refusing to validate.",
              file=sys.stderr)
        result("CONTROL-FAILED")
        return 3

    try:
        if not a.probe:
            raise Void("no --probe given")
        if PLACEHOLDER not in a.probe:
            raise Void(f"the probe contains no {PLACEHOLDER} — a command that "
                       f"ignores its corpus is not reading one, and running it "
                       f"three times would validate nothing")
        if not a.present_case or not a.absent_case:
            # ⚠ THE HONEST LIMIT. For a genuinely new question there may be no case
            # whose answer is already known. That is not this tool's to invent.
            raise Void(
                "both --present-case and --absent-case are required. ⚠ If no case "
                "with a KNOWN answer exists — which is the normal situation for a "
                "genuinely new question — then this probe CANNOT be validated, and "
                "that is a real answer: report the reading as UNVALIDATED rather "
                "than as a finding.")
        if a.present_case == a.absent_case:
            raise Void("--present-case and --absent-case are the same path; a "
                       "control pair that is one case establishes nothing")
    except Void as exc:
        print(f"⛔ UNESTABLISHED: {exc}", file=sys.stderr)
        result("UNESTABLISHED")
        return 2

    try:
        ok, rows = validate(a.probe, a.present_case, a.absent_case)
    except Void as exc:
        print(f"⛔ UNESTABLISHED: {exc}", file=sys.stderr)
        result("UNESTABLISHED")
        return 2

    print(f"probe: {a.probe}\n")
    for corpus, expect, got, rc, good, why in rows:
        print(f"  {'ok  ' if good else 'FAIL'} expect {expect:<8} got {got:<8} "
              f"(exit {rc})  {corpus}")
        print(f"        {why}")
    print()

    if not ok:
        bad = [r for r in rows if not r[4]]
        print("⛔ INVALID — this probe cannot return an answer it must be able to "
              "return.")
        for corpus, expect, got, rc, _, _ in bad:
            print(f"   it could not say {expect} about {corpus}, where {expect} is "
                  f"KNOWN to be the truth (it said {got}).")
        print("\n⇒ Any reading from this probe is UNINTERPRETABLE, including one that "
              "\n  looks like a finding. Fix the probe before reading anything with it.")
        result("INVALID")
        return 1

    print("✅ VALIDATED — the probe returned BOTH answers, on this run, through the "
          "same\n   template. A reading from it is now interpretable.")
    if a.target:
        rc, out = reading(a.probe, a.target)
        got = verdict_of(rc, out)
        print(f"\n  target {a.target}  ->  {got}  (exit {rc})")
        if got == "ERROR":
            print("  ⚠ the probe ERRORED on the target though both controls passed — "
                  "the\n    target may not be readable the way the cases were.")
    else:
        print("\n⚠ No --target given: the PROBE is validated, no reading was taken.")

    print("\n⚠ WHAT THIS DOES NOT ESTABLISH: that the cases are representative, or "
          "that\n  the probe asks the question you meant. A validated probe can still "
          "answer\n  a proposition nobody asked (Class C). This shows it CAN "
          "discriminate — never\n  that it discriminates the RIGHT thing.")
    result("VALIDATED")
    return 0


def _control_fires():
    """Known-positive for this tool: a trivially correct probe must validate, and a
    trivially broken one must not."""
    import tempfile, os
    d = tempfile.mkdtemp()
    yes, no = os.path.join(d, "yes.txt"), os.path.join(d, "no.txt")
    open(yes, "w").write("needle\n")
    open(no, "w").write("nothing here\n")
    good, _ = validate("grep -q needle {}", yes, no)
    # ⛔ A probe that says PRESENT about everything — DEV2's 13-of-13 shape.
    bad, _ = validate("true # {}", yes, no)
    return good and not bad


def self_test():
    """⛔ CRITERION 4 — the fixtures are the REAL broken probes from 2026-08-20, and
    the tool must report INVALID for each. Literals, so the controls survive repair."""
    import tempfile, os
    d = tempfile.mkdtemp()

    def w(name, text):
        p = os.path.join(d, name)
        open(p, "w").write(text)
        return p

    # DEV3's estate sweep: the encoded ~/.claude/projects/ form the regex missed.
    # ⛔ ASSEMBLED, NOT WRITTEN — the fixture needs the SHAPE, never the owner.
    # ⇒ The rule and its five cases live in docs/ESTATE-BOUNDARY.md, "The fixture
    #   rule: the shape, never the owner". POINTER, NOT A COPY (#78): a copy cannot
    #   inherit a correction, and that section has already been corrected twice.
    # Local reason only: this fixture demonstrates that the ENCODED path form does
    # not match a `/Users/…/code/<name>` pattern. The shape is the subject; the
    # owner would only make this file read as contamination to its own detector.
    slug = "~/.claude/" + "projects/" + "-Users-someone-code-Neighbour-Estate/memory"
    has_estate = w("has_estate.py",
                   'ap.add_argument("--dir", default=os.path.expanduser(\n'
                   f'    "{slug}"))\n')
    no_estate = w("no_estate.py", 'ap.add_argument("--dir", default=".")\n')

    # DEV2's wrapped phrase: present, but split across a line boundary.
    wrapped = w("wrapped.md", "a PROPERTY OF YOUR OWN\nMETHOD is what this is\n")
    unwrapped_absent = w("plain.md", "nothing of the sort here\n")

    cases = [
        ("⛔ DEV3's estate regex — missed the encoded ~/.claude/projects/ form",
         r"""grep -qE '/Users/[a-zA-Z]+/(code|\.claude)/[A-Za-z0-9_.-]+' {}""",
         has_estate, no_estate, 1),
        ("✅ the same sweep, repaired to match the estate NAME",
         """grep -qE 'Neighbour-Estate|Other-Org' {}""",
         has_estate, no_estate, 0),
        ("⛔ DEV2's wrapped phrase — grep matches LINES, the phrase spans two",
         """grep -q 'PROPERTY OF YOUR OWN METHOD' {}""",
         wrapped, unwrapped_absent, 1),
        ("✅ repaired by joining lines before matching",
         """tr '\\n' ' ' < {} | grep -q 'PROPERTY OF YOUR OWN METHOD'""",
         wrapped, unwrapped_absent, 0),
        ("⛔ the 13-of-13 shape — a probe that says PRESENT about everything",
         """true # {}""", has_estate, no_estate, 1),
        ("⛔ a probe that ERRORS — must not read as ABSENT",
         """cat /nonexistent/{} 2>/dev/null; exit 2""", has_estate, no_estate, 1),
    ]

    fails = []
    for why, probe, pc, ac, expect_rc in cases:
        ok, _ = validate(probe, pc, ac)
        got_rc = 0 if ok else 1
        good = got_rc == expect_rc
        if not good:
            fails.append((why, expect_rc, got_rc))
        print(f"  {'ok  ' if good else 'FAIL'} expect "
              f"{'VALIDATED' if expect_rc == 0 else 'INVALID  '} "
              f"got {'VALIDATED' if got_rc == 0 else 'INVALID  '}  {why}")

    if not _control_fires():
        fails.append(("this tool's own known-positive", 0, 1))
        print("  FAIL this tool's own known-positive did not fire")

    if fails:
        print("\n⛔ the validator is broken; no verdict it produces can be trusted.")
        return 3
    print(f"\n  {len(cases)}/{len(cases)} controls passed. ⇒ Two are REAL broken "
          f"probes from\n    2026-08-20, each shown INVALID, and each paired with "
          f"its REPAIRED form\n    shown VALIDATED — which is the only evidence this "
          f"discriminates rather\n    than always saying one thing.")
    return 0


if __name__ == "__main__":
    begin("probe-validity")
    sys.exit(main())
