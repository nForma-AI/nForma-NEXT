#!/usr/bin/env python3
"""Run this role's cheap checkers when `main` moves, and report what they found.

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
  OWN INSTRUMENTS  both subjects — `scripts/check-tools-index.py` and `tools/verdict-census.py
                   --stale-check` — are instruments of this role. Arming a leg on another
                   role's instrument remains the operator's, not mine.

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
import time
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

# ⛔ A SECOND LEG ON THE SAME TRIGGER — and it is a trigger COLLAPSE, not a second watcher.
# #164 item 2 asked whether two drift-watchers should be merged. The answer I filed was: collapse
# the TRIGGER, not the watchers, because two instruments with the same trigger and disjoint
# finding-sets are one poller and two questions. This is that, applied to my own two instruments.
#
# ★ WHY verdict-census EARNS A SEAT HERE and did not before. ARCHITECT measured the census
# emitting a real finding that nobody read, because reading it cost over two minutes — and an
# instrument whose cost exceeds the attention available is not consulted, which makes its verdict
# indistinguishable from one never produced (#2, from the opposite side). `--stale-check` runs NO
# subprocesses and concludes in 0.085s. ⇒ It is affordable on a merge cadence; a full census is
# not, and is deliberately NOT wired here.
#
# ⚠ BOUND 4 HOLDS: both subjects are instruments of this role. Arming a leg on another role's
# instrument remains the operator's, not mine.
LEGS = [
    {"key": "index", "title": "scripts/check-tools-index.py",
     "path": ROOT / "scripts" / "check-tools-index.py", "argv": [],
     "doc": {0: "clean", 1: "drift", 2: "established nothing"},
     "finding": re.compile(r"^\s*FAIL\s+(.*\S)\s*$", re.M)},
    {"key": "ledger", "title": "tools/verdict-census.py --stale-check",
     "path": ROOT / "tools" / "verdict-census.py", "argv": ["--stale-check"],
     # ⚠ 0 HERE MEANS "the record is current", NOT "every instrument produces verdicts". The two
     # legs' codes look alike and mean different things; printing the MEANING per leg is what
     # keeps them apart at the point a reader sees them.
     "doc": {0: "record current", 1: "population moved", 2: "established nothing"},
     # ⛔ ITS OUTPUT DOES NOT SAY "FAIL". Reusing the first leg's pattern made this leg exit 1
     # and the watch report "quiet" — a leg with NO REACHABLE FAILING STATE, which is the mirror
     # of #26 and was invisible to a self-test whose fixtures all emit FAIL lines. Caught by
     # running it, not by testing it.
     "finding": re.compile(r"^\s*⛔\s+(.*\S)\s*$", re.M)},
]
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

    # ⛔ ASK "AM I THE CURRENT BLOB" BEFORE ASKING "HOW OLD AM I", because the history walk
    # below cannot answer the first question and was reporting the second as if it were.
    #
    # MEASURED 2026-08-20 (#320), from a clean checkout of origin/main at 280ac70:
    #     git diff origin/main -- tools/index-watch.py    -> empty
    #     this function                                   -> "87 COMMIT(S) BEHIND (pinned at 06e6dca8)"
    # The file had not changed in 89 commits. 87 is a correct answer to *how long since this
    # file was last edited*; it was printed as the answer to *how far behind is this source*,
    # which is a different question whose answer was ZERO.
    #
    # ⇒ The two collapse only for a file that is still being edited. For a settled file they
    # diverge without bound, and in the direction that produces the LOUDEST warning: the more
    # stable a tool is, the more stale it claims to be. ⚠ That is a false positive on a
    # staleness warning, fired unconditionally, and a warning that fires on the state needing no
    # action is how a reader learns to skip the line — while the real case it exists to catch
    # (#205: panes running instruments from trees dozens of commits behind) is live.
    #
    # ★ The reassuring answer was also UNREPRESENTABLE before this: the only outcomes were a
    # distance or UNKNOWN, so the state a reader most wants confirmed could not be printed.
    head = run("git", "rev-parse", f"origin/main:tools/{me.name}", cwd=str(repo or ROOT))
    if head.returncode == 0 and head.stdout.strip() == blob:
        return 0, "origin/main"

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
        # ⛔ MIGRATION, AND IT IS THE PART THAT CAN SILENTLY DESTROY A BASELINE. Findings are now
        # namespaced "<leg>\t<finding>" so two legs' identical strings cannot mask one another.
        # A state file written before the second leg holds BARE strings; read as unprefixed they
        # would match nothing, every held finding would read as RESOLVED on the next run, and the
        # baseline would roll forward over a report that was never made. ⇒ A bare entry is
        # attributed to the original leg, which is the only leg that could have written it.
        raw = sorted(d.get("findings") or [])
        return d.get("sha"), [f if "\t" in f else f"index\t{f}" for f in raw]
    except Exception:
        return None, []


def save_state(path, sha, findings):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sha": sha, "findings": sorted(findings)}, indent=1))


def check_once(state_path, force=False, subject=None, repo=None, legs=None, sha=None):
    """Return (exit_code, lines). One poll of `main`, every leg run against it.

    ⛔ COMBINING THE LEGS' EXIT CODES IS ITSELF A COLLAPSED PAIR, so the rule is stated rather
    than assumed. If leg A returns a FINDING and leg B VOIDs, a combined `2` would assert
    "established nothing" while something WAS established, and hide the finding behind it.

        1  any leg produced a finding          ← knowledge exists; it outranks a refusal
        2  no findings, and at least one leg established nothing
        0  every leg ran and found nothing

    ⚠ AND THE COMBINED CODE NEVER STANDS ALONE: every leg prints its own code and its own
    MEANING on every run, so a per-leg VOID can never be absorbed by another leg's finding.
    """
    legs = LEGS if legs is None else legs
    if subject is not None:
        # back-compat for the injected single-subject controls
        legs = [{**legs[0], "path": subject}]
    repo = ROOT if repo is None else repo
    # ⛔ THREADED, NEVER CACHED IN A MODULE GLOBAL. A cached SHA would be correct here and WRONG in
    # the monitor path, whose entire job is noticing that this value CHANGED — a cache there turns
    # a change detector into a constant. ⇒ The caller may pass a SHA it already fetched; nothing
    # is remembered between calls.
    # ⚠ Measured 2026-08-21: the self-test called this ~8 times at ~1.3s of network each. The
    # control ran in ~22s against a 30s gate bound — 8s of margin on a laptop, and a CI runner is
    # slower. A control that passes only on fast hardware is a control with a hidden precondition.
    sha = remote_sha(repo) if sha is None else sha
    if sha is None:
        return 2, [f"  VOID  could not read origin/main from {repo} — establishes nothing about"
                   " the index. ⛔ This is NOT 'unchanged'."]

    prev, base = load_state(state_path)
    if prev == sha and not force:
        # The only silent-ish path, and it is silent about the SUBJECTS, not about itself.
        #
        # ⛔ #598: THIS LINE NAMES ITS OWN REMEDY NOW, and the omission was the whole cost.
        # `--force` exists and is documented in --help ("run the subject even if main has not
        # moved"), and this output — the ONLY output a reader sees when the legs did not run —
        # never mentioned it. Measured 2026-09-06: 0 occurrences of "--force" in a
        # short-circuit run.
        #
        # ⚠ WHAT THAT COST, from the field: a pane probing whether index-watch invokes
        # verdict-census planted a recording stub and watched it fire on run 1 and NOT on runs
        # 2-4. It nearly reported a FALSE NEGATIVE — "this caller does not exist" — because
        # nothing here said the legs could be MADE to run. ⇒ The prose was true and complete
        # about what happened, and silent about what to do, which is the shape #73 records:
        # an absence report that does not name its remedy converts a gap into a wall.
        #
        # ⚠ EXIT 0 IS DELIBERATELY UNCHANGED. This file's contract already reads "0 main
        # unchanged, OR checked and the subject reported clean" — two-valued by declaration,
        # not by accident — and twelve files reference this tool. #598 argues that declaring
        # it does not make it safe, and that argument stands; it is recorded there, not
        # settled here. What is settled: a reader who sees this line now knows the next move.
        return 0, [f"  ok    main unchanged at {sha[:8]} — {len(legs)} leg(s) not run"
                   f" (nothing to re-check; --force runs them anyway)",
                   f"  ⚠ this is a SKIP, not a verdict: exit 0 here means the legs did NOT"
                   f" run. See #598."]

    codes, all_lines, all_found = [], [], []
    for leg in legs:
        rc, lines, found, sub_rc = _run_leg(leg, base, prev, sha, repo)
        codes.append(rc)
        all_found += found
        # ⚠ TWO DIFFERENT NUMBERS, AND THEY WERE PRINTED AS ONE. `sub_rc` is what the SUBJECT
        # exited and carries the subject's meaning; `rc` is what THIS WATCH concluded, which is 0
        # when a finding is real but already reported. Labelling the watch's verdict with the
        # subject's vocabulary printed "record current" while the record was stale.
        meaning = leg["doc"].get(sub_rc, "⛔ UNDOCUMENTED") if sub_rc is not None else "not run"
        all_lines += [f"  == {leg['title']}  ->  subject exited {sub_rc} ({meaning});"
                      f" watch says {rc}"] + lines
    # ⛔ Roll the baseline only over legs that ESTABLISHED something. A leg that VOIDed keeps its
    # previous findings, because nothing replaced them — dropping them would manufacture a
    # RESOLVED line for a report that was never made.
    voided = {leg["key"] for leg, rc in zip(legs, codes) if rc == 2}
    kept = [f for f in base if f.split("\t", 1)[0] in voided]
    save_state(state_path, sha, sorted(set(all_found) | set(kept)))
    rc = 1 if 1 in codes else (2 if 2 in codes else 0)
    head = f"main moved {(prev or 'unknown')[:8]} -> {sha[:8]}"
    return rc, [f"  ----  {head}; {len(legs)} leg(s) run"] + all_lines


def _run_leg(leg, base_all, prev, sha, repo):
    """(watch_rc, lines, namespaced_found, subject_rc) for one leg. Never rolls state."""
    key, subject, DOCUMENTED = leg["key"], leg["path"], leg["doc"]
    base = [f.split("\t", 1)[1] for f in base_all if f.split("\t", 1)[0] == key]
    if not subject.is_file():
        # ⚠ NOT exit 2 from the runtime. `python3 <missing>` also exits 2 (#58), so the absence is
        # detected HERE, before running, and never inferred from a code.
        return 2, [f"  VOID  subject missing: {subject} — establishes nothing"], [], None

    r = run(sys.executable, str(subject), *leg["argv"])
    rc = r.returncode

    if rc not in DOCUMENTED:
        return 2, [f"  VOID  subject exited {rc}, which it does not document"
                   f" (documented: {sorted(DOCUMENTED)}) — establishes nothing",
                   f"        stderr: {(r.stderr or '').strip()[:300]}"], [], rc

    head = f"exited {rc} ({DOCUMENTED[rc]})"

    if rc == 2:
        # ⛔ Do NOT roll the baseline on a VOID — nothing was established, so the previous
        # finding set is still the best knowledge available.
        return 2, [f"  VOID  {head} — the subject established nothing; ⛔ not a clean result",
                   *(f"        {l}" for l in (r.stdout or "").splitlines() if l.strip())], [], rc

    found = sorted(set(leg.get("finding", FAIL_LINE).findall(r.stdout or "")))
    # ⛔ THE EXTRACTOR MUST BE ABLE TO SEE THIS SUBJECT'S FINDINGS. If the subject exited its
    # DRIFT code and the pattern matched nothing, the pattern does not understand this output —
    # and reporting "quiet" would turn a real finding into silence. That is exactly what happened
    # when the ledger leg inherited the first leg's `FAIL` pattern. Establishes NOTHING, loudly.
    if rc == 1 and not found:
        return 2, [f"  VOID  subject exited 1 but this watch extracted NO findings from its"
                   f" output — the pattern does not match this subject. ⛔ NOT 'quiet'.",
                   *[f"        {l}" for l in (r.stdout or "").splitlines() if l.strip()][:8]], [], rc
    fresh = [f for f in found if f not in base]
    gone = [f for f in base if f not in found]
    ns = [f"{key}\t{f}" for f in found]

    if not found:
        if gone:
            return 0, [f"  ok    {head}", "  ⇒ RESOLVED since the last report:",
                       *(f"        - {g}" for g in gone)], ns, rc
        return 0, [f"  ok    {head} — nothing found"], ns, rc

    if not fresh:
        # Repeat-firing is a defect of the same severity as silence. Stay quiet about the
        # finding — but NAME the baseline, so this can never be read as "nothing is wrong".
        lines = [f"  ok    {head}",
                 f"  ----  {len(found)} finding(s) UNCHANGED since last reported — not re-raised"
                 f" (repeat-firing trains its reader to skip; tools/README.md)"]
        lines += [f"        held: {f}" for f in found]
        if gone:
            lines += ["  ⇒ RESOLVED since the last report:"] + [f"        - {g}" for g in gone]
        return 0, lines, ns, rc

    return 1, [f"  FIND  {head}",
               f"  ⇒ {len(fresh)} NEW finding(s) since the last report:",
               *(f"        + {f}" for f in fresh),
               *([f"  ---- {len(found) - len(fresh)} other finding(s) already reported, held"]
                 if len(found) > len(fresh) else []),
               "", *(f"        {l}" for l in (r.stdout or "").splitlines() if l.strip()), "",
               "  ⚠ This is a FINDING, not a task. It names no owner and requests no action."], ns, rc


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
    # ⛔ FETCHED ONCE, THREADED DOWN. Every check_once below would otherwise hit the network
    # again; measured at ~8 calls x ~1.3s. Not a module cache — see check_once.

    _sha = remote_sha()
    ok = True
    # ⛔ --help IS NOT A REFUSAL. argparse exits 0 after printing usage; catching every SystemExit
    # as "unrecognised arguments" made this tool print its help and then declare it established
    # nothing (#350). ⚠ Placed BEFORE the unreachable-origin early return, because asking a tool
    # what it does needs no network — a control that only runs when the forge answers is a control
    # that is absent exactly when someone is debugging.
    import contextlib, io
    for _flag, _want in (("--help", 0), ("-h", 0), ("--zzz-not-a-real-flag", 2)):
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
            _got = main(["x", _flag])
        ok &= _got == _want
        print(f"  {'ok  ' if _got == _want else 'FAIL'}  {_flag} -> {_got} (want {_want})"
              f"{' — help is not VOID' if _want == 0 else ' — a bogus flag is still VOID'}")
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
            rc, lines = check_once(st, sha=_sha)
            # ⚠ The assertion is on the SEMANTIC — that the quiet path names what did NOT run —
            # not on the old wording. "clean" must never appear on a path where nothing ran.
            hit = (rc == 0 and any("not run" in l for l in lines)
                   and not any("clean" in l for l in lines))
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  unchanged main says what did NOT run, never "
                  f"'clean' (got {rc})")
        else:
            # ⛔ A VOID IS NOT A FAILURE, and reporting it as one is the exact collapse this file
            # exists against — stated in its own docstring, and committed three lines from it.
            # `remote_sha()` needs a reachable origin. On a runner without network, or with no
            # credentials, this control cannot run — which says nothing about the code.
            # ⚠ Measured 2026-08-21 with `git ls-remote` stubbed to fail: the self-test exited 1.
            # Gating that would ship a BORN-RED guard, the failure mode
            # `.github/workflows/tools.yml` calls load-bearing in its own hermetic/fleet split.
            print("  ----  NOT ESTABLISHED  origin/main is unreachable, so the unchanged-SHA path"
                  " was NOT exercised. ⛔ Untested, not correct — and NOT a failure of the code.")

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
            # ⛔ THE DIRECTION THAT WAS NEVER TESTED, and #320 is what lived in the gap: a copy
            # that IS origin/main must report 0. Only "an older copy reports > 0" existed, and
            # BOTH a correct implementation and one reporting age-of-last-edit satisfy that.
            #
            # ⚠ SYNTHETIC, not the working tree. Asserting on this file as it sits on disk would
            # pass only while it is committed and unmodified — it fails during every edit to
            # itself, including the edit that adds this control. A control whose verdict depends
            # on the author's uncommitted state is a control that will be deleted for being
            # flaky, and the finding goes with it.
            # ⚠ THE BASENAME IS LOAD-BEARING. source_staleness looks up
            # `origin/main:tools/<me.name>`, so a copy named anything else asks git for a path
            # that does not exist and comes back UNKNOWN — which looks exactly like the defect
            # under test passing. Written first as `current-index-watch.py`; it reported
            # UNKNOWN and I nearly read that as the control catching something.
            curdir = Path(d) / "cur"
            curdir.mkdir(exist_ok=True)
            curcopy = curdir / "index-watch.py"
            cur = run("git", "show", "origin/main:tools/index-watch.py", cwd=str(ROOT))
            if cur.returncode == 0:
                curcopy.write_text(cur.stdout)
                ns0 = {}
                exec(compile(Path(__file__).read_text().replace(
                    "Path(__file__).resolve()", f"Path({str(curcopy)!r})"), "iw", "exec"), ns0)
                n_cur, why_cur = ns0["source_staleness"](ROOT)
                hit = n_cur == 0
                ok &= hit
                print(f"  {'ok  ' if hit else 'FAIL'}  a CURRENT copy reports 0, not the age of "
                      f"its last edit (got {n_cur}, {why_cur})")
            else:
                print("  ----  current-copy control NOT EXERCISED: origin/main unreadable")

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

    # ------------------------------------------------------------------------------
    # TWO LEGS — every control below targets a place a wrong answer would be INVISIBLE.
    # ------------------------------------------------------------------------------
    # ⛔ PRECONDITION, AND WITHOUT IT THESE CONTROLS CRASH RATHER THAN REFUSE. `check_once`
    # tests `remote_sha()` FIRST and returns VOID before it ever reaches `save_state` — so with
    # origin unreachable the state file is never written and every control below dies on
    # FileNotFoundError. ⚠ Measured 2026-08-21 with `git ls-remote` stubbed: exit 1 from a
    # traceback, which the gate reads as FINDINGS. A crash is not a finding and an unreachable
    # forge is not a defect; both were being reported as one.
    if _sha is None:
        print("  ----  NOT ESTABLISHED  origin/main is unreachable, so the two-leg controls were"
              " NOT exercised. ⛔ Untested, not correct — and NOT a failure of the code.")
        return 0 if ok else 3

    with tempfile.TemporaryDirectory() as d:
        st = Path(d) / "two.json"
        DOC = {0: "clean", 1: "drift", 2: "established nothing"}
        mk = lambda k, f: {"key": k, "title": k, "path": _fixture_subject(Path(d), f) if f
                           else Path(d) / ("clean_" + k + ".py"), "argv": [], "doc": DOC}
        for k in ("a", "b"):
            (Path(d) / f"clean_{k}.py").write_text("raise SystemExit(0)\n")

        # ⛔ THE SAME FINDING STRING FROM TWO LEGS MUST NOT MASK ONE ANOTHER. Un-namespaced, leg
        # b's identical finding would already be in the baseline that leg a wrote, and would
        # never be reported at all.
        same = "the index disagrees"
        la = {**mk("a", [same])}
        lb = {**mk("b", [same])}
        la["path"] = _fixture_subject(Path(d), [same])
        lb["path"] = Path(d) / "fixture_b.py"
        lb["path"].write_text(f'print("  FAIL  {same}")\nraise SystemExit(1)\n')
        rc, lines = check_once(st, force=True, legs=[la, lb], sha=_sha)
        state = json.loads(st.read_text())["findings"]
        hit = rc == 1 and sorted(state) == sorted([f"a\t{same}", f"b\t{same}"])
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  two legs reporting the SAME string are recorded "
              f"separately, so neither masks the other (got {state})")

        # ⛔ A FINDING OUTRANKS A REFUSAL. Combined 2 would assert "established nothing" while
        # something WAS established, and bury the finding under it.
        st2 = Path(d) / "mixed.json"
        missing = {"key": "b", "title": "b", "path": Path(d) / "not-here.py", "argv": [],
                   "doc": DOC}
        rc, lines = check_once(st2, force=True, legs=[la, missing], sha=_sha)
        hit = rc == 1 and any("VOID" in l for l in lines) and any("FIND" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  finding + VOID exits 1, and the VOID line still "
              f"PRINTS — a refusal is never absorbed by another leg's finding (got {rc})")

        # ⛔ A VOIDED LEG KEEPS ITS BASELINE. Rolling over it would manufacture a RESOLVED line
        # for a report that was never made.
        held = json.loads(Path(d).joinpath("mixed.json").read_text())["findings"]
        hit = any(f.startswith("a\t") for f in held)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  the establishing leg's findings are recorded while "
              f"the VOIDed leg's baseline is preserved")

        # ⛔ THE MIGRATION. A state file written before the second leg holds BARE strings. Read
        # unprefixed they match nothing, every held finding reads as RESOLVED, and the baseline
        # rolls over a report nobody made.
        st3 = Path(d) / "old.json"
        st3.write_text(json.dumps({"sha": "deadbeef", "findings": [same]}))
        _, base = load_state(st3)
        hit = base == [f"index\t{same}"]
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a pre-two-leg state file migrates to the ORIGINAL "
              f"leg, so nothing false-RESOLVES (got {base})")

        # ⛔ THE CONTROL FOR THE DEFECT THIS FILE SHIPPED AND I CAUGHT BY RUNNING IT, NOT BY
        # TESTING IT. The ledger leg inherited the first leg's `FAIL` pattern; verdict-census
        # emits `⛔`, so the leg exited 1 and the watch reported QUIET. A leg with no reachable
        # failing state — #26's mirror. Every fixture above emits FAIL lines, which is exactly
        # why none of them could see it.
        odd = Path(d) / "odd_output.py"
        odd.write_text('print("  ⛔ something is wrong")\nraise SystemExit(1)\n')
        st4 = Path(d) / "odd.json"
        rc, lines = check_once(st4, sha=_sha, force=True, legs=[
            {"key": "odd", "title": "odd", "path": odd, "argv": [], "doc": DOC}])
        hit = rc == 2 and any("extracted NO findings" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a subject that exits 1 with output the pattern "
              f"cannot match is VOID, never 'quiet' (got {rc})")

        # ⚠ and the same subject WITH a matching pattern must find it — otherwise the guard above
        # could pass by never matching anything at all.
        rc, lines = check_once(Path(d) / "odd2.json", sha=_sha, force=True, legs=[
            {"key": "odd", "title": "odd", "path": odd, "argv": [], "doc": DOC,
             "finding": re.compile(r"^\s*⛔\s+(.*\S)\s*$", re.M)}])
        hit = rc == 1 and any("something is wrong" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  with the RIGHT pattern the same subject yields a "
              f"finding — the guard is not passing by matching nothing (got {rc})")

        # ⛔ the two numbers that were printed as one
        rc, lines = check_once(Path(d) / "hdr.json", sha=_sha, force=True, legs=[la])
        hdr = [l for l in lines if l.startswith("  == ")][0]
        hit = "subject exited 1" in hdr and "watch says 1" in hdr
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  the header prints the SUBJECT's code and the "
              f"WATCH's verdict as two numbers, not one")

        # ⚠ and the real second leg must actually be affordable on this trigger
        t0 = time.time()
        r = run(sys.executable, str(ROOT / "tools" / "verdict-census.py"), "--stale-check")
        dt = time.time() - t0
        hit = r.returncode in (0, 1, 2) and dt < 10
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  the ledger leg concludes in {dt:.2f}s "
              f"(rc={r.returncode}) — a full census here would be ~4m and is deliberately NOT "
              f"wired")


    # ==================================================================================
    # ⛔ A POPULATION THIS AUTHOR DID NOT DRAW — criterion 5's population leg (#164 item 1,
    # ARCHITECT's ruling, PR #341). EVERY control above runs against fixtures I wrote, and that
    # is why every one of them PASSED while the ledger leg reported "quiet" on a real finding:
    # my fixtures all emit `FAIL`, because I wrote them from my own model of the output.
    #
    # ★ #26 AND CRITERION 5 ARE DIFFERENT DEMANDS AND SATISFYING ONE DOES NOTHING FOR THE OTHER:
    #     #26          can this control be SILENCED BY A REPAIR?     -> stay outside the population
    #     criterion 5  can it be BLIND TO AN INPUT I NEVER IMAGINED? -> do not DRAW the population
    #   The fixtures above satisfy #26 completely. This leg is the other half.
    #
    # ⚠ AND IT IS ALLOWED TO ESTABLISH NOTHING. If a subject exits 0 today, its finding vocabulary
    # is UNOBSERVABLE — the pattern is untested, not correct. Reported as NOT-ESTABLISHED, never
    # folded into `ok`, because a control that reports success when it measured nothing is the
    # defect this whole file exists against.
    # ==================================================================================
    for leg in LEGS:
        pat = leg.get("finding", FAIL_LINE)
        if not leg["path"].is_file():
            print(f"  ----  NOT ESTABLISHED  {leg['title']}: subject absent — its finding"
                  f" vocabulary is unobserved, NOT verified")
            continue
        rr = run(sys.executable, str(leg["path"]), *leg["argv"])
        if rr.returncode == 1:
            n = len(set(pat.findall(rr.stdout or "")))
            ok &= n > 0
            print(f"  {'ok  ' if n else 'FAIL'}  {leg['title']} exited 1 and its REAL output"
                  f" yields {n} finding(s) under this leg's pattern — population not drawn by"
                  f" the author")
        else:
            # ⛔ NOT 'ok'. The subject had nothing to say today, so nothing about the pattern was
            # tested. This is the exact reading that "exit 2 means established nothing" protects.
            print(f"  ----  NOT ESTABLISHED  {leg['title']} exited {rr.returncode}, so it emitted"
                  f" no findings — this leg's pattern was NOT exercised against real output."
                  f" ⛔ Untested, not correct.")

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
    repo = Path(a.repo) if a.repo else None
    rc, lines = check_once(Path(a.state), force=a.force, repo=repo)
    print("\nindex-watch — this role's checkers vs main")
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
