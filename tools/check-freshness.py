#!/usr/bin/env python3
"""A red check is evidence about the MOMENT IT RAN, not about now.

⛔ MEASURED 2026-08-20 on a board of 56 open PRs, 49 failing a required context:

    46 failing required checks
       37  completed BEFORE the resource recovered   <- STALE EVIDENCE
        9  completed AFTER it                        <- REAL

⇒ **80% of the board's red was a measurement taken under conditions that no longer
held.** The fleet spent hours treating it as 49 defects.

★ AND BASE FRESHNESS DOES NOT DETECT THIS. Measured the same day: PRs zero commits
behind main failed required checks at 88%, stale ones at 86% -- indistinguishable.
A PR can sit exactly on main's tip while its checks are four hours old. Three
different quantities that all sound like "is this PR current":

    head commit date    when the author last pushed
    merge-base distance how far the BASE is behind main
    check completedAt   when the EVIDENCE was produced   <- the one that mattered

⛔ AND EVERY `first:N` WINDOW IS A SILENT TRUNCATION UNTIL YOU COMPARE IT TO
`totalCount`. Both windows in the query below were unchecked. Measured 2026-08-21
on Borduas-Holdings/Blazing-Back:

    branchProtectionRules(first:5)   totalCount 1     -- 5x headroom
    contexts(first:100)              totalCount 56-57 -- HALF the window, already

⇒ Neither binds today, so nothing was wrong. But 57 of 100 is not margin: this
board is one CI expansion away from silently dropping contexts out of the
freshness verdict, and NOTHING would have said so. `totalCount` sits in the same
response as the `nodes` window, which makes not reading it inexcusable rather
than merely unlucky.

★ The truncation is worse HERE than in most tools, because `branchProtectionRules`
decides WHICH contexts count as required. A dropped rule does not shrink the
answer -- it silently redefines the question, and the output looks identical.

⚠ THE BOUNDARY IS NOT GUESSABLE and this tool does not guess it. `--since` is
REQUIRED: the caller states when the condition changed -- a funding floor crossed,
a runner pool restored, a fix landed -- because only they know what changed. A
default would manufacture a verdict from an arbitrary clock.

⛔ AND IT DOES NOT SAY A STALE RED IS A PASS. It says the evidence predates the
change and cannot speak to now. Re-running is what produces current evidence;
this only refuses to let old evidence pose as it.
"""

# NO-SELF-TEST: controlled by tools/test_check_freshness.py, which the CI glob gates and which
# passes on main — 28 controls, counted by AST (ast.Call to `check`), measured
# 2026-09-06 at origin/main by `python3 tools/test_check_freshness.py` exit 0 in the gating job. ⛔ This is a DECLARATION of where the control lives,
# not a claim that none exists — tools/README.md records two control conventions in
# one directory (`--self-test` and `test_*.py`).
#
# ⚠ WHY THIS TOOL HAS NO `--self-test`: a completedAt boundary is pure arithmetic, so the controls drive classify() with
# synthetic instants and need no forge.
# ⛔ THIS DECLARATION DOES NOT CHANGE THE GATE'S VERDICT, AND SAYING SO IS THE POINT.
# This tool takes REQUIRED ARGUMENTS, so it reaches the cannot-invoke-bare branch at
# gate-selftests.sh:272, which returns before `DECLARES_NONE` is consulted at :340.
# Measured 2026-09-06, two-poled: with this line present and with it renamed, the gate
# emits IDENTICAL BYTES and this tool REMAINS UNESTABLISHED.
# ⇒ So: an external control EXISTS and is gated; the gate cannot SEE it. Those are
# two different facts and a reader must not infer the second from the first.
# The mismatch — the gate names this line as the remedy on a path that ignores it —
# is nForma-AI/nForma-NEXT#603, not this file's to fix.
import argparse, json, subprocess, sys
from datetime import datetime, timezone

CURRENT, STALE, UNDATED = "CURRENT", "STALE", "UNDATED"

QUERY = """
query($owner:String!, $name:String!, $n:Int!) {
  repository(owner:$owner, name:$name) {
    branchProtectionRules(first:5){totalCount nodes{pattern requiredStatusCheckContexts}}
    pullRequests(states:OPEN, first:$n, orderBy:{field:UPDATED_AT, direction:DESC}) {
      nodes { number title
        commits(last:1){nodes{commit{statusCheckRollup{contexts(first:100){totalCount nodes{
          __typename
          ... on CheckRun { name conclusion completedAt }
          ... on StatusContext { context state createdAt } }}}}}} } } } }
"""


def fetch(owner, name, n):
    """The board, or None — a failed query is never an empty board."""
    try:
        r = subprocess.run(
            ["gh", "api", "graphql", "-f", "query=" + QUERY,
             "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"n={n}"],
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)["data"]["repository"]
    except (ValueError, KeyError, TypeError):
        return None


def classify(completed_at, since):
    """CURRENT · STALE · UNDATED — three states, because a missing date is not old."""
    if not completed_at:
        return UNDATED
    try:
        t = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError:
        return UNDATED
    return CURRENT if t >= since else STALE


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--since", required=True,
                    help="ISO instant the condition CHANGED, e.g. 2026-08-20T22:00:00Z. "
                         "Required on purpose — only the caller knows what changed.")
    ap.add_argument("--limit", type=int, default=60)
    a = ap.parse_args()

    try:
        since = datetime.fromisoformat(a.since.replace("Z", "+00:00"))
    except ValueError:
        print(f"⛔ --since is not an ISO instant: {a.since!r}")
        return 2
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)

    owner, _, name = a.repo.partition("/")
    d = fetch(owner, name, a.limit)
    if d is None:
        print("⛔ ESTABLISHED NOTHING — the query failed. A failed query and a green "
              "board print the same empty table.")
        return 2

    # ⛔ SATURATION FIRST, BEFORE ANY VERDICT. A `first:N` window is a silent
    # truncation until compared to totalCount, and the branch-protection one is the
    # dangerous half: dropping a rule does not shrink the answer, it redefines which
    # contexts are "required" — and the output looks identical either way.
    bp = d["branchProtectionRules"]
    if bp["totalCount"] > len(bp["nodes"]):
        print(f"⛔ ESTABLISHED NOTHING — {bp['totalCount']} branch protection rule(s) "
              f"exist and the query read {len(bp['nodes'])}. The required set is "
              f"INCOMPLETE, so every verdict below would be about the wrong question, "
              f"not merely about fewer PRs.")
        return 2

    req = set()
    for r in d["branchProtectionRules"]["nodes"]:
        if r["pattern"] in ("main", "master"):
            req |= set(r.get("requiredStatusCheckContexts") or [])
    if not req:
        print("⛔ ESTABLISHED NOTHING — no required contexts found on main. Every check "
              "would count as optional, which is a verdict about the QUERY, not the board.")
        return 2

    truncated_prs = []
    buckets = {CURRENT: [], STALE: [], UNDATED: []}
    prs = d["pullRequests"]["nodes"]
    for p in prs:
        cm = p["commits"]["nodes"]
        if not cm or not cm[0]["commit"]["statusCheckRollup"]:
            continue
        ctx_conn = cm[0]["commit"]["statusCheckRollup"]["contexts"]
        if ctx_conn["totalCount"] > len(ctx_conn["nodes"]):
            # ⚠ NOT fatal, unlike the rules above: a dropped CONTEXT loses rows from
            # one PR's verdict, it does not change what "required" means. But it must
            # be named — a missing red check reads as a green PR.
            truncated_prs.append((p["number"], ctx_conn["totalCount"], len(ctx_conn["nodes"])))
        for c in ctx_conn["nodes"]:
            if c["__typename"] == "CheckRun":
                nm, st, when = c.get("name"), c.get("conclusion"), c.get("completedAt")
            else:
                nm, st, when = c.get("context"), c.get("state"), c.get("createdAt")
            if nm not in req or st not in ("FAILURE", "ERROR"):
                continue
            buckets[classify(when, since)].append((p["number"], nm, when))

    total = sum(len(v) for v in buckets.values())
    # ⇒ printed on success too: a line that appears only on failure is one nobody
    # has ever seen working, and its absence then reads as "fine".
    if truncated_prs:
        print(f"  ⛔ {len(truncated_prs)} PR(s) had MORE contexts than the window read: "
              + " · ".join(f"#{n} {t}>{g}" for n, t, g in truncated_prs[:6]))
        print("     ⇒ a missing red check reads as a green PR. Counts below are LOWER bounds.")
    else:
        print(f"  windows: {bp['totalCount']}/5 protection rule(s), "
              f"all context lists within the 100 read — no truncation")
    print(f"── {len(prs)} open PR(s) · {len(req)} required context(s) · "
          f"condition changed {a.since}")
    if not total:
        print("\n  no failing required checks — and that is a real reading only because "
              "the query returned a board and a required set.")
        return 0
    print(f"\n  {total} failing required check(s):")
    for k in (CURRENT, STALE, UNDATED):
        print(f"    {len(buckets[k]):4d}  {k}")
    print(f"\n  ⛔ STALE means the check completed BEFORE {a.since} — it is evidence "
          f"about\n     conditions that no longer hold. It does NOT mean the PR passes.")
    print("  ⚠ UNDATED is not old. A check with no completion time has not been dated,\n"
          "     and guessing would be the defect this tool exists to prevent.")

    if buckets[CURRENT]:
        print(f"\n  ── CURRENT — the only reds that are evidence about now ──")
        for n, nm, when in sorted(buckets[CURRENT]):
            print(f"    #{n:<6} {nm:34s} {when}")
    share = 100 * len(buckets[STALE]) // total
    if share >= 50:
        print(f"\n  ⇒ {share}% of the board's red predates the change. Diagnosing it "
              f"would be\n     diagnosing a world that ended at {a.since}. RE-RUN "
              "produces evidence; reading does not.")
    return 1 if buckets[CURRENT] else 0


if __name__ == "__main__":
    sys.exit(main())
