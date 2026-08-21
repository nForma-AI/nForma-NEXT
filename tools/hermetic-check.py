#!/usr/bin/env python3
"""Is a suite that CLAIMS to be hermetic actually hermetic?

⛔ THE CLAIM IS CURRENTLY MADE BY THE ABSENCE OF A MARKER. A suite runs in the
`hermetic suites (gating)` job iff nobody wrote `# SUITE-DEPENDS` in it. Nothing
verifies that. A suite that shells out to `gh` is declared hermetic by default and
passes on any authenticated machine, then fails on the runner — which is where it
blocks a merge and where the failure is least legible.

  Instance: #499 — `close-condition-scan.py` handles `--states` at line 264, THIRTY
  lines after the network fetch at 234. `--states` is a pure DECLARE that needs no
  repository at all. Locally `gh` answers and the misordering is invisible; the
  runner has no usable `gh`, so the DECLARE returns 2 and the gate goes red with
  `AssertionError: 2 != 0` — an assertion that names neither `gh` nor the ordering.

Method: run each declared-hermetic suite twice, changing exactly ONE thing — `gh` is
shadowed by a stub that always fails. A suite whose EXIT CODE MOVES is not hermetic.

⚠ SHADOWING ONLY `gh`, NOT TRUNCATING PATH. Replacing PATH wholesale also drops
homebrew and /usr/local/bin, so a suite that failed because `git` moved would score
as a network leak. The stub goes on the FRONT of the real PATH and `git`/`python3`
are asserted to still resolve to their original binaries before anything is measured.

Exit:
  0  every declared-hermetic suite is hermetic with respect to gh
  1  finding — at least one declared-hermetic suite changes verdict
  2  established nothing (no suites, or no real gh to shadow, or the shadow failed)
  3  the known-positive control failed — the probe cannot detect a leak

⛔ WHY "NO REAL gh" IS EXIT 2 AND NOT EXIT 0. If `gh` is not installed, shadowing it
changes nothing and every suite scores hermetic — a clean board produced by an
instrument that measured nothing. "There was no gh to shadow" and "no suite depends
on gh" are two states this tool's verdict depends on telling apart, so they must
never collapse into the same code.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_RC = 124                      # GNU timeout convention, per tools/README.md
MARKER = "SUITE-DEPENDS"
STUB = '#!/bin/sh\necho "gh: shadowed by hermetic-check" >&2\nexit 1\n'


def result(word):
    print(f"NFORMA-RESULT {word}")


def declared_hermetic(tools_dir):
    """Suites the gate treats as hermetic: test_*.py WITHOUT the marker."""
    out = []
    for p in sorted(glob.glob(str(Path(tools_dir) / "test_*.py"))):
        try:
            if MARKER not in Path(p).read_text(encoding="utf-8", errors="replace"):
                out.append(p)
        except OSError:
            continue                  # unreadable is not "hermetic"; it is not measured
    return out


def make_shadow(d):
    s = Path(d) / "gh"
    s.write_text(STUB)
    s.chmod(0o755)
    return str(Path(d))


def run_suite(path, cwd, shadow_dir=None, timeout=180):
    env = dict(os.environ)
    if shadow_dir:
        env["PATH"] = shadow_dir + os.pathsep + env.get("PATH", "")
    try:
        return subprocess.run([sys.executable, os.path.basename(path)],
                              capture_output=True, timeout=timeout, env=env,
                              cwd=str(Path(path).parent)).returncode
    except subprocess.TimeoutExpired:
        return TIMEOUT_RC


def tree_provenance():
    """★ A measurement of a suite is a measurement of a CHECKOUT. Say which one."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                           text=True, cwd=str(Path(__file__).resolve().parent))
        if r.returncode != 0:
            return "  ---- tree UNKNOWN — not a git checkout; this reading cannot be attributed."
        # ⛔ A DIRTY TREE MUST NOT REPORT A CLEAN SHA. The SHA names committed content;
        # the suites that just ran are whatever is on disk. Reporting the SHA alone lets a
        # reading taken over uncommitted edits be attributed to a commit that never
        # contained them — the defect this line exists to prevent, in the line itself.
        d = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                           cwd=str(Path(__file__).resolve().parent))
        dirty = " +UNCOMMITTED CHANGES — this reading is NOT attributable to that commit" \
            if (d.returncode == 0 and d.stdout.strip()) else ""
        return f"  ---- tree {r.stdout.strip()}{dirty}"
    except OSError:
        return "  ---- tree UNKNOWN — git unavailable; this reading cannot be attributed."


def verify_shadow(shadow_dir):
    """⛔ THE PRECONDITION, not a nicety. Returns (ok, reason).

    Three things must hold before any suite result means anything:
      1. a REAL gh exists — otherwise shadowing changes nothing and every suite
         scores hermetic, which is a clean board produced by measuring nothing;
      2. the shadow actually WINS on PATH — a stub that loses is not a shadow;
      3. nothing ELSE moved — git and python3 must resolve where they did before,
         or a suite that breaks for an unrelated reason scores as a network leak.
    """
    real = shutil.which("gh")
    if not real:
        return False, ("no real `gh` on PATH — there is nothing to shadow. Every suite "
                       "would score hermetic and the verdict would be an artefact of "
                       "this machine, not a fact about the suites.")
    env = dict(os.environ)
    env["PATH"] = shadow_dir + os.pathsep + env.get("PATH", "")
    shadowed = shutil.which("gh", path=env["PATH"])
    if not shadowed or os.path.dirname(shadowed) != shadow_dir:
        return False, f"the stub did not win on PATH (gh still resolves to {shadowed!r})"
    r = subprocess.run(["gh", "--version"], capture_output=True, env=env)
    if r.returncode == 0:
        return False, "the shadowed `gh` still succeeded — the stub is not being executed"
    for binary in ("git", sys.executable and "python3"):
        if not binary:
            continue
        before, after = shutil.which(binary), shutil.which(binary, path=env["PATH"])
        if before != after:
            return False, (f"{binary} moved when the shadow was applied "
                           f"({before!r} -> {after!r}) — more than one variable changed")
    return True, f"real gh at {real}, shadowed by {shadowed}; git and python3 unmoved"


def survey(tools_dir, timeout=180, quiet=False):
    """Returns (rc, lines). Never raises on a suite; a suite that dies is data."""
    lines = []
    suites = declared_hermetic(tools_dir)
    if not suites:
        lines.append(f"  ⛔ ESTABLISHED NOTHING: no test_*.py without `# {MARKER}` in "
                     f"{tools_dir} — an empty population is not a clean one.")
        return 2, lines
    with tempfile.TemporaryDirectory() as d:
        shadow = make_shadow(d)
        ok, why = verify_shadow(shadow)
        if not ok:
            lines.append(f"  ⛔ ESTABLISHED NOTHING: {why}")
            lines.append("  ⚠ This is exit 2, NOT exit 0. A survey that cannot vary its one "
                         "variable has measured nothing, and must not read as all-clear.")
            return 2, lines
        if not quiet:
            lines.append(f"  ok    precondition — {why}")
        leaks, moved = [], []
        for p in suites:
            a = run_suite(p, tools_dir, None, timeout)
            b = run_suite(p, tools_dir, shadow, timeout)
            name = os.path.basename(p)
            if a != b:
                leaks.append((name, a, b))
                lines.append(f"  ⛔ LEAK  {name:<42} gh:{a} -> shadowed:{b}")
            elif a == TIMEOUT_RC:
                moved.append(name)
                lines.append(f"  ⚠ TIMED OUT {name:<38} in BOTH conditions at {timeout}s — "
                             f"unchanged, so not a leak, and not a pass either")
    lines.append("")
    lines.append(f"  {len(suites) - len(leaks)} of {len(suites)} declared-hermetic suites are "
                 f"hermetic with respect to `gh`")
    if leaks:
        lines.append("  ⛔ A DECLARED-HERMETIC SUITE THAT MOVES WHEN gh IS SHADOWED WILL PASS ON "
                     "ANY AUTHENTICATED MACHINE AND FAIL ON THE RUNNER, where it blocks a merge "
                     "with an assertion that names neither `gh` nor the dependency.")
    lines.append("  ⚠ HERMETIC WITH RESPECT TO gh ONLY. This tool varies exactly one binary. A "
                 "suite reaching the network by another route — curl, urllib, a git remote — is "
                 "NOT covered and is not thereby clean.")
    lines.append(tree_provenance())
    return (1 if leaks else 0), lines


LEAKY = ('import subprocess, sys\n'
         'r = subprocess.run(["gh", "--version"], capture_output=True)\n'
         'raise SystemExit(0 if r.returncode == 0 else 1)\n')
CLEAN = 'raise SystemExit(0)\n'


def self_test():
    """⛔ KNOWN-POSITIVE AND ITS NEGATIVE, ASSERTED AS A PAIR.

    "the leaky suite is DETECTED" passes if the probe flagged everything.
    "the clean suite is NOT flagged" passes if the probe flagged nothing.
    Neither half can fail on the defect. Both together pin both directions.
    """
    ok = True
    print("hermetic-check --self-test")
    with tempfile.TemporaryDirectory() as d:
        td = Path(d) / "tools"
        td.mkdir()
        (td / "test_leaky.py").write_text(LEAKY)
        (td / "test_clean.py").write_text(CLEAN)
        # ⛔ THE SELF-TEST SUPPLIES ITS OWN `gh`. It must not borrow the machine's, or this
        # tool ships the very defect it detects: the runner has no gh, survey() would hit its
        # own precondition and refuse, and --self-test would fail in the gating job while
        # passing on every developer's laptop. Caught by running it without gh instead of
        # reasoning about it — the same check that found #499.
        fake = Path(d) / "realbin"
        fake.mkdir()
        (fake / "gh").write_text('#!/bin/sh\nexit 0\n')
        (fake / "gh").chmod(0o755)
        real_path0 = os.environ.get("PATH", "")
        os.environ["PATH"] = str(fake) + os.pathsep + real_path0
        try:
            rc, lines = survey(str(td), timeout=60, quiet=True)
        finally:
            os.environ["PATH"] = real_path0
        body = "\n".join(lines)
        hit = ("test_leaky.py" in body and "LEAK" in body
               and "test_clean.py" not in body and rc == 1)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a suite that shells out to gh is DETECTED and a "
              f"suite that does not is NOT flagged (rc={rc}) — the pair, not either half")

        # ⛔ A SUITE DECLARING THE MARKER IS OUT OF POPULATION — the gate skips it, so it
        #    cannot fail the board and this tool must not claim it as a pass.
        (td / "test_marked.py").write_text(f"# {MARKER}: a fleet corpus\n" + LEAKY)
        pop = [os.path.basename(p) for p in declared_hermetic(str(td))]
        hit = "test_marked.py" not in pop
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a suite declaring # {MARKER} is EXCLUDED from the "
              f"population even though it leaks (population={pop})")

        # ⛔ THE PRECONDITION MUST REFUSE. With no real gh, shadowing changes nothing and
        #    every suite scores hermetic — the false all-clear this tool exists against.
        real_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = str(Path(d) / "empty")
            (Path(d) / "empty").mkdir(exist_ok=True)
            rc2, lines2 = survey(str(td), timeout=60, quiet=True)
            hit = rc2 == 2 and any("nothing to shadow" in l for l in lines2)
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  with NO real gh the tool exits 2 and says so "
                  f"(rc={rc2}) — never 0, which would be a clean board from an unrun probe")
        finally:
            os.environ["PATH"] = real_path

        # ⛔ an empty population is VOID, not clean
        empty = Path(d) / "bare"
        empty.mkdir()
        rc3, _ = survey(str(empty), timeout=60, quiet=True)
        ok &= rc3 == 2
        print(f"  {'ok  ' if rc3 == 2 else 'FAIL'}  a directory with no declared-hermetic suite "
              f"exits 2 VOID, not 0 (got {rc3})")
    print("all checks passed" if ok else "⛔ FINDINGS")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="Do the suites the gate treats as hermetic actually run without gh?")
    ap.add_argument("--tools-dir", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--timeout", type=int, default=180,
                    help="per-suite seconds; a suite that exceeds it reports 124 in BOTH "
                         "conditions and is reported as TIMED OUT, never as a pass")
    ap.add_argument("--self-test", action="store_true")
    try:
        a = ap.parse_args()
    except SystemExit as exc:
        # ⚠ --help is 0; a bogus flag is 2 (established nothing), never 1 (a finding).
        raise SystemExit(0 if exc.code == 0 else 2)
    print("NFORMA-RUN hermetic-check")
    if a.self_test:
        rc = self_test()
        result("SELF-TEST-PASSED" if rc == 0 else "SELF-TEST-FINDINGS")
        return rc
    rc, lines = survey(a.tools_dir, a.timeout)
    for l in lines:
        print(l)
    result({0: "HERMETIC", 1: "LEAK-FOUND", 2: "ESTABLISHED-NOTHING"}.get(rc, "UNKNOWN"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
