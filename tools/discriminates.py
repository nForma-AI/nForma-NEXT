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

Exit: 0 the check discriminated · 2 non-discriminating (verdict refused)
      3 the control failed — the harness itself is broken
"""
import argparse, subprocess, sys


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="command producing the reading for state A")
    ap.add_argument("--b", required=True, help="command producing the reading for state B")
    ap.add_argument("--control-a", help="command over a KNOWN-DIFFERENT pair (with --control-b)")
    ap.add_argument("--control-b", help="the other half of the known-different pair")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    args = ap.parse_args()

    if bool(args.control_a) != bool(args.control_b):
        sys.exit("--control-a and --control-b must be given together")

    if args.control_a:
        ca, cb = reading(args.control_a), reading(args.control_b)
        if (ca[0], ca[1]) == (cb[0], cb[1]):
            print("⛔ CONTROL FAILED — the comparison reports no difference between two "
                  "states known to differ. The harness is broken; every result it produces "
                  "would read NON-DISCRIMINATING and look rigorous.", file=sys.stderr)
            return 3
        print("✅ control: the comparison can report a difference", file=sys.stderr)

    ra, rb = reading(args.a), reading(args.b)
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
