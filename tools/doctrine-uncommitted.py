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

⚠ AND IT CUTS BOTH WAYS, which is why this reports two directions:

  READ-NOT-COMMITTED   the fleet acts on text no ref carries. If the change is
                       abandoned, so is the reasoning built on it.
  COMMITTED-NOT-READ   a stale or dirty checkout HIDES landed doctrine. The agent
                       is reading an older world and cannot tell.

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
        if read_only or committed_only:
            findings.append((p, read_only, committed_only))

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
    for p, ro, co in findings:
        print(f"\n  {p}")
        if ro:
            print(f"    ⛔ {len(ro)} line(s) READ BUT NOT COMMITTED — the fleet is acting "
                  f"on text no ref carries")
            for l in ro[:a.show]:
                print(f"        + {l.strip()[:96]}")
            if len(ro) > a.show:
                print(f"        … {len(ro) - a.show} more (--show)")
        if co:
            print(f"    ⚠ {len(co)} line(s) COMMITTED BUT NOT READ — this checkout HIDES "
                  f"landed doctrine")
            for l in co[:a.show]:
                print(f"        - {l.strip()[:96]}")
            if len(co) > a.show:
                print(f"        … {len(co) - a.show} more (--show)")

    print(f"\n⚠ ONE CHECKOUT ONLY. Another agent on another machine reads a different "
          f"working copy;\n   a clean report here says nothing about theirs.")
    print("⚠ Neither direction is an error by itself — work in progress is normal. The "
          "finding is\n   that nothing otherwise SAYS which of the two you are holding.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
