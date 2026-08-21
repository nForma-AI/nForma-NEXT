#!/usr/bin/env python3
"""When `role:` and `dev:N` disagree about who owns an issue, which one is a pane meant to obey?

⛔ WHY THIS EXISTS — #461. Both fields are queryable, both are populated, and until 2026-08-21
nothing stated which wins. 15 open issues carried a `dev:N` alongside a `role:` that is not
`role:DEV`, and a pane running `--label dev:5` and a pane running `--label role:DEVOPS` both got an
authoritative-looking answer naming different owners.

★ THE RULE THIS ENFORCES (prompts/README.md, § "A LABEL IS NOT AN ASSIGNMENT EITHER"):

    role:X            is the QUEUE. Authoritative for routing, always.
    dev:N + role:DEV  is the ADDRESS within that queue -- DEV is the only subdivided role,
                      so role:DEV stopped being an address when DEV was split into five.
    dev:N + any other role:   is PROVENANCE. It records which pane the content came from.
                      ⚠ IT IS NOT AN ASSIGNMENT AND NO PANE SHOULD ACT ON IT.

⛔ SO A COLLISION COUNT OF ZERO IS NOT THE GOAL AND MUST NOT BE THE TARGET. #461 says so in its own
Done-when: the query can be driven to 0 by stripping labels, which destroys provenance and
reproduces the "what is mine?" gap with a clean-looking board. ⇒ This tool never reports a bare
collision count as a verdict. It reports WHICH KIND each collision is.

★ THE ONE KIND THAT IS A DEFECT is the shape that already bit on #319: a `dev:N` sitting beside a
`role:` whose queue RESERVES action from panes. A pane running its own queue query was being told
by the board to work inside an operator quarantine. That is a HAZARD; the other 14 were ambiguity.

⇒ EXIT CODES

    0  no HAZARD collisions -- provenance collisions may exist and are reported, not counted against
    1  at least one HAZARD -- a dev:N beside a reserved queue. A finding, established.
    2  ESTABLISHED NOTHING -- the forge could not be read, OR the buckets did not sum to the
       stated population (#466). ⛔ NEVER read as "all clear".

⚠ WHAT THIS TOOL CANNOT DO. It cannot tell an intentional provenance label from a mislabelling:
both render as `dev:N` on a non-DEV issue. ⇒ It reports the provenance set so a reader can look;
it does not judge it. A tool that guessed would be inventing the distinction the board does not
carry.
"""
import argparse
import json
import subprocess
import sys

RESERVED = ("role:OPERATOR",)   # queues whose work a pane must not self-assign
# ⛔ #466: every row must land in one of these, and the sum is asserted against the population.
KINDS = ("HAZARD", "ADDRESS", "PROVENANCE", "UNROUTED", "NO-DEV-LABEL")


def fetch(repo):
    """(ok, rows). ok=False means the forge was unreadable -- VOID, never 'no issues'."""
    p = subprocess.run(
        ["gh", "issue", "list", "-R", repo, "--state", "open", "--limit", "1000",
         "--json", "number,labels,title"],
        capture_output=True, text=True, timeout=120)
    if p.returncode != 0 or not p.stdout.strip():
        return False, []
    try:
        return True, json.loads(p.stdout)
    except ValueError:
        return False, []


def classify(row):
    """-> (kind, devs, roles). Kind is one of HAZARD / ADDRESS / PROVENANCE / UNROUTED / None."""
    names = [l["name"] for l in row.get("labels", [])]
    devs = sorted(n for n in names if n.startswith("dev:"))
    roles = sorted(n for n in names if n.startswith("role:"))
    if not devs:
        return "NO-DEV-LABEL", devs, roles
    if any(r in RESERVED for r in roles):
        return "HAZARD", devs, roles
    if "role:DEV" in roles:
        return "ADDRESS", devs, roles
    if roles:
        return "PROVENANCE", devs, roles
    return "UNROUTED", devs, roles


def report(repo, out=sys.stdout):
    ok, rows = fetch(repo)
    if not ok:
        print("⛔ VOID — the forge could not be read. ESTABLISHED NOTHING, not 'no collisions'.",
              file=out)
        return 2
    buckets = {}
    for r in rows:
        kind, devs, roles = classify(r)
        buckets.setdefault(kind, []).append((r["number"], devs, roles, r.get("title", "")))
    print(f"dev:N labels on {len(rows)} open issues in {repo}", file=out)
    for kind in KINDS:
        items = buckets.get(kind, [])
        print(f"  {kind:<11} {len(items):>3}", file=out)
        for n, devs, roles, title in items:
            if kind in ("HAZARD", "UNROUTED"):
                print(f"      #{n:<5} {','.join(devs)} / {','.join(r[5:] for r in roles) or '(none)'}"
                      f"  {title[:52]}", file=out)
    # ⛔ #466: a count is a partition of a stated population. If the parts do not sum to the
    # whole, the summary has not measured the thing it names -- so it REFUSES (exit 2, established
    # nothing) instead of reporting a verdict. ⚠ This convicts the output on its own face; it needs
    # no reference run and no second environment.
    # ⚠ Summed over KINDS -- the buckets a reader can SEE -- and NOT over buckets.values().
    # Summing the dict would include a kind the printer never enumerates, so the total would equal
    # the population by construction and the check could never fail. It was written that way first
    # and the known-negative below caught it: an invariant that cannot fail is decoration.
    shown = sum(len(buckets.get(k, [])) for k in KINDS)
    print(f"  {'PARTITION':<11} {shown:>3}  = sum of the {len(KINDS)} buckets above", file=out)
    if shown != len(rows):
        missing = sorted(set(buckets) - set(KINDS))
        print(f"⛔ VOID — the printed buckets sum to {shown} against a stated population of"
              f" {len(rows)}. {len(rows) - shown} row(s) landed in a bucket nothing prints"
              f" {missing}. A summary that cannot add up has not measured what it names."
              f" ESTABLISHED NOTHING.", file=out)
        return 2
    print("", file=out)
    print("⚠ PROVENANCE is not a defect and its count is not a target. Stripping those labels to"
          " reach zero destroys the record of which pane produced the work (#461, Done-when leg 3).",
          file=out)
    print("⚠ A PROVENANCE row and a mislabelling render identically here. This tool reports the"
          " set; it does not judge it.", file=out)
    if buckets.get("UNROUTED"):
        print("⚠ UNROUTED rows carry a dev:N and NO role:. They are invisible to every role query"
              " and are reported for that reason, not as a hazard.", file=out)
    haz = len(buckets.get("HAZARD", []))
    if haz:
        print(f"⛔ {haz} HAZARD — a dev:N beside a reserved queue {RESERVED}. The board is telling a"
              f" pane to act on work reserved from it (#319's shape).", file=out)
        return 1
    print("✅ no HAZARD collisions. ⚠ This is a statement about reserved queues only.", file=out)
    return 0


def self_test(out=sys.stdout):
    """Every bucket exercised on constructed rows, including the two-sided case."""
    cases = [
        ({"number": 1, "labels": [{"name": "dev:2"}, {"name": "role:OPERATOR"}]}, "HAZARD"),
        ({"number": 2, "labels": [{"name": "dev:3"}, {"name": "role:DEV"}]}, "ADDRESS"),
        ({"number": 3, "labels": [{"name": "dev:5"}, {"name": "role:DEVOPS"}]}, "PROVENANCE"),
        ({"number": 4, "labels": [{"name": "dev:1"}]}, "UNROUTED"),
        ({"number": 5, "labels": [{"name": "role:DX"}]}, "NO-DEV-LABEL"),
        ({"number": 6, "labels": []}, "NO-DEV-LABEL"),
        # ⚠ the discriminating pair: role:DEV must NOT rescue a reserved queue
        ({"number": 7, "labels": [{"name": "dev:4"}, {"name": "role:DEV"},
                                  {"name": "role:OPERATOR"}]}, "HAZARD"),
    ]
    bad = 0
    for row, want in cases:
        got, _, _ = classify(row)
        flag = "ok " if got == want else "FAIL"
        if got != want:
            bad += 1
        print(f"  {flag} #{row['number']}: want={want} got={got}", file=out)
    seen = {classify(r)[0] for r, _ in cases}
    # ⛔ Derived from KINDS, never re-typed. A hard-coded copy of the bucket set is #39's shape
    # inside the check built to catch it: add a bucket to KINDS and the copy keeps the old space.
    # Found in review by TEAMLEAD -- the definition is 100 lines above and the copy read as correct.
    if seen != set(KINDS):
        print(f"  FAIL not every bucket exercised: {seen}", file=out)
        bad += 1
    else:
        print("  ok  every bucket exercised — the classifier can return each answer", file=out)
    print("PASS" if not bad else f"{bad} FAILED", file=out)
    return 0 if not bad else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default="nForma-AI/nForma-NEXT")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--states", action="store_true",
                    help="print the exit states this tool can return, and stop")
    a = ap.parse_args(argv)
    if a.states:
        # ⛔ The contract is machine-readable and TAB-separated -- `EXIT\t<code>\t<meaning>`.
        # A first version printed the same information as prose separated by "·". It read
        # correctly to a human and `states-index-check.py` could not parse a single line of it,
        # so this tool declared --states and was counted, correctly, as not exposing it. Copying
        # the README row's LOOK instead of the producer's CONTRACT is #39's shape from the other
        # side: a new producer speaking a dialect its consumer does not read.
        # ⚠ EXIT lines ONLY, and that is deliberate. A first version also declared five VERDICT
        # states, one of which (NO-DEV-LABEL) exists only on the branch of a DIFFERENT open PR --
        # so merging this one first would have made the tool DECLARE A STATE IT DOES NOT HAVE,
        # which is #39's defect inside the PR about #39. `emit_row` reads EXIT lines only, so the
        # VERDICT lines bought nothing and cost a merge-order dependency. ⇒ Removed rather than
        # documented: an order a reader must remember is the weakest carrier on the ladder.
        # VERDICT declarations can be added once the bucket set is settled on `main`.
        for kind, code, meaning in (
                ("EXIT", "0", "no HAZARD collisions"),
                ("EXIT", "1", "at least one HAZARD -- a finding, established"),
                ("EXIT", "2", "established nothing: forge unreadable, or the buckets did not sum")):
            print(f"{kind}\t{code}\t{meaning}")
        return 0
    if a.self_test:
        return self_test()
    return report(a.repo)


if __name__ == "__main__":
    sys.exit(main())
