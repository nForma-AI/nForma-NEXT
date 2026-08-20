#!/usr/bin/env python3
"""Flag an added line that a previous commit DELIBERATELY REMOVED — the ADDITION failure mode.

⛔ THE DEFECT, measured (#220, ARCHITECT). There are three ways to resolve a
contradiction between a document and a claim ABOUT the document, and they are not
equally scrutinised:

    deletion   remove the thing the claim denies        -> conspicuous, obvious victim
    narrowing  shrink until the claim is true           -> defensible in isolation
    ADDITION   add the thing the claim says is missing  -> READS AS FIXING A GAP

★ The third attracts the LEAST scrutiny while doing identical work. Measured case:
a drift row asserted a goal file "carries no pushing-to-main clause -- a live gap."
FALSE -- that file had converted to a pointer and was the only one conformant with
the one-source ruling. An agent acting on the row would have ADDED the clause back,
undoing the conversion and re-introducing the duplication the ruling exists to
remove. ⇒ Nothing would have looked wrong. A deletion has a victim; an addition has
a rationale.

⇒ SO THIS TOOL DOES NOT JUDGE. It cannot know whether a re-addition is right -- a
revert is a legitimate re-addition. What it does is put THE REMOVAL'S OWN REASONING
in front of the person restoring it:

    "you are adding a line that 988d932 removed, saying: convert Reserved to a pointer"

That is the whole mechanism. The defect is not the addition, it is that the earlier
DECISION is invisible at the moment of reversal. This manufactures the scrutiny the
shape avoids.

⛔ THE MECHANIC, AND THE OBVIOUS ONE IS WRONG. Measured while building this:

    git log -S'<line>' -- <path>                  -> finds the ADD, MISSES the removal
    git log --full-history -m -S'<line>' -- path  -> finds the ADD, MISSES the removal
    git log -S'<line>'   (no pathspec)            -> finds other files, wrong answer
    presence-walk over the file's history         -> CORRECT

The pickaxe with a pathspec silently reported no prior removal for a line that is
provably absent from main and was removed in 988d932. ⚠ A detector built on it would
have returned a clean scan for the exact case it exists to catch -- the tool's own
subject, in its own foundation. So this walks: for each file, replay its history and
record every 1->0 transition per line.

Exit: 0 no re-additions · 1 re-additions found · 2 established nothing
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runmarker import guard, result  # noqa: E402

MIN_LEN = 24  # a short line re-appears by coincidence; a long one does not


class Void(Exception):
    """Established nothing. Never convertible into a verdict."""


def git(args, cwd, ok=(0,)):
    p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if p.returncode not in ok:
        raise Void(f"git {' '.join(args[:3])}… failed: {p.stderr.strip()[:120] or 'no stderr'}")
    return p.stdout


def significant(line):
    """⚠ A threshold is a calibration. Short lines ('```', '---', '') recur across
    unrelated edits, and reporting them would bury the real finding in noise -- the
    repeat-alarm defect. Stated rather than tuned silently."""
    s = line.strip()
    return len(s) >= MIN_LEN and not s.startswith("```")


def removals_for(path, ref, cwd):
    """Every line ever removed from `path`, mapped to the commit that removed it.

    ⛔ COMPARED AGAINST EACH COMMIT'S OWN PARENT, not against the previous entry in
    the log. The first version walked `git log --reverse` and diffed consecutive
    snapshots, which is correct ONLY on a linear history.

    Measured on this repository (#226 follow-up): `git log --reverse` interleaves
    sibling branches. `9a64ea8` and `0b378ca` are BOTH children of `eb22230`, and
    are walked consecutively — so a line present on one branch and absent on the
    other reads as removed-then-re-added. That produced 82 phantom findings across
    18 doctrine files, every one attributing a removal to a commit whose own parent
    did not contain the line either.

    ★ The self-test did not catch it because the fixture is a LINEAR chain. A
    control validated on a linear history has been validated on the history's
    linearity — the homogeneous-sample defect, in the tool's own known-positive.

    ⚠ Merges are compared against the FIRST parent. A line dropped on a side branch
    and never on mainline is not "removed" from the reader's point of view, and
    first-parent is the history that reader sees.
    """
    commits = git(["log", "--format=%H %P", ref, "--", path], cwd).splitlines()
    removed = {}
    for entry in commits:
        parts = entry.split()
        if not parts:
            continue
        c, parents = parts[0], parts[1:]
        cur = _blob_lines(c, path, cwd)
        if not parents:
            continue                      # root commit adds; it removes nothing
        prev = _blob_lines(parents[0], path, cwd)
        for line in prev - cur:
            if significant(line):
                removed.setdefault(line.strip(), c)
    return removed


def _blob_lines(commit, path, cwd):
    out = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=cwd,
                         capture_output=True, text=True)
    return set(out.stdout.splitlines()) if out.returncode == 0 else set()


def added_lines(base, cwd):
    diff = git(["diff", f"{base}...HEAD", "--unified=0"], cwd)
    out = {}
    path = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and path:
            if significant(line[1:]):
                out.setdefault(path, []).append(line[1:].strip())
    return out


def subject(c, cwd):
    return git(["log", "-1", "--format=%s|%ad", "--date=short", c], cwd).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="origin/main",
                    help="compare HEAD against this ref (default origin/main)")
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _mark(self_test())

    try:
        adds = added_lines(args.base, args.root)
        if not adds:
            print(f"no significant added lines vs {args.base} — nothing to check")
            return _mark(0)
        findings = []
        for path, lines in adds.items():
            rm = removals_for(path, args.base, args.root)
            for ln in lines:
                if ln in rm:
                    findings.append((path, ln, rm[ln]))
        if not findings:
            print(f"{sum(len(v) for v in adds.values())} added line(s) across "
                  f"{len(adds)} file(s); none was previously removed.")
            return _mark(0)
        print(f"⛔ {len(findings)} line(s) being RE-ADDED after a deliberate removal.\n")
        for path, ln, c in findings:
            subj, date = subject(c, args.root).split("|")
            print(f"  {path}")
            print(f"    + {ln[:96]}")
            print(f"    removed by {c[:8]} ({date}): {subj[:88]}")
        print("\n⚠ This is NOT a verdict. A revert is a legitimate re-addition. It surfaces the")
        print("  earlier decision so the reversal is a CHOICE rather than an omission.")
        return _mark(1)
    except Void as exc:
        print(f"VOID: {exc}", file=sys.stderr)
        print("⛔ established nothing — this is NOT 'no re-additions'.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2


def _mark(rc):
    result({0: "OK", 1: "FINDING", 2: "ESTABLISHED-NOTHING", 3: "SELF-TEST-FAILED"}
           .get(rc, f"EXIT-{rc}"))
    return rc


def self_test():
    """⛔ Known-positive built here, not sampled from this repository.

    ★ Why synthetic: the live repo's re-additions are whatever happens to exist
    today, so a control anchored to them goes silent the moment they are resolved --
    #26's sharp subtype. A constructed remove-then-re-add is reachable forever."""
    import tempfile
    checks, failed = [], 0

    def check(name, got, want):
        nonlocal failed
        if got != want:
            failed += 1
        checks.append((got == want, name, got, want))

    with tempfile.TemporaryDirectory() as t:
        def g(*a):
            subprocess.run(["git"] + list(a), cwd=t, capture_output=True, text=True, check=False)
        g("init", "-q", "-b", "main")
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        keep = "a deliberately long line that will be removed and later restored"
        open(f"{t}/f.md", "w").write(f"{keep}\nunrelated filler line of sufficient length here\n")
        g("add", "-A"); g("commit", "-qm", "add the line")
        open(f"{t}/f.md", "w").write("unrelated filler line of sufficient length here\n")
        g("add", "-A"); g("commit", "-qm", "convert Reserved to a pointer")
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=t,
                              capture_output=True, text=True).stdout.strip()
        # now RE-ADD it, which is the defect
        open(f"{t}/f.md", "w").write(f"{keep}\nunrelated filler line of sufficient length here\n")
        g("add", "-A"); g("commit", "-qm", "fix the gap")

        rm = removals_for("f.md", base, t)
        check("the removal is found by presence-walk", keep in rm, True)
        adds = added_lines(base, t)
        check("the re-addition is seen in the diff", keep in adds.get("f.md", []), True)

        # ⛔ known-NEGATIVE: a genuinely new line must NOT be flagged
        open(f"{t}/f.md", "a").write("a brand new line never previously present here\n")
        g("add", "-A"); g("commit", "-qm", "genuinely new")
        adds2 = added_lines(base, t)
        new = [l for l in adds2.get("f.md", []) if "brand new" in l]
        check("a genuinely new line is NOT flagged", any(l in rm for l in new), False)

        # ⛔ BRANCHY known-positive — the case the linear fixture could not express,
        # and the one that would have caught the sibling-walk bug (82 phantoms on the
        # real repo, 0 after the parent-walk fix).
        #
        # main:  A(add L) -> C(remove L) -> M(merge side) -> E(re-add L)
        # side:  A -------> B(unrelated) ------^
        #
        # B is a SIBLING of C. A walk that diffs consecutive log entries compares B
        # against C and invents a removal; a parent-walk does not.
        g("checkout", "-q", "-b", "side")
        # ⛔ The sibling MUST touch the SAME FILE. A first attempt had it edit another
        # file, and `git log -- f.md` filtered the sibling out of the walk entirely —
        # so the control PASSED ON THE BROKEN VERSION and was decorative (#26). The
        # bug needs two commits on one path with a common parent to reproduce.
        open(f"{t}/f.md", "a").write("a line added only on the side branch, long enough\n")
        g("add", "-A"); g("commit", "-qm", "unrelated work on a side branch")
        g("checkout", "-q", "main")
        open(f"{t}/f.md", "w").write("unrelated filler line of sufficient length here\n")
        g("add", "-A"); g("commit", "-qm", "remove L on mainline")
        g("merge", "-q", "--no-ff", "-m", "merge side", "side")
        open(f"{t}/f.md", "w").write(f"{keep}\nunrelated filler line of sufficient length here\n")
        g("add", "-A"); g("commit", "-qm", "re-add L after the merge")

        rm2 = removals_for("f.md", "main", t)
        check("branchy: the REAL removal is still found", keep in rm2, True)
        phantom = [l for l in rm2 if "side branch" in l]
        check("branchy: a sibling branch invents NO removal", phantom, [])

        # VOID path must execute
        try:
            removals_for("f.md", "refs/heads/no-such-ref", t)
            check("bad ref -> VOID", "no exception", "Void raised")
        except Void:
            check("bad ref -> VOID", "Void raised", "Void raised")

    for ok, name, got, want in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"   got {got!r}, want {want!r}"))
    if failed:
        print(f"\n⛔ {failed} of {len(checks)} known-positives failed.", file=sys.stderr)
        return 3
    print(f"\n{len(checks)} of {len(checks)} reachable (removal · re-addition · known-negative · VOID).")
    return 0


if __name__ == "__main__":
    sys.exit(guard("readd-scan", main))
