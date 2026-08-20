#!/usr/bin/env python3
"""Run `scripts/check-tools-index.py` when `main` moves, and report what it found.

⛔ Why this exists. `tools/ci-log-clean.py` landed on `main` with no table row and no prose
entry. The checker that detects exactly that had existed for hours and **nothing invoked it** —
the defect was found only because a human ran the check by hand after a merge. A mechanism that
is correct and unrun is indistinguishable from one that is absent. #27 is closed as *mitigated*
rather than *prevented* for precisely this reason.

★ Armed under the operator grant of 2026-08-20 in `goals/RESERVED-ACTIONS.md` — *read-only
monitors on your own instruments*. The four bounds are load-bearing and each is implemented
here rather than promised:

  READ-ONLY        it runs a checker and prints. It never merges, pushes, closes, edits a file,
                   or writes into another pane. The only mutation is its own state file.
  NO AUTHORITY     it emits a FINDING. It never emits a task, an instruction or a grant. A timer
                   that re-enters an agent with a plausible instruction has genuine provenance,
                   which is worse than a forgery: a forgery can be caught by checking the
                   channel and a real scheduled job cannot.
  SILENCE == RAN   silence means *ran and found nothing*, never *could not run*. Every failure
                   path prints. See the exit table below.
  OWN INSTRUMENTS  the subject is `scripts/check-tools-index.py`, written by this role.

⚠ EVENT-DRIVEN, NOT CLOCKED — DEVOPS's finding on #131, taken rather than re-derived. The defect
arrives when `main` moves, so this polls `git ls-remote origin refs/heads/main` and runs the
subject only when the SHA CHANGES. A 30-minute timer on a quiet repo fires ~47 times a day with
nothing to say and trains its reader to skip it, which is the duplicate-alarm defect in
`tools/README.md`.

⛔ THE KNOWN-POSITIVE IS NOT DRAWN FROM THE POPULATION BEING MEASURED — also DEVOPS's, from the
self-test defect it declared on its own watch. A control of the form *"the repo currently has a
drift, so a finding proves I work"* is silenced the moment the repo is repaired, which is #26's
sharp subtype. `--self-test` here asserts the SUBJECT INSTRUMENT'S OWN `--self-test`, which no
amount of repository repair can touch.

⚠ What this does NOT do. It does not fix anything, does not open an issue, and does not tell
anyone to. It has no opinion about whether a finding matters. And it inherits every blind spot
the subject declares — presence not accuracy, `tools/*.py` only — because it only relays.

Exit: 0 main unchanged, or checked and the subject reported clean
      1 FINDING — the subject reported drift
      2 established nothing — the subject could not run, gave an undocumented code, or the
        remote could not be read
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBJECT = ROOT / "scripts" / "check-tools-index.py"
# Exit codes the subject DOCUMENTS. Anything else is "could not run", never "clean".
DOCUMENTED = {0: "clean", 1: "drift", 2: "established nothing"}
DEFAULT_STATE = Path.home() / ".claude" / "dev1-index-watch.sha"


def run(*args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def remote_sha():
    """The SHA of origin/main, or None. None is a VOID condition, never 'unchanged'."""
    r = run("git", "ls-remote", "origin", "refs/heads/main", cwd=str(ROOT))
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.split()[0]


def check_once(state_path, force=False, subject=None):
    """Return (exit_code, lines). `subject` is injectable so the self-test can
    exercise the missing-subject path without mutating module state."""
    subject = SUBJECT if subject is None else subject
    sha = remote_sha()
    if sha is None:
        return 2, ["  VOID  could not read origin/main — establishes nothing about the index."
                   " ⛔ This is NOT 'unchanged'."]

    prev = state_path.read_text().strip() if state_path.is_file() else None
    if prev == sha and not force:
        # The only silent-ish path, and it is silent about the SUBJECT, not about itself.
        return 0, [f"  ok    main unchanged at {sha[:8]} — subject not run (nothing to re-check)"]

    if not subject.is_file():
        return 2, [f"  VOID  subject missing: {subject} — establishes nothing"]

    r = run(sys.executable, str(subject))
    rc = r.returncode
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(sha + "\n")

    if rc not in DOCUMENTED:
        return 2, [f"  VOID  subject exited {rc}, which it does not document"
                   f" (documented: {sorted(DOCUMENTED)}) — establishes nothing",
                   f"        stderr: {(r.stderr or '').strip()[:300]}"]

    head = f"main moved {(prev or 'unknown')[:8]} -> {sha[:8]}; subject exited {rc}" \
           f" ({DOCUMENTED[rc]})"
    if rc == 0:
        return 0, [f"  ok    {head}"]
    if rc == 2:
        return 2, [f"  VOID  {head} — the subject established nothing; ⛔ not a clean index",
                   *(f"        {l}" for l in (r.stdout or "").splitlines() if l.strip())]
    return 1, [f"  FIND  {head}", "",
               *(f"        {l}" for l in (r.stdout or "").splitlines() if l.strip()),
               "",
               "  ⚠ This is a FINDING, not a task. It names no owner and requests no action."]


def self_test():
    """⛔ The control lives OUTSIDE the population being measured.

    A positive of the form "the repo has a drift right now" dies the moment the repo is
    repaired. This asserts the SUBJECT'S OWN --self-test instead, which is a property of the
    instrument and not of the directory it reads.
    """
    ok = True
    r = run(sys.executable, str(SUBJECT), "--self-test")
    if r.returncode != 0:
        r = run(sys.executable, str(SUBJECT), "--selftest")
    hit = r.returncode == 0
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'}  subject's own self-test passes (got {r.returncode})"
          " — control is outside the population this watch measures")

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        st = Path(d) / "s.sha"

        # unchanged-SHA path must not claim to have checked the subject
        sha = remote_sha()
        if sha:
            st.write_text(sha + "\n")
            rc, lines = check_once(st)
            hit = rc == 0 and any("subject not run" in l for l in lines)
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  unchanged main says 'subject not run', never "
                  f"'clean' (got {rc})")
        else:
            ok = False
            print("  FAIL  could not read origin/main during self-test — control VOID")

        # ⛔ a missing subject must be VOID, never silence
        st.write_text("0" * 40 + "\n")
        rc, lines = check_once(st, subject=Path(d) / "absent.py")
        hit = rc == 2 and any("VOID" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a missing subject exits 2 VOID, not 0 (got {rc})")
    return 0 if ok else 3


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="run the subject even if main has not moved")
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        print("  VOID  unrecognised arguments — established nothing", file=sys.stderr)
        return 2
    if a.self_test:
        return self_test()
    rc, lines = check_once(Path(a.state), force=a.force)
    print("\nindex-watch — scripts/check-tools-index.py vs main")
    for l in lines:
        print(l)
    print({0: "  quiet", 1: "  FINDING", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
