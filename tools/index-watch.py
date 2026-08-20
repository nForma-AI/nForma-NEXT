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
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ⛔ THE SCRIPT'S LOCATION AND THE REPOSITORY IT MEASURES ARE DIFFERENT THINGS, and conflating
# them makes the monitor unpinnable. Measured, on this tool: armed from the working tree, a
# branch switch I made for unrelated work silently swapped the RUNNING monitor's own source to a
# pre-#139 version, which then read its JSON state as a raw string, printed `{ "sha"` where a SHA
# belonged, re-raised held findings, and overwrote the rolled baseline. Isolation did not help —
# it was my own tree and my own checkout. ⇒ A long-running monitor must run from a copy of its
# source that nothing can rewrite, which is only possible if --repo is separable from __file__.
ROOT = Path(__file__).resolve().parent.parent
SUBJECT = ROOT / "scripts" / "check-tools-index.py"
# Exit codes the subject DOCUMENTS. Anything else is "could not run", never "clean".
DOCUMENTED = {0: "clean", 1: "drift", 2: "established nothing"}
DEFAULT_STATE = Path.home() / ".claude" / "dev1-index-watch.json"

# ⛔ ROLL THE BASELINE FORWARD. tools/README.md: "An alarm that fires forever on one event trains
# its reader to ignore it — which is worse than not firing, because the reader also stops seeing
# the next one." The first armed run proved this on itself: `ci-log-clean.py` was undocumented
# BEFORE main moved, so a SHA-change trigger alone re-reported a pre-existing gap on every merge,
# for as long as the gap survived — and its author is the only party who may close it.
# ⇒ The trigger is a CHANGE IN THE FINDING SET, not a change in the SHA.
# ⚠ Silence still may not be ambiguous (bound 3), so the unchanged-findings path PRINTS the
# baseline it is holding rather than saying nothing.
FAIL_LINE = re.compile(r"^\s*FAIL\s+(.*\S)\s*$", re.M)


def run(*args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def source_staleness(repo=None):
    """How far behind `origin/main` is THE SOURCE THIS PROCESS IS RUNNING FROM?

    ⛔ Why this exists — #149's own remedy, corrected. That issue established that a monitor must
    not read its own source from a mutable tree, and prescribed pinning. It argued ONE direction.
    Measured on TEAMLEAD's monitor: pinned at ~07:0x, correctly applying the remedy, and frozen 42
    commits later — the derived-delta fix landed on main and never reached the thing reporting.

        Unpinned means rewritten under you.  Pinned means never updated.  Neither is safe.

    ⇒ **A pin is a calibration and nothing re-takes calibrations.** This does not re-take it and
    does not decide whether the staleness matters. It STATES it, on every run, so a silent freeze
    becomes a stated one.

    ⛔ DERIVED, never stored. The answer comes from this file's OWN BYTES — hash them, find which
    commit of `tools/<name>` carries that blob. A recorded "pinned at <sha>" alongside the copy
    would be a second calibration, freezing exactly like the first. **A derived value cannot go
    stale**, which is the same argument that settled #183's watermark.

    ⚠ Returns (None, reason) when it cannot establish the answer — a copy that matches no commit is
    UNKNOWN, never "0 behind". Absence of a match establishes nothing.
    """
    me = Path(__file__).resolve()
    r = run("git", "hash-object", str(me), cwd=str(repo or ROOT))
    if r.returncode != 0 or not r.stdout.strip():
        return None, "could not hash this file"
    blob = r.stdout.strip()
    listing = run("git", "rev-list", "origin/main", "--", f"tools/{me.name}",
                  cwd=str(repo or ROOT))
    if listing.returncode != 0:
        return None, "could not read origin/main history"
    for c in listing.stdout.split():
        # ⚠ BRACED. `"$c:tools/…"` unbraced applies a zsh history modifier and silently rewrites
        # the path — tools/README.md carries the rule, and it caught the author of that rule a
        # third time while writing this function.
        got = run("git", "rev-parse", f"{c}:tools/{me.name}", cwd=str(repo or ROOT))
        if got.returncode == 0 and got.stdout.strip() == blob:
            n = run("git", "rev-list", "--count", f"{c}..origin/main", cwd=str(repo or ROOT))
            if n.returncode != 0 or not n.stdout.strip().isdigit():
                return None, f"matched {c[:8]} but could not count the distance"
            return int(n.stdout.strip()), c
    return None, ("this copy matches no commit of origin/main — locally modified, never committed,"
                  " or from another branch")


def remote_sha(repo=None):
    """The SHA of origin/main, or None. None is a VOID condition, never 'unchanged'."""
    r = run("git", "ls-remote", "origin", "refs/heads/main", cwd=str(repo or ROOT))
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.split()[0]


def load_state(path):
    """(sha, findings). Absent or unreadable state is a clean slate, never an assertion."""
    try:
        d = json.loads(path.read_text())
        return d.get("sha"), sorted(d.get("findings") or [])
    except Exception:
        return None, []


def save_state(path, sha, findings):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sha": sha, "findings": sorted(findings)}, indent=1))


def check_once(state_path, force=False, subject=None, repo=None):
    """Return (exit_code, lines). `subject` is injectable so the self-test can
    exercise the missing-subject path without mutating module state."""
    subject = SUBJECT if subject is None else subject
    repo = ROOT if repo is None else repo
    sha = remote_sha(repo)
    if sha is None:
        return 2, [f"  VOID  could not read origin/main from {repo} — establishes nothing about"
                   " the index. ⛔ This is NOT 'unchanged'."]

    prev, base = load_state(state_path)
    if prev == sha and not force:
        # The only silent-ish path, and it is silent about the SUBJECT, not about itself.
        return 0, [f"  ok    main unchanged at {sha[:8]} — subject not run (nothing to re-check)"]

    if not subject.is_file():
        return 2, [f"  VOID  subject missing: {subject} — establishes nothing"]

    r = run(sys.executable, str(subject))
    rc = r.returncode

    if rc not in DOCUMENTED:
        return 2, [f"  VOID  subject exited {rc}, which it does not document"
                   f" (documented: {sorted(DOCUMENTED)}) — establishes nothing",
                   f"        stderr: {(r.stderr or '').strip()[:300]}"]

    head = f"main moved {(prev or 'unknown')[:8]} -> {sha[:8]}; subject exited {rc}" \
           f" ({DOCUMENTED[rc]})"

    if rc == 2:
        # ⛔ Do NOT roll the baseline on a VOID — nothing was established, so the previous
        # finding set is still the best knowledge available.
        return 2, [f"  VOID  {head} — the subject established nothing; ⛔ not a clean index",
                   *(f"        {l}" for l in (r.stdout or "").splitlines() if l.strip())]

    found = sorted(set(FAIL_LINE.findall(r.stdout or "")))
    fresh = [f for f in found if f not in base]
    gone = [f for f in base if f not in found]
    save_state(state_path, sha, found)

    if not found:
        if gone:
            return 0, [f"  ok    {head}", "  ⇒ RESOLVED since the last report:",
                       *(f"        - {g}" for g in gone)]
        return 0, [f"  ok    {head} — index clean"]

    if not fresh:
        # Repeat-firing is a defect of the same severity as silence. Stay quiet about the
        # finding — but NAME the baseline, so this can never be read as "nothing is wrong".
        lines = [f"  ok    {head}",
                 f"  ----  {len(found)} finding(s) UNCHANGED since last reported — not re-raised"
                 f" (repeat-firing trains its reader to skip; tools/README.md)"]
        lines += [f"        held: {f}" for f in found]
        if gone:
            lines += ["  ⇒ RESOLVED since the last report:"] + [f"        - {g}" for g in gone]
        return 0, lines

    return 1, [f"  FIND  {head}",
               f"  ⇒ {len(fresh)} NEW finding(s) since the last report:",
               *(f"        + {f}" for f in fresh),
               *([f"  ---- {len(found) - len(fresh)} other finding(s) already reported, held"]
                 if len(found) > len(fresh) else []),
               "", *(f"        {l}" for l in (r.stdout or "").splitlines() if l.strip()), "",
               "  ⚠ This is a FINDING, not a task. It names no owner and requests no action."]


def _fixture_subject(d, fails):
    """A stand-in subject emitting a chosen FAIL set and exit 1.

    ⛔ Deliberately synthetic: keying the baseline test on the repository's CURRENT drift would
    make it pass only while that drift survives, and its author may close it at any moment.
    """
    f = Path(d) / "fixture_subject.py"
    body = "\n".join(f'print("  FAIL  {x}")' for x in fails)
    f.write_text("#!/usr/bin/env python3\n" + body + "\nraise SystemExit(1)\n")
    return f


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
            save_state(st, sha, [])
            rc, lines = check_once(st)
            hit = rc == 0 and any("subject not run" in l for l in lines)
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  unchanged main says 'subject not run', never "
                  f"'clean' (got {rc})")
        else:
            ok = False
            print("  FAIL  could not read origin/main during self-test — control VOID")

        # ⛔ REPEAT-FIRING is a defect of the same severity as silence. A finding already
        # reported must be HELD and NAMED, never re-raised — and never silently dropped either.
        if sha:
            known = "no table row for: probe.py"
            save_state(st, "0" * 40, [known])
            rc, lines = check_once(st, subject=_fixture_subject(d, [known]))
            hit = (rc == 0 and any("UNCHANGED since last reported" in l for l in lines)
                   and any(known in l for l in lines))
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  a repeat finding is held and NAMED, not "
                  f"re-raised (got {rc})")

            # ...and a genuinely new one still fires
            save_state(st, "0" * 40, [known])
            rc, lines = check_once(st, subject=_fixture_subject(d, [known, "no prose entry for: probe.py"]))
            hit = rc == 1 and any("NEW finding(s)" in l for l in lines)
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  a NEW finding alongside a held one still fires "
                  f"(got {rc})")

        # ⛔ a --repo that is not a git repository must VOID, never read as 'unchanged'
        save_state(st, "0" * 40, [])
        rc, lines = check_once(st, repo=Path(d))
        hit = rc == 2 and any("could not read origin/main" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a non-repo --repo exits 2 VOID, not 'unchanged' "
              f"(got {rc})")

        # ⛔ SOURCE-AGE CONTROLS. #149 shipped pinning with no expiry and no re-pin trigger;
        # these assert the tool can at least STATE its own age, and that it refuses to call an
        # unmatchable copy current.
        hist = run("git", "rev-list", "origin/main", "--", "tools/index-watch.py", cwd=str(ROOT))
        older = [c for c in hist.stdout.split()][1:2] if hist.returncode == 0 else []
        if older:
            oldcopy = Path(d) / "index-watch.py"
            got = run("git", "show", f"{older[0]}:tools/index-watch.py", cwd=str(ROOT))
            oldcopy.write_text(got.stdout)
            src2 = Path(__file__).read_text().replace("Path(__file__).resolve()",
                                                      f"Path({str(oldcopy)!r})")
            ns = {}
            exec(compile(src2, "iw", "exec"), ns)
            n_old, _ = ns["source_staleness"](ROOT)
            hit = isinstance(n_old, int) and n_old > 0
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  an older pinned copy reports a POSITIVE "
                  f"distance, not 0 (got {n_old})")

            oldcopy.write_text(got.stdout + "\n# locally modified\n")
            ns2 = {}
            exec(compile(Path(__file__).read_text().replace(
                "Path(__file__).resolve()", f"Path({str(oldcopy)!r})"), "iw", "exec"), ns2)
            n_mod, why = ns2["source_staleness"](ROOT)
            hit = n_mod is None and "matches no commit" in why
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  an unmatchable copy is UNKNOWN, never 0 "
                  f"(got {n_mod})")
        else:
            print("  ----  source-age controls NOT EXERCISED: no older revision available")

        # ⛔ a missing subject must be VOID, never silence
        save_state(st, "0" * 40, [])
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
    ap.add_argument("--repo", default=None,
                    help="repository to measure, when this script is run from a pinned copy "
                         "outside it (see the ⛔ note at ROOT)")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        print("  VOID  unrecognised arguments — established nothing", file=sys.stderr)
        return 2
    if a.self_test:
        return self_test()
    repo = Path(a.repo) if a.repo else None
    rc, lines = check_once(Path(a.state), force=a.force, repo=repo)
    print("\nindex-watch — scripts/check-tools-index.py vs main")
    # ⛔ PRINTED ON EVERY RUN, including the quiet path. A pin makes the source immutable, which
    # is #149's remedy and also #149's cost: TEAMLEAD's monitor froze 42 commits behind by
    # applying it correctly. This does not re-take the pin and does not decide whether the
    # distance matters — it states it, so a SILENT freeze becomes a STATED one.
    behind_n, src = source_staleness(repo)
    if behind_n is None:
        print(f"  ----  SOURCE AGE UNKNOWN — {src}. ⛔ Not 'current': absence of a match"
              f" establishes nothing.")
    elif behind_n == 0:
        print(f"  ok    source is origin/main ({str(src)[:8]}) — not pinned behind")
    else:
        print(f"  ----  ⚠ THIS SOURCE IS {behind_n} COMMIT(S) BEHIND origin/main"
              f" (pinned at {str(src)[:8]}). A fix to this tool that landed since then is NOT"
              f" running here. Stated, not judged — re-pin if it matters.")
    for l in lines:
        print(l)
    print({0: "  quiet", 1: "  FINDING", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
