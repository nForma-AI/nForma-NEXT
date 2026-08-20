#!/usr/bin/env python3
"""Which open PRs must be STACKED, and which are already stale against main?

⛔ THE DEFECT. Every PR branches from `main`, so a fix that has not shipped is
absent from every PR opened after it. Whoever lands second rebases under conflict
pressure, and the fix that was already written gets re-derived or lost. Measured
2026-08-20 on this repository: **11 of 21 open-PR pairs conflicted**, and one file
caused **11 of the 11**.

★ AND THE ORDER IS A DECISION SOMEBODY MAKES ANYWAY. It is made either now, with
the pairs visible, or later by whichever PR happens to be merged first. This
prints it so it can be the first.

⚠ THREE VERDICTS, because "they both apply cleanly" is not "they are compatible":

  CONFLICTS    git merge-tree reports a textual conflict. One of them MUST rebase
               on the other; choosing which is the whole decision.
  OVERLAPS     same files, no textual conflict. ⛔ THIS IS THE DANGEROUS ONE — a
               semantic incompatibility that both branches pass and the merge
               result fails. CI tests your branch, never the merge result.
  independent  disjoint file sets. Nothing to decide.

⚠⚠ WHAT THIS CANNOT SEE. `merge-tree` is textual. Two PRs that touch no common
file can still be incompatible — one deletes a function the other starts calling.
An `independent` verdict is the absence of a textual signal and never a claim of
compatibility.
"""
import argparse, itertools, json, subprocess, sys


def sh(*a, check=False):
    r = subprocess.run(a, capture_output=True, text=True)
    if check and r.returncode != 0:
        return None
    return r.stdout.strip()


def open_prs(repo=None, limit=50):
    """[(number, headRef, title)] or None — a failed query is not an empty board."""
    cmd = ["gh", "pr", "list", "--state", "open", "--json",
           "number,headRefName,title", "--limit", str(limit)]
    if repo:
        cmd += ["--repo", repo]
    out = sh(*cmd, check=True)
    if out is None:
        return None
    try:
        rows = json.loads(out)
    except ValueError:
        return None
    return [(r["number"], r["headRefName"], r["title"]) for r in rows] or None


def files_of(ref, base):
    out = sh("git", "diff", "--name-only", f"{base}...{ref}", check=True)
    return set(out.split("\n")) - {""} if out else set()


def relation(r1, r2):
    """CONFLICTS | OVERLAPS | independent, plus the files implicated."""
    r = subprocess.run(["git", "merge-tree", "--write-tree", r1, r2],
                       capture_output=True, text=True)
    if r.returncode != 0 or "CONFLICT" in r.stdout:
        files = sorted({l.split(" in ")[-1] for l in r.stdout.splitlines()
                        if l.startswith("CONFLICT")})
        return "CONFLICTS", files
    return None, []


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip the fetch; unresolved heads are reported as UNKNOWN, never clean")
    a = ap.parse_args()

    prs = open_prs(a.repo, a.limit)
    if prs is None:
        print("⛔ ESTABLISHED NOTHING — the PR query failed or returned nothing. "
              "An empty board and a failed query print the same table.")
        return 2

    # ⛔ A HEAD THAT IS NOT FETCHED IS NOT AN ABSENT CONFLICT. The first run of this
    # tool skipped 2 of 4 PRs for that reason and printed a conflict count derived
    # from the half it could see — a smaller number that looks like better news.
    # So fetch first, and report what still cannot be resolved as UNKNOWN.
    if not a.no_fetch:
        sh("git", "fetch", "--quiet", "origin",
           *[f"+refs/heads/{h}:refs/remotes/origin/{h}" for _, h, _ in prs])

    rows, unresolved = [], []
    for n, head, title in prs:
        ref = f"origin/{head}"
        if sh("git", "rev-parse", "--verify", ref, check=True) is None:
            unresolved.append(n)
            continue
        behind = sh("git", "rev-list", "--count", f"{ref}..{a.base}") or "0"
        ahead = sh("git", "rev-list", "--count", f"{a.base}..{ref}") or "0"
        rows.append((n, head, ref, int(behind), int(ahead), files_of(ref, a.base)))
    if not rows:
        print("⛔ ESTABLISHED NOTHING — no PR head could be resolved locally. "
              "Run `git fetch origin` first.")
        return 2

    print(f"── {len(rows)} open PR(s) against {a.base}"
          + (f"  ⛔ {len(unresolved)} UNRESOLVED: {unresolved} — "
             "their conflicts are UNKNOWN, not absent" if unresolved else "") + "\n")
    print(f"{'PR':>6} {'behind':>6} {'ahead':>5}  branch")
    for n, head, _, b, ah, _ in sorted(rows, key=lambda r: -r[3]):
        flag = "  ⚠ STALE" if b else ""
        print(f"{n:>6} {b:>6} {ah:>5}  {head}{flag}")

    conflicts, overlaps = [], []
    for (n1, _, r1, _, _, f1), (n2, _, r2, _, _, f2) in itertools.combinations(rows, 2):
        kind, files = relation(r1, r2)
        if kind == "CONFLICTS":
            conflicts.append((n1, n2, files))
        elif f1 & f2:
            overlaps.append((n1, n2, sorted(f1 & f2)))

    print(f"\n── CONFLICTS — one MUST rebase on the other; decide which now ({len(conflicts)})")
    for n1, n2, files in conflicts:
        print(f"  #{n1} × #{n2}   {', '.join(files[:3])}")
    print(f"\n── OVERLAPS — same files, no textual conflict ({len(overlaps)})")
    print("   ⛔ The dangerous set: both branches pass, the MERGE RESULT is untested.")
    for n1, n2, files in overlaps:
        print(f"  #{n1} × #{n2}   {', '.join(files[:3])}")

    if conflicts:
        hot = {}
        for _, _, files in conflicts:
            for f in files:
                hot[f] = hot.get(f, 0) + 1
        top, cnt = max(hot.items(), key=lambda kv: kv[1])
        print(f"\n⇒ {cnt} of {len(conflicts)} conflicts are in ONE file: {top}")
        if cnt == len(conflicts):
            print("   A single file causing EVERY conflict is a structural collision, "
                  "not bad luck.\n   Fix the file's shape before rebasing anything.")

    print("\n⚠ merge-tree is TEXTUAL. 'independent' is the absence of a textual signal, "
          "never\n   a claim of compatibility — a PR can delete what another starts calling.")
    return 1 if (conflicts or unresolved or any(r[3] for r in rows)) else 0


if __name__ == "__main__":
    sys.exit(main())
