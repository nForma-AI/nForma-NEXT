#!/usr/bin/env python3
"""Refuse a verdict from a check that cannot tell the two states apart.

⛔ The failure this exists for, measured:

    "Is my worktree stale?"
        grep -c "46.6%"  worktree  -> 1
        grep -c "46.6%"  origin/main -> 1
    Concluded: the states agree, the worktree is fine.
    Actual: the worktree was 163 commits behind, and the figure had been
    RETRACTED on main. The retraction QUOTES the number it retracts, so the
    token survives inside its own withdrawal.

★ The mistake was not failing to run the check on both states. Both were run.
The mistake was reading equal outputs as *the states agree* when they mean
*this check cannot distinguish them*.

    > Identical readings from a discriminator are an INSTRUMENT FAILURE,
    > not evidence of sameness.

So this tool never reports "same". It reports DIFFER (the check discriminated,
here is how) or NON-DISCRIMINATING (you have learned nothing, and must not
record a conclusion).

⚠ Generalisation worth keeping: when testing whether a claim was retracted,
never search for the claim's distinctive number. A retraction quotes it. Search
for a change in occurrence count instead — `git log -S<string>` tracks the
claim; `grep -c` tracks the token.

Usage:
    discriminates.py --a '<command for state A>' --b '<command for state B>'
                     [--control-a '<cmd>' --control-b '<cmd>']

    --control-a/--control-b are a KNOWN-DIFFERENT pair. If supplied, the tool
    first proves the comparison method can report a difference at all. Without
    that, a comparison harness that is itself broken reports NON-DISCRIMINATING
    for everything and looks rigorous while measuring nothing.

⛔ AND THE MIRROR DEFECT, in this tool, found by probing it: it had a
KNOWN-DIFFERENT control and no KNOWN-SAME one. Measured —

    discriminates.py --a 'date +%N' --b 'date +%N'
    -> ✅ DISCRIMINATED, exit 0

One state, compared against itself, with a check that is pure noise. The tool
built to refuse a false *same* verdict emitted a false *differ* verdict, because
nothing established that a single state reads consistently at all.

    > A difference between two states is only evidence if ONE state does not
    > differ from itself.

So each command is now read TWICE and must agree with itself. A check that is not
self-consistent supports no comparison in either direction: exit 4, UNSTABLE.

⚠ The control pair is also NOT verified to use the same check as --a/--b. Passing
`--control-a 'echo 1' --control-b 'echo 2'` satisfies it while the real check is
noise. Nothing here can enforce that; the ✅ line now says what the control did and
did not establish, and prints the commands so a reader can see for themselves.

Exit: 0 the check discriminated · 2 non-discriminating (verdict refused)
      3 the control failed — the harness itself is broken
      4 a state is not self-consistent — the comparison is uninterpretable
     64 USAGE — an unrecognised argument. ⛔ NOT a verdict, and deliberately outside
        0/2/3/4: every one of those is a statement ABOUT THE COMPARISON, and a
        mistyped flag is a statement about the INVOCATION. 64 is EX_USAGE (BSD
        sysexits), chosen because this file's verdict space was already full and
        reusing 2 would have made "you typed it wrong" indistinguishable from
        "the check did not discriminate" — the exact exit-2 collision #58 records.
"""
import argparse, os, subprocess, sys


def run(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def reading(cmd):
    """A reading is (status, stdout). Status is part of it deliberately: a check
    that exits 1 with empty output is not the same reading as one that exits 0
    with empty output, and collapsing them is how a failed command reads as a
    negative result."""
    rc, out, err = run(cmd)
    return rc, out, err


def stable_reading(cmd):
    """Read twice. Returns (reading, None) if the state reads consistently, or
    (first, second) if it does not.

    ⛔ Without this, a check carrying a clock, a PID, a random ordering or a
    timestamp differs from ITSELF, and every comparison built on it reports
    DISCRIMINATED. That is the same error this tool exists to refuse, pointing
    the other way: over-firing is caught by a known-same control, under-firing
    by a known-different one, and only one of the two was here.
    """
    first, second = reading(cmd), reading(cmd)
    if (first[0], first[1]) != (second[0], second[1]):
        return first, second
    return first, None


def self_test():
    """⛔ Controls for the tool that refuses non-discriminating verdicts — which shipped
    with none. Measured 2026-08-20: of 26 instruments in tools/, 16 carried a control and
    10 did not, and this file was on the second list. A tool whose whole subject is "your
    check cannot tell these apart" had no check that it could tell anything apart.

    ★ Every case below is SYNTHETIC and reaches its verdict from fixed inputs, so each
    stays reachable in the REPAIRED state (#26). None is drawn from the fleet, from this
    repository, or from any live population — a control whose failing state exists only
    while something else is broken goes silent the moment it is fixed.

    ⚠ Each of the four documented exits gets a case. An exit code with no case is a
    verdict this tool can emit and has never been shown to emit correctly.

    ⛔ KNOWN LIMIT, measured on this control by the mutation probe from #26. Inverting
    every comparison in this file also inverts `"--self-test" in sys.argv`, so the
    sabotaged copy never REACHES these cases — argparse refuses it for missing --a/--b
    and exits 2. That is a VOID, not a detection, and it reads as one only if the reader
    checks that control output was produced. ⇒ A sabotage probe scoring `exit != 0` as
    "the control caught it" is satisfied by a tool that failed to launch.
    """
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'}  {label}: got {got} want {want}")
        return good

    here = [sys.executable, os.path.abspath(__file__)]

    def rc(*args):
        return subprocess.run(here + list(args), capture_output=True, text=True).returncode

    # 0 — the check DISCRIMINATED. Two states, one stable check, different readings.
    check("known-positive  two different states -> 0",
          rc("--a", "echo A", "--b", "echo B"), 0)

    # 2 — NON-DISCRIMINATING. The verdict this tool exists to refuse.
    check("known-negative  identical readings -> 2 (refused)",
          rc("--a", "echo SAME", "--b", "echo SAME"), 2)

    # ⛔ The case this tool was BUILT for: a retraction QUOTES the claim it retracts, so
    # `grep -c <token>` returns 1 on both the live claim and its withdrawal.
    check("known-negative  grep -c cannot separate a claim from its retraction -> 2",
          rc("--a", "echo 'the figure is 46.6%' | grep -c '46.6'",
             "--b", "echo 'RETRACTED: the figure is 46.6%' | grep -c '46.6'"), 2)

    # 3 — the CONTROL failed: a known-different pair that does not differ.
    check("known-negative  control pair that does NOT differ -> 3",
          rc("--a", "echo A", "--b", "echo B",
             "--control-a", "echo SAME", "--control-b", "echo SAME"), 3)

    # 0 — a control pair that DOES differ must not itself trip the harness.
    check("known-positive  a genuinely different control pair -> 0",
          rc("--a", "echo A", "--b", "echo B",
             "--control-a", "echo X", "--control-b", "echo Y"), 0)

    # 4 — UNSTABLE: a state that differs from itself supports no comparison.
    #     $RANDOM is re-evaluated per invocation, so the two reads disagree.
    check("known-negative  a self-inconsistent state -> 4 (uninterpretable)",
          rc("--a", "echo $RANDOM$RANDOM$RANDOM", "--b", "echo B"), 4)

    # ⚠ Exit status is part of a reading, not just stdout. A command that fails with
    #    empty output must not read as one that succeeds with empty output.
    check("known-positive  same stdout, different exit -> 0",
          rc("--a", "true", "--b", "false"), 0)

    print("\nall four documented exits reachable" if ok
          else "\n⛔ a documented exit could not be produced")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="command producing the reading for state A")
    ap.add_argument("--b", required=True, help="command producing the reading for state B")
    ap.add_argument("--control-a", help="command over a KNOWN-DIFFERENT pair (with --control-b)")
    ap.add_argument("--control-b", help="the other half of the known-different pair")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--self-test", action="store_true",
                    help="run the controls and exit")

    # ⛔ Intercepted BEFORE parse_args, because --a/--b are required=True: argparse would
    # refuse `--self-test` alone with a usage error and exit 2 — which is this tool's
    # documented NON-DISCRIMINATING verdict. A control that cannot be invoked without
    # emitting a real verdict code is worse than no control (#58, the exit-2 collision).
    if "--self-test" in sys.argv:
        # ⛔ AN UNRECOGNISED FLAG ALONGSIDE `--self-test` MUST REFUSE. The gate measured this
        # file UNVERIFIABLE: `--self-test --zzz-not-a-flag` exited 0, so "the flag is matched
        # and the rest DISCARDED — a control result here describes an invocation that was only
        # half read." Measured 2026-09-06.
        # ⚠ 64, not 2. This file's 0/2/3/4 are ALL verdicts about the comparison; a mistyped
        # flag is not one. Reusing 2 would make it indistinguishable from NON-DISCRIMINATING,
        # which is the collision the interception below already exists to avoid (#58).
        _extra = [a for a in sys.argv[1:] if a != "--self-test"]
        if _extra:
            print(f"⛔ USAGE — unrecognised argument(s) alongside --self-test: {_extra}.\n"
                  f"   The controls take no other flags, and running them while ignoring an\n"
                  f"   argument would report a verdict for an invocation that was only half read.\n"
                  f"   NO REMEDY — run `--self-test` alone. (exit 64 = usage, NOT a verdict)",
                  file=sys.stderr)
            return 64
        return self_test()

    args = ap.parse_args()


    if bool(args.control_a) != bool(args.control_b):
        sys.exit("--control-a and --control-b must be given together")

    if args.control_a:
        ca, ca2 = stable_reading(args.control_a)
        cb, cb2 = stable_reading(args.control_b)
        for lbl, cmd, drift in (("--control-a", args.control_a, ca2),
                                ("--control-b", args.control_b, cb2)):
            if drift is not None:
                print(f"⛔ CONTROL UNUSABLE — {lbl} does not read the same twice:\n"
                      f"   {cmd}\n"
                      f"   A known-different pair proves nothing if either half is noise; "
                      f"the difference it 'shows' may be the noise.", file=sys.stderr)
                return 3
        if (ca[0], ca[1]) == (cb[0], cb[1]):
            print("⛔ CONTROL FAILED — the comparison reports no difference between two "
                  "states known to differ. The harness is broken; every result it produces "
                  "would read NON-DISCRIMINATING and look rigorous.", file=sys.stderr)
            return 3
        print(f"✅ control: this pair differs, so the harness CAN report a difference.\n"
              f"   ⚠ That is all it establishes. It does NOT establish that YOUR check\n"
              f"   discriminates — nothing here verifies the control runs the same check:\n"
              f"     --control-a {args.control_a}\n"
              f"     --control-b {args.control_b}", file=sys.stderr)

    ra, ra2 = stable_reading(args.a)
    rb, rb2 = stable_reading(args.b)
    for lbl, cmd, first, drift in ((args.label_a, args.a, ra, ra2),
                                   (args.label_b, args.b, rb, rb2)):
        if drift is not None:
            print(f"⛔ UNSTABLE — {lbl} does not read the same twice:\n"
                  f"   {cmd}\n"
                  f"   1st: exit={first[0]} out={first[1]!r}\n"
                  f"   2nd: exit={drift[0]} out={drift[1]!r}\n"
                  f"   A difference between two states is evidence only if one state does "
                  f"not differ\n"
                  f"   from itself. This check supports no conclusion in either direction.",
                  file=sys.stderr)
            return 4

    same = (ra[0], ra[1]) == (rb[0], rb[1])

    print(f"{args.label_a}: exit={ra[0]} out={ra[1]!r}")
    print(f"{args.label_b}: exit={rb[0]} out={rb[1]!r}")

    if same:
        print(f"\n⛔ NON-DISCRIMINATING — {args.label_a} and {args.label_b} produced the "
              f"IDENTICAL reading.\n"
              f"   This does NOT mean the states agree. It means this check cannot tell "
              f"them apart,\n"
              f"   so it supports no conclusion in either direction. Record nothing; "
              f"change the check.\n"
              f"   (If you are testing whether a claim was retracted: a retraction quotes "
              f"the claim.\n"
              f"    Search for a change in occurrence count — `git log -S` — not for the "
              f"token itself.)",
              file=sys.stderr)
        return 2

    print(f"\n✅ DISCRIMINATED — the readings differ, so the check is capable of "
          f"distinguishing these states.\n"
          f"   ⚠ That the check WORKS is now established. What the difference MEANS is "
          f"still yours to interpret.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
