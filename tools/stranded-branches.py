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
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runmarker import guard, result  # noqa: E402

import json, subprocess, sys
from collections import Counter

BASE = "origin/main"


def sh(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    return (r.returncode, r.stdout.strip(), r.stderr.strip())


DEFAULT_LIMIT = 1000


def merged_refs(limit=DEFAULT_LIMIT):
    """Branch names of merged PRs. Returns (rows, err, truncated) — never bare [].

    ⚠ [] and "the query failed" must not share a representation. A caller that
    cannot tell them apart will report a clean fleet when gh is broken.

    ⛔ AND NEITHER MUST "complete" AND "TRUNCATED", which is the state this function
    was missing. It asked for `--limit 100`, and `gh` answers a request for more
    than exists with everything, and a request for less with a silent prefix.
    Measured 2026-08-20:

        nForma-AI/nForma-NEXT       69 merged   ->  69 seen
        Digital-Frontier-LDA/df-wiki 178 merged  -> 100 seen
        Borduas-Holdings/Blazing-Back 775 merged -> 100 seen

    ⇒ On the repository with the actual branch churn the sweep inspected **13% of
    the population** and reported `0 stranded, exit 0` about the rest. That is the
    failure this file's own docstring says exit 2 exists to prevent — absence read
    as success, inside a check written to catch absence read as success. It guarded
    the ERROR path and left the TRUNCATION path open.

    ⚠ The truncation test is `len(rows) == limit`, deliberately local: it needs no
    second API call and cannot itself be rate-limited or return a stale count.
    """
    rc, out, err = sh("gh", "pr", "list", "--state", "merged", "--limit", str(limit),
                      "--json", "number,headRefName")
    if rc != 0 or not out:
        return None, err or "gh returned nothing", False
    try:
        rows = json.loads(out)
    except ValueError as exc:
        return None, f"unparseable gh output: {exc}", False
    return rows, None, len(rows) >= limit


def blob_at(rev, path):
    """Blob oid of `path` at `rev`, or None when the path is absent there.

    ⚠ None is a real value here, not a failure: absent-at-both-ends is EQUAL, which
    is how a landed DELETION reads. Collapsing None into "unreadable" would make
    every merged deletion look unlanded forever.
    """
    rc, out, _ = sh("git", "rev-parse", f"{rev}:{path}")
    return out if rc == 0 else None


def touched_paths(shas):
    """Union of paths the given commits changed. Empty set means ESTABLISHED NOTHING."""
    paths = set()
    for sha in shas:
        rc, out, _ = sh("git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha)
        if rc != 0:
            return set()            # one unreadable commit voids the whole union
        paths.update(ln for ln in out.splitlines() if ln)
    return paths


def content_upstream(remote, shas):
    """True when every path those commits touched is byte-identical at BASE.

    ⇒ This establishes LANDEDNESS, never AUTHORSHIP. If BASE and the branch hold the
    same bytes the work is not lost, whoever put them there. Direction stays outside
    what this tool can claim, exactly as the report footer says.

    ⛔ The empty path set must return False, not True. "Every element of {} matches"
    is vacuously true, and a state that reports CONTENT-UPSTREAM after examining zero
    paths is the empty-population false pass this repository keeps re-learning: a
    control whose silence is indistinguishable from its success.
    """
    same, total, _ = path_agreement(remote, shas)
    return total > 0 and same == total


def content_state(unmatched, same, tot, held=0):
    """LANDED · UNRESOLVED · N/A, from counts alone — no repository required.

    ⛔ tot == 0 is UNRESOLVED, never LANDED. "Every path matched" over zero paths is
    vacuously true, and it is the whole reason this lives in its own pure function:
    the empty-population false pass is invisible inside a generator expression and
    obvious in a table of counts.
    """
    if not unmatched:
        return "N/A"
    if tot == 0:
        return "UNRESOLVED"
    if same == tot:
        return "LANDED"                       # byte-identical: conclusive
    # ⇒ Weaker and separately named ON PURPOSE. Every line is upstream with multiplicity,
    # but a file of boilerplate satisfies that without its work landing. A reader must be
    # able to tell which evidence they have.
    if held == tot:
        return "LANDED-BY-LINES"
    return "UNRESOLVED"


def line_contained(remote, base, path):
    """Is every line of `remote:path`, with multiplicity, present in `base:path`?

    ⇒ ARCHITECT's primitive, and it answers the question byte-identity cannot:
    *is this content upstream* — WITHOUT a patch id, without a case rule, and without
    caring how the merge was performed. **Immune to squash by construction**, which is the
    exact limitation the NO-UPSTREAM-MATCH row carries.

    ⚠ WEAKER THAN BYTE-IDENTITY AND REPORTED SEPARATELY. Byte-identity is conclusive.
    Containment is not: a file whose lines ALL recur elsewhere in `base` — boilerplate,
    blanks, closing braces — reads contained without its work having landed. Measured
    known-negatives: a single unique line -> False; three copies of a line `base` holds
    once -> False (Counter compares COUNTS, not membership); an all-blank file -> True,
    and that last one is the limitation, not a bug.
    """
    b, m = blob_at(remote, path), blob_at(base, path)
    if b is None and m is None:
        return True                                   # deleted both ends
    if b is None or m is None:
        return False
    rc1, bt, _ = sh("git", "show", "%s:./%s" % (remote, path))
    rc2, mt, _ = sh("git", "show", "%s:./%s" % (base, path))
    if rc1 != 0 or rc2 != 0:
        return False
    return lines_contained(bt, mt)


def lines_contained(branch_text, base_text):
    """Every line of `branch_text`, WITH MULTIPLICITY, present in `base_text`.

    ⛔ PURE, AND SEPARATE FROM THE GIT FETCH, so it can be controlled without a repository.
    The first version of this lived inline and `--self-test` PASSED when the predicate was
    mutated to `return True` — the suite controlled only the counts derived from it, so a
    broken containment leg was invisible. A control that cannot fail for the thing it
    appears to cover is the defect this tool exists to report.
    """
    cb, cm = Counter(branch_text.splitlines()), Counter(base_text.splitlines())
    return not [ln for ln, n in cb.items() if cm[ln] < n]


def path_agreement(remote, shas):
    """(paths byte-identical at BASE, paths examined). (0, 0) means established nothing.

    ⚠ Reported even when the verdict is negative, because all-or-nothing hides the
    interesting middle. A branch reading "2 of 3" is almost certainly landed and
    vetoed by one shared index file that every pane edits; a branch reading "0 of 3"
    is a different animal entirely. Collapsing both to NO-UPSTREAM-MATCH throws away
    the only signal that separates them.
    """
    paths = touched_paths(shas)
    if not paths:
        return 0, 0, 0
    same = sum(blob_at(remote, q) == blob_at(BASE, q) for q in paths)
    held = sum(line_contained(remote, BASE, q) for q in paths)
    return same, len(paths), held


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
            found.append((ref, sha, None, None, prs, (0, 0, 0)))  # unreadable is not zero
            continue
        marks = [ln[:1] for ln in out.splitlines() if ln[:1] in "+-"]
        if not marks:
            continue                                    # nothing ahead: the good case
        unmatched = marks.count("+")
        # ⇒ Patch id answered "no equivalent commit". That is not the same question as
        # "is this work upstream". Two branch commits squash-merged into ONE upstream
        # commit can never match by patch id — the diffs are different sizes — yet the
        # bytes are all there. Ask the content question before reporting an absence.
        plus = [ln[2:].strip() for ln in out.splitlines() if ln[:1] == "+"]
        agree = path_agreement(remote, plus) if unmatched else (0, 0, 0)
        found.append((ref, sha, len(marks), unmatched, prs, agree))
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
    # ⇒ The fourth state needs its own control, and the row that matters is the
    # vacuous one: zero paths examined must NOT read LANDED.
    cs = {case: content_state(*case) for case in
          [(2, 3, 3, 3), (2, 2, 3, 2), (2, 0, 0, 0), (0, 0, 0, 0), (2, 0, 3, 3), (2, 0, 3, 2)]}
    for case, got in cs.items():
        print(f"  content-state   unmatched={case[0]} bytes={case[1]}/{case[2]} "
              f"lines={case[3]}/{case[2]}: {got}")
    # ⇒ THE PREDICATE ITSELF, not only the counts derived from it. Mutating
    # lines_contained to `return True` used to leave --self-test green.
    lc = {
        "identical":            lines_contained("a\nb\n", "a\nb\n"),
        "subset (main grew)":   lines_contained("a\nb\n", "a\nb\nc\n"),
        "one unique line":      lines_contained("a\nZZ\n", "a\nb\n"),
        "3 copies vs 1":        lines_contained("x\nx\nx\n", "x\ny\n"),
        "empty branch":         lines_contained("", "a\n"),
    }
    for name, got in lc.items():
        print(f"  lines-contained {name:<20}: {got}")

    ok = (pos == ["b/stranded"] and neg == [] and unk == ["d/unreadable"]
          and cap == ["dev4/instruction-precedence"]
          and cs[(2, 3, 3, 3)] == "LANDED"            # byte-identical: conclusive
          and cs[(2, 2, 3, 2)] == "UNRESOLVED"        # partial on both legs
          and cs[(2, 0, 0, 0)] == "UNRESOLVED"        # ⛔ examined nothing is not landed
          and cs[(0, 0, 0, 0)] == "N/A"
          # ⇒ ARCHITECT's leg: bytes differ everywhere, lines all upstream -> its OWN state,
          # never silently promoted to LANDED, and never demoted to UNRESOLVED.
          and cs[(2, 0, 3, 3)] == "LANDED-BY-LINES"
          and cs[(2, 0, 3, 2)] == "UNRESOLVED"        # partial containment is not containment
          and lc["identical"] and lc["subset (main grew)"]
          and not lc["one unique line"]                # ⛔ it must be able to say NO
          and not lc["3 copies vs 1"]                  # counts, not membership
          and lc["empty branch"])                      # vacuous, and stated in the docstring
    print("  ✅ discriminated" if ok else "  ⛔ FAILED to discriminate", file=sys.stderr)
    return 0 if ok else 2


def verdict_exit(n_unmatched, truncated):
    """0 clean · 1 findings · 2 established nothing.

    ⛔ THE ASYMMETRY, applied to the POPULATION as well as to the states. A positive
    finding survives a partial sweep — a ref found stranded in the prefix is still
    stranded. A negative does not: "none found" over 13% of the population
    establishes nothing about the other 87%, and exiting 0 there is exactly the
    reading this tool exists to refuse.

    Extracted so it can be tested without a repository. The branch that matters —
    truncated AND nothing found — is the one hardest to produce against a live
    remote, which is how it shipped unwritten.
    """
    if n_unmatched:
        return 1
    return 2 if truncated else 0


KNOWN_FLAGS = {"--self-test", "--limit"}


def main():
    # ⛔ EQUALITY OVER A KNOWN SET. Membership accepts a flag without rejecting anything
    # else: `--zzz` was discarded and this tool went on to run a FULL NETWORK SWEEP,
    # answering a question nobody asked at real cost. (#321's shape; measured 2026-08-21.)
    unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in KNOWN_FLAGS]
    if unknown:
        print("⛔ unrecognised flag(s): %s. ESTABLISHED NOTHING — no sweep was run. "
              "Known flags: %s" % (", ".join(unknown), ", ".join(sorted(KNOWN_FLAGS))),
              file=sys.stderr)
        return 2
    if "--self-test" in sys.argv[1:]:
        return self_test()
    sh("git", "fetch", "-q", "--prune", "origin")
    limit = DEFAULT_LIMIT
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        if i + 1 >= len(sys.argv) or not sys.argv[i + 1].isdigit():
            print("⛔ --limit needs a positive integer", file=sys.stderr)
            return 2
        limit = int(sys.argv[i + 1])
    rows, err, truncated = merged_refs(limit)
    if rows is None:
        print(f"⛔ could not enumerate merged PRs ({err}) — ESTABLISHED NOTHING, not clean.\n"
              "   ADDABLE — FIXABLE HERE: `gh auth status`, then re-run. A gh failure and\n"
              "   a tidy repository are indistinguishable in this output without it.",
              file=sys.stderr)
        return 2
    if not rows:
        print("⛔ zero merged PRs enumerated — ESTABLISHED NOTHING, not clean. "
              "A repo with merged PRs returning an empty list is a broken query, "
              "not a tidy history.", file=sys.stderr)
        return 2
    if truncated:
        print(f"⛔ TRUNCATED SWEEP — `gh pr list` returned exactly {len(rows)} rows, the limit "
              f"asked for. There are almost certainly more merged PRs than that, and the ones "
              f"beyond it were NOT examined. Raise --limit. Every count below describes the "
              f"prefix, not the repository.", file=sys.stderr)
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
    for ref, sha, cnt, unmatched, prs, (same, tot, held) in found:
        if cnt is None:
            state, n = "UNREADABLE", "-"
        elif content_state(unmatched, same, tot, held) == "LANDED":
            # Patch ids diverged but every touched path is byte-identical at BASE.
            state, n = "CONTENT-UPSTREAM", f"{unmatched} of {cnt} commit(s), {same}/{tot} paths landed"
        elif content_state(unmatched, same, tot, held) == "LANDED-BY-LINES":
            state, n = "LINES-UPSTREAM", (f"{unmatched} of {cnt} commit(s), {held}/{tot} paths "
                                          f"line-contained (bytes differ: main moved)")
        elif unmatched == 0:
            # Every commit has a patch-equivalent upstream. The sha is unreachable
            # and the WORK landed. Reported, never called stranded.
            state, n = "EQUIVALENT-UPSTREAM", f"{cnt} commit(s)"
        else:
            agreed = f", {same}/{tot} paths already upstream" if tot else ""
            state, n = "NO-UPSTREAM-MATCH", f"{unmatched} of {cnt} commit(s){agreed}"
        print(f"{state:<20} {ref}@{sha}  {n}   (merged PR"
              f"{'s' if len(prs) > 1 else ''} {', '.join('#%d' % p for p in prs)})")
    # ⚠ Every ref accounted for, in named buckets. A denominator that silently
    # excludes part of its population is how "0 stranded" gets believed.
    # ⚠ CONTENT-UPSTREAM leaves the unmatched bucket ON PURPOSE. The footer names this
    # tool's preferred error direction — a false "lost" makes a reader re-do work that
    # already exists — and byte equality is evidence, not a guess.
    unmatched_refs = [f for f in found if f[3] not in (0,)
                      and content_state(f[3], *f[5]) not in ("LANDED", "LANDED-BY-LINES")]
    print(f"\n{len(unmatched_refs)} ref(s) with no upstream patch-match, of {checked} examined; "
          f"{len(deleted)} ref(s) deleted on merge (nothing to examine); "
          f"{checked + len(deleted)} of {len(by_ref_count(rows))} merged-PR refs accounted for.",
          file=sys.stderr)
    print("⇒ CONTENT-UPSTREAM: patch ids diverged, but every path those commits touched is "
          f"byte-identical at {BASE}, so the WORK is upstream even though the OBJECTS are not. "
          "It is what a squash-merge of two commits into one looks like. ⛔ It establishes "
          "LANDEDNESS ONLY — never authorship, never direction.", file=sys.stderr)
    print("⚠ The path ratio on a NO-UPSTREAM-MATCH row is the number worth reading. The "
          "predicate is all-or-nothing, so ONE shared index file that every pane edits "
          "(tools/README.md is the usual one) vetoes the whole ref even when the branch's "
          "own deliverables are byte-identical upstream. A row reading n-1 of n is a near "
          "certainty that the work landed; 0 of n is not. Measured 2026-08-20 at 6faec9a: "
          "of 4 refs with unmatched commits, 1 read CONTENT-UPSTREAM and 2 of the other 3 "
          "were vetoed by tools/README.md alone.", file=sys.stderr)
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
    code = verdict_exit(len(unmatched_refs), truncated)
    if code == 2:
        print("⛔ no unmatched refs IN THE PREFIX EXAMINED — and the sweep was truncated, so "
              "this ESTABLISHED NOTHING about the repository. Not clean. Raise --limit and "
              "re-run.", file=sys.stderr)
    return code


def _entry():
    """Emit the terminal state for every path this tool controls.

    guard() covers only the argparse SystemExit path, where the tool never regains
    control. Without this, a successful run emits NFORMA-RUN and no NFORMA-RESULT —
    which reads as STARTED-AND-NEVER-FINISHED, the collapse #58 exists to prevent.
    """
    rc = main()
    result({0: "OK", 1: "FINDING", 2: "ESTABLISHED-NOTHING", 3: "CONTROL-FAILED"}.get(rc, f"EXIT-{rc}"))
    return rc


if __name__ == "__main__":
    sys.exit(guard("stranded-branches", _entry))
