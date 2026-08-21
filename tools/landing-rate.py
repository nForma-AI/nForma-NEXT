#!/usr/bin/env python3
"""How long since anything LANDED — and is that a stall, or a queue being worked?

⛔ WHY THIS EXISTS. Measured 2026-08-20: three merge stalls of 125, 125 and 171 minutes.
The first ran to 126 minutes UNSEEN — every armed instrument was green throughout, and
all of them were correct. Four instruments, four STATE variables, zero derivatives:
context depth per session, DUE-set transitions, open-PR count, pane liveness. None of
them can go red for "nothing has landed", because none of them measures a rate.

⇒ The number that would have caught it needs no roster, no pane identity and no fleet
knowledge: TIME SINCE LAST LANDING. One forge call.

★ AND THE CAUSE CLAUSE IS DERIVED, NEVER ASSERTED — this is the part that was wrong
twice. The first version carried the constant string "accumulating with no exit": true
during stall 1 (15 open, 15 mergeable) and FALSE during stall 2, where every open PR
was CONFLICTING and no merge was possible. A stall gauge that names the wrong cause
misroutes the response — it points at whoever holds the merge bit when the owner is
whoever rebases.

⛔ The second version derived the clause from the SPLIT and still got it wrong: `M > 0`
means MERGEABLE WORK EXISTS, not that nothing is consuming it. It announced
merger-absence on every landing, with a zero-minute gap, seconds after a merge. A queue
being worked and a queue with no merger are IDENTICAL in M alone. The discriminator is
the gap, which was printed one clause away the whole time.

⚠ WHAT IT CANNOT ESTABLISH:
  · A gap is not a cause. It cannot tell an absent merger from a deliberate hold, a
    freeze, or a fleet asleep. It reports the interval and the split; the reason is
    someone's ruling.
  · Zero mergeable is not calm. All-CONFLICTING means no merge is POSSIBLE, which is
    rebase work, not a stall.
  · A quiet sample is not a property. A run of successes cannot locate a boundary you
    have not crossed yet.

Exit: 0 something landed inside the window · 1 the window is exceeded, cause named ·
      2 ESTABLISHED NOTHING — the forge did not answer. NEVER read 2 as calm.
"""
import argparse, datetime, json, subprocess, sys

STALL_MIN = 30


def classify(total, mergeable, conflicting, unknown, mins, stall=STALL_MIN):
    """Pure decision. No repository, no network — so the suite can drive every branch.

    Returns (exit_code, verdict, because).
    """
    if mins is None:
        return 2, "VOID", ("no landing timestamp — the forge did not answer. This "
                           "ESTABLISHES NOTHING about throughput and is not a clean bill.")
    split = f"{total} open = {mergeable} MERGEABLE / {conflicting} CONFLICTING / {unknown} UNKNOWN"
    if total == 0:
        return 0, "EMPTY", f"{split}. Nothing is open — an empty board, not a blocked one."
    if unknown == total:
        return 0, "RECOMPUTE", (f"{split}. Every open PR is UNKNOWN — a recompute window, "
                                "not a verdict. Establishes nothing yet.")
    if mergeable == 0 and conflicting > 0:
        return 0, "NO-MERGE-POSSIBLE", (
            f"{split}. ZERO mergeable: all {conflicting} open PR(s) are CONFLICTING. "
            "This is NOT a merger-absence stall — no merge is possible, rebase work is "
            "the blocker, and naming it a stall would misroute it.")
    if mergeable > 0 and mins >= stall:
        return 1, "STALLED", (f"{split}. {mergeable} mergeable and nothing landed in "
                              f"{mins}m — the merger-absence shape.")
    return 0, "WORKING", (f"{split}. {mergeable} mergeable, last landing {mins}m ago — "
                          "a queue being worked, not a stalled one.")


def gh_json(args):
    p = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if p.returncode:
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default="nForma-AI/nForma-NEXT")
    ap.add_argument("--stall-min", type=int, default=STALL_MIN,
                    help="minutes without a landing before the gap is called a stall")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        ok = True
        for args, want in (
            ((5, 5, 0, 0, 0), "WORKING"), ((5, 5, 0, 0, 63), "STALLED"),
            ((3, 0, 3, 0, 45), "NO-MERGE-POSSIBLE"), ((5, 0, 0, 5, 2), "RECOMPUTE"),
            ((0, 0, 0, 0, 10), "EMPTY"), ((5, 5, 0, 0, None), "VOID"),
        ):
            got = classify(*args)[1]
            print(f"  {'PASS' if got == want else 'FAIL'}  {args} -> {got} (want {want})")
            ok &= got == want
        return 0 if ok else 1

    merged = gh_json(["pr", "list", "-R", a.repo, "--state", "merged", "--limit", "40",
                      "--json", "number,mergedAt"])
    openp = gh_json(["pr", "list", "-R", a.repo, "--state", "open", "--limit", "100",
                     "--json", "number,mergeable"])
    if merged is None or openp is None or not merged:
        code, verdict, because = classify(0, 0, 0, 0, None)
        print(f"  {verdict}  {because}", file=sys.stderr)
        return code

    last = max(merged, key=lambda r: r["mergedAt"])
    t = datetime.datetime.strptime(last["mergedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc)
    mins = int((datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() // 60)
    M = sum(1 for p in openp if p["mergeable"] == "MERGEABLE")
    C = sum(1 for p in openp if p["mergeable"] == "CONFLICTING")
    U = len(openp) - M - C

    code, verdict, because = classify(len(openp), M, C, U, mins, a.stall_min)
    print(f"  last landing  #{last['number']} at {last['mergedAt']} ({mins}m ago)")
    print(f"  {verdict}  {because}")
    print("\n⚠ A gap is not a cause: this cannot tell an absent merger from a deliberate")
    print("  hold or a freeze. It reports the interval and the split; the reason is a ruling.")
    if code:
        print(f"⛔ {verdict}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
