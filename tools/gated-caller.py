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
STUB = (
    "#!/usr/bin/env python3\n"
    "import os, sys\n"
    "_n = os.path.basename(__file__)\n"
    "_a = ' '.join(sys.argv[1:])\n"
    "open(os.environ['GC_LOG'], 'a').write(_n + '|' + _a + chr(10))\n"
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
    seen = {n: {"selftest": [], "reached": []} for n in instruments}
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
                subprocess.run([sys.executable, str(tmp / suite.name)], capture_output=True,
                               text=True, timeout=timeout, cwd=str(Path(d)), env=env)
            except (subprocess.TimeoutExpired, OSError):
                continue
            # ⚠ The suite's own exit code is IGNORED on purpose. Under stubs a strict suite fails,
            # and reading that as "did not call" would report every rigorous suite as a
            # non-caller — the answer would be anti-correlated with the quality it measures.
            if not log.exists():
                continue
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
                name, _, argv = line.partition("|")
                if name not in seen:
                    continue
                key = "selftest" if "--self-test" in argv else "reached"
                if suite.name not in seen[name][key]:
                    seen[name][key].append(suite.name)
    return seen


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
    out, orphan, reached = [], [], []
    for n in names:
        st, rc_ = seen[n]["selftest"], seen[n]["reached"]
        if st:
            out.append(f"  ok           {n:<{width}}  --self-test run by {', '.join(st)}")
        elif rc_:
            # ⚠ A THIRD STATE. The suite reaches the code in-process and exercises SOME of it,
            # but never passes the flag — so whatever lives behind `--self-test` is still unrun.
            reached.append(n)
            out.append(f"  ⚠ REACHED     {n:<{width}}  imported by {', '.join(rc_)}, but its"
                       f" --self-test is NEVER invoked")
        else:
            orphan.append(n)
            out.append(f"  ⛔ NO CALLER  {n:<{width}}  no gated suite runs or imports it")
    out.append("")
    out.append(f"  {len(names) - len(orphan) - len(reached)} of {len(names)} instruments have a"
               f" gated caller that RUNS --self-test · {len(reached)} are imported but never"
               f" self-tested · {len(orphan)} are untouched")
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

        rc, lines = census(tools_dir=td, timeout=60)
        hit = rc == 1 and any("NO CALLER" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a tools dir with an uncalled self-test exits 1 and "
              f"names it (got {rc})")

        empty = Path(d) / "empty"
        empty.mkdir()
        rc, lines = census(tools_dir=empty, timeout=60)
        hit = rc == 2 and any("VOID" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a directory with no gated suite exits 2 VOID, not 0"
              f" (got {rc})")
    return 0 if ok else 3


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--timeout", type=int, default=120)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
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
