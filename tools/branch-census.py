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


def branch_names(repo, remote, base):
    """Remote branch names, excluding HEAD and the base.

    ⛔ Factored out because --touches was calling census(), which builds a patch-id
    index over 600 commits of the base before answering. A path query needs the branch
    LIST and nothing else; paying the squash-detection cost for it timed the sweep out
    at two minutes and hid the exit-2 path from its own verification.
    """
    refs = [r.strip() for r in git(
        repo, "for-each-ref", "--format=%(refname)", f"refs/remotes/{remote}"
    ).splitlines() if r.strip()]
    names = [r.split(f"refs/remotes/{remote}/", 1)[1] for r in refs
             if f"refs/remotes/{remote}/" in r]
    return [b for b in names if b not in ("HEAD", base)]


def touching(repo, remote, base, path, branches):
    """Which branches carry changes to <path>, measured FROM THE MERGE-BASE.

    ⛔ WHY THIS IS A FLAG AND NOT A NOTE. The naive form answers a different question
    and inflates by an order of magnitude. Measured on this repository, 2026-08-21:

        git diff origin/main..$b  -- docs/DEFECT-CLASSES.md   ->  130 branches
        git diff origin/main...$b -- docs/DEFECT-CLASSES.md   ->   13
        git diff origin/main..$b  -- tools/README.md          ->  121
        git diff origin/main...$b -- tools/README.md          ->   25

    Two dots compares ENDPOINTS, so every branch cut before `main` last changed the file
    "touches" it — the difference is main moving, not the branch doing anything. Three
    dots compares from the MERGE-BASE: what the branch itself changed.

    ⇒ A freeze sweep run with the two-dot form names most of the fleet as violating a
    hold they are respecting. TEAMLEAD hit this while checking compliance with its own
    freeze; the count that matters was 13, and the naive form said 130.

    ⚠ A note in a docstring tells a reader who already opened the file. This is a flag
    so the wrong form is not reachable through the tool at all.
    """
    hits = []
    for b in branches:
        out = git(repo, "diff", "--name-only", f"{base}...{remote}/{b}", "--", path)
        if out.strip():
            hits.append(b)
    return hits


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

    branches = branch_names(repo, remote, base)
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
    ap.add_argument("--touches", metavar="PATH",
                    help="list branches carrying changes to PATH, measured from the "
                         "merge-base (never endpoint-to-endpoint) — the freeze-sweep question")
    ap.add_argument("--contrast", action="store_true",
                    help="with --touches, also compute the endpoint-form count (slow: "
                         "one extra git spawn per branch)")
    ap.add_argument("--window", type=int, default=600,
                    help="commits of <base> to index for squash detection")
    a = ap.parse_args()

    ref_now = 0
    try:
        ref_now = int(git(a.repo, "log", "-1", "--format=%ct", f"{a.remote}/{a.base}").strip() or 0)
    except Exception:
        pass
    if a.touches:
        base_ref = f"{a.remote}/{a.base}"
        names = branch_names(a.repo, a.remote, a.base)
        if not names:
            print(f"⛔ ESTABLISHED NOTHING — {a.remote} has no branches besides "
                  f"{a.base}.", file=sys.stderr)
            return 2
        hits = touching(a.repo, a.remote, base_ref, a.touches, names)
        naive = ([b for b in names
                  if git(a.repo, "diff", "--name-only",
                         f"{base_ref}..{a.remote}/{b}", "--", a.touches).strip()]
                 if a.contrast else None)
        for b in hits:
            print(f"  TOUCHES  {age_of(a.repo, a.remote, b, ref_now):>7}  {b}")
        print(f"\n  {len(hits)} of {len(names)} branch(es) change {a.touches} "
              f"(measured from the merge-base)")
        if naive is None:
            print(f"  ⚠ measured 2026-08-21: the endpoint form `{a.base}..<branch>` named "
                  "130 for this path where the merge-base form named 13. Pass --contrast "
                  "to recompute it here (one extra git spawn per branch).")
        else:
            print(f"  ⚠ the endpoint form `{a.base}..<branch>` names {len(naive)} — "
                  "that counts main moving, not the branch changing anything.")
        if not hits:
            print("\n⛔ ESTABLISHED NOTHING about a quiet moment: zero branches change "
                  "this path RIGHT NOW, which is a SAMPLE, not a property. A run of "
                  "successes cannot locate a boundary you have not crossed yet.",
                  file=sys.stderr)
            return 2
        return 0

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
