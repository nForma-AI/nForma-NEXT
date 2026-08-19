#!/usr/bin/env python3
"""Work left on a branch after its PR merged — commits that are on the ref and not on main.

⛔ THE INCIDENT. A sweep across every merged PR with a surviving ref found 2 of 15
stranded, in two roles, with no contact between them. One ref had been REPOINTED
after its PR merged, so the same branch name carried both merged and unmerged work.
Nothing lost — both are now on follow-up PRs *because the sweep ran* — but nothing
would have run it.

★ WHY THIS IS A TOOL AND NOT A DOCTRINE LINE, and the measurement is better than
the argument. Three observers measured the same ref within an hour and got three
different values, none of them wrong when taken:

    sweep, first pass   3 commits ahead
    a reviewer          branch 749 lines
    sweep, minutes later 4 commits ahead, 755 lines

The ref moved between measurements, INSIDE a thread about refs moving, among agents
who had just finished diagnosing that class. A doctrine line saying "remember the
branch may have moved" depends on exactly the attention that failed for three of
them at once.

⇒ So every row here is stamped with the ref's object id AT MEASUREMENT TIME. A row
without its sha is not comparable to the same row from another run, and reporting a
count alone is what made three honest observers disagree.

⚠ The mechanism already existed — `git for-each-ref` plus `git rev-list --count` —
and had no reader. That is `fleet-state.py`'s shape one layer over: a signal
demanded with no consumer built. What was missing was never the commands.

Exit: 0 clean · 1 stranded refs found · 2 ESTABLISHED NOTHING.

⛔ Exit 2 matters more here than usual. If the ref listing breaks — renamed remote,
auth failure, `gh` returning an empty array on a swallowed error — a naive version
reports "0 stranded" and exits 0. That is absence read as success, inside a check
written to catch absence read as success.
"""
import json, subprocess, sys

BASE = "origin/main"


def sh(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    return (r.returncode, r.stdout.strip(), r.stderr.strip())


def merged_refs():
    """Branch names of merged PRs. Returns None on ANY failure — never [].

    ⚠ [] and "the query failed" must not share a representation. A caller that
    cannot tell them apart will report a clean fleet when gh is broken.
    """
    rc, out, err = sh("gh", "pr", "list", "--state", "merged", "--limit", "100",
                      "--json", "number,headRefName")
    if rc != 0 or not out:
        return None, err or "gh returned nothing"
    try:
        rows = json.loads(out)
    except ValueError as exc:
        return None, f"unparseable gh output: {exc}"
    return rows, None


def stranded(rows):
    """(ref, sha, count, prs) for every merged-PR ref that still has unmerged commits.

    Pure enough to control: takes the PR rows, asks git per ref, returns rows.
    """
    by_ref = {}
    for r in rows:
        by_ref.setdefault(r["headRefName"], []).append(r["number"])
    found, checked = [], 0
    for ref, prs in sorted(by_ref.items()):
        remote = f"origin/{ref}"
        rc, sha, _ = sh("git", "rev-parse", "--short", remote)
        if rc != 0:
            continue                      # ref deleted on merge: the good case
        checked += 1
        rc, cnt, _ = sh("git", "rev-list", "--count", f"{BASE}..{remote}")
        if rc != 0:
            found.append((ref, sha, None, prs))   # unreadable is not zero
            continue
        if int(cnt) > 0:
            found.append((ref, sha, int(cnt), prs))
    return found, checked


def verdict(count_by_ref):
    """The predicate alone, so it carries controls that survive the fix.

    ⛔ Deliberately NOT keyed on a live branch. #26 instance 3: a control propped up
    by a defect queued for repair stops being a control the moment the defect is
    fixed. `dev2/role-ready-consumer` is a real known-positive today and will not be
    one tomorrow, so it is not the fixture.
    """
    return sorted(ref for ref, n in count_by_ref.items() if n is None or n > 0)


def self_test():
    pos = verdict({"a/merged-clean": 0, "b/stranded": 3})
    neg = verdict({"a/merged-clean": 0, "c/also-clean": 0})
    unk = verdict({"d/unreadable": None})
    print(f"  known-positive  stranded ref   : {pos}")
    print(f"  known-negative  all merged     : {neg}")
    print(f"  known-positive  unreadable ref : {unk}   (unreadable is not zero)")
    ok = (pos == ["b/stranded"] and neg == [] and unk == ["d/unreadable"])
    print("  ✅ discriminated" if ok else "  ⛔ FAILED to discriminate", file=sys.stderr)
    return 0 if ok else 2


def main():
    if "--self-test" in sys.argv:
        return self_test()
    sh("git", "fetch", "-q", "--prune", "origin")
    rows, err = merged_refs()
    if rows is None:
        print(f"⛔ could not enumerate merged PRs ({err}) — ESTABLISHED NOTHING, not clean.",
              file=sys.stderr)
        return 2
    if not rows:
        print("⛔ zero merged PRs enumerated — ESTABLISHED NOTHING, not clean. "
              "A repo with merged PRs returning an empty list is a broken query, "
              "not a tidy history.", file=sys.stderr)
        return 2
    found, checked = stranded(rows)
    if checked == 0:
        print(f"⛔ {len(rows)} merged PRs, but NOT ONE of their refs still exists locally — "
              "ESTABLISHED NOTHING. Expected at least one surviving ref; a fetch or prune "
              "failure looks exactly like a tidy repository.", file=sys.stderr)
        return 2
    for ref, sha, cnt, prs in found:
        n = "UNREADABLE" if cnt is None else f"{cnt} commit(s)"
        print(f"{ref}@{sha}  {n} not on {BASE}   (merged PR{'s' if len(prs) > 1 else ''} "
              f"{', '.join('#%d' % p for p in prs)})")
    print(f"\n{len(found)} stranded of {checked} surviving merged-PR ref(s).", file=sys.stderr)
    print("⚠ Each row is stamped with the ref's object id AT MEASUREMENT TIME. Refs move — "
          "three observers of one ref disagreed within an hour, none of them wrong. A count "
          "without its sha is not comparable to the same count from another run.",
          file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
