#!/usr/bin/env python3
"""Which instruments' `--self-test` does CI actually INVOKE? Answered by running the gate's suites.

⛔ WHY. Criterion 4, amended 2026-08-21 (#381): a control must be *"shown to FAIL on real data — BY
A CALLER THAT STILL RUNS IT. A demonstration that happened once and cannot happen again is a
SCREENSHOT."* ⇒ Two issues now carry a COUNT of instruments whose controls have no such caller —
#372 says 11, I measured 13, and reconciled to 17. ★ A count in an issue body decays the moment a
suite lands. A check does not. This is that count, derived.

⛔ IT IS MEASURED BEHAVIOURALLY, AND THE TEXTUAL VERSION IS THE TRAP. "Does some gated suite
mention this tool and the flag?" cannot tell an INVOCATION from a MENTION — a suite naming
`verdict-census.py --self-test` inside a comment or a docstring scores identical to one that runs
it. That is the same use/mention collapse reported against `pipe-exit-scan.py` on #375, and I used
the textual predicate myself on #392 before replacing it here.

★ SO: for each instrument, copy the whole `tools/` tree to a temp dir, REPLACE THAT ONE SUBJECT
with a recording stub, run each gated suite there, and read the stub's log. A suite that truly
invokes the subject writes a line. A suite that merely talks about it writes nothing.

⚠ THE SUITE IS EXPECTED TO FAIL under a stub, and that is irrelevant — the question is whether the
subject was CALLED, never whether the suite passed. Conflating those would report every strict
suite as a non-caller.

⛔ WHAT IS "GATED" IS READ FROM THE GATE, NOT ASSUMED. `.github/workflows/tools.yml` runs
`scripts/exit-code-gate.sh tools 'test_*.py'`, which SKIPS any file whose first column carries
`# SUITE-DEPENDS:` — those are reported, not gating. A suite that only runs in the non-gating job
is not a caller for this purpose, and treating it as one would credit a control that cannot fail
the board.

⚠ WHAT THIS DOES NOT ESTABLISH:
  · That an INVOKED self-test is a GOOD control. It says the flag was passed, nothing more.
  · That a NON-INVOKED instrument is untested — its paired suite may cover the same ground by
    other means. This reports the CALLER's absence, not the tool's quality.
  · Anything about `scripts/*.py`. The gate runs those BARE, so none of their self-tests are
    invoked; that is #372's four, it needs no probe, and it is reported as a stated constant.

Exit: 0 every instrument with a --self-test has a gated caller that invokes it
      1 at least one does not — a finding
      2 established nothing (the tools dir, the gate, or the suite list could not be read)
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
SKIP = re.compile(r"^# SUITE-DEPENDS:", re.M)
# ★ THE STUB RECORDS ITS OWN NAME, which is what collapses the cost from (instruments x suites)
# to (suites). Every instrument is stubbed at once and each suite runs ONCE; the log attributes
# each call. Measured: 750 tree copies became 1 per suite.
# ⛔ AND IT RECORDS AN IMPORT TOO, because a suite that `importlib`s a tool and calls its internals
# REACHES THE CODE WITHOUT EVER PASSING --self-test. That is a third state, not a "no", and a
# binary answer would file it under the same verdict as a suite that merely mentions the tool.
# ⛔ THE STUB MUST BE FAITHFUL IN THE PROPERTIES SUITES SELECT ON, not merely in its name.
# Measured 2026-08-21: a suite that DISCOVERS its population by reading each instrument's source
# for the literal "--self-test" found NOTHING under this probe, because the stub did not contain
# that string. ⇒ The suite invoked nothing, and this tool reported every instrument REACHED —
# a confident wrong answer produced entirely by the measuring apparatus.
# ★ The marker below is a FAITHFULNESS fix, not a courtesy: a stand-in for an instrument must
#   carry the property by which instruments are identified, or the probe measures its own stub.
STUB = (
    "#!/usr/bin/env python3\n"
    "# marker for source-reading discovery, QUOTED because the real predicate is\n"
    "# quote-anchored to match add_argument(\"--self-test\") rather than prose:\n"
    "# \"--self-test\"\n"
    "import os, sys\n"
    "_n = os.path.basename(__file__)\n"
    "_a = ' '.join(sys.argv[1:])\n"
    # ⛔ RECORD __name__. A bare SUBPROCESS run and an IMPORT both log an empty argv when the
    # suite itself was invoked without arguments, so argv alone cannot separate them — and the
    # first version filed both under "reached". ★ ARCHITECT named the consequence on #164: the
    # fleet audits whether its CONTROLS run and has nothing auditing whether its SWEEPS run.
    # ⇒ A subprocess run is __main__; an importlib import is not. The discriminator was already
    #   flowing through this stub and was discarded at the bucket.
    "_k = 'MAIN' if __name__ == '__main__' else 'IMPORT'\n"
    "open(os.environ['GC_LOG'], 'a').write(_n + '|' + _k + '|' + _a + chr(10))\n"
    # ⛔ RECORD IN-PROCESS INVOCATION (#551). __name__ separates SUBPROCESS from IMPORT and
    # nothing more. It cannot separate an import that merely LOADS the module from one that
    # CALLS THE SWEEP — and only the second is what the count is about, so `1 of 36` was a
    # LOWER BOUND reported as a count. ★ #550 is the instance: a gated suite that runs
    # doctrine-discriminability's sweep in-process via importlib.
    # ⇒ PEP 562 module __getattr__ fires only for attributes the module does NOT define, and
    #   this stub defines none of the subject's — so every reach lands here.
    # ⚠ RECORDED ON CALL, NOT ON ACCESS. `m.CHANNELS` is an attribute read and is NOT a sweep;
    #   `m.main()` is. Writing the record inside __getattr__ would score the first as the
    #   second, which is the over-report that would make this worse than the false negative.
    "def __getattr__(_name):\n"
    "    def _call(*_a, **_k):\n"
    "        open(os.environ['GC_LOG'], 'a').write(_n + '|CALL|' + _name + chr(10))\n"
    "        return 0\n"
    "    return _call\n"
    "if __name__ == '__main__':\n"
    "    raise SystemExit(0)\n"
)


def has_selftest(src):
    return '"--self-test"' in src or "'--self-test'" in src


def gated_suites(tools_dir):
    """Suites the GATING job runs. `# SUITE-DEPENDS:` marks the reported-not-gating job."""
    out = []
    for p in sorted(tools_dir.glob("test_*.py")):
        try:
            if not SKIP.search(p.read_text(encoding="utf-8", errors="replace")):
                out.append(p)
        except OSError:
            continue
    return out


def probe(suites, tools_dir, instruments, timeout=120):
    """{instrument: {"selftest": [suites], "reached": [suites]}} — behavioural, never textual.

    Every instrument is stubbed at once; each suite runs ONCE. The stub records its own name, so
    one log attributes every call the suite made.
    """
    seen = {n: {"selftest": [], "swept": [], "called": [], "reached": []} for n in instruments}
    truncation_risk = []   # suites that exited nonzero under the stub — see the loop below
    for suite in suites:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / "tools"
            shutil.copytree(tools_dir, tmp,
                            ignore=shutil.ignore_patterns("__pycache__", "*.json"))
            for n in instruments:
                (tmp / n).write_text(STUB)
            log = Path(d) / "calls.log"
            env = dict(os.environ, GC_LOG=str(log))
            try:
                _r = subprocess.run([sys.executable, str(tmp / suite.name)],
                                    capture_output=True, text=True, timeout=timeout,
                                    cwd=str(Path(d)), env=env)
                # ⛔ TRUNCATION RISK, MEASURED. The exit code must not decide whether a suite
                # counted as a caller (see below) — but a suite that DIED under the stub may
                # have died BEFORE a call it would otherwise have made, so anything after that
                # point is invisible. ⚠ This is the probe changing what it observes.
                # ★ Measured instance: test_prevalence.py imports the subject at line 27, reads
                #   pv.<attr> from line 41, and only at line 141 runs it bare. With a stub that
                #   defined nothing, the attribute read raised AttributeError and the suite
                #   never reached the bare run — so `1 of 36` was an UNDERCOUNT PRODUCED BY
                #   THIS TOOL, not a fact about the repository.
                if _r.returncode != 0:
                    truncation_risk.append(suite.name)
            except (subprocess.TimeoutExpired, OSError):
                truncation_risk.append(suite.name)
                continue
            # ⚠ The suite's own exit code is IGNORED on purpose. Under stubs a strict suite fails,
            # and reading that as "did not call" would report every rigorous suite as a
            # non-caller — the answer would be anti-correlated with the quality it measures.
            if not log.exists():
                continue
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.split("|", 2)
                if len(parts) != 3:
                    continue                      # pre-__name__ format; not this run's
                name, kind, argv = parts
                if name not in seen:
                    continue
                # ⛔ THREE OUTCOMES, NOT TWO. A bare SUBPROCESS run is the SWEEP — the thing that
                # produces findings. An IMPORT exercises the module in-process and produces none.
                # Folding them lost exactly the distinction #164 asks about.
                if kind == "CALL":
                    # ⛔ A THIRD STATE, NOT A WIDER "swept". A gated suite reached into the
                    # module and INVOKED something — but "called any function" is NOT the
                    # proposition "the sweep has a caller". test_close_condition_scan.py calls
                    # main() with argv patched to --states, a DECLARE path that measures
                    # nothing. ⇒ Folding these into `swept` would move the published figure
                    # from 1 to 26 by SILENTLY CHANGING THE QUESTION — a correct reading of
                    # the wrong proposition, under a number other panes are acting on.
                    key = "called"
                elif "--self-test" in argv:
                    key = "selftest"
                elif kind == "MAIN":
                    key = "swept"
                else:
                    key = "reached"
                if suite.name not in seen[name][key]:
                    seen[name][key].append(suite.name)
    seen["__truncation_risk__"] = sorted(set(truncation_risk))
    return seen


# ⛔ A WORKFLOW-LEVEL RUNNER IS A CALLER, AND THIS TOOL COULD NOT SEE ONE. It probes
# `tools/test_*.py` suites and answers "does a gated SUITE invoke this tool's --self-test?" —
# a correct answer to ITS question and the wrong answer to "is this control run in CI".
# ⚠ MEASURED COST: I read `REACHED doctrine-watch.py` and published on #183 that its controls
#   "are silent because nothing calls them". `.github/workflows/tools.yml` had been running
#   `SUBJ_DIR=tools ./scripts/gate-selftests.sh` in the GATING job since #444, which invokes
#   every subject in tools/. DEVOPS corrected me. ★ CLASS C in the instrument I built for this
#   question, four hours after naming the class in docs/DEFECT-CLASSES.md.
# ⇒ A third verdict, kept DISTINCT from a dedicated suite rather than folded into it: a blanket
#   runner invokes the flag but proves nothing about whether THAT tool's control discriminates.
#   pretooluse-guard.py is the live proof — the runner calls it and it exits 0 for a bogus flag,
#   so its green is worth nothing. "Has a caller" and "its green means something" are two
#   questions and this tool answers only the first.
WORKFLOWS = ROOT / ".github" / "workflows"


def blanket_runners():
    """Directories whose every subject is invoked by a workflow step. Read from the workflow.

    ⚠ Derived from the file, never a constant: a hard-coded {"tools"} would be correct today and
    silently wrong the moment the step moves, which is the stale-calibration defect this
    repository has filed three times.
    """
    dirs = set()
    if not WORKFLOWS.is_dir():
        return dirs
    for wf in sorted(WORKFLOWS.glob("*.y*ml")):
        try:
            text = wf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "gate-selftests.sh" not in text:
            continue
        # SUBJ_DIR: tools   (or SUBJ_DIR=tools inline)
        for m in re.finditer(r"SUBJ_DIR[:=]\s*[\"']?([A-Za-z0-9_./-]+)", text):
            dirs.add(m.group(1))
        if re.search(r"^\s*run:\s*\./scripts/gate-selftests\.sh\s*$", text, re.M):
            dirs.add("scripts")          # its documented default when SUBJ_DIR is unset
    return dirs


def tree_provenance(root=None):
    """Which checkout produced this reading, and how far behind `origin/main` is it?

    ⛔ WHY EVERY TOOL READING NEEDS THIS. A measurement of a tool is a measurement of a CHECKOUT.
    Three panes hit that in one night, all published:
        the doctrine watermark  — two live values, forked by working tree (TEAMLEAD, #183)
        pane-census --help=1    — true in my worktree, already fixed on main (DEV1)
        pane-census --help=0    — DEVOPS's correction of the above, taken from a tree 7 behind
    ⇒ The third is the one that settles it: DEVOPS reported a property of their checkout as a
      property of the repository MINUTES AFTER telling me that is what I had done. ★ The rule is
      easy to state and very hard to apply to your own next reading, which is why it belongs in
      the OUTPUT rather than in anyone's discipline.

    ⚠ `index-watch.py` has carried this since #229 and `doctrine-watch.py` has it too. Measured
    2026-08-21: 2 of 34 instruments state which tree answered. This is the third.

    Returns a line, never None — "unknown" is stated, never silently omitted.
    """
    root = root or ROOT
    def g(*a):
        try:
            r = subprocess.run(["git", *a], capture_output=True, text=True, cwd=str(root),
                               timeout=20)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    head = g("rev-parse", "--short", "HEAD")
    if head is None:
        return "  ---- TREE UNKNOWN — not a git checkout, or git did not answer. ⛔ This reading" \
               " cannot be attributed to any revision."
    behind = g("rev-list", "--count", "HEAD..origin/main")
    if behind is None:
        return f"  ---- tree {head}; distance to origin/main UNKNOWN — ⛔ not 'current'."
    if behind == "0":
        return f"  ---- tree {head} — level with origin/main."
    return (f"  ---- ⚠ tree {head} is {behind} COMMIT(S) BEHIND origin/main. This reading is a"
            f" property of THIS CHECKOUT, not of the repository.")


def census(tools_dir=None, timeout=120):
    tools_dir = tools_dir or (ROOT / "tools")
    if not tools_dir.is_dir():
        return 2, [f"  VOID  no tools directory at {tools_dir} — established nothing"]
    suites = gated_suites(tools_dir)
    if not suites:
        return 2, ["  VOID  the gate's suite glob matched nothing — the layout changed, or every"
                   " suite is marked SUITE-DEPENDS. Established nothing."]
    me = Path(__file__).name
    names = []
    for p in sorted(tools_dir.glob("*.py")):
        if p.name.startswith("test_") or p.name == me:
            continue
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if has_selftest(src):
            names.append(p.name)
    if not names:
        return 2, ["  VOID  no instrument in tools/ exposes --self-test — established nothing"]
    seen = probe(suites, tools_dir, names, timeout)
    width = max(len(n) for n in names)
    out, orphan, reached, runner = [], [], [], []
    # ⛔ NAMED, never silently omitted. This tool excluded ITSELF and its nested-run peer from its
    # own output entirely, so "N of M" was reported against a population the reader could not see
    # had been narrowed. verdict-census.py states this rule and this file did not follow it.
    if (tools_dir / me).is_file():
        out.append(f"  SELF-EXCLUDED  {me:<{width}}  not counted — probing it inside its own probe"
                   f" spawns a nested run that terminates only by timeout")
    # ⛔ COMPARE THE RESOLVED PATH, NEVER THE BARE NAME. Keying on `tools_dir.name` made a TEMP
    # FIXTURE directory named "tools" register as the repository's real tools/ — every fixture
    # subject read as runner-covered and the NO-CALLER control stopped firing.
    # ★ The name matched and the thing did not — the use/mention collapse this repository is
    #   built around, introduced by me into a control that was already working.
    blanket = any((ROOT / d).resolve() == tools_dir.resolve() for d in blanket_runners())
    for n in names:
        st, rc_ = seen[n]["selftest"], seen[n]["reached"]
        if st:
            out.append(f"  ok           {n:<{width}}  --self-test run by {', '.join(st)}")
        elif blanket:
            # ⚠ A WORKFLOW-LEVEL RUNNER INVOKES IT, but that is a weaker fact than a dedicated
            # suite and is kept separate rather than counted as one. The runner passes --self-test
            # to every subject in the directory; whether THIS tool's control discriminates is a
            # different question, and pretooluse-guard.py answers it "no" while being invoked.
            runner.append(n)
            out.append(f"  ~ RUNNER      {n:<{width}}  invoked by a workflow-level runner over"
                       f" {tools_dir.name}/ — NOT by a dedicated suite")
        elif rc_:
            # ⚠ A THIRD STATE. The suite reaches the code in-process and exercises SOME of it,
            # but never passes the flag — so whatever lives behind `--self-test` is still unrun.
            reached.append(n)
            out.append(f"  ⚠ REACHED     {n:<{width}}  imported by {', '.join(rc_)}, but its"
                       f" --self-test is NEVER invoked")
        else:
            orphan.append(n)
            out.append(f"  ⛔ NO CALLER  {n:<{width}}  no gated suite, no workflow runner")
    out.append("")
    out.append(f"  {len(names) - len(orphan) - len(reached) - len(runner)} of {len(names)} have a"
               f" DEDICATED suite running --self-test · {len(runner)} reached only by a"
               f" workflow-level runner · {len(reached)} imported but never self-tested ·"
               f" {len(orphan)} untouched")
    # ⛔ THE SWEEP IS A SEPARATE AXIS, NOT A FIFTH RUNG — reported on its own line for that reason.
    # ★ ARCHITECT, #164: the fleet audits whether its CONTROLS run and has nothing that audits
    #   whether its MEASUREMENTS run. The rows above are a ladder of CONTROL strength; whether a
    #   tool's sweep is ever invoked is independent of all four rungs. Folding it in would hide one
    #   fact behind the other for any tool that is both — the collapsed pair, in the instrument
    #   whose job is refusing collapses.
    swept = [n for n in names if seen[n]["swept"]]
    called = [n for n in names if seen[n]["called"] and n not in swept]
    out.append(f"  {len(swept)} of {len(names)} have a gated caller that runs the SWEEP — invoked as a"
               f" subprocess WITHOUT --self-test{': ' + ', '.join(swept) if swept else ''}")
    if not swept:
        out.append("  ⚠ NO INSTRUMENT'S SWEEP HAS A GATED CALLER. The gate runs --self-test over"
                   " tools/ and nothing runs the MEASUREMENTS, so a sweep that silently stopped"
                   " finding things would produce no failing check — only silence, and silence is"
                   " indistinguishable from a clean board. This is NOT the same defect as an"
                   " uninvoked control: a dead control yields a false all-clear, a dead sweep"
                   " yields no signal at all.")
    # ⛔ NAME THE BOUNDARY OR THE COUNT IS UNREADABLE. This population is `tools/*.py`, NOT a
    # recursive walk — tools/README.md keeps subdirectories out of scope deliberately. ⚠ But a
    # reader of "N of M" takes M for the instrument count, and an instrument in a subdirectory is
    # then not reported as UNCALLED: it is outside the sentence entirely.
    # ★ #544 is exactly this case — tools/architect-sweeps/prior-art.py is the instrument whose
    #   skipped run shipped a duplicate, and no caller audit here can see it to say so.
    # ⇒ Named, not indexed. Only DIRECTORIES and COUNTS are printed; the quarantine's disposition
    #   is the operator's and contributes 0 qualifying instruments in any case.
    subdirs = []
    for d in sorted(x for x in Path(tools_dir).iterdir() if x.is_dir() and x.name != "__pycache__"):
        n = sum(1 for f in sorted(d.glob("*.py"))
                if "--self-test" in f.read_text(encoding="utf-8", errors="replace"))
        if n:
            subdirs.append((d.name, n))
    if subdirs:
        detail = " · ".join(f"{name}/ {n}" for name, n in subdirs)
        out.append(f"  ⚠ POPULATION BOUNDARY: {sum(n for _, n in subdirs)} instrument(s) exposing"
                   f" --self-test live in SUBDIRECTORIES and are OUTSIDE the counts above"
                   f" — {detail}. They are not reported as uncalled; they are not reported.")
    # ⛔ THE PROBE'S OWN OBSERVER EFFECT, REPORTED AS A NUMBER RATHER THAN A WORRY.
    # A suite that DIED under the stub may have died before a call it would have made, so every
    # count above is a LOWER BOUND by an amount this line bounds. ⚠ Its exit code still does not
    # decide caller-hood — that would anti-correlate with rigour — it only bounds the error.
    trunc = seen.get("__truncation_risk__", [])
    if trunc:
        out.append(f"  ⚠ TRUNCATION RISK: {len(trunc)} of {len(suites)} gated suites exited"
                   f" NONZERO under the recording stub. Each may have stopped before a call it"
                   f" would otherwise have made, so every count above is a LOWER BOUND — this"
                   f" tool changes what it observes, and this is by how much it might.")
    # ⇒ REPORTED SEPARATELY, on its own line, for the reason above: it answers a DIFFERENT
    #   question and must not be summed with the one above it.
    out.append(f"  {len(called)} of {len(names)} are INVOKED IN-PROCESS by a gated suite that"
               f" imports the module and calls into it — NOT the same claim as a sweep:"
               f" calling main() with a --help or --states argv measures nothing.")
    out.append(tree_provenance())
    out.append("  ⚠ RUNNER is INVOCATION, not evidence. A blanket runner passes --self-test to"
               " every subject; whether a given tool's control DISCRIMINATES is a separate"
               " question this tool does not ask (see pretooluse-guard.py, invoked and"
               " UNVERIFIABLE).")
    out.append(f"  ----  gated suites probed: {len(suites)} (SUITE-DEPENDS files excluded — the"
               f" gate skips them, so they cannot fail the board)")
    out.append("  note  measured by REPLACING each subject with a recording stub and running the"
               " suites. A suite that only MENTIONS the tool writes nothing to the log.")
    out.append("  note  the suites' own exit codes are ignored — under a stub a strict suite"
               " fails, and reading that as 'did not call' would penalise rigour.")
    out.append("  note  an INVOKED self-test is not thereby a GOOD control, and a non-invoked"
               " instrument is not thereby untested — this reports the CALLER, not the quality.")
    out.append("  ----  scripts/*.py are OUT OF SCOPE and uniformly uncovered: the gate runs them"
               " BARE (`python3 \"$f\"`), so none of their self-tests is invoked. #372's four.")
    out.append("  note  REACHED is not a pass: the suite exercises the module in-process, so"
               " whatever the --self-test asserts is still never executed by the gate.")
    return (1 if (orphan or reached) else 0), out


def self_test():
    """⛔ Synthetic suites, outside `tools/`. The discriminating pair is a suite that RUNS the
    subject against one that only TALKS about running it — identical to a textual predicate,
    opposite under this one."""
    ok = True
    with tempfile.TemporaryDirectory() as d:
        td = Path(d) / "tools"
        td.mkdir()
        (td / "subject.py").write_text("import sys\nraise SystemExit(0)\n")
        (td / "quiet.py").write_text("import sys\nraise SystemExit(0)\n")
        (td / "test_real.py").write_text(
            "import subprocess, sys, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "subprocess.run([sys.executable, os.path.join(here,'subject.py'), '--self-test'])\n"
            "raise SystemExit(0)\n")
        # ⛔ THE DISCRIMINATOR: this file NAMES the tool and the flag and never runs anything.
        # A textual predicate scores it identical to test_real.py.
        (td / "test_mention.py").write_text(
            '"""We should really run quiet.py --self-test here one day."""\n'
            "# quiet.py --self-test\nraise SystemExit(0)\n")
        suites = gated_suites(td)
        for name, want in (("subject.py", True), ("quiet.py", False)):
            got = bool(probe(suites, td, [name], timeout=60)[name]["selftest"])
            ok &= got == want
            print(f"  {'ok  ' if got == want else 'FAIL'}  {name:<11} invoked={got} (want {want})"
                  f" — a MENTION must not score as a caller")

        # ⚠ a suite that calls the subject and then FAILS is still a caller
        (td / "test_strict.py").write_text(
            "import subprocess, sys, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "r = subprocess.run([sys.executable, os.path.join(here,'strict.py'), '--self-test'],"
            " capture_output=True)\n"
            "raise SystemExit(3)\n")
        (td / "strict.py").write_text("raise SystemExit(0)\n")
        got = bool(probe(gated_suites(td), td, ["strict.py"], timeout=60)["strict.py"]["selftest"])
        ok &= got
        print(f"  {'ok  ' if got else 'FAIL'}  a suite that invokes the subject and then EXITS 3 "
              f"still counts as a caller — rigour is not penalised")

        # ⛔ a SUITE-DEPENDS suite is not gating, so it is not a caller
        (td / "test_dep.py").write_text(
            "# SUITE-DEPENDS: a fleet corpus\n"
            "import subprocess, sys, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "subprocess.run([sys.executable, os.path.join(here,'depsub.py'), '--self-test'])\n"
            "raise SystemExit(0)\n")
        (td / "depsub.py").write_text("raise SystemExit(0)\n")
        got = bool(probe(gated_suites(td), td, ["depsub.py"], timeout=60)["depsub.py"]["selftest"])
        ok &= not got
        print(f"  {'ok  ' if not got else 'FAIL'}  a SUITE-DEPENDS suite is NOT a gated caller "
              f"(invoked={got}) — it cannot fail the board")

        # ⚠ census() only considers instruments that EXPOSE the flag, so the fixtures must
        # actually carry it — otherwise the population is empty and the run VOIDs, which is a
        # true statement about the fixture and no statement at all about census().
        for n in ("subject.py", "quiet.py"):
            (td / n).write_text('import sys\nif "--self-test" in sys.argv:\n'
                                '    raise SystemExit(0)\nraise SystemExit(0)\n')
        # ⛔ THE REACHED STATE NEEDS A DEMONSTRATED INSTANCE, or it is a claim rather than a
        # verdict. This suite IMPORTS the subject — the idiom tools/test_pointer_verified.py and
        # friends actually use — and never passes the flag. Binary logic files it with `quiet.py`.
        (td / "imported.py").write_text('import sys\nif "--self-test" in sys.argv:\n'
                                        '    raise SystemExit(0)\nraise SystemExit(0)\n')
        (td / "test_import.py").write_text(
            "import importlib.util, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "sp = importlib.util.spec_from_file_location('m', os.path.join(here,'imported.py'))\n"
            "m = importlib.util.module_from_spec(sp)\nsp.loader.exec_module(m)\n"
            "raise SystemExit(0)\n")
        r = probe(gated_suites(td), td, ["imported.py"], timeout=60)["imported.py"]
        hit = not r["selftest"] and bool(r["reached"])
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a suite that IMPORTS the subject without the flag "
              f"is REACHED, not NO-CALLER (selftest={r['selftest']}, reached={r['reached']})")

        # ⛔ THE SWEEP IS A THIRD OUTCOME, and it needs a demonstrated instance in BOTH directions.
        # ★ ARCHITECT on #164: the fleet audits whether its CONTROLS run and has nothing that
        #   audits whether its MEASUREMENTS run. A control that never runs yields a false
        #   all-clear; a sweep that never runs yields silence, which is cheaper to miss.
        # ⚠ ASSERTED AS A PAIR ON PURPOSE. "the bare run is SWEPT" alone passes if every caller
        #   were routed to swept; "the import is NOT swept" alone passes if swept were dead and
        #   always empty. Neither half can fail on the defect. Both together pin both directions.
        (td / "swept.py").write_text('import sys\nif "--self-test" in sys.argv:\n'
                                     '    raise SystemExit(0)\nraise SystemExit(0)\n')
        (td / "test_sweep.py").write_text(
            "import subprocess, sys, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "subprocess.run([sys.executable, os.path.join(here,'swept.py')])\n"
            "raise SystemExit(0)\n")
        # ⛔ AN IN-PROCESS CALLER THAT RUNS THE SWEEP IS SWEPT (#551). The pair is the point:
        # "the caller that INVOKES is swept" passes if every importer were swept, and
        # "the importer that only LOADS is reached" passes if none were. Neither half alone.
        (td / "inproc.py").write_text('import sys\nif "--self-test" in sys.argv:\n'
                                      '    raise SystemExit(0)\nraise SystemExit(0)\n')
        (td / "test_inproc.py").write_text(
            "import importlib.util, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "sp = importlib.util.spec_from_file_location('q', os.path.join(here,'inproc.py'))\n"
            "m = importlib.util.module_from_spec(sp)\nsp.loader.exec_module(m)\n"
            "m.main()\n"                      # <- the sweep, in-process
            "raise SystemExit(0)\n")
        ri = probe(gated_suites(td), td, ["inproc.py", "imported.py"], timeout=60)
        nosweep = not ri["inproc.py"]["swept"]
        ok &= nosweep
        print(f"  {'ok  ' if nosweep else 'FAIL'}  an IN-PROCESS caller does NOT count as SWEPT "
              f"(swept={ri['inproc.py']['swept']}) — 'calls any function' is not 'runs the "
              f"sweep'; folding them would move a published figure by changing the question")
        hit = bool(ri["inproc.py"]["called"]) and not ri["imported.py"]["called"]
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a suite that IMPORTS and CALLS the subject is "
              f"CALLED (a state of its own, NOT swept), while one that imports and does not "
              f"call is neither (inproc={ri['inproc.py']['called']}, "
              f"import={ri['imported.py']['called']}) — __name__ cannot see this")

        # ⛔ ATTRIBUTE ACCESS IS NOT A SWEEP. Reading a module constant must not score as one,
        # or the fix trades a false negative for a false positive, which is worse here.
        (td / "test_readattr.py").write_text(
            "import importlib.util, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "sp = importlib.util.spec_from_file_location('r', os.path.join(here,'inproc.py'))\n"
            "m = importlib.util.module_from_spec(sp)\nsp.loader.exec_module(m)\n"
            "_ = m.SOME_CONSTANT\n"
            "raise SystemExit(0)\n")
        (td / "test_inproc.py").unlink()
        ra = probe(gated_suites(td), td, ["inproc.py"], timeout=60)
        hit = not ra["inproc.py"]["called"]
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  reading an ATTRIBUTE is not an invocation "
              f"(called={ra['inproc.py']['called']}) — recorded on CALL, never on ACCESS")

        rs = probe(gated_suites(td), td, ["swept.py", "imported.py"], timeout=60)
        hit = bool(rs["swept.py"]["swept"]) and not rs["imported.py"]["swept"]
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a BARE subprocess run is SWEPT and an IMPORT is not"
              f" (swept={rs['swept.py']['swept']}, import-swept={rs['imported.py']['swept']})"
              f" — argv is empty for both; __name__ is what separates them")

        # ⛔ THE SELF ROW MUST BE NAMED. This tool omitted itself entirely, so "N of M" was
        # reported against a population the reader could not see had been narrowed — the defect
        # check-tools-index.py exists against, and one verdict-census.py states in its own source.
        (td / Path(__file__).name).write_text('import sys\nif "--self-test" in sys.argv:\n'
                                              '    raise SystemExit(0)\nraise SystemExit(0)\n')
        _, _lines = census(tools_dir=td, timeout=60)
        hit = any("SELF-EXCLUDED" in l and Path(__file__).name in l for l in _lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  the census NAMES its own exclusion by file, rather"
              f" than omitting the row")
        (td / Path(__file__).name).unlink()

        # ⛔ TRUNCATION RISK MUST BE COUNTED, AND MUST NOT COUNT A CLEAN SUITE. Asserted as a
        # pair: "a dying suite is flagged" passes if every suite were flagged; "a clean suite is
        # not" passes if none were.
        (td / "dies.py").write_text('import sys\nif "--self-test" in sys.argv:\n'
                                    '    raise SystemExit(0)\nraise SystemExit(0)\n')
        (td / "test_dies.py").write_text(
            "import subprocess, sys, os\n"
            "here = os.path.dirname(os.path.abspath(__file__))\n"
            "subprocess.run([sys.executable, os.path.join(here,'dies.py')])\n"
            "raise SystemExit(7)\n")               # <- nonzero: may have stopped early
        rt = probe(gated_suites(td), td, ["dies.py"], timeout=60)
        risk = rt.get("__truncation_risk__", [])
        hit = "test_dies.py" in risk and "test_import.py" not in risk
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a gated suite that EXITS NONZERO under the stub is"
              f" counted as truncation risk and a clean one is not (risk={risk}) — the probe"
              f" states how much it may have changed what it observed")

        # ⛔ THE BOUNDARY LINE NEEDS A DEMONSTRATED INSTANCE, and its ABSENCE needs one too.
        # ⚠ Asserted as a pair: "the line appears when a subdir instrument exists" passes if the
        #   line were unconditional; "no line when no subdir" passes if it never printed at all.
        _, before = census(tools_dir=td, timeout=60)
        quiet = not any("POPULATION BOUNDARY" in l for l in before)
        sub = td / "extra-sweeps"
        sub.mkdir()
        (sub / "hidden.py").write_text('import sys\nif "--self-test" in sys.argv:\n'
                                       '    raise SystemExit(0)\nraise SystemExit(0)\n')
        _, after = census(tools_dir=td, timeout=60)
        named = any("POPULATION BOUNDARY" in l and "extra-sweeps" in l for l in after)
        hit = quiet and named
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a subdirectory instrument is NAMED as outside the "
              f"population, and the line is ABSENT when there is none (absent={quiet}, "
              f"named={named}) — an excluded row must not be a silent one")

        # ⛔ A SUBDIR FILE WITHOUT --self-test DOES NOT QUALIFY, so it must not inflate the count.
        (sub / "plain.py").write_text("raise SystemExit(0)\n")
        _, after2 = census(tools_dir=td, timeout=60)
        one = any("BOUNDARY: 1 instrument" in l for l in after2)
        ok &= one
        print(f"  {'ok  ' if one else 'FAIL'}  a subdirectory file NOT exposing --self-test is not"
              f" counted (still 1) — the boundary reports the population, not the directory")

        rc, lines = census(tools_dir=td, timeout=60)
        hit = rc == 1 and any("NO CALLER" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a tools dir with an uncalled self-test exits 1 and "
              f"names it (got {rc})")

        empty = Path(d) / "empty"
        # ⛔ A WORKFLOW-LEVEL RUNNER IS A CALLER, controlled BOTH ways: a blanket_runners() that
        # returned everything would make NO CALLER unreachable; one returning nothing restores
        # the defect this fixes. ⇒ Derived from the workflow FILE, never a constant.
        global WORKFLOWS
        _real_wf = WORKFLOWS
        try:
            wfd = Path(d) / "wf"
            wfd.mkdir()
            (wfd / "x.yml").write_text("jobs:\n  g:\n    steps:\n"
                                       "      - env:\n          SUBJ_DIR: tools\n"
                                       "        run: ./scripts/gate-selftests.sh\n")
            WORKFLOWS = wfd
            got = blanket_runners()
            ok &= "tools" in got
            print(f"  {'ok  ' if 'tools' in got else 'FAIL'}  a workflow step declaring SUBJ_DIR"
                  f" is read as a blanket runner (got {sorted(got)}) — derived, not hard-coded")
            (wfd / "x.yml").write_text("jobs:\n  g:\n    steps:\n      - run: echo nothing\n")
            got2 = blanket_runners()
            ok &= not got2
            print(f"  {'ok  ' if not got2 else 'FAIL'}  a workflow NOT running gate-selftests"
                  f" yields none (got {sorted(got2)}) — NO CALLER stays reachable")
        finally:
            WORKFLOWS = _real_wf

        # ⛔ TREE PROVENANCE, ALL THREE STATES. The BEHIND case is the whole point of the
        # function, so it is synthesised rather than left unreachable — a control that can only
        # observe "level" would pass forever on a laptop standing on main.
        prov = Path(d) / "prov"
        prov.mkdir()
        def _g(*a):
            subprocess.run(["git", *a], cwd=str(prov), capture_output=True, text=True)
        _g("init", "-q")
        _g("config", "user.email", "x@y.z"); _g("config", "user.name", "x")
        (prov / "a.txt").write_text("one\n"); _g("add", "-A"); _g("commit", "-qm", "one")
        first = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(prov),
                               capture_output=True, text=True).stdout.strip()
        (prov / "a.txt").write_text("two\n"); _g("add", "-A"); _g("commit", "-qm", "two")
        second = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(prov),
                                capture_output=True, text=True).stdout.strip()
        _g("update-ref", "refs/remotes/origin/main", second)
        _g("checkout", "-q", first)
        line = tree_provenance(prov)
        hit = "BEHIND" in line and " 1 COMMIT" in line
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a checkout 1 behind origin/main SAYS so — the"
              f" state the function exists for is reachable")

        _g("checkout", "-q", second)
        line = tree_provenance(prov)
        hit = "level with" in line
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a checkout level with origin/main says level —"
              f" the branch is not a constant")

        nongit = Path(d) / "nongit"
        nongit.mkdir()
        line = tree_provenance(nongit)
        hit = "TREE UNKNOWN" in line
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a non-git directory is TREE UNKNOWN and SAYS the"
              f" reading cannot be attributed — never silently omitted")

        empty.mkdir()
        rc, lines = census(tools_dir=empty, timeout=60)
        hit = rc == 2 and any("VOID" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a directory with no gated suite exits 2 VOID, not 0"
              f" (got {rc})")

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
    ap.add_argument("--timeout", type=int, default=120)
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
    print("\ngated caller — whose --self-test does CI actually invoke? (#372, #381)")
    for l in lines:
        print(l)
    print({0: "  every instrument's self-test has a gated caller",
           1: "  FINDING", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
