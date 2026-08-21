#!/usr/bin/env python3
"""Does a tool's `--self-test` consult anything its author did not write?

⛔ WHY. ARCHITECT's ruling on #164 item 1: *"name a caller whose INPUTS YOU DID NOT CHOOSE"* is
`goals/README.md` criterion 5's population leg applied to a control. A `--self-test` over
author-chosen fixtures satisfies criteria 3 and 4 — it executes, and it can fail — and fails 5.

★ MEASURED INSTANCE, and it is why this exists. `index-watch.py` gained a second leg whose finding
pattern did not match its subject's output. The leg ran, exited 1, and the watch printed *quiet* —
a real finding turned into silence. **Sixteen controls passed.** Every one used a fixture written
by the same author from the same wrong model of the output, so not one could see it. A live run
found it in seconds.

⛔ #26 AND CRITERION 5 ARE DIFFERENT DEMANDS, AND SATISFYING ONE DOES NOTHING FOR THE OTHER. This
is the confusion the tool exists to make visible:

    #26          can this control be SILENCED BY A REPAIR?       -> keep it OUTSIDE the population
    criterion 5  can it be BLIND TO AN INPUT NOBODY IMAGINED?    -> do not DRAW the population

⇒ A synthetic fixture satisfies #26 perfectly and fails 5 completely. Several tools here cite #26
in their docstrings as evidence of rigour. The credit is real and it is PARTIAL.

★ HOW IT IS MEASURED — differentially, on BEHAVIOUR, never by reading the source. Every instrument
in this repository derives its root from `__file__`. ⇒ Copying a tool into a barren temp tree makes
the repository unreachable **without editing one byte of the tool**. Run `--self-test` in both
places and compare:

    different                            ->  UNDRAWN        it consulted something it did not create.
                                                            SOUND: only an undrawn input can do this.
    identical exit code AND output       ->  NO-REPO-INPUT  it consulted no REPOSITORY input.
                                                            ⚠ NOT "it drew its own population" — the
                                                            network, the clock and the environment all
                                                            survive relocation. A candidate, not a verdict.

⚠ THE COMPARISON IS UNSOUND WITHOUT MASKING, and the masking is the whole method. Both runs print
their own absolute paths, so an unmasked diff reports UNDRAWN for every tool and the instrument
becomes a machine for agreeing with itself. Both roots are replaced with a placeholder first —
the same discipline as `verdict-census.py`'s length-matched probe flag, and for the same reason.

⚠ WHAT THIS DOES NOT ESTABLISH — and the first one is the important one:

  · `UNDRAWN` does NOT mean the population leg is GOOD. It means one exists. A self-test that
    reads a real file and asserts nothing interesting about it lands here too.
  · ⛔ `NO-REPO-INPUT` DOES NOT MEAN CRITERION 5 IS UNMET. Relocation removes the repository and
    nothing else. `label-exists.py` reads 27 real labels off the forge in its self-test and still
    scores NO-REPO-INPUT here, because `gh` does not care what directory it runs in. ⇒ Read every
    such row as *worth checking by hand*, never as *this control drew its own population*.
  · `DRAWN` is not a defect in the tool. It is a statement about the tool's CONTROL, and for some
    tools an undrawn population is genuinely unaffordable — `verdict-census.py` cannot exercise
    its classifier against a population it did not draw without running the real instruments,
    which is the ~4-minute cost that made #2 unreadable to begin with. ⇒ Such cases want a STATED
    exception with a reason, not a silent omission and not a forced fix.
  · ⚠ THE DETERMINISM GUARD IS A SAMPLE, NOT A PROOF. Two agreeing in-place runs establish only
    that the tool did not disagree twice. `fleet-identity.py` returned DRAWN, UNDRAWN, DRAWN on
    three consecutive readings; on a later run its two samples agreed and it scored UNDRAWN. ⇒
    NON-DETERMINISTIC is a positive DETECTION; its absence is not a clean bill, and every
    DRAWN/UNDRAWN verdict inherits that.
  · A tool that still CRASHES under isolation after its sibling imports are supplied is reported
    UNDRAWN-BY-CRASH, and that reading stays weak — it may depend on repository CONTENT, or on
    something else relocation broke. ⚠ Measured: the first live run called 7 of 35 tools
    UNDRAWN-BY-CRASH on one shared cause, a missing sibling module. Every one of those was an
    artifact of this method CREDITING a tool with a population leg. Sibling source is now copied
    on demand; repository content still is not.

★ AND ITS OWN CONTROL HAS THE DEFECT IT MEASURES. `--self-test` below runs synthetic fixtures this
author wrote, so it is DRAWN. Its population leg is the LIVE RUN over `tools/`, whose contents it
did not choose. That is stated rather than hidden, because a tool that measured this property and
exempted itself would be the joke version of itself.

Exit: 0 every self-test consulted something outside its own fixtures
      1 at least one is DRAWN — a finding
      2 established nothing (the index could not be read, or it named no instruments)
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "tools" / "README.md"
ROW = re.compile(r"^\|\s*`([A-Za-z0-9_.-]+\.py)`\s*\|", re.M)
TIMEOUT = 60
# ⛔ THE POSITIVE STATE IS NAMED FOR WHAT THE METHOD ACTUALLY MEASURES, NOT FOR THE CRITERION IT
# SERVES — and the first release got this wrong. Relocation removes the REPOSITORY. It does not
# remove the network, the clock, or the environment. ⇒ A control can consult a population its
# author did not choose and still be byte-identical when relocated.
#
# ★ MEASURED COUNTER-EXAMPLE, from my own other tool within the hour: `label-exists.py` reads the
# forge's 27 REAL labels in its self-test — an undrawn population by any reading — and scores
# NO-REPO-INPUT here, because `gh label list` works just as well from a temp directory.
#
# ⇒ NO-REPO-INPUT is a FINDING ABOUT REPOSITORY DEPENDENCE, which is real and checkable, and a
#   CANDIDATE for criterion 5 — never a verdict that criterion 5 is unmet. Calling it DRAWN
#   asserted the second, which is the use/mention slip this repository files defects about.
FORGE = "UNDRAWN-VIA-FORGE"
DRAWN, UNDRAWN, NOST, SLOW, CRASH = ("NO-REPO-INPUT", "UNDRAWN", "NO-SELF-TEST",
                                     "NO-VERDICT-IN-TIME", "UNDRAWN-BY-CRASH")
# ⛔ THE STATE THAT MAKES THE WHOLE METHOD HONEST. A differential compares two runs and attributes
# every difference to the ONE variable it changed. That attribution is only valid if the tool is
# DETERMINISTIC — and measured here, one is not: fleet-identity.py's self-test returned DRAWN,
# UNDRAWN, DRAWN on three consecutive readings of identical bytes in an identical environment.
# ⇒ Its output varies for reasons of its own (live session state), and a diff cannot then tell
#   "consulted the repository" from "consulted a clock". Reporting either is a coin flip wearing
#   a verdict's clothes. This establishes NOTHING, and says so.
NONDET = "NON-DETERMINISTIC"


def _mask(text, *roots):
    """Absolute paths differ between the two runs by construction. Unmasked, EVERY tool reads
    UNDRAWN and this instrument becomes a machine for agreeing with itself."""
    for r in sorted((str(r) for r in roots), key=len, reverse=True):
        text = text.replace(r, "<ROOT>")
    return text


def _run(path, cwd, timeout):
    try:
        r = subprocess.run([sys.executable, str(path), "--self-test"], capture_output=True,
                           text=True, timeout=timeout, cwd=str(cwd))
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return None, ""
    except OSError as e:
        return None, f"could not execute: {e}"


def classify(tool, tmp_parent, timeout=TIMEOUT):
    """(state, detail) for one instrument. Runs it twice; never reads its source."""
    here_rc, here_out = _run(tool, ROOT, timeout)
    if here_rc is None:
        return SLOW, f"no verdict within {timeout}s in place — the bound is mine, not the tool's"
    # ⛔ argparse rejects an unknown flag with 2, and this repo's convention ALSO uses 2. The two
    # are told apart by the usage banner, never by the code — #58's collision, met head on.
    if here_rc == 2 and ("unrecognized arguments" in here_out or "usage:" in here_out.lower()):
        return NOST, "does not accept --self-test"

    # ⛔ RUN IT IN PLACE TWICE BEFORE CHANGING ANYTHING. If a tool disagrees with ITSELF, the
    # differential below has no valid attribution and must refuse rather than pick a side.
    again_rc, again_out = _run(tool, ROOT, timeout)
    if again_rc is not None:
        r0 = [tool.resolve().parent.parent, tool.parent.parent, ROOT]
        if again_rc != here_rc or _mask(here_out, *r0) != _mask(again_out, *r0):
            return NONDET, ("two runs IN PLACE, nothing changed between them, and they disagree"
                            " — this control's output varies on its own, so a relocation diff"
                            " cannot attribute anything. ⛔ Establishes NOTHING about its"
                            " population.")

    tmp = Path(tempfile.mkdtemp(dir=tmp_parent))
    try:
        # ★ The tool is copied UNMODIFIED. Its root is derived from __file__, so relocating it is
        # enough to make the repository unreachable — no edit, no flag, no cooperation required.
        d = tmp / "tools"
        d.mkdir(parents=True)
        shutil.copy2(tool, d / tool.name)
        # ⛔ SUPPLY CODE DEPENDENCIES, NEVER REPOSITORY DATA — and this correction was forced by a
        # measurement, not foreseen. The first live run reported 7 of 35 instruments UNDRAWN-BY-
        # CRASH, all with the SAME cause: `ModuleNotFoundError: No module named 'runmarker'`, a
        # sibling import broken by relocation. That is an artifact of THIS METHOD, not a property
        # of their controls, and it CREDITED seven tools with a population leg they may not have.
        # ⇒ A missed finding is worse than a false one: a false finding gets argued with, a missed
        #   one is indistinguishable from an absent defect.
        # ★ Resolved by retrying: whenever the relocated run dies on a missing module that exists
        #   as a sibling .py, copy that ONE module and run again. Bounded, so a cycle terminates.
        #   Sibling SOURCE travels; the repository's CONTENT does not, which is the whole variable.
        away_rc, away_out = _run(d / tool.name, tmp, timeout)
        for _ in range(6):
            m = re.search(r"No module named '([A-Za-z0-9_]+)'", away_out or "")
            if not m:
                break
            sib = tool.parent / f"{m.group(1)}.py"
            if not sib.is_file() or (d / sib.name).exists():
                break
            shutil.copy2(sib, d / sib.name)
            away_rc, away_out = _run(d / tool.name, tmp, timeout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if away_rc is None:
        return UNDRAWN, f"in place {here_rc}; timed out when relocated — it waited on something"
    # ⛔ MASK THE ROOT OF THE TOOL BEING MEASURED, not this module's ROOT. In production they
    # coincide, so this bug is INVISIBLE on the real population — the self-test caught it only
    # because its fixtures live outside the repository. Under-masking makes every tool read
    # UNDRAWN, which is the exact failure the masking exists to prevent, arrived at from inside.
    # ⚠ AND BOTH FORMS OF EACH ROOT. On macOS `tempfile.mkdtemp` yields /var/folders/… while a
    # tool's own `Path(__file__).resolve()` yields /private/var/folders/… — the same directory
    # through a symlink. Masking one form and not the other leaves the path in the text and the
    # tool reads UNDRAWN for a reason that has nothing to do with its population.
    roots = [tool.resolve().parent.parent, tool.parent.parent, ROOT, tmp, tmp.resolve()]
    a, b = _mask(here_out, *roots), _mask(away_out, *roots)
    if here_rc == away_rc and a == b:
        forge = forge_probe(tool, here_rc, here_out, timeout)
        if forge:
            return FORGE, (f"no repository input ({here_rc} both ways), {forge}")
        return DRAWN, (f"exit {here_rc} and byte-identical output with the repository unreachable"
                       f" — it consulted no REPOSITORY input and no FORGE. ⚠ The clock, the"
                       f" environment and the filesystem outside the repo still survive"
                       f" relocation; this is a candidate, not a verdict.")
    if "Traceback (most recent call last)" in away_out:
        last = [l for l in away_out.strip().splitlines() if l.strip()][-1][:80]
        return CRASH, (f"in place {here_rc}; CRASHED when relocated ({last}). ⚠ Weak: this may be"
                       f" repository dependence or merely a sibling import.")
    n = sum(1 for x, y in zip(a.splitlines(), b.splitlines()) if x != y)
    return UNDRAWN, (f"in place {here_rc}, relocated {away_rc}; {n} line(s) differ after masking"
                     f" — it consulted something it did not create")


def forge_probe(tool, here_rc, here_out, timeout):
    """Second axis: does this control consult the FORGE? Returns a detail string, or None.

    ⛔ WHY A SECOND AXIS EXISTS AT ALL. Relocation removes the repository and nothing else, so
    `NO-REPO-INPUT` was accusing controls that DO consult an undrawn population by another route.
    Measured on my own tool: `label-exists.py` reads the forge's 27 real labels in its self-test
    and landed in that column, because `gh` does not care what directory it runs in.

    ★ So this cuts ONE named alternative route rather than pretending relocation cut them all: a
    stub `gh` is placed first on PATH and made to fail. If the control's output changes, its
    population includes the forge — undrawn, and invisible to the relocation axis.

    ⚠ IT CUTS `gh` ONLY. A control reading the clock, the filesystem outside the repo, or any
    other environment still shows nothing here. ⇒ This narrows the blind spot; it does not close
    it, and a row with no forge dependence is still only a CANDIDATE.
    """
    import os
    with tempfile.TemporaryDirectory() as bindir:
        stub = Path(bindir) / "gh"
        stub.write_text("#!/bin/sh" + chr(10) + "exit 70" + chr(10))
        stub.chmod(0o755)
        env = dict(os.environ, PATH=f"{bindir}:{os.environ.get('PATH', '')}")
        try:
            r = subprocess.run([sys.executable, str(tool), "--self-test"], capture_output=True,
                               text=True, timeout=timeout, cwd=str(ROOT), env=env)
        except (subprocess.TimeoutExpired, OSError):
            return None
        roots = [tool.resolve().parent.parent, tool.parent.parent, ROOT]
        if r.returncode == here_rc and _mask(r.stdout + r.stderr, *roots) == _mask(here_out,
                                                                                  *roots):
            return None
        return (f"but its output CHANGES when `gh` is made to fail (exit {r.returncode} vs"
                f" {here_rc}) — it consults the FORGE, an undrawn population the relocation axis"
                f" cannot see")


def census(index=None, tools_dir=None, timeout=TIMEOUT):
    index = index or INDEX
    tools_dir = tools_dir or (ROOT / "tools")
    try:
        text = index.read_text(encoding="utf-8")
    except OSError as e:
        return 2, [f"  VOID  cannot read {index}: {e} — established nothing"]
    names = sorted(set(ROW.findall(text)))
    if not names:
        return 2, ["  VOID  the index named no instruments — established nothing"]
    me = Path(__file__).name
    rows = []
    with tempfile.TemporaryDirectory() as parent:
        for n in names:
            p = tools_dir / n
            if not p.is_file():
                rows.append((n, "ABSENT", "indexed but not on disk"))
                continue
            if n == me:
                # ⛔ NAMED, not skipped. Its own control IS drawn — see the docstring. Silently
                # omitting itself is the population narrowing this repository files defects about.
                rows.append((n, DRAWN, "SELF — its control is author-drawn and says so; its"
                             " population leg is this live run"))
                continue
            rows.append((n, *classify(p, parent, timeout)))

    width = max(len(n) for n, *_ in rows)
    out = []
    for n, st, detail in rows:
        mark = "⛔" if st in (DRAWN, "ABSENT") else "  "
        out.append(f"  {mark} {st:<18} {n:<{width}}  {detail}")
    tally = {}
    for _, st, _ in rows:
        tally[st] = tally.get(st, 0) + 1
    out.append("")
    out.append("  " + " · ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    out.append("  ⛔ NO-REPO-INPUT is a finding about REPOSITORY DEPENDENCE and a CANDIDATE for"
               " criterion 5 — it is NOT a verdict that the control drew its own population."
               " Relocation removes the repository and nothing else: label-exists.py reads 27"
               " real labels off the forge and lands in this column.")
    out.append("  note  UNDRAWN means a population leg EXISTS. It does not mean it is a good one —"
               " a self-test that reads a real file and asserts nothing lands here too.")
    out.append("  note  DRAWN is not a defect in the TOOL. It is a statement about its CONTROL,"
               " and for some tools an undrawn population is genuinely unaffordable. Those want a"
               " STATED exception with a reason, not a forced fix.")
    out.append("  note  measured by RELOCATING each tool, never by reading its source — every"
               " instrument here derives its root from __file__, so a copy in a barren tree"
               " cannot reach the repository.")
    out.append("  ⚠ THE DETERMINISM GUARD IS A SAMPLE, NOT A PROOF. Two in-place runs that AGREE"
               " do not establish that a tool is deterministic — they establish that it did not"
               " disagree twice. Measured: fleet-identity.py returned DRAWN, UNDRAWN, DRAWN on"
               " three consecutive readings, and on a later run its two in-place samples agreed"
               " and it was scored UNDRAWN. ⇒ Every DRAWN/UNDRAWN row inherits that uncertainty;"
               " only NON-DETERMINISTIC is a positive detection.")
    out.append("  note  NON-DETERMINISTIC establishes NOTHING about that tool — its own output"
               " varies between two identical in-place runs, so no relocation diff can attribute"
               " anything to relocation. It is neither a finding nor a clean bill.")
    out.append("  note  NO-SELF-TEST is not counted as a finding here; a missing control is"
               " criteria 3 and 4's territory, not criterion 5's.")
    # ⚠ NON-DETERMINISTIC is not folded into either side. It is not a finding (nothing was
    # established) and it is not clean (the question is unanswered) — the same reason exit 2
    # exists in this repository at all.
    # ⚠ UNDRAWN-VIA-FORGE is NOT a finding: the control DOES consult an undrawn population,
    # it simply does so by a route relocation cannot cut. Counting it would re-commit the false
    # accusation this axis exists to correct.
    rc = 1 if tally.get(DRAWN) or tally.get("ABSENT") else 0
    return rc, out


def self_test():
    """⛔ SYNTHETIC, and therefore DRAWN — which this tool reports about itself rather than hiding.

    The control that matters is the MASKING: without it every tool reads UNDRAWN, and the
    instrument becomes a machine for agreeing with itself.
    """
    ok = True
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        td = d / "tools"
        td.mkdir()
        # a control that consults only itself
        (td / "closed.py").write_text(
            "import sys\nif '--self-test' in sys.argv:\n    print('  ok  fixture')\n"
            "    raise SystemExit(0)\nraise SystemExit(0)\n")
        # ⛔ A MARKER THAT EXISTS ONLY IN THE REAL ROOT. Without it both trees hold exactly
        # `tools/`, a fixture that COUNTS entries sees 1 either way, and it reads DRAWN while
        # genuinely consulting its root — a false negative produced by the fixture, not the method.
        (d / "MARKER-only-here.txt").write_text("x")
        # a control that reads its root's CONTENTS — a population it did not draw
        (td / "open.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            "if '--self-test' in sys.argv:\n"
            "    n=sorted(q.name for q in (Path(__file__).resolve().parent.parent).glob('*'))\n"
            "    print(f'  ok  saw {n}')\n    raise SystemExit(0)\nraise SystemExit(0)\n")
        # ⛔ THE MASKING CONTROL NEEDS A FIXTURE THAT PRINTS A PATH. `closed.py` prints a
        # constant, so disabling masking cannot change its verdict and the control passes
        # VACUOUSLY. This one emits its own root — content it did not consult, but text that
        # differs between the two runs, which is precisely what masking exists to absorb.
        (td / "pathy.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            "if '--self-test' in sys.argv:\n"
            "    print(f'  ok  I live under {Path(__file__).resolve().parent.parent}')\n"
            "    raise SystemExit(0)\nraise SystemExit(0)\n")
        # no self-test at all
        (td / "bare.py").write_text(
            "import argparse,sys\nap=argparse.ArgumentParser()\n"
            "try:\n    ap.parse_args(sys.argv[1:])\nexcept SystemExit:\n    raise SystemExit(2)\n"
            "raise SystemExit(0)\n")
        with tempfile.TemporaryDirectory() as parent:
            for name, want in (("closed.py", DRAWN), ("open.py", UNDRAWN), ("bare.py", NOST),
                               ("pathy.py", DRAWN)):
                got, _ = classify(td / name, parent, timeout=30)
                ok &= got == want
                print(f"  {'ok  ' if got == want else 'FAIL'}  {name:<10} -> {got} (want {want})")

            # ⛔ THE CONTROL FOR THE METHOD ITSELF. Defeat the masking and the closed fixture must
            # stop reading DRAWN — if it still reads DRAWN, the comparison was never doing work.
            global _mask
            real = _mask
            try:
                _mask = lambda t, *r: t
                got, _ = classify(td / "pathy.py", parent, timeout=30)
                hit = got != DRAWN
            finally:
                _mask = real
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  with masking DISABLED a fixture that merely "
                  f"prints its own path stops reading DRAWN ({got}) — masking absorbs the paths, "
                  f"and the comparison does the rest")

            # ⛔ THE CONTROL FOR THE ATTRIBUTION ITSELF. A tool that disagrees with itself must
            # REFUSE, not pick a side — measured on fleet-identity.py, which returned DRAWN,
            # UNDRAWN, DRAWN on three consecutive readings before this state existed.
            (td / "flaky.py").write_text(
                "import sys,random\nif '--self-test' in sys.argv:\n"
                "    print('  ok  %d' % random.randint(0, 10**9))\n    raise SystemExit(0)\n"
                "raise SystemExit(0)\n")
            got, _ = classify(td / "flaky.py", parent, timeout=30)
            ok &= got == NONDET
            print(f"  {'ok  ' if got == NONDET else 'FAIL'}  a control that disagrees with ITSELF "
                  f"establishes NOTHING, rather than picking a side (got {got})")

            # ⛔ THE CONTROL FOR THE RENAME. A fixture that consults an UNDRAWN population by a
            # route relocation cannot cut must still land in NO-REPO-INPUT — that is the method's
            # stated blind spot, and a control that did not demonstrate it would leave the
            # limitation as a claim in a comment.
            (td / "netlike.py").write_text(
                "import sys,os\nif '--self-test' in sys.argv:\n"
                "    print('  ok  env says %s' % os.environ.get('POPLEG_PROBE','unset'))\n"
                "    raise SystemExit(0)\nraise SystemExit(0)\n")
            os.environ["POPLEG_PROBE"] = "an input the author did not draw"
            got, _ = classify(td / "netlike.py", parent, timeout=30)
            ok &= got == DRAWN
            print(f"  {'ok  ' if got == DRAWN else 'FAIL'}  a control reading an UNDRAWN input"
                  f" that survives relocation still lands in NO-REPO-INPUT ({got}) — the method's"
                  f" blind spot, demonstrated rather than merely claimed")

            # ⛔ THE CONTROL FOR THE FORGE AXIS. Without it, "UNDRAWN-VIA-FORGE" is a state
            # nothing can be shown to reach — and a state with no reachable instance is a claim,
            # not a measurement. This fixture consults `gh` and nothing else, so relocation
            # cannot see it and only the stubbed-PATH probe can.
            NL = chr(10)
            (td / "forgey.py").write_text("import subprocess,sys" + NL + "if '--self-test' in sys.argv:" + NL + "    r=subprocess.run(['gh','--version'],capture_output=True,text=True)" + NL + "    print('  ok  gh rc=%d' % r.returncode)" + NL + "    raise SystemExit(0)" + NL + "raise SystemExit(0)" + NL)
            # ⛔ THIS CONTROL HAS A PRECONDITION AND MUST ESTABLISH IT BEFORE IT MAY FAIL.
            # The forge axis works by making `gh` fail and looking for a DIFFERENCE. If ambient
            # `gh` is already failing — no binary, no auth, no network, a CI runner — both runs
            # produce the same output, no difference exists, and this control reports FAIL for a
            # reason that has nothing to do with the code under test.
            # ⚠ Measured 2026-08-21: with a failing `gh` first on PATH this exited 3. Gating it
            # in that state would ship a BORN-RED guard — the defect .github/workflows/tools.yml
            # calls load-bearing in its own split, committed in a control ABOUT control quality.
            # ⇒ Precondition first, and a missing precondition is NOT ESTABLISHED, never FAIL.
            try:
                amb = subprocess.run(["gh", "--version"], capture_output=True, text=True,
                                     timeout=20).returncode
            except (OSError, subprocess.TimeoutExpired):
                amb = None
            if amb != 0:
                print(f"  ----  NOT ESTABLISHED  ambient `gh` does not answer (rc={amb}), so the"
                      f" forge axis has nothing to differentiate against. ⛔ The control was NOT"
                      f" exercised — untested, not correct, and NOT a failure of the code.")
            else:
                got, _ = classify(td / "forgey.py", parent, timeout=30)
                ok &= got == FORGE
                print(f"  {'ok  ' if got == FORGE else 'FAIL'}  a control that consults the FORGE"
                      f" and nothing else is UNDRAWN-VIA-FORGE, not NO-REPO-INPUT (got {got})")

        idx = d / "R.md"
        idx.write_text("# no table\n")
        rc, lines = census(index=idx, tools_dir=td, timeout=30)
        hit = rc == 2 and any("VOID" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an index naming no instruments exits 2 VOID (got "
              f"{rc})")

        idx.write_text("| `closed.py` | f |\n| `ghost.py` | f |\n")
        rc, lines = census(index=idx, tools_dir=td, timeout=30)
        hit = rc == 1 and any("ghost.py" in l and "ABSENT" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an indexed-but-absent tool is named and exits 1, "
              f"not skipped (got {rc})")

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


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
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
    rc, lines = census(timeout=a.timeout)
    print("\npopulation leg — whose inputs does each --self-test consult? (#164 item 1)")
    for l in lines:
        print(l)
    print({0: "  every self-test consulted something outside its own fixtures",
           1: "  FINDING", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
