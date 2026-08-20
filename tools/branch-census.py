#!/usr/bin/env python3
"""Which remote branches are still live, and which are work that died quietly?

⛔ WHY THIS EXISTS. `git ls-remote origin 'refs/heads/*'` returned 89 branches and
nothing said which were finished. Measured 2026-08-20: FOUR panes independently
opened a fix for the same defect (#307) — dev2/index-sees-subdirs,
dev4/tools-index-recurse, devops/tools-index-recurse, dev1/index-population. One
defect, four branches, three wasted. That is not untidiness; it is a coordination
surface that does not exist, and duplicated work is the bill for it.

⛔ THE COLLAPSE THIS EXISTS TO BREAK. This repository squash-merges. A squash lands
the CONTENT on main and never makes the branch tip an ancestor, so
`git merge-base --is-ancestor` calls every squash-merged branch unmerged. Measured
here: 12 of 35 non-ancestor branches had already landed. ⇒ MERGED and STRANDED
become ONE VALUE at the squash boundary, and STRANDED is the flattering default —
it reads as "someone abandoned work" when the truth is "this shipped".

⚠ `git cherry` does NOT close this. It patch-id-matches commits INDIVIDUALLY, so a
three-commit branch squashed into one matches nothing and still reads unmerged.
The cumulative diff is the unit that survives a squash, so that is what is hashed.

⇒ WHAT IT CANNOT ESTABLISH, stated in the output and not only here:
  · It cannot tell ABANDONED from PAUSED. STRANDED is a shape, not a verdict.
  · A STRANDED branch may be someone's live worktree on another machine that has
    not been pushed. This reads THIS checkout's worktrees and no one else's.
  · LIVE is therefore a LOWER BOUND, and STRANDED an UPPER bound.
⛔ It proposes no deletions. Classification only; deletion is a separate ruling and
DEVOPS holds the stranded-branches work.

Exit: 0 the census discriminated · 2 ESTABLISHED NOTHING — no remote refs, or every
branch fell in one bucket. A census with one bucket has not classified a population,
it has relabelled it (#58). ⛔ 2 must never be read as "all clear".
"""
import argparse, collections, subprocess, sys

MERGED, SQUASH, LIVE, STRANDED = "MERGED", "SQUASH-MERGED", "LIVE", "STRANDED"
ORDER = [MERGED, SQUASH, LIVE, STRANDED]


def git(repo, *args, check=False):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout


def patch_id(repo, *diff_args):
    """Stable patch-id of a diff, or None when the diff is empty."""
    d = subprocess.run(["git", "-C", repo, *diff_args], capture_output=True)
    if not d.stdout.strip():
        return None
    p = subprocess.run(["git", "-C", repo, "patch-id", "--stable"],
                       input=d.stdout, capture_output=True)
    out = p.stdout.decode(errors="replace").split()
    return out[0] if out else None


def age_of(repo, remote, branch, now):
    """Age of a branch's last commit, as a compact string.

    ⛔ WHY THIS COLUMN EXISTS. Running this tool on its own repository, four branches
    pushed within FIFTEEN MINUTES classified STRANDED — correctly, by the definition:
    unmerged and not checked out in this checkout. ⇒ But STRANDED reads as ABANDONED,
    and "pushed 8 minutes ago" and "untouched since yesterday" were the same word.
    The classification was right and the presentation made it wrong.
    """
    try:
        t = int(git(repo, "log", "-1", "--format=%ct", f"{remote}/{branch}").strip())
    except Exception:
        return "?"
    d = max(0, now - t)
    if d < 3600:
        return f"{d // 60}m"
    if d < 86400:
        return f"{d // 3600}h"
    return f"{d // 86400}d"


def checked_out_branches(repo):
    """Branches checked out in THIS checkout's worktrees. A lower bound on LIVE."""
    live = set()
    for line in git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("branch "):
            live.add(line.split("refs/heads/", 1)[-1].strip())
    return live


def census(repo, remote="origin", base="main", window=600):
    base_ref = f"{remote}/{base}"
    if not git(repo, "rev-parse", "--verify", "-q", base_ref).strip():
        return None, f"no {base_ref} — nothing to classify against"

    refs = [r.strip() for r in git(
        repo, "for-each-ref", "--format=%(refname)", f"refs/remotes/{remote}"
    ).splitlines() if r.strip()]
    branches = [r.split(f"refs/remotes/{remote}/", 1)[1] for r in refs
                if f"refs/remotes/{remote}/" in r]
    branches = [b for b in branches if b not in ("HEAD", base)]
    if not branches:
        return None, f"{remote} has no branches besides {base}"

    # One patch-id index over main's recent history, rather than re-walking per branch.
    index = {}
    for sha in git(repo, "rev-list", f"-{window}", base_ref).split():
        pid = patch_id(repo, "show", sha)
        if pid:
            index.setdefault(pid, sha)

    live_local = checked_out_branches(repo)
    now = int(git(repo, "log", "-1", "--format=%ct", base_ref).strip() or 0)
    rows = []
    for b in sorted(branches):
        ref = f"{remote}/{b}"
        if subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", ref, base_ref],
                          capture_output=True).returncode == 0:
            rows.append((b, MERGED, "")); continue
        mb = git(repo, "merge-base", base_ref, ref).strip()
        pid = patch_id(repo, "diff", mb, ref) if mb else None
        hit = index.get(pid) if pid else None
        if hit:
            rows.append((b, SQUASH, f"content landed as {hit[:9]}")); continue
        rows.append((b, LIVE if b in live_local else STRANDED,
                     "checked out here" if b in live_local else ""))
    return rows, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="repository to read (default: cwd)")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--base", default="main")
    ap.add_argument("--window", type=int, default=600,
                    help="commits of <base> to index for squash detection")
    a = ap.parse_args()

    ref_now = 0
    try:
        ref_now = int(git(a.repo, "log", "-1", "--format=%ct", f"{a.remote}/{a.base}").strip() or 0)
    except Exception:
        pass
    try:
        rows, why = census(a.repo, a.remote, a.base, a.window)
    except Exception as ex:
        print(f"⛔ ESTABLISHED NOTHING — {type(ex).__name__}: {ex}", file=sys.stderr)
        return 2
    if rows is None:
        print(f"⛔ ESTABLISHED NOTHING — {why}. NOT a clean bill.", file=sys.stderr)
        return 2

    counts = collections.Counter(s for _, s, _ in rows)
    for state in ORDER:
        for b, s, note in rows:
            if s == state:
                age = age_of(a.repo, a.remote, b, ref_now)
                print(f"  {s:<14} {age:>7}  {b}{('  — ' + note) if note else ''}")
    print(f"\n  {len(rows)} branch(es): " +
          " · ".join(f"{s} {counts.get(s, 0)}" for s in ORDER))

    print("\n⚠ WHAT THIS DOES NOT ESTABLISH:")
    print("  · STRANDED is a shape, not a verdict — it cannot tell ABANDONED from PAUSED.")
    print("  · ⛔ AGE IS NOT MEMBERSHIP. A branch pushed minutes ago classifies STRANDED if it")
    print("    is unmerged and not checked out here — measured: 4 such branches under 15m old.")
    print("    Read the age column before reading the word.")
    print("  · It reads THIS checkout's worktrees only, so a branch live on another")
    print("    machine reads STRANDED here. LIVE is a LOWER bound, STRANDED an UPPER one.")
    print("  · It proposes no deletions. Classification only (DEVOPS holds that work).")

    if len(counts) == 1:
        print(f"\n⛔ ESTABLISHED NOTHING — all {len(rows)} branches classified "
              f"{next(iter(counts))}. A census with one bucket has relabelled the "
              f"population, not discriminated it (#58).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
