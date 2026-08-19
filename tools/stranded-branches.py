#!/usr/bin/env python3
"""Commits on a merged PR's branch with no equivalent change upstream.

⛔ THE WORD "STRANDED" IS A VERDICT AND THIS TOOL DOES NOT EARN IT. An earlier
version reported three refs as stranded. All three were false alarms: the work had
landed, and an orchestrator was one step from telling the operator that a commit was
outstanding before a relaunch. SHA-reachability is the right predicate for the
founding case — a branch quietly advancing past its merged PR — and the WRONG one
after a recovery-by-recommit, where the original sha stays unreachable forever.

⇒ After a rewrite the commits are the same WORK and not the same OBJECTS. So this
reports STATES, not loss:

    EQUIVALENT-UPSTREAM  `git cherry` found an equivalent patch id on main. Landed.
    NO-UPSTREAM-MATCH    unreachable AND no patch-equivalent found. ⛔ NOT "lost" —
                         work recovered by recommit-WITH-EDITS reads this way too.
    UNREADABLE           the comparison could not be made. Not a pass.

⚠ The error direction matters more here than usual. A false "lost" makes a reader
re-do work that already exists, and the second copy is a fresh conflict — worse than
silence, for a tool whose entire subject is duplicated effort.

⛔ THE TWO STATES ARE NOT SYMMETRIC, AND THE ASYMMETRY IS THE WHOLE READING RULE:

    EQUIVALENT-UPSTREAM  PROVES the work landed.
    NO-UPSTREAM-MATCH    PROVES NOTHING EITHER WAY.

★ THE STANDING EXAMPLE IS THIS FILE. `devops/stranded-branches@8a9251a` reads
NO-UPSTREAM-MATCH and will do so indefinitely, for a change that is demonstrably on
main — it is the commit that added `git cherry` to this very tool.

Why, measured rather than assumed:

    8a9251a  patch-id 409ec00b3297   cut before main gained an unrelated PR
    1e13e59  patch-id 7b73ec65dc31   the same work, cherry-picked onto the moved base
             tools/README.md 2 +-  vs  3 +-   — the adapted diff is ONE LINE different

⇒ A CHERRY-PICK ONTO A MOVED BASE DOES NOT PRESERVE THE PATCH ID. "Cherry-pick, not
a rewrite" is true of the OPERATION and false of the RESULT once the base has moved.
The predicate answered its question correctly: there is no equivalent patch upstream,
because the patch was adapted.

⇒ So a reader who sees this tool's own name in a NO-UPSTREAM-MATCH row must NOT
conclude the fix never landed. That is exactly the misreading the bucket rename was
for, one level in — and it was predicted the other way round: the author expected the
row to flip on merge and said that a non-flip would mean the `git cherry` path was
broken. The path was sound and the prediction was wrong.


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
    found, checked, deleted, unfetched = [], 0, [], []
    for ref, prs in sorted(by_ref.items()):
        remote = f"origin/{ref}"
        rc, sha, _ = sh("git", "rev-parse", "--short", remote)
        if rc != 0:
            # ⛔ NOT one state. "Deleted on merge" is the good case; "exists on
            # origin but not in this clone" is a FETCH GAP, and the two are
            # indistinguishable from a failed rev-parse. Conflating them
            # under-reports toward "nothing is stranded" — the flattering
            # direction — inside the detector for work going unnoticed. That is
            # a silently shrinking population, which is the defect this family
            # of tools exists to refuse.
            _, ls, _ = sh("git", "ls-remote", "--heads", "origin", ref)
            (unfetched if ls.strip() else deleted).append(ref)
            continue
        checked += 1
        # ⛔ SHA-reachability alone is the WRONG predicate after a
        # recovery-by-recommit: the original sha stays unreachable forever, so the
        # tool emits a permanent false positive on precisely the work someone
        # already rescued. `git cherry` compares PATCH IDS against the merge base
        # and marks "-" when an equivalent change is already upstream.
        rc, out, _ = sh("git", "cherry", BASE, remote)
        if rc != 0:
            found.append((ref, sha, None, None, prs))   # unreadable is not zero
            continue
        marks = [ln[:1] for ln in out.splitlines() if ln[:1] in "+-"]
        if not marks:
            continue                                    # nothing ahead: the good case
        unmatched = marks.count("+")
        found.append((ref, sha, len(marks), unmatched, prs))
    return found, checked, deleted, unfetched


def by_ref_count(rows):
    return {r["headRefName"] for r in rows}


def verdict(count_by_ref):
    """The predicate alone, so it carries controls that survive the fix.

    ⛔ Deliberately NOT keyed on a live branch. #26 instance 3: a control propped up
    by a defect queued for repair stops being a control the moment the defect is
    fixed. `dev2/role-ready-consumer` is a real known-positive today and will not be
    one tomorrow, so it is not the fixture.
    """
    return sorted(ref for ref, n in count_by_ref.items() if n is None or n > 0)


# ⇒ Three fixture tiers, not two. LIVE-REAL decays: both stranded branches this
# tool was built for read zero within the hour. SYNTHETIC comes from the author's
# model and can only confirm it. CAPTURED-REAL is an observation taken from the
# world and frozen — the row below was actually read on 2026-08-19 before the ref
# moved. It does not decay, and because the predicate takes counts rather than
# objects it does not depend on any SHA surviving `git gc`.
CAPTURED = {"dev4/instruction-precedence": 1}   # observed at f5e71bb, merged PR #32
# ⚠ And the world later supplied its ANSWER: that row was a FALSE POSITIVE. `git
# cherry` marks it "-", an equivalent patch is on main, and the work had landed via
# #46. A captured-real fixture whose correct verdict is known is stronger than one
# that only records what was seen — it controls the predicate, not just the parser.


def self_test():
    cap = verdict(dict(CAPTURED))
    print(f"  captured-real   observed row  : {cap}   (read from the world 2026-08-19)")
    pos = verdict({"a/merged-clean": 0, "b/stranded": 3})
    neg = verdict({"a/merged-clean": 0, "c/also-clean": 0})
    unk = verdict({"d/unreadable": None})
    print(f"  known-positive  stranded ref   : {pos}")
    print(f"  known-negative  all merged     : {neg}")
    print(f"  known-positive  unreadable ref : {unk}   (unreadable is not zero)")
    ok = (pos == ["b/stranded"] and neg == [] and unk == ["d/unreadable"]
          and cap == ["dev4/instruction-precedence"])
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
    found, checked, deleted, unfetched = stranded(rows)
    if unfetched:
        print(f"⛔ {len(unfetched)} merged-PR ref(s) exist on origin but not in this clone: "
              f"{', '.join(unfetched)} — a fetch or prune failure. Those refs were NOT examined, "
              "so this run ESTABLISHED NOTHING about them and must not be read as clean.",
              file=sys.stderr)
        return 2
    if checked == 0:
        print(f"⛔ {len(rows)} merged PRs, but NOT ONE of their refs still exists locally — "
              "ESTABLISHED NOTHING. Expected at least one surviving ref; a fetch or prune "
              "failure looks exactly like a tidy repository.", file=sys.stderr)
        return 2
    for ref, sha, cnt, unmatched, prs in found:
        if cnt is None:
            state, n = "UNREADABLE", "-"
        elif unmatched == 0:
            # Every commit has a patch-equivalent upstream. The sha is unreachable
            # and the WORK landed. Reported, never called stranded.
            state, n = "EQUIVALENT-UPSTREAM", f"{cnt} commit(s)"
        else:
            state, n = "NO-UPSTREAM-MATCH", f"{unmatched} of {cnt} commit(s)"
        print(f"{state:<20} {ref}@{sha}  {n}   (merged PR"
              f"{'s' if len(prs) > 1 else ''} {', '.join('#%d' % p for p in prs)})")
    # ⚠ Every ref accounted for, in named buckets. A denominator that silently
    # excludes part of its population is how "0 stranded" gets believed.
    unmatched_refs = [f for f in found if f[3] not in (0,) ]
    print(f"\n{len(unmatched_refs)} ref(s) with no upstream patch-match, of {checked} examined; "
          f"{len(deleted)} ref(s) deleted on merge (nothing to examine); "
          f"{checked + len(deleted)} of {len(by_ref_count(rows))} merged-PR refs accounted for.",
          file=sys.stderr)
    print("⛔ THE STATES ARE ASYMMETRIC: EQUIVALENT-UPSTREAM proves the work landed; "
          "NO-UPSTREAM-MATCH proves NOTHING either way. This tool's own row "
          "(devops/stranded-branches) is the standing example — it reads NO-UPSTREAM-MATCH "
          "for a change that is on main, because a cherry-pick onto a moved base does not "
          "preserve the patch id.", file=sys.stderr)
    print("⛔ NO-UPSTREAM-MATCH IS NOT 'LOST'. It means the sha is unreachable from "
          f"{BASE} AND no commit upstream has an equivalent patch id. Work recovered by "
          "recommit-with-edits legitimately reads this way, because after a rewrite the "
          "commits are the same WORK and not the same OBJECTS. ⚠ The error direction "
          "matters here more than usual: a false 'lost' makes a reader re-do work that "
          "already exists, and the second copy is a fresh conflict — worse than silence "
          "for a tool whose subject is duplicated effort.", file=sys.stderr)
    print("⚠ Each row is stamped with the ref's object id AT MEASUREMENT TIME. Refs move — "
          "three observers of one ref disagreed within an hour, none of them wrong. A count "
          "without its sha is not comparable to the same count from another run.",
          file=sys.stderr)
    return 1 if unmatched_refs else 0


if __name__ == "__main__":
    sys.exit(main())
