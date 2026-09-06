#!/usr/bin/env python3
"""Which open issues carry no close condition -- and which hide one where a closer will not look.

⛔ THE DEFECT, measured. TEAMLEAD reported "~31 open issues still lack completion
conditions." The number had never been produced by anything. An issue with no
falsifiable close condition cannot be CLOSED honestly -- it can only be abandoned
or declared -- so the count is load-bearing, and it was a recollection.

★ AND THE SECOND STATE IS THE ONE THAT MOTIVATED THE TOOL. Measured on DEV3's own
five queued issues: all five carried a `Done when` clause, and NONE of them carried
it in the BODY. Every clause lived in a COMMENT, three of them under six other
comments. A closer who opens the issue and reads it sees no condition at all. The
condition is PRESENT and UNREACHABLE, which is this fleet's recurring shape:

    a container that survives while its contents are lost.

⇒ So the verdict has three states, not two. `BURIED` is not a softer `NONE`; it is
a different defect with a different repair (move the clause into the body) and it
is invisible to any check that asks only "does a condition exist somewhere?"

⛔⛔ WHAT THIS DOES NOT DO, AND THE BOUND IS SHARP. It detects the PRESENCE of a
marked condition clause. It does not and cannot judge whether that condition is
FALSIFIABLE. `## Done when: it feels done` passes this tool. Presence is
checkable; quality is a reading, and an instrument that claimed to do the second
while doing the first would be believed for the wrong reason. ⇒ Exit 0 means
"every open issue has a clause in its body", never "every open issue can be closed
honestly."

⚠ THE PATTERN IS ANCHORED AT LINE START, on purpose. A bare `done when` substring
matches prose ABOUT close conditions. Issue #189 is a friction report whose whole
subject is close conditions; a substring match flags it as HAVING one. That is
use-vs-mention, the same failure `text-provenance.py` was corrected for, and the
negative control below is the case that catches it.

⚠ TRUNCATION. `gh issue list --limit N` clamps silently, and a clamped list is a
clean answer about a set the tool never saw. The fetched count is compared against
`search/issues`'s stated `total_count`; a shortfall is exit 2, never a verdict.
Per gh-complete.py: `--limit 100` is safe-by-repo-size, which is not a check.

Usage:
    python3 tools/close-condition-scan.py
    python3 tools/close-condition-scan.py --label dev:3
    python3 tools/close-condition-scan.py --self-test

Exit: 0 every open issue carries a clause IN ITS BODY
      1 at least one NONE or BURIED -- a finding, established
      2 established nothing (query failed, empty board, or a truncated reading)
      3 the known-positive control failed -- the classifier itself is broken
"""
import argparse
import json
import re
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from runmarker import begin, result  # noqa: E402

DEFAULT_REPO = "nForma-AI/nForma-NEXT"

# ⛔ Anchored at line start, after at most 3 spaces of indent and any combination of
# markdown heading marks, bold, list bullets and this repo's arrow glyphs. The clause
# must be a STRUCTURAL element of the document -- a heading or a lead-in -- not a
# phrase inside a sentence. See the use-vs-mention control in self_test().
CONDITION = re.compile(
    r"^[ ]{0,3}"
    r"(?:[-*+][ ]+)?"
    r"(?:#{1,6}[ ]*)?"
    r"(?:[⇒★⚠⛔→][ ]*)*"
    r"(?:#{1,6}[ ]*)?"
    r"(?:\*\*|__)?[ ]*"
    r"(?:done[ ]when"
    r"|closes?[ ]when"
    r"|closes?[ ]only[ ]when"
    r"|close[ ]condition"
    r"|completion[ ]condition"
    r"|acceptance[ ]criteri)",
    re.IGNORECASE | re.MULTILINE,
)


# ⇒ Printed BESIDE the finding, in the execution path, because a writer who has just
# been told "no close condition" is one line away from being told what one looks like —
# and that is the moment they need it. A rule stated only in a README is a rule you have
# to already know to go and read.
ACCEPTED_FORM = """
    ⇒ WHAT COUNTS, and it is stricter than it looks:
       · the clause must start a LINE — a heading, a bold lead-in, or a list item.
         A sentence CONTAINING "done when" does not count and is not meant to:
         prose ABOUT close conditions is not a close condition.
       · it must be IN THE ISSUE BODY. A clause in a comment scores BURIED, not OK.
       ✅ accepted:   ## Done when          ⇒ **Closes when** …        - **Done when:** …
       ⛔ not:        "we should decide the completion condition for this someday"
"""

# ⛔ A CORRECTION THAT KILLS A CONDITION'S PREMISE USUALLY DOES NOT RESTATE THE
# CONDITION, so it carries no clause and is INVISIBLE to "take the last comment
# carrying one." Measured on #579, 2026-09-06: the only clause-bearing comment was
# the OLDEST of three, and the two after it were both corrections — one refuting the
# very number the clause was anchored to ("today's answer is 5" -> "43 of 61").
# Promoting verbatim, as the remedy said, would have installed a known-false anchor.
# ⇒ Same class as #601: a refutation nobody propagated.
#
# ⚠ This WARNS, it does not verdict. A false positive costs a re-read; a false
# negative costs a promoted-wrong condition. So it fails toward warning, and the
# words below are deliberately broad.
SUPERSEDED = re.compile(
    r"correcting|correction|withdraw|retract|supersed|no longer|"
    r"i was wrong|that was wrong|refut",
    re.IGNORECASE,
)


def supersession_risk(issue):
    """(clause_idx, n_later, n_later_correcting) for a BURIED issue.

    clause_idx is the LAST comment carrying a clause -- the one the remedy says to
    promote. n_later_correcting counts comments AFTER it that read like corrections.
    ⇒ Any nonzero means "read those before you copy", never "do not copy".
    """
    cs = issue.get("comments") or []
    idx = None
    for i, c in enumerate(cs):
        if has_clause(c.get("body")):
            idx = i
    if idx is None:
        return (None, 0, 0)
    later = cs[idx + 1:]
    return (idx, len(later), sum(1 for c in later if SUPERSEDED.search(c.get("body") or "")))


BURIED_REMEDY = """
    ⇒ THE FIX IS A MOVE, NOT A REWRITE: copy the clause from the comment into the BODY,
      verbatim. ⚠ Take it from the LAST comment carrying one — a corrected disposition
      supersedes an earlier one, and promoting the first can promote a WITHDRAWN condition.
    ⛔ AND THAT IS NOT SUFFICIENT. A correction usually does NOT restate the condition,
      so it carries no clause and this rule cannot see it. Any ⚠ line above names the
      later comments that read as corrections; read them before you copy, and if one
      refutes what the clause is anchored to, promote it CORRECTED and say so.
"""

class Void(Exception):
    """Established nothing. ⛔ Never collapse into a verdict."""


def gh(args):
    try:
        p = subprocess.run(["gh"] + args, capture_output=True, text=True)
    except OSError as exc:
        raise Void(f"cannot run gh: {exc}")
    if p.returncode != 0:
        raise Void(f"gh exited {p.returncode}: {(p.stderr or '').strip()[:300]}")
    return p.stdout


def has_clause(text):
    return bool(CONDITION.search(text or ""))


def classify(issue):
    """BODY / BURIED / NONE. ⇒ BURIED is a distinct defect, not a weaker NONE."""
    if has_clause(issue.get("body")):
        return "BODY"
    for c in issue.get("comments") or []:
        if has_clause(c.get("body")):
            return "BURIED"
    return "NONE"


def stated_total(repo, label):
    """The population size as the API STATES it -- not as our list happens to arrive.

    ⛔ This is the whole truncation check. Counting what we received tells us nothing
    about what we did not."""
    q = f"repo:{repo} is:issue is:open"
    if label:
        q += f' label:"{label}"'
    out = gh(["api", "-X", "GET", "search/issues",
              "-f", f"q={q}", "-F", "per_page=1", "--jq", ".total_count"])
    try:
        return int(out.strip())
    except ValueError:
        raise Void(f"search/issues did not return a count: {out.strip()[:120]!r}")


def fetch(repo, label, limit):
    args = ["issue", "list", "--repo", repo, "--state", "open",
            "--limit", str(limit), "--json", "number,title,body,comments,labels"]
    if label:
        args += ["--label", label]
    raw = gh(args)
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError as exc:
        raise Void(f"issue list was not JSON: {exc}")


def self_test():
    """⛔ KNOWN-POSITIVE, and the fixtures are LITERALS so the control survives repair.

    A control keyed on repo state stops failing the moment the repo is fixed, which
    is #26's defect: it becomes decoration exactly when it stops being exercised.
    These three cases are exercised on every run, forever."""
    cases = [
        # (body, comments, expected, why this case exists)
        ("## Done when\nthe scanner reports zero.", [], "BODY",
         "a heading clause in the body"),
        ("no condition here.", [{"body": "**Done when:** #285 merges."}], "BURIED",
         "clause exists, but only where a body-reader will not see it"),
        # ⛔ THE LOAD-BEARING CONTROL. Prose ABOUT close conditions is not a close
        # condition. A bare-substring matcher passes the two above and FAILS here.
        ("An issue is not closeable until somebody says what done when means.",
         [{"body": "we should decide the completion condition for this someday"}],
         "NONE", "use-vs-mention: discussing a clause is not carrying one"),
        ("⇒ **Closes when** the retracted bullet is struck in the body.", [], "BODY",
         "this repo's arrow+bold lead-in, taken from #271's real disposition"),
        ("", [], "NONE", "an empty body establishes nothing about a comment"),
    ]
    failures = []
    for body, comments, expected, why in cases:
        got = classify({"body": body, "comments": comments})
        mark = "ok  " if got == expected else "FAIL"
        if got != expected:
            failures.append((why, expected, got))
        print(f"  {mark} expect {expected:<6} got {got:<6}  {why}")
    if failures:
        print("\n⛔ the classifier is broken; no verdict it produces can be trusted:")
        for why, exp, got in failures:
            print(f"     {why}: expected {exp}, got {got}")
        return 3
    # ── supersession_risk: two-sided, both poles NAMED ─────────────────────────
    # ⛔ The dangerous shape is a LATER correction that carries no clause. A detector
    # keyed on clauses alone cannot see it, which is the whole reason this exists.
    clause = {"body": "## Done when\nthe number is 5."}
    corr = {"body": "⛔ Correcting my own comment above. Both numbers were wrong."}
    plain = {"body": "Agreed, nice write-up."}

    got = supersession_risk({"comments": [clause, corr, plain]})
    assert got == (0, 2, 1), \
        f"KNOWN-POSITIVE FAILED: a later correction must be counted, got {got}"

    got = supersession_risk({"comments": [clause, plain, plain]})
    assert got == (0, 2, 0), \
        f"KNOWN-NEGATIVE FAILED: ordinary later comments are not corrections, got {got}"

    # ⚠ The LAST clause wins, not the first — and a correction BEFORE it is not a risk.
    got = supersession_risk({"comments": [clause, corr, clause]})
    assert got == (2, 0, 0), \
        f"KNOWN-NEGATIVE FAILED: a correction before the last clause is spent, got {got}"

    got = supersession_risk({"comments": [plain]})
    assert got == (None, 0, 0), \
        f"KNOWN-NEGATIVE FAILED: no clause at all must yield None, got {got}"

    print(f"\n  {len(cases)}/{len(cases)} controls passed — including the "
          f"use-vs-mention negative.")
    print("  4/4 supersession controls passed — a later correction is counted, an "
          "ordinary comment is not, and a correction BEFORE the last clause is spent.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--label", default=None, help="restrict to one label")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--self-test", action="store_true")
    # ⛔ RENAMED from --states. `--states` collided across three tools with TWO
    # RELATIONS under one name: doctrine-version.py and runnable-condition.py DECLARE
    # a state space; this printed SUBJECTS GROUPED BY STATE. ⇒ A format convention
    # cannot fix a name that means two things (ARCHITECT, #498). Priority is theirs by
    # 62 minutes (e8e1cff 19:07 vs 2fcd8e1 20:09), the count is theirs 2-to-1, and the
    # NAME FITS THEIR RELATION — `--states` reads as "tell me the states". So this one
    # moved. ⚠ No caller invoked it; only the index row named it.
    ap.add_argument("--by-state", action="store_true", dest="by_state",
                    help="print only `<STATE> <issue-number>` lines, for piping")
    ap.add_argument("--states", action="store_true",
                    help="DECLARE this tool's state space and exit codes (TAB-separated), "
                         "so an index row can be GENERATED rather than hand-written")
    a = ap.parse_args()

    if a.self_test:
        rc = self_test()
        result("SELF-TEST-PASS" if rc == 0 else "SELF-TEST-FAILED")
        return rc

    if a.states:
        # ⇒ The DECLARE relation, conforming to tools/states-index-check.py's contract:
        #   VERDICT\t<name>\t<meaning>   the state space
        #   EXIT\t<code>\t<meaning>      what a caller reads
        # ⛔ Emitted BEFORE any network call, so declaring the space never depends on
        # reaching the forge — a tool that cannot say what it CAN report is worse than
        # one that cannot report.
        for name, why in (
            ("BODY", "a close condition is in the issue BODY, where a closer reads it"),
            ("BURIED", "a condition exists ONLY in a comment — a body-reader sees none"),
            ("NONE", "no close condition anywhere — cannot be closed, only declared"),
        ):
            print(f"VERDICT\t{name}\t{why}")
        for code, why in (
            (0, "every open issue carries a clause in its body"),
            (1, "NONE or BURIED found — a finding, established"),
            (2, "established nothing (failed query, empty board, or a truncated reading)"),
            (3, "the known-positive control failed"),
        ):
            print(f"EXIT\t{code}\t{why}")
        result("STATES-DECLARED")
        return 0

    # ⛔ The control runs before every real scan. A tool that only self-tests when
    # asked is one whose caller never asks.
    for body, comments, expected in (
        ("## Done when\nx", [], "BODY"),
        ("talk about done when clauses", [], "NONE"),
    ):
        if classify({"body": body, "comments": comments}) != expected:
            print("⛔ known-positive control failed at startup — refusing to scan.",
                  file=sys.stderr)
            result("CONTROL-FAILED")
            return 3

    try:
        total = stated_total(a.repo, a.label)
        issues = fetch(a.repo, a.label, a.limit)
    except Void as exc:
        print(f"⛔ ESTABLISHED NOTHING: {exc}", file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    if total == 0:
        # ⚠ An empty board is not a clean board. It is also what a mistyped label
        # returns: `gh issue list --label <nonexistent>` exits 0 with zero bytes on
        # stdout AND stderr, byte-identical to "your queue is empty." Measured.
        print(f"⛔ ESTABLISHED NOTHING: the query matched no open issues"
              f"{f' with label {a.label!r}' if a.label else ''}. An empty result is "
              f"NOT a clean board — a mistyped label produces this exact output.",
              file=sys.stderr)
        result("ESTABLISHED-NOTHING")
        return 2

    if len(issues) < total:
        print(f"⛔ ESTABLISHED NOTHING: read {len(issues)} of {total} stated open "
              f"issues — the reading is a PREFIX, and a verdict over it would be a "
              f"clean answer about a set this tool never saw. Raise --limit.",
              file=sys.stderr)
        result("TRUNCATED")
        return 2

    buckets = {"BODY": [], "BURIED": [], "NONE": []}
    for it in issues:
        buckets[classify(it)].append(it)

    if a.by_state:
        for state in ("NONE", "BURIED", "BODY"):
            for it in buckets[state]:
                print(f"{state} {it['number']}")
    else:
        print(f"open issues read: {len(issues)} of {total} stated"
              f"{f'   label={a.label}' if a.label else ''}\n")
        for state, gloss, remedy in (
            ("NONE", "no close condition anywhere — cannot be closed, only declared",
             ACCEPTED_FORM),
            ("BURIED", "condition exists ONLY in a comment — a body-reader sees none",
             BURIED_REMEDY),
        ):
            rows = buckets[state]
            print(f"{state}  ({len(rows)})  {gloss}")
            for it in sorted(rows, key=lambda i: i["number"]):
                print(f"    #{it['number']:<5} {it['title'][:88]}")
                # ⇒ Printed per-row, not once at the bottom: the reader deciding
                # WHICH comment to copy is deciding it here.
                if state == "BURIED":
                    idx, n_later, n_corr = supersession_risk(it)
                    if n_corr:
                        print(f"           ⚠ the last clause is comment #{idx + 1}; "
                              f"{n_corr} of the {n_later} comment(s) after it read as "
                              f"CORRECTIONS. Read them before copying — the clause may "
                              f"be anchored to a refuted number.")
                    elif n_later:
                        print(f"           · last clause is comment #{idx + 1}; "
                              f"{n_later} later comment(s), none reading as corrections.")
            # ⛔ The remedy prints WITH the finding, not in a README. DEV2 met both
            # requirements only by READING THE REGEX; nothing in the issue template,
            # goals/README.md, or this tool's own output said a comment scores BURIED
            # or that the pattern is line-anchored. ⇒ TEAMLEAD produced twelve BURIED
            # and ARCHITECT four prose ones, neither carelessly: the requirement was
            # discoverable only by reading an implementation.
            if rows:
                print(remedy)
            print()
        print(f"BODY    ({len(buckets['BODY'])})  condition is in the body, where a "
              f"closer reads it")
        print("\n⚠ PRESENCE ONLY. This does not check that any clause is FALSIFIABLE.")

    findings = len(buckets["NONE"]) + len(buckets["BURIED"])
    result("FINDINGS" if findings else "CLEAN")
    return 1 if findings else 0


if __name__ == "__main__":
    begin("close-condition-scan")
    sys.exit(main())
