#!/usr/bin/env python3
"""Given a field a closed issue REFUTED, which open close conditions still turn on it?

⛔ THE DEFECT, and it has an instance. #327 measured that `gh --author '@me'`
returns all nine panes' PRs -- the shared credential makes an author filter
succeed with the wrong answer -- and was closed COMPLETED 2026-08-23. #601 then
found FIVE open issues whose close conditions still turn on authorship: #173,
#268, #214, #80, #172. The refutation was never propagated.

★ AND THE OBVIOUS INSTRUMENT DOES NOT WORK. The first design was "list open
issues whose condition CITES the closed one". Checked against the known case
before building it:

    #173 #268 #214 #80 #172   cite #327 in their bodies:  0, all five

⇒ The dependency is SEMANTIC, not by citation. Those conditions never mention
#327; they mention the FIELD #327 refuted. A citation-based tool finds nothing
here, and finding that out cost one query instead of a build.

⛔ AND A BODY-WIDE GREP IS TOO COARSE. Measured 2026-09-07:

    body-wide "author|@me|--author"     #363 -> 2 hits, and #363 is about
                                        vendoring, not authorship
    scoped to the CLOSE-CONDITION section:
        #173 #268 #214 #80 #172 -> hit      (the five, correctly)
        #363 #205               -> no hit   (controls, correctly)
        7 of 7

⇒ So the predicate is the field, scoped to the clause. #601's own wording is
"its authorship CLAUSE", and that word is doing the work.

⛔⛔ THE DIVISION OF LABOUR IS THE DESIGN, AND IT IS NOT AUTOMATABLE AWAY.
WHICH FIELD a closed issue refuted is a READING -- supply it with --field. The
REACH over open conditions is mechanical, and that is all this does.

⚠ MENTIONING IS NOT DEPENDING. #601 measured 20 of 60 conditions mentioning
authorship and judged 5 to depend on it; the 5 turns on that judgement. This
reports the mentions and names them, and refuses to make the second call.

⚠ The clause predicate is IMPORTED from close-condition-scan.py, never
re-implemented: a second reading of one noun drifts from the first (#345), and
this repo has measured that happening.

Exit: 0 nothing reaches the field · 1 at least one condition mentions it ·
2 established nothing.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runmarker import guard, result  # noqa: E402

import argparse
import importlib.util
import json
import re
import subprocess


def _clause_re():
    """close-condition-scan.py's CONDITION, imported rather than copied."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "close-condition-scan.py")
    spec = importlib.util.spec_from_file_location("_ccs", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONDITION


class Void(Exception):
    """Established nothing. ⛔ Never collapse into a verdict."""


def gh(args):
    """⛔ RAISES. A helper returning "" on failure turns a failed fetch into
    'this issue does not reach the field', which is the defect inverted."""
    try:
        p = subprocess.run(["gh"] + args, capture_output=True, text=True)
    except OSError as exc:
        raise Void(f"cannot run gh: {exc}")
    if p.returncode != 0:
        raise Void(f"gh exited {p.returncode}: {(p.stderr or '').strip()[:200]}")
    return p.stdout


def condition_section(body, clause_re, max_lines=40):
    """The clause and what follows it, to the next H2. None if there is no clause.

    ⚠ Bounded at max_lines. An unbounded read to the next H2 swallows a whole
    issue when the clause is the last heading, and then a field mentioned in the
    provenance footer scores as part of the condition.
    """
    lines = (body or "").splitlines()
    start = None
    for i, line in enumerate(lines):
        if clause_re.search(line):
            start = i
            break
    if start is None:
        return None
    out = []
    for line in lines[start + 1:]:
        if line.startswith("## ") and out:
            break
        out.append(line)
        if len(out) >= max_lines:
            break
    return "\n".join(out)


def self_test():
    clause = _clause_re()
    field = re.compile(r"author|@me", re.I)
    failures = []
    cases = [
        ("## Done when\n- the --author filter is replaced", True,
         "KNOWN-POSITIVE: the field appears inside the clause"),
        ("## Done when\n- the thing is measured\n\n## Notes\nauthor of this is DX", False,
         "KNOWN-NEGATIVE: the field is AFTER the section, in another H2"),
        ("intro mentions author\n\n## Done when\n- the thing is measured", False,
         "KNOWN-NEGATIVE: the field is BEFORE the clause, in the preamble"),
        ("no clause at all, and author appears here", None,
         "no clause ⇒ no section ⇒ not a candidate, not a hit"),
        ("", None, "an empty body establishes nothing"),
    ]
    for body, expected, why in cases:
        sec = condition_section(body, clause)
        got = None if sec is None else bool(field.search(sec))
        mark = "ok  " if got == expected else "FAIL"
        if got != expected:
            failures.append((why, expected, got))
        print(f"  {mark} {why}")

    try:
        gh(["--zzz-not-a-real-subcommand"])
    except Void:
        print("  ok   a failed gh RAISES — it cannot read as 'does not reach the field'")
    except Exception as exc:                                  # noqa: BLE001
        failures.append(("gh must raise Void", "Void", type(exc).__name__))
    else:
        failures.append(("gh must RAISE on failure", "Void", "returned normally"))

    if failures:
        print("\n⛔ broken; no verdict it produces can be trusted:")
        for why, exp, got in failures:
            print(f"     {why}: expected {exp}, got {got}")
        result("CONTROL-FAILED")
        return 3
    print(f"\n  {len(cases) + 1}/{len(cases) + 1} controls passed — including both "
          "out-of-section negatives and the fail-closed fetch.")
    result("SELF-TEST-PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--field", default=r"author|@me|--author",
                    help="regex for the refuted field (a READING — you supply it)")
    ap.add_argument("--refuted-by", default="",
                    help="the closed issue that refuted it, for the record")
    ap.add_argument("--repo", default="nForma-AI/nForma-NEXT")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    try:
        field = re.compile(args.field, re.I)
    except re.error as exc:
        print(f"⛔ VOID — --field is not a valid regex: {exc}", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    try:
        clause = _clause_re()
        total = int(gh(["api", "-X", "GET", "search/issues", "-f",
                        f"q=repo:{args.repo} is:issue is:open",
                        "--jq", ".total_count"]).strip())
        nums = [i["number"] for i in json.loads(gh(
            ["issue", "list", "--repo", args.repo, "--state", "open",
             "--limit", str(args.limit), "--json", "number"]))]
    except (Void, ValueError, OSError) as exc:
        print(f"⛔ VOID — {exc}", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    # ⛔ A COMPLETE POPULATION OF ZERO IS CLEAN, NOT VOID. This read
    # `if not nums or len(nums) < total`, which returned 2 for an empty board --
    # and 2 means "established nothing", so it would have refused a reading that
    # was in fact complete. Review on #629, 2026-09-07.
    #
    # ⚠ THE JUSTIFICATION FOR THE OLD GUARD WAS MEASURED AND IS FALSE HERE. The
    # claim was "an empty board and a failed query are byte-identical". Measured
    # against this endpoint:
    #     q=… is:issue is:open            -> 102     the real board
    #     q=… label:zzz-no-such           -> 0       ⚠ silent, and the board is NOT empty
    #     q=repo:nForma-AI/zzz-no-such    -> HTTP 422, which gh() RAISES
    # ⇒ A malformed query CAN return 0 silently -- but this query is FIXED, and
    #   the only user-supplied part (--repo) fails 422 and raises. So reaching
    #   total == 0 here means the search succeeded and the board is empty.
    if len(nums) < total:
        print(f"⛔ VOID — read {len(nums)} of {total} stated. A truncated reading "
              f"cannot support 'nothing reaches the field'.", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2
    if total == 0:
        # ⚠ Loudly, because 102 is the standing size: a zero here is far more
        # likely to be a --repo pointing somewhere unexpected than a cleared board.
        print("⚠ the board is EMPTY (0 open issues, and the search agrees). Nothing "
              "reaches the field because there is nothing to reach it.", file=sys.stderr)

    print(f"POPULATION  {len(nums)} open issues of {total} stated · repo={args.repo}")
    print(f"PREDICATE   the CLOSE-CONDITION section mentions /{args.field}/")
    if args.refuted_by:
        print(f"REFUTED BY  #{args.refuted_by}  (that this field IS refuted is a reading)")
    print("CHANNEL     issue body, clause predicate imported from close-condition-scan.py\n")

    hits, noclause = [], 0
    for n in nums:
        try:
            d = json.loads(gh(["issue", "view", str(n), "--repo", args.repo,
                               "--json", "body,title"]))
        except Void as exc:
            print(f"⛔ VOID — issue #{n} unreadable: {exc}", file=sys.stderr)
            print("   Skipping it would make an unread issue look clean.", file=sys.stderr)
            result("ESTABLISHED-NOTHING")
            return 2
        sec = condition_section(d.get("body") or "", clause)
        if sec is None:
            noclause += 1
            continue
        if field.search(sec):
            hits.append((n, (d.get("title") or "")[:58]))

    print(f"  no close condition in the body   {noclause:3d}  (not a candidate either way)")
    print(f"  ⛔ condition mentions the field   {len(hits):3d}\n")
    for n, t in sorted(hits):
        print(f"    #{n:<5} {t}")

    if hits:
        print("""
    ⇒ MENTIONS, NOT DEPENDENCIES. #601 measured 20 of 60 conditions mentioning
      authorship and judged 5 to DEPEND on it — that second step is a reading and
      this refuses to make it. Open the conditions named above.
    ⇒ THE REPAIR is to replace the clause with a measurable discriminator, or to
      annotate it unmeetable-as-written citing the issue that refuted the field.""")
    result("FINDINGS" if hits else "CLEAN")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(guard("refuted-field-reach", main))
