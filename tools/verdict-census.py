#!/usr/bin/env python3
"""Has each indexed instrument EVER produced a verdict? Answered by running them.

⛔ Why this exists — #2. Two existing properties presuppose execution: *did the read succeed*
catches a confident EMPTY answer, *did it read the right things* catches a confident WRONG one.
Neither can see a check that has never spoken at all. `tools/README.md` indexes fifteen
instruments and records, for each, what its exit codes MEAN — and nothing anywhere records
whether any of them has ever emitted one.

★ **The answer is produced by execution, never by reading the index.** An index entry is a claim
that an instrument exists; this runs it and reports what came back. That distinction is the whole
point of #2, and asserting verdict-history from a table would reproduce the defect.

⛔ FOUR STATES, and collapsing any pair loses the finding #2 is about:

    VERDICT-SEEN        ran, and exited a code its own docstring documents as a CONCLUSION
    ESTABLISHED-NOTHING ran, and refused a verdict — exit 2 by this repo's convention.
                        ⚠ A refused verdict is NOT a verdict. It is the honest form of silence.
    NO-VERDICT-VOCAB    ran, but documents NO exit codes at all, so "did it conclude?" cannot
                        be read from its contract. ⚠ Unanswerable is not the same as "no".
    NEVER-RUN           did not conclude: crashed, timed out, or exited a code it does not
                        document. ⛔ This is the state #2 says is invisible to everything else.

⇒ `NEVER-RUN` and `ESTABLISHED-NOTHING` are deliberately separate, per #2's acceptance criteria
and #58: one exit code carrying both is the defect, not the reporting of it.

⛔ THE KNOWN-POSITIVE IS OUTSIDE THE MEASURED POPULATION. The population is `tools/`; the control
is a set of SYNTHETIC fixtures written at self-test time, one per state. Keying it on a tool that
happens to be broken today would make this pass only while that breakage survives — #26's sharp
subtype, and the mistake `index-watch.py` shipped with before #139.

⚠ What this does NOT do. It does not decide what to do about a never-run check — that is #2's
premise, not its remedy, and is explicitly out of scope on the issue. It does not judge whether a
verdict was CORRECT. It runs each instrument with no arguments and a timeout: an instrument whose
real verdict needs flags may report ESTABLISHED-NOTHING here and be healthy in use, which is
reported rather than hidden.

⛔ THREE MODES, AND THEIR EXIT CODES ARE NOT INTERCHANGEABLE — #2 is answered by the second,
not the first, and the third is not a verdict about anything.

    (bare)          FULL CENSUS. Runs every indexed instrument. Answers "what is true now."
                    Measured on this repository: 4m20s cold.
    --ledger        THE RECORD #2 ASKS FOR. Same question restricted to "has this instrument EVER
                    produced a verdict" — a monotone predicate, so a confirmed verdict from
                    unchanged bytes is taken from `tools/verdict-ledger.json` rather than re-run.
                    ⛔ MEASURED, AND IT IS THE OPPOSITE OF WHAT I PREDICTED: a warm refresh
                    SKIPPED 23 OF 32 INSTRUMENTS — 72% of the population — AND STILL TOOK 3m16s
                    against a 4m20s cold run. ★ Skipping 72% of the WORK bought 25% of the TIME:
                    the cost is not spread across the population, it is concentrated entirely in
                    the rows the design refuses to skip. An instrument that concluded is fast
                    *because* it concluded; the expensive rows are the ones that timed out or
                    refused. ⇒ THE SKIP IS ANTI-CORRELATED WITH THE COST, and no amount of
                    further skipping fixes that.
    --stale-check   Does the record still cover the index? RUNS NOTHING. Measured 0.085s.
                    ⇒ This is the mode that is affordable on a merge cadence. It exists because
                    a 3-minute refresh is past the attention a reader has, and an instrument
                    nobody can afford to consult is indistinguishable from one that never spoke —
                    which is this issue's own property, reached from the opposite side
                    (ARCHITECT, #2).

⛔ THE CODES MEAN DIFFERENT THINGS PER MODE. Reading one as the other is the whole defect class:
      bare / --ledger   0 every indexed instrument concluded (or has a verdict on record)
                        1 at least one has NOT — ⛔ this is #2's finding
                        2 established nothing (the index was unreadable or named nothing)
      --stale-check     0 THE RECORD IS CURRENT. ⚠ NOT "every instrument produces verdicts."
                        1 the indexed population moved — a name or a blob the record lacks
                        2 established nothing

Exit: 0 no finding · 1 a finding · 2 established nothing
"""
import argparse
import re
import subprocess
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "tools" / "README.md"
LEDGER = ROOT / "tools" / "verdict-ledger.json"
ROW = re.compile(r"^\|\s*`([A-Za-z0-9_.-]+\.py)`\s*\|", re.M)
# "Exit: 0 clean · 1 findings · 2 established nothing"  ->  {0,1,2}
EXIT_DOC = re.compile(r"^Exit(?:\s+codes)?:\s*(.+?)(?:\n\n|\n\"\"\")", re.M | re.S)
CODE = re.compile(r"\b(\d)\b")
# This repo's single carried convention: 2 means "established nothing", never "all clear".
REFUSAL = 2
# ⚠ AN INVENTED CALIBRATION, and it is labelled as one. 90 was extrapolated from a SINGLE
# measurement of a SINGLE instrument (stranded-branches.py, ~45s) after a 25s bound manufactured a
# false NEVER-RUN. ⛔ One doubling of one observation is not a distribution.
# ⇒ Rather than guess a better number, every run now PRINTS the elapsed time of each instrument
# and the slowest observed against this bound, so a reader can see whether 90 is anywhere near
# anything. Same move as #229's source-age line: state the calibration's basis, do not judge it.
# ⛔ And note what a clean run does NOT prove: if nothing times out, the bound was never TESTED.
# "No instrument approached it" and "the bound is correct" are different propositions.
TIMEOUT = 90

VERDICT, NOTHING, NOVOCAB, NEVERRUN, SLOW = (
    "VERDICT-SEEN", "ESTABLISHED-NOTHING", "NO-VERDICT-VOCAB", "NEVER-RUN", "NO-VERDICT-IN-TIME")

# ⛔ A SECOND QUESTION, and #151 is why it exists. `doctrine-watch.py` shipped to main with a
# FAILING known-positive: its control asserted that a doctrine-moved range exits 1, but the tool
# exits 1 only when a role is BEHIND — so the control fired only while the fleet was broken and
# went silent once everyone caught up. Drawn from inside the population it measured (#26).
# ⛔ NOTHING CAUGHT IT, because nothing runs `--self-test`. TEAMLEAD named that as #2's territory.
# ⇒ A bare run answers "did it produce a verdict". It does NOT answer "is that verdict worth
#   anything", and an instrument whose own known-positive is broken reads VERDICT-SEEN either way.
STPASS, STFAIL, STNONE, STDECL = ("SELFTEST-PASS", "SELFTEST-FAIL", "NO-SELF-TEST",
                                  "SELFTEST-DECLARED")
# ⛔ A FIFTH STATE, AND ITS ABSENCE WAS THE SAME COLLAPSE THIS FILE ALREADY FIXED ONCE. classify()
# separates NO-VERDICT-IN-TIME from NEVER-RUN (#248) because a timeout is a property of the BOUND
# the caller chose, not of the instrument. selftest_state() folded a timeout into NO-SELF-TEST —
# "I could not wait long enough" reported as "this tool has no control".
# ⚠ MEASURED ON THIS FILE ITSELF: selftest_state runs THREE subprocesses, and one is a BARE run.
#   A bare verdict-census.py is a full census, minutes long. At a 60s bound it times out and this
#   tool reported ITSELF as NO-SELF-TEST — while `--self-test` returns 0 with 49 lines of controls.
# ★ The detail string said "no self-test verdict within 60s". The STATE did not, and a state is
#   what a census tallies. I read my own row as ABSENT before reading the detail beside it.
STSLOW = "NO-SELFTEST-IN-TIME"
SELFTEST = "--self-test"
# ⛔ THE PROBE MUST BE THE SAME LENGTH AS THE REAL FLAG, and this was measured rather than
# reasoned. A flag NAME influences output beyond its own occurrence: `gh`'s usage block wraps to
# a width the argument affects, so `--self-test` (11) and `--zzz-not-a-real-flag` (21) produced
# usage text that differed in LAYOUT after the name itself was masked out. gh-complete.py was
# then read as recognising a flag it has never heard of. ⇒ Masking a token cannot undo a layout
# effect the token caused. Same length, and the difference is substance.
BOGUS = "--zzzz-zzzz"
assert len(BOGUS) == len(SELFTEST), "the probe must be length-matched or masking is unsound"


def documented_codes(src):
    m = EXIT_DOC.search(src)
    if not m:
        return None
    return {int(c) for c in CODE.findall(m.group(1))}


# ⚠ Which code does THIS instrument use for "established nothing"? Read from its own docstring,
# with 2 as a NAMED fallback rather than an assumption.
# ⛔ THE PHRASE, NEVER THE BARE WORD — and the bare word cost two wrong rows before this line
# existed. `pane-binding.py` documents `1 at least one is not (ESTABLISHED)` and `grant-check.py`
# documents `1 no live grant (ESTABLISHED)`. In BOTH, "ESTABLISHED" means THE FINDING IS
# ESTABLISHED — the opposite of "established nothing". A predicate matching bare `establish`
# picked code 1 as their refusal, turning a real verdict into a refusal in one tool and a real
# refusal into a verdict in the other.
# ★ A word-sense collapse inside the remedy for a word-sense collapse. Found only by diffing the
#   old rows against the new — the audit I had said on #440 that I had not done.
REFUSAL_WORDS = re.compile(
    r"establish\w*\s+nothing|nothing\s+(?:is\s+)?establish|"
    r"\bvoid\b|\brefus\w*|\bno\s+verdict\b|\bcould\s+not\s+(?:read|run|tell)\b", re.I)


def refusal_code(src, default=2):
    """(codes, derived) — the exit code(s) this instrument documents as establishing nothing.

    ⛔ WHY THIS IS NOT JUST `2`. This file already reads each instrument's docstring to decide
    whether a code is DOCUMENTED — and then ignored that same docstring to decide what 2 MEANS,
    using a module constant. Using the documentation for one question and a constant for the
    other is the derive-vs-hardcode split this repository files defects about, committed here.

    ⚠ MEASURED 2026-08-21: three indexed instruments document exit 2 as something other than a
    refusal, and one of them is unambiguous — `exists-anywhere.py` documents
        `2 absent everywhere · 3 established nothing`
    ⇒ "absent everywhere" is a CONCLUSION. Read through a hardcoded refusal it becomes
    ESTABLISHED-NOTHING: a real finding inverted into a non-answer, about someone else's tool.

    ⚠ AND THE FALLBACK IS REPORTED, NOT SILENT. Prose is a weak thing to parse; where no code's
    description carries refusal vocabulary this returns (2, False) so the caller can say the
    reading rests on this repository's convention rather than on the instrument's own words.
    """
    m = EXIT_DOC.search(src or "")
    if not m:
        return {default}, False
    # ⛔ SLICE BETWEEN CODE POSITIONS — NEVER SPLIT ON A SEPARATOR. The first version joined the
    # block to one line and split on `·`, which two instruments do not use: `runnable-condition.py`
    # and `estate-provenance.py` write an ALIGNED MULTI-LINE block. With no separator to split on,
    # the WHOLE BLOCK became code 0's description, "ESTABLISHED NOTHING" was found inside it, and
    # both returned refusal={0}.
    # ⛔ EXIT 0 READ AS A REFUSAL misclassifies every clean run — strictly worse than the defect
    #   this function was written to fix. Found by auditing the risk I had named rather than by
    #   anything announcing itself, which is the third time in this file that was the only route.
    # ⇒ Separators are NORMALISED to newlines, then each code owns the text up to the NEXT code.
    block = re.sub(r"[·|]", "\n", m.group(1))
    marks = list(re.finditer(r"(?m)^[ \t]*\**(\d)\**[ \t]+", block))
    found = set()
    for i, mk in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(block)
        desc = block[mk.end():end]
        if REFUSAL_WORDS.search(desc):
            found.add(int(mk.group(1)))
    return (found, True) if found else ({default}, False)


def _norm(r, flag):
    """Output with the probe flag itself masked, so two rejections differ only in substance."""
    return (r.returncode, ((r.stdout or "") + (r.stderr or "")).replace(flag, "<FLAG>"))


def selftest_state(path, timeout=TIMEOUT):
    """Does this instrument have a self-test, and does it pass?

    ⛔ DIFFERENTIAL, not a grep and not a bare exit code, and both alternatives were measured
    to fail on this population:

      grep the source for '--self-test'   -> a MENTION check. The string appears in comments
                                             and in docstrings that merely discuss it.
      read the exit code of --self-test   -> COLLIDES. Measured: fleet-state.py exits 2 for an
                                             unrecognised flag AND this repo reserves 2 for
                                             "established nothing". doctrine-watch.py exits 0
                                             for a passing self-test and 2 for a bogus flag.
                                             ⇒ 2-vs-2 is indistinguishable by code alone.

    So the negative half of the control is a flag nothing can implement. If `--self-test` and
    BOGUS produce the same (code, output) once the flag name is masked, the flag was not
    recognised. That is `discriminates.py`'s principle applied to argument parsing.
    """
    try:
        real = subprocess.run([sys.executable, str(path), SELFTEST], capture_output=True,
                              text=True, timeout=timeout, cwd=str(ROOT))
        alt = subprocess.run([sys.executable, str(path), BOGUS], capture_output=True,
                             text=True, timeout=timeout, cwd=str(ROOT))
        bare = subprocess.run([sys.executable, str(path)], capture_output=True,
                              text=True, timeout=timeout, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        # ⛔ NOT NO-SELF-TEST. The bound is the caller's, not the instrument's — and one of the
        # three probes below is a BARE run, which for a census-shaped tool is its whole workload.
        return STSLOW, (f"no self-test verdict within {timeout}s — ⚠ one of the three probes is a"
                        f" BARE run, which for some instruments is minutes of work. Raise"
                        f" --timeout before reading this as 'no control'.")
    except OSError as e:
        return STNONE, f"could not execute: {e}"

    if _norm(real, SELFTEST) == _norm(alt, BOGUS):
        return STNONE, "ABSENT — does not distinguish --self-test from a nonexistent flag"

    # ⛔ THE THIRD STATE, and it is worse than ABSENT. `add_argument("--self-test")` with nothing
    # reading args.self_test is a DECLARATION of a self-test, not an implementation: argparse
    # accepts the flag, the tool runs its NORMAL path, and the normal verdict is returned.
    # ⇒ On a healthy fleet that normal run exits 0, and a census reads "control passed" for a
    #   control that never ran. That is #2's own subject, manufactured by the flag parser.
    # ⚠ An argument parser is a surface where a MENTION is indistinguishable from a CAPABILITY,
    #   and it is the one surface nobody audits. (Found by TEAMLEAD on doctrine-version.py, which
    #   declares the flag at line 235 and reads args.self_test zero times.)
    if (real.returncode, real.stdout, real.stderr) == (bare.returncode, bare.stdout, bare.stderr):
        return STDECL, ("DECLARED but NOT WIRED — --self-test is accepted and produces the "
                        "IDENTICAL output to a bare run. Its exit code is the normal verdict, "
                        "not a control result. ⛔ A passing exit here would be a normal run "
                        "misread as a passing control.")
    if "Traceback (most recent call last)" in (real.stderr or ""):
        last = [l for l in (real.stderr or "").strip().splitlines() if l.strip()][-1][:80]
        return STFAIL, f"self-test crashed: {last}"
    if real.returncode == 0:
        return STPASS, "its own known-positive passes"
    return STFAIL, (f"self-test exited {real.returncode} — ⛔ its known-positive is broken, so "
                    f"its verdicts are not trustworthy")


def classify(path, timeout=TIMEOUT):
    """(state, detail). Runs the instrument with no arguments."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return NEVERRUN, f"unreadable: {e}"
    codes = documented_codes(src)
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                           timeout=timeout, cwd=str(ROOT))
        elapsed = time.time() - t0
    except subprocess.TimeoutExpired:
        # ⛔ NOT NeverRun. A timeout is a property of the bound I chose, not of the instrument.
        # Measured: stranded-branches.py concludes in ~45s and was reported NEVER-RUN under a 25s
        # bound — a wrong verdict about someone else's tool, manufactured by my own parameter.
        return SLOW, (f"no verdict within {timeout}s — raise --timeout before reading this as"
                      f" never-run; the bound is mine, not the instrument's")
    except OSError as e:
        return NEVERRUN, f"could not execute: {e}"

    # ⛔ A traceback is not a verdict, whatever code it exits with. Checked BEFORE the exit
    # code, because a crash that happens to exit 1 would otherwise read as a conclusion.
    if "Traceback (most recent call last)" in (r.stderr or ""):
        last = [l for l in (r.stderr or "").strip().splitlines() if l.strip()][-1][:90]
        return NEVERRUN, f"crashed: {last} [{elapsed:.1f}s]"

    if codes is None:
        return NOVOCAB, f"exited {r.returncode}; docstring documents no exit codes [{elapsed:.1f}s]"
    if r.returncode not in codes:
        return NEVERRUN, (f"exited {r.returncode}, not in its documented set {sorted(codes)}"
                          f" [{elapsed:.1f}s]")
    refs, derived = refusal_code(src)
    if r.returncode in refs:
        ref = r.returncode
        why = ("its own docstring" if derived
               else "this repo's convention — ⚠ ITS docstring does not say, so this reading is"
                    " the convention's, not the instrument's")
        return NOTHING, (f"exit {ref} — refused a verdict (honest silence), per {why}"
                         f" [{elapsed:.1f}s]")
    return VERDICT, f"exit {r.returncode} — a documented conclusion [{elapsed:.1f}s]"


def census(index=None, tools_dir=None, timeout=TIMEOUT):
    # timeout is threaded into the notes below so the reader sees the bound that produced them
    index = index or INDEX
    tools_dir = tools_dir or (ROOT / "tools")
    out, rows = [], []
    try:
        text = index.read_text(encoding="utf-8")
    except OSError as e:
        return 2, [f"  VOID  cannot read {index}: {e} — established nothing"], []
    names = sorted(set(ROW.findall(text)))
    if not names:
        return 2, ["  VOID  the index named no instruments — the table format changed, or it is"
                   " gone. Established nothing."], []

    me = Path(__file__).name
    for n in names:
        if n == me:
            # ⛔ NAMED, never silently skipped — an invisible population narrowing is the defect
            # check-tools-index.py exists against. Running the census inside the census spawns a
            # nested census, which terminates only by timeout and once per level.
            rows.append((n, "SELF-EXCLUDED", "the census does not census itself — a nested run "
                         "terminates only by timeout", STNONE, "n/a"))
            continue
        p = tools_dir / n
        if not p.is_file():
            rows.append((n, NEVERRUN, "indexed but absent from the directory",
                         STNONE, "absent"))
            continue
        st, sd = selftest_state(p, timeout)
        rows.append((n, *classify(p, timeout), st, sd))

    width = max(len(n) for n, *_ in rows)
    for n, st, detail, sst, sdetail in rows:
        out.append(f"  {st:<20} {sst:<14} {n:<{width}}  {detail}")
        if sst in (STFAIL, STDECL):
            out.append(f"  {'':<20} {'':<14} {'':<{width}}  ⛔ {sdetail}")

    tally = {s: sum(1 for _, x, *_ in rows if x == s)
             for s in (VERDICT, NOTHING, NOVOCAB, SLOW, NEVERRUN)}
    tally["SELF-EXCLUDED"] = sum(1 for _, x, *_ in rows if x == "SELF-EXCLUDED")
    stally = {s: sum(1 for *_, x, _ in rows if x == s)
              for s in (STPASS, STFAIL, STDECL, STNONE, STSLOW)}
    stally[STNONE] -= tally["SELF-EXCLUDED"]  # the self row carries no self-test reading
    out.append("")
    out.append("  " + " · ".join(f"{k} {v}" for k, v in tally.items()))
    out.append("  note  verdict-history is measured BY EXECUTION here, not read from the index")
    out.append("  note  each instrument was run with NO ARGUMENTS; one whose real verdict needs"
               " flags may show ESTABLISHED-NOTHING and be healthy in use")
    out.append("  note  this does not judge whether a verdict was CORRECT, only that one was"
               " produced")
    out.append(f"  note  NO-VERDICT-IN-TIME is a statement about the {timeout}s bound, NOT about"
               " the instrument — re-run it alone with a longer --timeout before concluding")
    # ⛔ MAKE THE BOUND CHECKABLE. 90 was one doubling of one observation; printing the observed
    # distribution turns "safe by guess" into "safe against a measurement a reader can see".
    times = []
    for _, _, detail, _, _ in rows:
        m = re.search(r"\[(\d+\.\d)s\]", detail or "")
        if m:
            times.append(float(m.group(1)))
    if times:
        slow = max(times)
        out.append(f"  ----  slowest instrument that CONCLUDED: {slow:.1f}s against a {timeout}s"
                   f" bound ({len(times)} timed).")
        if tally[SLOW]:
            out.append(f"  ----  ⚠ {tally[SLOW]} instrument(s) hit the bound, so the slowest figure"
                       f" above is a LOWER limit — their true durations are unmeasured.")
        else:
            out.append("  ----  ⛔ nothing hit the bound, so the bound was NOT TESTED by this run."
                       " 'No instrument approached it' and 'the bound is correct' are different"
                       " propositions.")
    else:
        out.append("  ----  no durations recovered — the bound is UNEXAMINED by this run.")
    out.append("  " + " · ".join(f"{k} {v}" for k, v in stally.items()))
    out.append("  note  a bare run answers 'did it conclude'; the self-test column answers"
               " 'is that conclusion worth anything' — an instrument with a broken known-positive"
               " reads VERDICT-SEEN either way (#151)")
    # ⚠ STSLOW is NOT a finding: it establishes nothing about the instrument, exactly as
    # NO-VERDICT-IN-TIME does not. It is reported, never counted as a defect.
    rc = 1 if (tally[NEVERRUN] or tally[NOVOCAB] or tally[SLOW]
               or stally[STFAIL] or stally[STDECL]) else 0
    return rc, out, rows


def _fixture(d, name, body, exit_doc=True):
    doc = 'Exit: 0 a verdict · 2 established nothing.' if exit_doc else 'No exit documentation.'
    p = Path(d) / name
    p.write_text(f'#!/usr/bin/env python3\n"""Fixture.\n\n{doc}\n"""\n{body}\n')
    return p


def self_test():
    """⛔ The control is SYNTHETIC and lives outside `tools/`.

    A control drawn from the measured population — "instrument X is broken today, so a NEVER-RUN
    proves I work" — is silenced the moment X is repaired. That is #26's sharp subtype, and it is
    the defect `index-watch.py` shipped with until #139.
    """
    import tempfile
    ok = True
    cases = [
        ("verdict.py",  "raise SystemExit(0)",                       True,  VERDICT),
        ("refusal.py",  "raise SystemExit(2)",                       True,  NOTHING),
        ("novocab.py",  "raise SystemExit(0)",                       False, NOVOCAB),
        ("crash.py",    "raise ValueError('boom')",                  True,  NEVERRUN),
        ("undoc.py",    "raise SystemExit(7)",                       True,  NEVERRUN),
    ]
    with tempfile.TemporaryDirectory() as d:
        for name, body, doc, want in cases:
            p = _fixture(d, name, body, doc)
            got, detail = classify(p, timeout=30)
            hit = got == want
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  {name:<12} -> {got:<20} (want {want})")

        # ⛔ a crash that exits 1 must NOT read as a verdict
        p = _fixture(d, "crash1.py", "import sys\nraise ValueError('boom')", True)
        got, _ = classify(p, timeout=30)
        hit = got == NEVERRUN
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a traceback is not a verdict even when the exit "
              f"code is documented (got {got})")

        # ⛔ THE SELF-TEST COLUMN NEEDS ITS OWN CONTROL, and it is synthetic for the same
        # reason the rest are: keying it on "doctrine-watch is broken today" dies on repair.
        st_cases = [
            ("st_pass.py",
             "import sys\nraise SystemExit(0 if '--self-test' in sys.argv else 2)", STPASS),
            ("st_fail.py",
             "import sys\nraise SystemExit(1 if '--self-test' in sys.argv else 2)", STFAIL),
            # ⛔ the collision case: exits 2 for BOTH, exactly like fleet-state.py
            ("st_none.py", "raise SystemExit(2)", STNONE),
            # ⛔ and the false-positive guard: rejects unknown flags by ECHOING the flag name.
            # Without masking, the two outputs differ and this would read as having a self-test.
            ("st_echo.py",
             "import sys\nprint('unrecognised:', sys.argv[1])\nraise SystemExit(2)", STNONE),
            # ⛔ THE SHAPE THAT DEFEATED THE FIRST VERSION. Not an echo — a LAYOUT effect: the
            # rejection text is truncated to a fixed width, so the flag's LENGTH shifts where the
            # cut falls even after the flag name is masked out. This is gh-complete.py's real
            # shape, synthesised. It passes only because the probe is length-matched.
            # ⚠ st_echo.py above did NOT cover this: it was validated on a shape I invented, and
            # the real one differed. A control validated on a homogeneous sample has been
            # validated on the sample's homogeneity.
            ("st_wrap.py",
             "import sys\nprint(('unknown flag ' + sys.argv[1] + ' ' + 'x'*60)[:48])\n"
             "raise SystemExit(2)", STNONE),
            # ⛔ DECLARED: argparse accepts the flag and nothing reads it, so the tool runs its
            # normal path and returns its normal verdict. Worse than ABSENT — see selftest_state.
            ("st_declared.py",
             "import argparse,sys\n"
             "ap=argparse.ArgumentParser()\nap.add_argument('--self-test',action='store_true')\n"
             "ap.parse_args()\nprint('normal report')\nraise SystemExit(0)", STDECL),
        ]
        for name, body, want in st_cases:
            p2 = _fixture(d, name, body, True)
            got, detail = selftest_state(p2, timeout=30)
            hit = got == want
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  {name:<12} -> {got:<14} (want {want})")

        # ⛔ a timeout must NOT be reported as never-run — the bound is the caller's
        p = _fixture(d, "slow.py", "import time\ntime.sleep(30)\nraise SystemExit(0)", True)
        got, detail = classify(p, timeout=2)
        hit = got == SLOW and "bound is mine" in detail
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a slow instrument is NO-VERDICT-IN-TIME, not "
              f"NEVER-RUN (got {got})")

        # ⛔ an index naming nothing is VOID, never "all instruments fine"
        idx = Path(d) / "README.md"
        idx.write_text("# no table here\n")
        rc, lines, _ = census(index=idx, tools_dir=Path(d), timeout=30)
        hit = rc == 2 and any("VOID" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an index naming no instruments exits 2 VOID, not 0"
              f" (got {rc})")

        # ------------------------------------------------------------------
        # LEDGER — the controls below target the ONE place cost is saved, because a saving is
        # the only place a wrong answer becomes invisible. A ledger that skipped too much would
        # still print a clean report; nothing else in this file would notice.
        # ------------------------------------------------------------------
        import json
        ld = Path(d) / "ledger-tools"
        ld.mkdir()
        _fixture(ld, "good.py", "raise SystemExit(0)", True)
        lidx = Path(d) / "LEDGER-README.md"
        lidx.write_text("| `good.py` | a fixture |\n")
        lpath = Path(d) / "rec.json"

        rc, _, rec = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = rc == 0 and rec["good.py"]["ever_verdict"] is True
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a fixture that concludes is recorded EVER (rc={rc})")

        rc, lines, _ = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = rc == 0 and not any(l.startswith("  ran   ") for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a confirmed verdict from unchanged bytes is NOT "
              f"re-run — this is the whole saving")

        # ⛔ A SLOW INSTRUMENT IS NOT AN INSTRUMENT WITHOUT A CONTROL, and folding the two is
        # the collapse classify() already fixed as NO-VERDICT-IN-TIME vs NEVER-RUN (#248).
        # ⚠ Controlled in BOTH directions: a state that swallowed the absent case would report
        # every uncontrolled tool as merely slow, which is worse than the defect it replaced.
        slow = _fixture(d, "st_slow.py", "import time\ntime.sleep(20)\nraise SystemExit(0)")
        got, _ = selftest_state(slow, timeout=2)
        ok &= got == STSLOW
        print(f"  {'ok  ' if got == STSLOW else 'FAIL'}  an instrument slower than the bound is"
              f" {STSLOW}, not NO-SELF-TEST (got {got})")

        absent = _fixture(d, "st_absent.py", "raise SystemExit(0)")
        got, _ = selftest_state(absent, timeout=30)
        ok &= got == STNONE
        print(f"  {'ok  ' if got == STNONE else 'FAIL'}  and a genuinely uncontrolled instrument"
              f" is still NO-SELF-TEST (got {got}) — the new state does not swallow it")

        # ⛔ THE FINGERPRINT MUST MOVE FOR A CLASSIFICATION CHANGE AND HOLD FOR A COSMETIC ONE.
        # Controlled in BOTH directions: one that never moves preserves wrong rows forever, and
        # one that always moves discards 49 rows for a docstring fix and costs 12 minutes (#465).
        _fp0 = classifier_fingerprint()
        _real_words = REFUSAL_WORDS
        try:
            globals()["REFUSAL_WORDS"] = re.compile(r"zzz-not-the-real-vocabulary", re.I)
            _fp1 = classifier_fingerprint()
        finally:
            globals()["REFUSAL_WORDS"] = _real_words
        ok &= _fp1 != _fp0
        print(f"  {'ok  ' if _fp1 != _fp0 else 'FAIL'}  changing the refusal VOCABULARY moves the"
              f" fingerprint — a constant that decided three rows today is covered")

        _real_doc = globals()["documented_codes"]
        try:
            def _alt(src):          # a DIFFERENT classifying implementation
                return {0, 1, 2}
            globals()["documented_codes"] = _alt
            _fp2 = classifier_fingerprint()
        finally:
            globals()["documented_codes"] = _real_doc
        ok &= _fp2 != _fp0
        print(f"  {'ok  ' if _fp2 != _fp0 else 'FAIL'}  changing a classifying FUNCTION moves the"
              f" fingerprint")

        ok &= classifier_fingerprint() == _fp0
        print(f"  {'ok  ' if classifier_fingerprint() == _fp0 else 'FAIL'}  and it returns to the"
              f" original once both are restored — it is a function of the code, not of the run")

        # ⛔ a name in CLASSIFYING that no longer exists is VOID, never a quietly shorter hash
        _real_cls = globals()["CLASSIFYING"]
        try:
            globals()["CLASSIFYING"] = _real_cls + ("no_such_function_here",)
            _fp3 = classifier_fingerprint()
        finally:
            globals()["CLASSIFYING"] = _real_cls
        ok &= _fp3 is None
        print(f"  {'ok  ' if _fp3 is None else 'FAIL'}  a CLASSIFYING name that does not exist"
              f" returns None (-> VOID), rather than hashing what is left")

        # ⛔ THE SELF ROW MUST BE NAMED, NOT OMITTED. census() states this rule; the ledger path
        # broke it and reported "22 of 49" for a population of 50. An invisible narrowing is the
        # defect check-tools-index.py exists against.
        (ld / Path(__file__).name).write_text("raise SystemExit(0)\n")
        lidx.write_text(f"| `good.py` | f |\n| `{Path(__file__).name}` | f |\n")
        lpath.unlink()
        _, lines, rec = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = (any("SELF-EXCLUDED" in l for l in lines)
               and any(Path(__file__).name in l for l in lines)
               and any(" of 1 indexed" in l for l in lines))
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  the ledger NAMES its self-exclusion and drops it"
              f" from the denominator, rather than omitting it silently")
        lidx.write_text("| `good.py` | a fixture |\n")
        lpath.unlink()
        ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)

        # ⛔ A RECORD WRITTEN BY A DIFFERENT CLASSIFIER IS NOT EVIDENCE ABOUT THIS ONE, and the
        # discard must be NAMED. A silent full re-run is indistinguishable from a cheap warm one,
        # so a reader could not tell every prior row had been thrown away.
        stamped = json.loads(lpath.read_text())
        stamped["_classifier"] = "0" * 40
        lpath.write_text(json.dumps(stamped))
        rc, lines, _ = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = any("CLASSIFIER CHANGED" in l for l in lines) and any("ran   " in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a record stamped by ANOTHER classifier is discarded"
              f" AND the discard is named, not silent")

        rcx, _ = stale_check(index=lidx, tools_dir=ld, path=lpath)
        ok &= rcx == 0
        print(f"  {'ok  ' if rcx == 0 else 'FAIL'}  after the re-measure the record matches this"
              f" classifier again (rc={rcx})")

        stamped = json.loads(lpath.read_text())
        stamped["_classifier"] = "f" * 40
        lpath.write_text(json.dumps(stamped))
        rcx, lines = stale_check(index=lidx, tools_dir=ld, path=lpath)
        hit = rcx == 1 and any("DIFFERENT classifier" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  --stale-check reports a FOREIGN classifier as stale"
              f" and says why (rc={rcx})")

        # ⛔ THE CONTROL THAT MATTERS MOST. A stored NEGATIVE must be re-measured even when the
        # bytes are identical, because a negative flips without an edit: an absent credential, an
        # unreachable forge, a raised --timeout. Skipping it would freeze a NEVER-RUN forever and
        # the report would look no different.
        stale = json.loads(lpath.read_text())
        stale["good.py"]["ever_verdict"] = False
        stale["good.py"]["state"] = NEVERRUN
        lpath.write_text(json.dumps(stale))
        rc, lines, rec = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = rc == 0 and rec["good.py"]["ever_verdict"] is True and any("ran   good.py" in l
                                                                        for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a recorded NEGATIVE is re-run despite identical "
              f"bytes, and flips (rc={rc})")

        # ⛔ BOTH DIRECTIONS OF THE NEGATIVE SPLIT. Getting either backwards leaves the report
        # looking identical, so neither is observable except here.
        vocab = _fixture(ld, "novocab.py", "raise SystemExit(0)", False)
        lidx.write_text("| `good.py` | f |\n| `novocab.py` | f |\n")
        lpath.unlink()
        ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        _, lines, _ = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = not any("ran   novocab.py" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  NO-VERDICT-VOCAB is keyed on the blob — a TEXTUAL "
              f"negative is not re-run while the bytes hold")

        vocab.write_text(vocab.read_text().replace("No exit documentation.",
                                                   "Exit: 0 a verdict."))
        _, lines, rec = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = any("ran   novocab.py" in l for l in lines) and rec["novocab.py"]["ever_verdict"]
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  documenting the exit codes changes the blob, which "
              f"re-runs it, which flips it to EVER")

        env = _fixture(ld, "envneg.py", "raise SystemExit(2)", True)
        lidx.write_text("| `envneg.py` | f |\n")
        lpath.unlink()
        ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        _, lines, _ = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = any("ran   envneg.py" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  ESTABLISHED-NOTHING is re-run despite unchanged "
              f"bytes — an ENVIRONMENTAL negative is never taken from the record")
        lidx.write_text("| `good.py` | a fixture |\n")
        lpath.unlink()
        ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)  # reseed for the blob case below

        # ⚠ a positive whose recorded blob does not match the file on disk is not trusted
        tampered = json.loads(lpath.read_text())
        tampered["good.py"]["blob"] = "0" * 40
        lpath.write_text(json.dumps(tampered))
        _, lines, _ = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = any("bytes changed" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a recorded verdict whose blob no longer matches "
              f"the file is re-run, not believed")

        # ⛔ a record that cannot be parsed is VOID — and must NOT be overwritten. Reading a
        # corrupt ledger as "nothing recorded yet" would destroy the only history there is.
        lpath.write_text("{ this is not json")
        rc, _, _ = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = rc == 2 and lpath.read_text() == "{ this is not json"
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an unreadable record exits 2 VOID and is left "
              f"intact, not silently replaced (rc={rc})")

        # ⛔ THE TRIGGER MUST NOT BE A CONSTANT. A standing environmental negative is true
        # continuously; if it drove the exit code, --stale-check would return 1 forever and
        # could never signal that anything happened.
        lidx.write_text("| `good.py` | f |\n| `envneg.py` | f |\n")
        lpath.unlink()
        ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        rc, lines = stale_check(index=lidx, tools_dir=ld, path=lpath)
        hit = rc == 0 and any("STANDING" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a standing environmental negative is REPORTED but "
              f"does not make --stale-check a constant 1 (rc={rc})")

        (ld / "good.py").write_text((ld / "good.py").read_text() + "\n# edited\n")
        rc, _ = stale_check(index=lidx, tools_dir=ld, path=lpath)
        ok &= rc == 1
        print(f"  {'ok  ' if rc == 1 else 'FAIL'}  editing an instrument's bytes DOES move "
              f"--stale-check to 1 — it is an event detector (rc={rc})")

        rc, lines = stale_check(index=lidx, tools_dir=ld, path=Path(d) / "no-such.json")
        hit = rc == 1 and not any("VOID" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  no record at all is STALE (1), not VOID (rc={rc})")

        # ⛔ an instrument indexed but absent is a FINDING, never an omission
        lpath.unlink()
        lidx.write_text("| `good.py` | a fixture |\n| `ghost.py` | indexed, never written |\n")
        rc, _, rec = ledger(index=lidx, tools_dir=ld, timeout=30, path=lpath)
        hit = rc == 1 and rec["ghost.py"]["ever_verdict"] is False
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an indexed-but-absent instrument is ⛔ NEVER and "
              f"exits 1, not skipped (rc={rc})")


    # ==================================================================================
    # ⛔ A POPULATION THIS AUTHOR DID NOT DRAW, AND A STATED EXCEPTION FOR THE PART THAT CANNOT
    # HAVE ONE — criterion 5's population leg (#164 item 1). `population-leg.py` scored this tool
    # DRAWN, and I wrote the sentence saying a DRAWN control wants a real leg or an exception
    # WITH A REASON. On inspection the exception is NARROWER than I claimed when I wrote it:
    #
    #   classify() / selftest_state()   need a SUBPROCESS PER INSTRUMENT. Exercising them against
    #                                   an undrawn population means running the real tools — the
    #                                   ~4-minute cost that made #2 unreadable to begin with.
    #                                   ⇒ EXCEPTION STATED. Its undrawn population is `--ledger`
    #                                     and `--stale-check`, which are live runs, not controls.
    #   documented_codes()              is a PURE FUNCTION OVER SOURCE TEXT. Running it across
    #                                   every real instrument costs a file read each.
    #                                   ⇒ NO EXCEPTION AVAILABLE. It gets a real leg, below.
    #
    # ⚠ I asserted the whole tool was unaffordable in PR #352's body. That was wrong by exactly
    # this much, and a claim of unaffordability that nobody re-checks is how a stated exception
    # decays into an excuse.
    # ==================================================================================
    real = sorted((ROOT / "tools").glob("*.py"))
    if not real:
        print("  ----  NOT ESTABLISHED  no real instruments found, so the undrawn population was"
              " NOT exercised. ⛔ Untested, not correct.")
    else:
        bad = []
        for f in real:
            try:
                codes = documented_codes(f.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            # ⛔ THE ASSERTION ONLY REAL DOCSTRINGS CAN MAKE. Every fixture above documents its
            # exit codes in the one shape I thought of. A parser that returned an EMPTY SET on a
            # docstring it did not understand would classify that tool NO-VERDICT-VOCAB — a
            # confident wrong answer about someone else's tool, from my own parser, and no
            # invented fixture would ever show it.
            if codes is not None and not codes:
                bad.append(f.name)
        ok &= not bad
        print(f"  {'ok  ' if not bad else 'FAIL'}  documented_codes parsed {len(real)} REAL"
              f" instrument docstrings with no empty-set results — a population I did not draw"
              f"{'' if not bad else ' — EMPTY: ' + str(bad)}")

        seen = sum(1 for f in real
                   if documented_codes(f.read_text(encoding="utf-8", errors="replace")))
        ok &= seen > 0
        print(f"  {'ok  ' if seen else 'FAIL'}  and it EXTRACTED codes from {seen} of them — the"
              f" line above is not passing by parsing nothing")
        print("  ----  EXCEPTION STATED  classify() and selftest_state() have NO population leg:"
              " exercising them on an undrawn population means running every real instrument"
              " (~4m). Their undrawn population is --ledger / --stale-check, which are live runs.")


    # ==================================================================================
    # ⛔ THE REFUSAL CODE IS THE INSTRUMENT'S, NOT THIS FILE'S. Controls for the defect that
    # produced this function: exists-anywhere.py documents `2 absent everywhere · 3 established
    # nothing`, and a hardcoded REFUSAL=2 turned a CONCLUSION into a non-answer.
    # ==================================================================================
    EA = '"""x\n\nExit: 0 present on the default ref · 1 present only on other refs'\
         ' · 2 absent everywhere\n      · 3 established nothing.\n"""\n'
    got = refusal_code(EA)
    ok &= got == ({3}, True)
    print(f"  {'ok  ' if got == ({3}, True) else 'FAIL'}  an instrument documenting 3 as established"
          f"-nothing has refusal 3, NOT 2 (got {got}) — the exists-anywhere shape")

    # ⛔ THE WORD-SENSE CASE, AND IT IS THE ONE THAT COST TWO WRONG ROWS. Two instruments write
    # `1 ... (ESTABLISHED)` meaning THE FINDING IS ESTABLISHED — the opposite of "established
    # nothing". A predicate matching the bare word picks code 1 as their refusal, turning a real
    # verdict into a refusal in one tool and a real refusal into a verdict in the other.
    SENSE = ('"""x\n\nExit: 0 every pane BOUND · 1 at least one is not (ESTABLISHED)'
             ' · 2 established nothing\n      3 the self-test failed\n"""\n')
    got = refusal_code(SENSE)
    ok &= got == ({2}, True)
    print(f"  {'ok  ' if got == ({2}, True) else 'FAIL'}  '(ESTABLISHED)' meaning THE FINDING IS"
          f" established does not make code 1 a refusal (got {got}) — the pane-binding shape")

    # ⛔ THE ALIGNED MULTI-LINE FORM, which two real instruments use and which defeated the first
    # splitter completely: with no `·` to split on, the whole block became code 0's description
    # and "ESTABLISHED NOTHING" was found inside it -> refusal={0}. Exit 0 read as a refusal
    # misclassifies every clean run.
    MULTILINE = ('"""x\n\nExit codes:\n'
                 '    0  every condition read is RUNNABLE          (and both controls fired)\n'
                 '    1  at least one ASSERTED\n'
                 '    2  ESTABLISHED NOTHING -- unreadable, empty population, or truncated\n'
                 '       ⚠ never "all clear"\n'
                 '    3  CONTROL FAILED -- the positive did not fire\n"""\n')
    got = refusal_code(MULTILINE)
    ok &= got == ({2}, True)
    print(f"  {'ok  ' if got == ({2}, True) else 'FAIL'}  an ALIGNED MULTI-LINE Exit block with no"
          f" separator yields {{2}}, never {{0}} (got {got}) — the runnable-condition shape")

    # ⚠ and a continuation line belongs to the code ABOVE it, not to a new one
    got = refusal_code('"""x\n\nExit codes:\n  0  clean\n  1  a finding\n'
                       '  2  established nothing\n     never read as clean\n"""\n')
    ok &= got == ({2}, True)
    print(f"  {'ok  ' if got == ({2}, True) else 'FAIL'}  an unnumbered continuation line stays"
          f" with the code above it (got {got})")

    # ⚠ and more than one refusal code is a SET, not a first-match
    TWO = ('"""x\n\nExit: 0 fine · 1 a negative · 2 at least one UNAUDITABLE, establishes nothing'
           ' · 3 the harness is broken and every verdict is void\n"""\n')
    got = refusal_code(TWO)
    ok &= got == ({2, 3}, True)
    print(f"  {'ok  ' if got == ({2, 3}, True) else 'FAIL'}  an instrument with TWO"
          f" established-nothing codes yields both (got {got}) — first-match would hide one")

    NORMAL = '"""x\n\nExit: 0 clean · 1 findings · 2 established nothing\n"""\n'
    got = refusal_code(NORMAL)
    ok &= got == ({2}, True)
    print(f"  {'ok  ' if got == ({2}, True) else 'FAIL'}  the ordinary shape still derives 2, and"
          f" derives it from the DOCSTRING rather than assuming (got {got})")

    # ⛔ NO REFUSAL VOCABULARY AT ALL: fall back to 2, but the fallback must be VISIBLE. A silent
    # fallback is indistinguishable from a derivation, which is the whole defect one level down.
    SILENT = '"""x\n\nExit: 0 yes · 1 no · 2 maybe\n"""\n'
    got = refusal_code(SILENT)
    ok &= got == ({2}, False)
    print(f"  {'ok  ' if got == ({2}, False) else 'FAIL'}  a docstring with no refusal vocabulary"
          f" falls back to 2 and REPORTS the fallback (got {got})")

    # ⚠ and the fallback must reach the reader, not just the return value
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "silent.py"
        f.write_text('#!/usr/bin/env python3\n"""Fixture.\n\nExit: 0 yes · 1 no · 2 maybe\n"""\n'
                     "raise SystemExit(2)\n")
        st, detail = classify(f, timeout=30)
        hit = st == NOTHING and "convention" in detail
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  when the code is the CONVENTION's and not the"
              f" instrument's, the row says so (got {st})")

        g = Path(d) / "conclusive.py"
        g.write_text('#!/usr/bin/env python3\n"""Fixture.\n\nExit: 0 here · 2 absent everywhere'
                     '\n      · 3 established nothing.\n"""\n' + "raise SystemExit(2)\n")
        st, _ = classify(g, timeout=30)
        ok &= st == VERDICT
        print(f"  {'ok  ' if st == VERDICT else 'FAIL'}  exit 2 meaning 'absent everywhere' is a"
              f" VERDICT, not ESTABLISHED-NOTHING (got {st}) — the inversion this fixes")


    # ⛔ --help IS NOT A REFUSAL. argparse exits 0 after printing usage; catching every SystemExit
    # as "unrecognised arguments" made this tool print its help and then declare it established
    # nothing (#350). Controlled in BOTH directions, because a fix that returned 0 for everything
    # would pass the first half and destroy the refusal.
    import contextlib, io
    for _flag, _want in (("--help", 0), ("-h", 0), ("--zzz-not-a-real-flag", 2)):
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
            _got = main(["x", _flag])
        ok &= _got == _want
        print(f"  {'ok  ' if _got == _want else 'FAIL'}  {_flag} -> {_got} (want {_want})"
              f"{' — help is not VOID' if _want == 0 else ' — a bogus flag is still VOID'}")
    return 0 if ok else 3


# ---------------------------------------------------------------------------
# LEDGER MODE — the record #2 asks for, and the reason it is affordable to keep
# ---------------------------------------------------------------------------
# ⛔ A FULL CENSUS ANSWERS THE WRONG QUESTION FOR THE COST IT CHARGES. It re-runs every indexed
# instrument three times (bare · --self-test · a length-matched bogus flag) and takes over two
# minutes — measured by ARCHITECT on #2, whose finding is the mirror of the issue: the census
# DID emit `SELFTEST-DECLARED 1`, and nobody read it, because the reader had to spend two
# minutes to find out whether there was anything to read. A verdict nobody can afford to consult
# is indistinguishable from a verdict nobody produced.
#
# ★ #2 does not ask "what is true now". It asks whether each instrument has **EVER** produced a
# verdict — and EVER IS MONOTONE. An instrument that concluded once cannot un-conclude. So a
# CONFIRMED POSITIVE, keyed to the exact bytes that produced it, never needs re-running.
#
# ⚠ THIS IS A STORED CALIBRATION AND THIS REPOSITORY HAS A STANDING RULE AGAINST THOSE (#183,
# #149: derive, never store — a stored value decays silently). The rule is not suspended here;
# it is SATISFIED, and the argument has to be checked rather than assumed:
#
#     stored POSITIVE, blob unchanged  → cannot become false. Monotone. SKIPPED. ← the saving
#     stored POSITIVE, blob CHANGED    → could become false. Re-run. ← keyed on content, not time
#     stored NEGATIVE, any blob        → could become false without the file changing at all
#                                        (gh-complete.py exits 2 when `gh` is unauthenticated;
#                                        authenticate and it flips). ALWAYS re-run.
#     no record                        → new to the index. Run.
#
# ⇒ The ONLY thing ever skipped is the one direction that cannot rot. `doctrine-watch.py`'s
# watermark stores a POSITION, and a position moves both ways — which is why it decayed into the
# defect it replaced (#183). An ever-predicate has no second direction to decay in.
#
# ⛔ AND THE RECORD IS KEYED ON CONTENT, NOT ON A DATE OR A SHA OF main. `git hash-object` of the
# instrument's own bytes: the same value git stores, so a reader can `git cat-file -p <blob>` and
# see exactly which text produced the verdict. WHEN it was taken is derived from the ledger
# file's own `git log` — never written into it, because a written date is the thing that rots.


# ⛔ THE FINGERPRINT COVERS WHAT DETERMINES A VERDICT, NOT THE WHOLE FILE, and the first version
# got this wrong at real cost. Hashing every byte meant that ADDING A CONTROL or FIXING A DOCSTRING
# discarded all 49 rows and forced a 12-minute re-measure — which then finished STALE, because six
# instruments landed while it ran (#465).
# ★ Neither edit can change a single classification. ⇒ A fingerprint that invalidates a record for
#   a change that cannot alter its contents is not conservative, it is WRONG in the expensive
#   direction: it trains its owner to avoid improving the tool.
# ⚠ THE RISK RUNS THE OTHER WAY TOO and is stated rather than assumed: if a function that DOES
#   affect classification is left out of this list, rows survive a change that should have voided
#   them. ⇒ The list is NAMED here, derived from live source at run time (never a stored hash),
#   and every name in it is a function whose output feeds a state in the census vocabulary.
CLASSIFYING = ("documented_codes", "refusal_code", "classify", "selftest_state", "_norm")


def classifier_fingerprint():
    """Hash of the code that DETERMINES a verdict, plus the constants those functions read.

    ⚠ Derived from the module's own live source via `inspect.getsource`, so a renamed or deleted
    function fails loudly here rather than silently dropping out of the hash.
    """
    import inspect
    parts = []
    for name in CLASSIFYING:
        fn = globals().get(name)
        if fn is None:
            # ⛔ NOT a silent skip. A name in CLASSIFYING that no longer exists means this list and
            # the code have diverged, and every row keyed on it is of unknown provenance.
            return None
        parts.append(inspect.getsource(fn))
    # ⚠ CONSTANTS COUNT. `REFUSAL_WORDS` alone decided three rows wrongly today; a fingerprint over
    # functions only would have let that change ride on an unchanged record.
    parts += [repr(REFUSAL_WORDS.pattern), repr(sorted(DOC_CODES_CONSTS))]
    return blob_id("".join(parts).encode("utf-8"))


DOC_CODES_CONSTS = (VERDICT, NOTHING, NOVOCAB, NEVERRUN, SLOW, STPASS, STFAIL, STNONE, STDECL,
                    SELFTEST, BOGUS)


def blob_id(data):
    """git's own blob hash of `data`, so the key is checkable with `git cat-file -p`."""
    import hashlib
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def _rerun_reason(rec, blob):
    """Why this instrument must be run now, or None if the record already answers #2.

    ⛔ Returning None is the ONLY place cost is saved, so it is the only place a wrong answer
    becomes invisible. It is reachable for exactly one shape: a confirmed verdict, from these
    exact bytes, whose self-test did not fail.
    """
    if rec is None:
        return "new to the index"
    if rec.get("blob") != blob:
        return "the instrument's bytes changed since the record was taken"
    if not rec.get("ever_verdict"):
        # ⛔ "NEGATIVE" IS ITSELF A COLLAPSED PAIR, and treating it as one state costs a re-run
        # per cycle for information that cannot have changed.
        #
        #   TEXTUAL     NO-VERDICT-VOCAB is read out of the instrument's OWN DOCSTRING by
        #               documented_codes(). It is a function of the bytes. While the blob holds,
        #               re-running it can only produce the answer already on record.
        #   ENVIRONMENTAL  ESTABLISHED-NOTHING · NO-VERDICT-IN-TIME · NEVER-RUN all flip with NO
        #               EDIT: gh-complete.py exits 2 while `gh` is unauthenticated and 0 after;
        #               stranded-branches.py exceeds a 90s bound and concludes under a longer one;
        #               a crash can be an absent import rather than a defect in the file.
        #
        # ⇒ Only the environmental ones are re-measured unconditionally. Getting this backwards
        #   is invisible in the report either way, which is why both directions are controlled
        #   in self_test().
        if rec.get("state") == NOVOCAB:
            return None
        return ("recorded negative for an ENVIRONMENTAL reason — it can flip with no edit, so it"
                " is never taken from the record")
    if rec.get("selftest") in (STFAIL, STDECL):
        return "recorded with a broken or merely-declared known-positive (#151)"
    return None


def stale_check(index=None, tools_dir=None, path=None):
    """Does the record still describe the indexed population? NO SUBPROCESSES. Sub-second.

    ⛔ WHY THIS IS A SEPARATE MODE, and the measurement that forced it. The monotone skip was
    supposed to make a refresh cheap. Measured on this repository: a cold refresh took 4m20s and
    a warm one 3m05s — a 29% saving, NOT a collapse. ★ THE SKIP IS ANTI-CORRELATED WITH THE COST.
    An instrument that CONCLUDED is fast *because* it concluded; the expensive rows are the ones
    that timed out or refused, and those are precisely the environmental negatives a refresh must
    re-run. stranded-branches.py alone spends 90s per probe against the bound.
    ⇒ Three minutes still exceeds the attention a reader has (ARCHITECT, #2: an instrument whose
      cost exceeds the attention available is not consulted, and an unconsulted verdict is
      indistinguishable from one that was never produced).

    ★ So the affordable thing is not a cheaper refresh — it is a cheap way to know whether a
    refresh would say anything new. Every reason to re-run is either a NAME the record has not
    seen or a BLOB it no longer matches, and both are readable off the disk. This answers that
    and nothing else: it never claims a verdict, only whether the record is answerable.

    Exit-shaped return: 0 the record covers the index · 1 it does not · 2 established nothing.
    """
    import json
    index = index or INDEX
    tools_dir = tools_dir or (ROOT / "tools")
    path = path or LEDGER
    try:
        names = sorted(set(ROW.findall(index.read_text(encoding="utf-8"))))
    except OSError as e:
        return 2, [f"  VOID  cannot read {index}: {e} — established nothing"]
    if not names:
        return 2, ["  VOID  the index named no instruments — established nothing"]
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rec, dict):
            raise ValueError("not an object")
    except FileNotFoundError:
        return 1, [f"  ⛔ STALE  no record at {path} — nothing has ever been recorded",
                   f"  ----  refresh with: python3 {Path(__file__).name} --ledger"]
    except (OSError, ValueError) as e:
        return 2, [f"  VOID  {path} could not be read as a record ({e}) — established nothing"]

    # ⛔ TWO QUESTIONS, AND FOLDING THEM INTO ONE EXIT CODE DESTROYS THE MODE. First draft did:
    #
    #   STALE    the indexed population MOVED — a new name, changed bytes, a file gone. An event.
    #   STANDING an environmental negative is on record, so a refresh could still change it. NOT
    #            an event: it is true continuously until someone fixes the instrument.
    #
    # ⇒ Eight instruments are standing negatives here, so a code keyed on "could a refresh say
    #   anything new" returns 1 UNCONDITIONALLY — which is precisely useless as the trigger this
    #   mode exists to be. The exit code tracks STALE only; STANDING is printed every time,
    #   including on exit 0, so nobody can read a 0 as "they all produce verdicts".
    #
    # ⚠ AND STATE THE OTHER HALF, because the codes are close enough to swap by accident:
    #   exit 0 HERE means "the record is current". It does NOT mean every instrument has a
    #   verdict. That finding is --ledger's exit code, and it is 1.
    if rec.get("_classifier") != classifier_fingerprint():
        return 1, [f"  ⛔ STALE  the record was written by a DIFFERENT classifier"
                   f" ({str(rec.get('_classifier'))[:8]}) than the one asking"
                   f" ({str(classifier_fingerprint())[:8]}).",
                   "  ⚠ Rows written by another classifier are not evidence about this one —"
                   " they are not stale readings, they are readings of a different question.",
                   f"  ----  refresh with: python3 {Path(__file__).name} --ledger"]
    rec = {k: v for k, v in rec.items() if not k.startswith("_")}
    me = Path(__file__).name
    covered = [n for n in names if n != me]
    stale, standing = [], []
    for n in covered:
        r = rec.get(n)
        if r is None:
            stale.append((n, "in the index, absent from the record"))
            continue
        try:
            blob = blob_id((tools_dir / n).read_bytes())
        except OSError:
            stale.append((n, "indexed, and not on disk"))
            continue
        if r.get("blob") != blob:
            stale.append((n, f"bytes changed since the record ({str(r.get('blob'))[:8]}"
                             f" -> {blob[:8]})"))
        elif not r.get("ever_verdict") and r.get("state") != NOVOCAB:
            standing.append((n, str(r.get("state"))))
    gone = sorted(set(rec) - set(names))
    out = [f"  {'⛔ STALE' if stale or gone else 'current'}  the record answers"
           f" {len(covered) - len(stale)} of {len(covered)} indexed instruments"
           f"  (verdict-census.py excluded — it does not census itself)"]
    out += [f"  ⛔ {n}: {why}" for n, why in stale]
    out += [f"  ⛔ recorded but no longer indexed: {n}" for n in gone]
    if standing:
        out.append(f"  ⚠ {len(standing)} STANDING environmental negative(s) — on record, and a"
                   f" refresh could still change any of them. NOT staleness, and NOT counted in"
                   f" the exit code: this is true continuously, not an event.")
        out += [f"      {st:<20} {n}" for n, st in standing]
    out.append("  note  NOTHING WAS RUN. This reports whether the RECORD is current. It is not a"
               " verdict about any instrument, and exit 0 here does NOT mean every instrument has"
               " produced one — that finding is `--ledger`'s exit code.")
    if stale or gone:
        out.append(f"  ----  refresh with: python3 {Path(__file__).name} --ledger")
    return (1 if (stale or gone) else 0), out


def ledger(index=None, tools_dir=None, timeout=TIMEOUT, path=None, write=True):
    """Bring the ever-produced-a-verdict record up to date, running only what needs running.

    Returns (rc, lines, record).
    """
    import json
    index = index or INDEX
    tools_dir = tools_dir or (ROOT / "tools")
    path = path or LEDGER
    out = []
    try:
        text = index.read_text(encoding="utf-8")
    except OSError as e:
        return 2, [f"  VOID  cannot read {index}: {e} — established nothing"], {}
    names = sorted(set(ROW.findall(text)))
    if not names:
        return 2, ["  VOID  the index named no instruments — the table format changed, or it is"
                   " gone. Established nothing."], {}

    # ⛔ THE RECORD'S VALIDITY DEPENDS ON THE CLASSIFIER THAT WROTE IT, AND THE FIRST VERSION DID
    # NOT KEY ON THAT. Blobs covered each INSTRUMENT's bytes; nothing covered THIS FILE's. ⇒ Change
    # how a verdict is classified and every stored row silently keeps the old reading.
    #
    # ⚠ MEASURED, AND IT WAS NOT HYPOTHETICAL. `exists-anywhere.py` documents `3 established
    # nothing`; a hardcoded REFUSAL=2 classified its exit 3 as VERDICT-SEEN, and the merged ledger
    # recorded `ever_verdict: true` for an instrument that had REFUSED.
    # ⛔ AND THE MONOTONE SKIP MADE IT PERMANENT: "a verdict cannot un-happen" holds only if the
    #   READING was right. A wrong positive is the one case the design had no recovery path for —
    #   the row would never be re-run, so it could never self-correct.
    # ⇒ The classifier's own blob is part of the key. When it moves, every row is re-measured.
    my_blob = classifier_fingerprint()
    if my_blob is None:
        return 2, ["  VOID  a name in CLASSIFYING no longer exists — this list and the code have"
                   " diverged, so no record can be keyed. Established nothing."], {}
    try:
        prior = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(prior, dict):
            raise ValueError("not an object")
        if prior.get("_classifier") != my_blob:
            # ⚠ NAMED, never silent. A quiet full re-run looks identical to a cheap warm one, and
            # the reader would have no way to know the previous rows were discarded.
            out.append(f"  ⚠ CLASSIFIER CHANGED ({str(prior.get('_classifier'))[:8]} ->"
                       f" {my_blob[:8]}) — every row re-measured. Rows written by a different"
                       f" classifier are not evidence about this one.")
            prior = {}
    except FileNotFoundError:
        prior = {}
    except (OSError, ValueError) as e:
        # ⛔ NOT an empty ledger. A corrupt record read as "nothing recorded yet" would silently
        # re-run everything and then OVERWRITE the only history with today's reading.
        return 2, [f"  VOID  {path} exists but could not be read as a record ({e}) —"
                   " refusing to overwrite it. Established nothing."], {}

    me = Path(__file__).name
    prior = {k: v for k, v in prior.items() if not k.startswith("_")}
    record, rows = {}, []
    for n in names:
        if n == me:
            # ⛔ NAMED, never silently skipped. This file states that rule 680 lines above, in
            # census(), and then broke it here — an invisible population narrowing is the defect
            # check-tools-index.py exists against, and "22 of 49" silently meant "of 50".
            # ⇒ Citing a rule is not installing it (#275), in the file that carries the citation.
            rows.append((n, None, None, "self", "the census does not census itself — a nested run"
                         " terminates only by timeout"))
            continue
        p = tools_dir / n
        try:
            blob = blob_id(p.read_bytes())
        except OSError:
            blob = None  # indexed but absent; classify() reports it, and it must never be skipped
        rec = prior.get(n)
        why = _rerun_reason(rec, blob) if blob else "indexed but absent from the directory"
        if why is None:
            record[n] = rec
            rows.append((n, rec.get("state"), rec.get("selftest"), "kept", "record stands"))
            continue
        st, detail = classify(p, timeout) if blob else (NEVERRUN, "indexed but absent")
        sst, _ = selftest_state(p, timeout) if blob else (STNONE, "absent")
        ever = bool(rec and rec.get("ever_verdict")) or st == VERDICT
        record[n] = {"ever_verdict": ever, "blob": blob, "state": st, "selftest": sst}
        rows.append((n, st, sst, "RAN", why))

    dropped = sorted(set(prior) - set(record))
    width = max([len(n) for n, *_ in rows] + [1])
    for n, st, sst, mark in ((r[0], r[1], r[2], r[3]) for r in rows):
        if mark == "self":
            out.append(f"  {'SELF':<9} {'SELF-EXCLUDED':<20} {'':<18} {n:<{width}}"
                       f"  [not counted]")
            continue
        ever = record[n].get("ever_verdict")
        out.append(f"  {'EVER' if ever else '⛔ NEVER':<9} {str(st):<20} {str(sst):<18}"
                   f" {n:<{width}}  [{mark}]")
    ran = sum(1 for r in rows if r[3] == "RAN")
    # ⚠ the denominator EXCLUDES the self row and the output SAYS which row that was
    out.append("")
    counted = [r for r in rows if r[3] != "self"]
    out.append(f"  {sum(1 for n in record if record[n].get('ever_verdict'))} of {len(counted)}"
               f" indexed instruments carry a verdict ever recorded · {ran} run now,"
               f" {len(rows) - ran} answered from the record")
    for n, _, _, mark, why in rows:
        if mark == "RAN":
            out.append(f"  ran   {n}: {why}")
    if dropped:
        # ⛔ NAMED, not silently deleted. An instrument leaving the index is a fact about the
        # index; dropping its row without saying so would make a removal look like it never was.
        out.append(f"  ⚠ dropped from the record — no longer in the index: {', '.join(dropped)}")
    out.append("  note  a KEPT row was NOT re-run. It is a confirmed verdict from bytes that have"
               " not changed, and 'has ever produced a verdict' cannot become false.")
    out.append("  note  ENVIRONMENTAL negatives (exit 2 · timed out · crashed) are re-run every"
               " time — they flip with no edit. NO-VERDICT-VOCAB is read from the docstring, so"
               " it is keyed on the blob like a verdict: it cannot change while the bytes do not.")
    out.append("  note  WHEN a row was taken is derived from this file's `git log`, never stored"
               " in it. A written date is the part that rots.")
    if write:
        payload = dict(record)
        payload["_classifier"] = my_blob
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        out.append(f"  ----  wrote {path}")
    else:
        out.append("  ----  --dry-run: the record on disk was NOT updated")
    never = [n for n in record if not record[n].get("ever_verdict")]
    rc = 1 if never else 0
    return rc, out, record


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--ledger", action="store_true",
                    help="update the ever-produced-a-verdict record, running only what the "
                         "record cannot already answer")
    ap.add_argument("--stale-check", action="store_true",
                    help="does the record still cover the index? Runs NOTHING; sub-second.")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --ledger: report, but do not write the record")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit as e:
        # ⛔ argparse EXITS 0 AFTER PRINTING --help / -h. Catching every SystemExit and calling it
        # "unrecognised arguments" makes the tool REFUSE ITS OWN HELP: it prints the usage text and
        # then declares, one line below, that it established nothing. Reported by ARCHITECT on #350
        # against verdict-census.py; measured here across all five instruments sharing this
        # pattern, which I copied between them.
        # ⛔ `VOID — established nothing` is this repository's most load-bearing string. Emitting it
        # for a SUCCESSFUL request is not a cosmetic defect: it is the refusal vocabulary spent on
        # a non-refusal, which is exactly what makes a real refusal readable.
        if e.code == 0:
            return 0
        print("  VOID  unrecognised arguments — established nothing", file=sys.stderr)
        return 2
    if a.self_test:
        return self_test()
    if a.stale_check:
        rc, lines = stale_check()
        print("\nverdict ledger — is the record still answerable for the indexed population?")
        for l in lines:
            print(l)
        print({0: "  the record is CURRENT for the index — not a claim that any instrument"
                  " produced a verdict",
               1: "  FINDING — the indexed population moved; the record no longer answers it",
               2: "  VOID"}[rc])
        return rc
    if a.ledger:
        rc, lines, _ = ledger(timeout=a.timeout, write=not a.dry_run)
        print("\nverdict ledger — has each indexed instrument EVER produced a verdict?")
        for l in lines:
            print(l)
        print({0: "  every indexed instrument has a verdict on record",
               1: "  FINDING — at least one has never produced a verdict",
               2: "  VOID"}[rc])
        return rc
    rc, lines, _ = census(timeout=a.timeout)
    print("\nverdict census — tools/README.md's index, measured by running it")
    for l in lines:
        print(l)
    print({0: "  every indexed instrument produced or honestly refused a verdict",
           1: "  FINDING", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
