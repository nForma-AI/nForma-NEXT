#!/usr/bin/env python3
"""Which commits were pushed to a branch AFTER its PR merged — and never reached main?

⛔ #224's instrument, specified there and absent until now. The defect it exists for:

    #201   commits in the PR: 1   created 09:48:12Z   merged 09:48:54Z   42 SECONDS
    across 100 merged PRs:  37 merged <120s after creation · 25 merged <60s

★ A squash merge captures every commit IN THE PR AT MERGE TIME. It cannot capture one
the author has not pushed yet. So an author who opens a PR and keeps pushing loses
everything after the merge — and the PR shows `MERGED` with no indication anything is
missing. ⇒ *At 42 seconds the author is not late. The merger is early.* And `MERGED`
erases the difference.

⛔⛔ DETECTION IS BY CONTENT, NOT BY SHA, AND #224 IS EXPLICIT ABOUT IT. A squash merge
does not preserve SHAs, so `git merge-base --is-ancestor` answers a different question:
it says whether THIS COMMIT is on main, never whether ITS CONTENT is. Every squashed
commit is a non-ancestor, so ancestry alone reports the whole board as lost.

⇒ This compares `git patch-id --stable`. Two commits with the same diff have the same
patch-id regardless of sha, parent or message, which is exactly the equivalence a squash
preserves and ancestry does not.

⚠ WHAT PATCH-ID DOES NOT SURVIVE, stated because a silent miss here reads as a finding:
a commit whose content reached main **through a conflict resolution or a rebase that
altered the diff** has a different patch-id and will be reported as lost. ⇒ Findings are
CANDIDATES for a human read, not a proven loss. #445's distinction holds and is the
reason: ORPHANED ≠ CONTENT-LOST, and only the first is mechanically decidable.

The known-positive, live and re-verified 2026-09-05:

    PR #339          merged 2026-08-20T19:56:18Z
    commit 7447b1d   authored 19:57:18Z  — SIXTY SECONDS after the merge
                     docs/DEFECT-CLASSES.md, +10 lines
                     ancestry: not an ancestor · patch-id: absent from 400 commits of main

Exit: 0 no late pushes lost · 1 FINDINGS · 2 established nothing.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_REPO = "nForma-AI/nForma-NEXT"


class Void(Exception):
    """Established nothing. ⇒ exit 2, never a verdict."""


def sh(args, allow_fail=False, stdin=None):
    try:
        p = subprocess.run(args, capture_output=True, text=True, input=stdin)
    except OSError as exc:
        raise Void(f"cannot run {args[0]}: {exc}")
    if p.returncode != 0 and not allow_fail:
        raise Void(f"{args[0]} exited {p.returncode}: {(p.stderr or '').strip()[:200]}")
    return p.stdout


def iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ── The decision, separated from the data (#402) ──────────────────────────────

def classify(merged_at, commit_at, patch_on_main):
    """⇒ one of LATE-LOST · LATE-LANDED · IN-PR.

    ★ Separated from every subprocess call so the controls drive it with synthetic
    state — #402: for a stateful instrument, a caller that still runs it means one that
    drives the DECISION with synthetic prior-state, because the transition itself is not
    re-runnable."""
    if commit_at <= merged_at:
        return "IN-PR"
    return "LATE-LANDED" if patch_on_main else "LATE-LOST"


def patch_id(rev):
    out = sh(["git", "show", rev], allow_fail=True)
    if not out.strip():
        return None
    pid = sh(["git", "patch-id", "--stable"], allow_fail=True, stdin=out)
    return (pid.split() or [None])[0]


def main_patch_ids(since):
    """⛔ Built ONCE. Computing it per candidate is O(n·m) and was measured at minutes."""
    revs = sh(["git", "log", "origin/main", f"--since={since}", "--format=%H"],
              allow_fail=True).split()
    ids = set()
    for r in revs:
        p = patch_id(r)
        if p:
            ids.add(p)
    if not ids:
        raise Void(f"no commits on origin/main since {since} — the comparison set is "
                   f"EMPTY, so every candidate would read as lost. That is a VOID "
                   f"reading, not a clean board.")
    return ids


def run(repo, since, limit, only=None):
    sh(["git", "fetch", "origin", "--quiet"], allow_fail=True)
    if only:
        # ⛔ --pr exists because --limit is a RECENCY window, not a filter. #224's own
        # known-positive (#339) is 16 days and ~250 merges down; reaching it by raising
        # --limit costs a git-log per PR over the whole board. A named PR makes the
        # specimen re-runnable, which is what an acceptance criterion needs.
        prs = []
        for n in only:
            raw = sh(["gh", "pr", "view", str(n), "--repo", repo,
                      "--json", "number,mergedAt,headRefName,headRefOid"])
            try:
                prs.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise Void(f"gh pr view {n} was not JSON: {exc}")
    else:
        raw = sh(["gh", "pr", "list", "--repo", repo, "--state", "merged",
                  "--limit", str(limit),
                  "--json", "number,mergedAt,headRefName,headRefOid"])
        try:
            prs = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise Void(f"gh pr list was not JSON: {exc}")
    if not prs:
        raise Void(f"no merged PRs returned for {repo} — nothing was enumerated, which "
                   f"is not the same as nothing being late.")

    cutoff = iso(since) if "T" in since else None
    ids = main_patch_ids(since if not cutoff else since)

    findings, checked, unreachable = [], 0, 0
    for pr in prs:
        if not pr.get("mergedAt"):
            continue
        merged = iso(pr["mergedAt"])
        ref = f"origin/{pr['headRefName']}"
        log = sh(["git", "log", ref, "--format=%H %cI", "-50"], allow_fail=True)
        if not log.strip():
            unreachable += 1          # branch deleted or never fetched — NOT a clean read
            continue
        for line in log.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            sha, when = parts[0], parts[1]
            try:
                cat = iso(when)
            except ValueError:
                continue
            if cat <= merged:
                continue
            checked += 1
            verdict = classify(merged, cat, (patch_id(sha) in ids))
            if verdict == "LATE-LOST":
                files = sh(["git", "show", "--stat", "--format=", sha],
                           allow_fail=True).strip().splitlines()
                findings.append((pr["number"], sha, int((cat - merged).total_seconds()),
                                 [f.strip() for f in files[:3]]))

    scope = f"PR(s) {','.join(str(p['number']) for p in prs)}" if only else \
            f"{len(prs)} most-recently-merged PR(s)"
    print(f"POPULATION  {scope} from {repo}; main patch-ids since {since}")
    if not only:
        print(f"            ⚠ --limit is a RECENCY window, not a filter: a PR older than "
              f"the\n            most recent {limit} is NOT examined and is not clean.")
    print(f"PREDICATE   a commit on the head ref dated AFTER mergedAt whose PATCH-ID is "
          f"absent from origin/main")
    print(f"CHANNEL     git patch-id --stable — ⛔ NOT ancestry: a squash preserves the "
          f"diff and not the sha\n")
    print(f"  late commits examined: {checked}")
    print(f"  ⚠ head refs unreadable (deleted or unfetched): {unreachable} — these are "
          f"UNCHECKED, not clean")

    if not findings:
        print("\n  no late push lost content in this window")
        return 0

    print(f"\n── {len(findings)} FINDING(S) ──")
    for num, sha, secs, files in findings:
        print(f"  ⛔ #{num}  {sha[:8]}  pushed {secs}s AFTER its PR merged")
        for f in files:
            print(f"        {f}")
    print("\n⚠ A finding is a CANDIDATE, not a proven loss. Content that reached main "
          "through\n   a conflict resolution or an altered rebase has a different "
          "patch-id and reads as\n   lost here. ⇒ #445: ORPHANED ≠ CONTENT-LOST, and "
          "only the first is mechanical.")
    return 1


# ── Controls ──────────────────────────────────────────────────────────────────

def self_test():
    """⛔ TWO-SIDED AND NAMED, driving the DECISION with synthetic state so no forge,
    no network and no clock are needed (#402)."""
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: got {got!r}, want {want!r}")

    M = iso("2026-08-20T19:56:18Z")
    after = iso("2026-08-20T19:57:18Z")     # #339 / 7447b1d — sixty seconds later
    before = iso("2026-08-20T19:50:00Z")

    print("⛔ the specimen this exists for (#224: #339, 7447b1d, +60s)")
    check("late AND absent from main -> LATE-LOST", classify(M, after, False), "LATE-LOST")

    print("★ the known-NEGATIVES, without which every squash reads as a loss")
    check("late but its CONTENT landed -> LATE-LANDED", classify(M, after, True), "LATE-LANDED")
    check("committed BEFORE the merge -> IN-PR", classify(M, before, False), "IN-PR")
    check("exactly at the merge instant is IN-PR, not late", classify(M, M, False), "IN-PR")

    print("⚠ one second late is still late — the boundary is not fudged")
    check("+1s -> LATE-LOST", classify(M, iso("2026-08-20T19:56:19Z"), False), "LATE-LOST")

    print(f"\n{'all controls pass' if ok else '⛔ CONTROLS FAILED'} — 5 legs, both directions")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="Commits pushed after their PR merged whose content never reached main.")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--since", default="24 hours ago",
                    help="git-log window, also bounding main's patch-id set")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--pr", type=int, action="append",
                    help="examine only these PR numbers (repeatable)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        extra = [a for a in sys.argv[1:] if a != "--self-test"]
        if extra:
            print(f"⛔ unrecognised argument(s) alongside --self-test: {extra}",
                  file=sys.stderr)
            return 2
        return self_test()
    try:
        return run(args.repo, args.since, args.limit, args.pr)
    except Void as exc:
        print(f"⛔ VOID — established nothing: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
