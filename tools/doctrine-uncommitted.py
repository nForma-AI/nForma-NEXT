#!/usr/bin/env python3
"""Which doctrine is the fleet READING that nobody has COMMITTED?

⛔ MEASURED 2026-08-21, and four agents acted on it. `CLAUDE.md` loads from the
WORKING COPY, so an uncommitted edit is fleet doctrine the moment it is written —
there is no landing step between "typed" and "authoritative".

  /Users/…/DigitalFrontier-infra   branch pr1136, .git/MERGE_HEAD PRESENT
  CLAUDE.md                        +79/-2 STAGED, conflicts resolved, never committed
  origin/main                      0 matches for the section
  the section                      an OPEN PR's content (#1136)

⇒ The interpreter-discriminator section was cited by FOUR agents that night as
doctrine. It is real, it is correct, and **it has never landed**. If that PR is
closed unmerged, every conclusion drawn from it rests on text no ref contains.

★ THE SHAPE: a role prompt has a version and a delivery channel, and tools exist
for both. A repo-root doctrine file has NEITHER — it is read by path, from disk,
by every agent, with no ref in between. **The file everyone trusts most is the one
with the weakest provenance.**

⚠ THREE STATES, NOT TWO — and the middle one is the COMMON one:

  READ-NOT-COMMITTED       no ref carries it          remedy: commit
  READ-ON-A-BRANCH         a BRANCH carries it,       remedy: LAND THE PR
                           main does not
  COMMITTED-NOT-READ       a stale or dirty checkout  remedy: rebase/refresh
                           HIDES landed doctrine

⛔ THE MIDDLE STATE IS WHAT AN OPEN DOCS PR LOOKS LIKE FROM THE WORKING COPY,
EVERY TIME — and the first version of this tool did not have it. It printed
"the fleet is acting on text no ref carries" about the interpreter section while
THREE COMMITS on branch `pr1136` carried it. The claim was false and the remedy
was wrong: "commit your work" is useless advice to someone whose work is
committed and waiting on review, and it sends a reviewer looking for unsaved
edits that do not exist.

★ The discriminator is free: `git log <ref>..HEAD -- <path>` non-empty means a
branch carries it. Name the branch. "CLAUDE.md's interpreter section is on
pr1136 and not on main" is actionable; "no ref carries it" is not, and it was
not true.

⛔ NEITHER IS AN ERROR BY ITSELF. Work in progress is normal. The finding is that
nothing SAYS which of the two you are in, and the file gives no sign — this prints
the difference so the reader knows which doctrine they are holding.

⚠ BOUND, stated: this reads ONE checkout. Another agent on another machine reads a
different working copy, and a clean report here says nothing about theirs.

Run: python3 tools/doctrine-uncommitted.py --repo-path ~/code/DigitalFrontier-infra
"""
import argparse, os, subprocess, sys

DEFAULT_PATHS = ["CLAUDE.md", "AGENTS.md", "goals/RESERVED-ACTIONS.md",
                 "prompts/README.md", ".github/copilot-instructions.md"]


def git(repo, *args):
    """stdout, or None — a failed command is never an empty answer."""
    try:
        r = subprocess.run(["git", "-C", repo, *args],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def state(repo):
    """The checkout's own situation — it is the EXPLANATION for any drift below."""
    br = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    merging = os.path.exists(os.path.join(repo, ".git", "MERGE_HEAD"))
    staged = git(repo, "diff", "--cached", "--name-only")
    return {"branch": (br or "?").strip(),
            "merging": merging,
            "staged": len([l for l in (staged or "").splitlines() if l.strip()])}


def on_head(repo, path, lines):
    """Which of `lines` a commit on the CURRENT BRANCH already carries.

    ⛔ THE STATE THE FIRST VERSION OF THIS TOOL MISSED. Working-copy text that the
    comparison ref lacks is NOT automatically uncommitted — a branch may carry it,
    which is what every open docs PR looks like from the working copy."""
    head = git(repo, "show", f"HEAD:{path}")
    if head is None:
        return set()
    hs = set(head.splitlines())
    return {l for l in lines if l in hs}


def branch_commits(repo, path, ref):
    """The commits between `ref` and HEAD that touched `path` — the evidence that
    a branch carries the text, and the thing a reviewer needs in order to act."""
    out = git(repo, "log", "--oneline", f"{ref}..HEAD", "--", path)
    return [l for l in (out or "").splitlines() if l.strip()]


def compare(repo, path, ref):
    """(read_only_lines, committed_only_lines) or None if either side is unreadable."""
    disk = os.path.join(repo, path)
    if not os.path.exists(disk):
        return None
    try:
        with open(disk, errors="replace") as fh:
            working = fh.read().splitlines()
    except OSError:
        return None
    committed = git(repo, "show", f"{ref}:{path}")
    if committed is None:
        # ⛔ NOT the same as "identical". A path absent from the ref means the whole
        # file is read-but-not-committed, which is the strongest form of this finding.
        return (working, [])
    c = committed.splitlines()
    cs, ws = set(c), set(working)
    return ([l for l in working if l.strip() and l not in cs],
            [l for l in c if l.strip() and l not in ws])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-path", default=".")
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--path", action="append", default=[],
                    help="doctrine file to check; repeatable. Defaults to the known set.")
    ap.add_argument("--show", type=int, default=6)
    a = ap.parse_args()

    repo = os.path.expanduser(a.repo_path)
    if git(repo, "rev-parse", "--git-dir") is None:
        print(f"⛔ ESTABLISHED NOTHING — {repo} is not a git checkout, so there is no "
              f"committed side to compare against. A missing repo and a clean one "
              f"print the same empty table.")
        return 2
    if git(repo, "rev-parse", "--verify", a.ref) is None:
        print(f"⛔ ESTABLISHED NOTHING — {a.ref} does not resolve in {repo}. Every file "
              f"would read as entirely uncommitted, which is a verdict about the REF.")
        return 2

    st = state(repo)
    paths = a.path or DEFAULT_PATHS
    checked, findings, absent = 0, [], []
    for p in paths:
        got = compare(repo, p, a.ref)
        if got is None:
            absent.append(p)
            continue
        checked += 1
        read_only, committed_only = got
        # ⛔ SPLIT read_only BY WHETHER A BRANCH ALREADY CARRIES IT. Without this the
        # tool asserts "no ref carries it" about an open PR's committed content, which
        # is false AND routes the reader to the wrong remedy.
        carried = on_head(repo, p, read_only)
        uncommitted = [l for l in read_only if l not in carried]
        on_branch = [l for l in read_only if l in carried]
        commits = branch_commits(repo, p, a.ref) if on_branch else []
        if read_only or committed_only:
            findings.append((p, uncommitted, on_branch, commits, committed_only))

    if not checked:
        print(f"⛔ ESTABLISHED NOTHING — none of {len(paths)} doctrine path(s) exist in "
              f"{repo}. Zero drift and zero files print the same clean result.")
        return 2

    print(f"── DOCTRINE vs {a.ref} ── {checked} file(s) read"
          + (f", {len(absent)} absent" if absent else ""))
    print(f"  checkout: branch {st['branch']}"
          + ("  ⛔ MERGE IN PROGRESS" if st["merging"] else "")
          + (f"  ·  {st['staged']} file(s) staged" if st["staged"] else ""))
    if st["merging"] or st["staged"]:
        print("  ⇒ that state is the EXPLANATION for anything below, not a separate problem.")

    if not findings:
        print(f"\n  every checked file matches {a.ref} exactly — "
              f"what the fleet reads is what landed.")
    for p, unc, onbr, commits, co in findings:
        print(f"\n  {p}")
        if unc:
            print(f"    ⛔ {len(unc)} line(s) READ BUT NOT COMMITTED — no ref carries "
                  f"them\n       ⇒ remedy: commit")
            for l in unc[:a.show]:
                print(f"        + {l.strip()[:96]}")
            if len(unc) > a.show:
                print(f"        … {len(unc) - a.show} more (--show)")
        if onbr:
            print(f"    ⚠ {len(onbr)} line(s) READ, COMMITTED ON {st['branch']}, NOT ON "
                  f"{a.ref}\n       ⇒ remedy: LAND THE PR — this is what an open docs PR "
                  f"looks like from here.\n       ⇒ NOT uncommitted: telling a reviewer to "
                  f"'commit your work' sends them after edits that do not exist.")
            for c in commits[:a.show]:
                print(f"        · {c[:96]}")
            for l in onbr[:2]:
                print(f"        ~ {l.strip()[:96]}")
        if co:
            print(f"    ⚠ {len(co)} line(s) COMMITTED BUT NOT READ — this checkout HIDES "
                  f"landed doctrine")
            for l in co[:a.show]:
                print(f"        - {l.strip()[:96]}")
            if len(co) > a.show:
                print(f"        … {len(co) - a.show} more (--show)")

    print(f"\n⚠ ONE CHECKOUT ONLY. Another agent on another machine reads a different "
          f"working copy;\n   a clean report here says nothing about theirs.")
    print("⚠ NONE of the three states is an error by itself — work in progress is normal, "
          "and an\n   open docs PR is SUPPOSED to be on a branch and not on main. The finding "
          "is that\n   nothing otherwise SAYS which of the three you are holding, and they "
          "have different\n   remedies and different owners.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
