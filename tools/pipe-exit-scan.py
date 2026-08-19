#!/usr/bin/env python3
"""Find exit codes read through a pipe — the measurement that isn't one.

⛔ THE INCIDENT, three times, in three roles, inside four hours:

    1  DEVOPS    `validate-recipe.py | tail -6; echo "exit=$?"`  -> read TAIL's status,
                 and nearly filed a working validator as an entrypoint that cannot fail.
    2  TEAMLEAD  `${PIPESTATUS[0]}` in a zsh context -> expanded EMPTY. Printed `exit=`
                 and had measured nothing while displaying something that looked like a result.
    3  DEV2      `python3 tool.py | sed ...; echo "EXIT=${PIPESTATUS[0]}"` -> `EXIT=`.

★ The third happened in a role that had been WARNED ABOUT IT IN THE SAME MESSAGE THAT
ASSIGNED THE TASK, against a rule already written in tools/README.md with two documented
instances. Three misses is the measurement that the prose form does not work. This file is
the tool form; the prose is retired rather than kept alongside, because a rule that exists
and does not fire is worse than no rule — its presence is mistaken for coverage.

⛔ AND THIS SCANNER IS ITS OWN HARDEST TEST CASE. A scanner for this is a content matcher,
and a document explaining the trap CONTAINS the string `PIPESTATUS`. Measured on this repo:
the only two occurrences of `PIPESTATUS` anywhere are in tools/README.md, in the paragraph
WARNING about it. So a naive identifier scan reports 2 findings here and BOTH ARE FALSE —
a 100% false-positive rate, in the direction that reads as work-to-do rather than as an error.

⇒ So it matches on something a MENTION CANNOT PRODUCE. The fleet has now solved this same
problem five separate times without naming it once:

    a nonce      — citation cannot precede creation
    line position— a quotation cannot occupy a position
    a path form  — prose has no path separator
    an exec record — a description is not an effect
    and here     — a comment is not code, and prose is not a shell file

The discriminators used, in order of strength:

    1. FILE KIND     prose lives in .md. A markdown file is never executed, so an
                     occurrence there cannot be a use. Markdown is scanned ONLY inside
                     ```bash / ```sh fences — a fence is code-shaped, inline backticks
                     are not.
    2. COMMENT STRIP a `#` comment inside a shell script is a mention. Code is a use.
                     This file's own docstring would trip an unstripped matcher.
    3. SHAPE         the finding is a PIPELINE whose status is then read, not the
                     identifier on its own.

⚠ What it does NOT do, stated rather than discovered: it does not parse shell. A `#` inside
a quoted string is treated as a comment start, so a pipeline written after a `#` in a string
is missed. It under-reports there and says so, because over-reporting on prose is the failure
this tool exists to avoid.

⛔ WHAT THIS TOOL DOES NOT DO, AND THE NUMBER THAT PROVES IT.

    git grep '\$?'          -> 0 hits in committed files
    git grep 'PIPESTATUS'   -> 2 hits, BOTH PROSE

⇒ It would have caught **0 of the 5 real instances**. Every one was an ephemeral
command typed into a tool call and never committed. This is a guard against the
idiom ENTERING a committed script — a real job, and `fleet-worktree.sh` is exactly
the file where it would land — and it is NOT a remedy for the failure mode that
produced it.

⚠ So read a clean run correctly: "0 findings" here is a statement that THE
POPULATION IS EMPTY, not a statement of coverage. Absence of findings in a
population the defect does not live in is not evidence of anything. The measured
failure mode lives at the point of execution, which is a PreToolUse hook and not
this file.

Exit: 0 clean · 1 findings · 2 established nothing (no files scanned).
"""
import os, re, subprocess, sys

# `cmd | cmd ; echo $?`  — the status read belongs to the LAST pipeline element.
AFTER_PIPE = re.compile(r"\|[^|&;]+[;&][^#\n]*\$\?")
# `${PIPESTATUS[n]}` — bash-only. Empty in zsh, and empty is not zero.
PIPESTATUS = re.compile(r"\$\{PIPESTATUS\[")
FENCE = re.compile(r"^\s*```\s*(bash|sh|shell|console)\s*$", re.I)
FENCE_END = re.compile(r"^\s*```\s*$")


def tracked():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if out.returncode != 0:
        return []
    return [p for p in out.stdout.splitlines() if p]


def is_shell(path):
    if path.endswith((".sh", ".bash", ".zsh")):
        return True
    try:
        with open(path, "rb") as fh:
            first = fh.readline(200).decode("utf-8", "replace")
    except OSError:
        return False
    return first.startswith("#!") and ("sh" in first)


def strip_comment(line):
    """A comment is a MENTION; code is a USE. Crude on purpose — see the caveat above."""
    i = line.find("#")
    return line if i < 0 else line[:i]


def scan_shell(path):
    hits = []
    try:
        lines = open(path, errors="replace").read().splitlines()
    except OSError:
        return hits
    for n, raw in enumerate(lines, 1):
        code = strip_comment(raw)
        if not code.strip():
            continue
        if AFTER_PIPE.search(code):
            hits.append((n, raw.strip(), "$? read after a pipeline — that is the LAST element's status"))
        elif PIPESTATUS.search(code):
            hits.append((n, raw.strip(), "PIPESTATUS — bash-only; expands EMPTY in zsh, and empty is not zero"))
    return hits


def scan_markdown(path):
    """Fenced bash blocks only. Inline backticks in prose are a mention: this repo's own
    warning paragraph is written that way, and firing on it is the defect, not the find."""
    hits, infence = [], False
    try:
        lines = open(path, errors="replace").read().splitlines()
    except OSError:
        return hits
    for n, raw in enumerate(lines, 1):
        if not infence:
            if FENCE.match(raw):
                infence = True
            continue
        if FENCE_END.match(raw):
            infence = False
            continue
        code = strip_comment(raw)
        if AFTER_PIPE.search(code):
            hits.append((n, raw.strip(), "$? read after a pipeline, inside a ```bash block — docs teach this"))
        elif PIPESTATUS.search(code):
            hits.append((n, raw.strip(), "PIPESTATUS inside a ```bash block"))
    return hits


SELFTEST_POSITIVE = "tools/testdata/pipe-exit-positive.sh"
SELFTEST_NEGATIVE = "tools/README.md"


def selftest():
    """⛔ Prove BOTH paths, because either alone is worthless.

    A scanner that has never fired is not a scanner. A scanner that fires on the
    document warning about the thing is worse than none — it produces a count
    that reads as work-to-do.

    The negative is REAL DATA, not a fixture: tools/README.md is the only file in
    this repository containing `PIPESTATUS`, and both occurrences are in the
    paragraph warning about it. A naive identifier matcher scores 2 findings
    there, both false — a 100% false-positive rate on the live repo.
    """
    ok = True
    pos = scan_shell(SELFTEST_POSITIVE)
    real = [h for h in pos if "MUST NOT" not in h[1]]
    if len(real) >= 3:
        print(f"  ok    known-positive: {len(real)} findings in {SELFTEST_POSITIVE}")
        for n, src, _ in real:
            print(f"          L{n}: {src[:72]}")
    else:
        print(f"  FAIL  known-positive: {len(real)} findings, expected >=3 — "
              f"the failing path does not fire")
        ok = False
    neg = scan_markdown(SELFTEST_NEGATIVE)
    if not neg:
        print(f"  ok    known-negative: 0 findings in {SELFTEST_NEGATIVE} "
              f"(which contains the only 2 `PIPESTATUS` strings in the repo)")
    else:
        print(f"  FAIL  known-negative: fired on prose about the trap — {neg}")
        ok = False
    cmt = [h for h in pos if h[0] < 12]
    if cmt:
        print(f"  FAIL  fired inside a comment block — comment-stripping regressed: {cmt}")
        ok = False
    else:
        print("  ok    no findings inside the fixture's comment block (a mention is not a use)")
    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def main():
    if "--selftest" in sys.argv:
        return selftest()
    files = tracked()
    if not files:
        print("⛔ no tracked files — ESTABLISHED NOTHING, not clean. "
              "Run inside a git repository.", file=sys.stderr)
        return 2
    scanned = 0
    findings = []
    for p in files:
        if not os.path.exists(p):
            continue
        if p.startswith("tools/testdata/"):
            continue          # fixtures are scanned only by --selftest
        if is_shell(p):
            scanned += 1
            findings += [(p, *h) for h in scan_shell(p)]
        elif p.endswith(".md"):
            scanned += 1
            findings += [(p, *h) for h in scan_markdown(p)]
    if scanned == 0:
        print("⛔ zero scannable files — ESTABLISHED NOTHING, not clean.", file=sys.stderr)
        return 2

    for path, n, src, why in findings:
        print(f"{path}:{n}")
        print(f"    {src}")
        print(f"    ⇒ {why}")
    print(f"\n{len(findings)} finding(s) across {scanned} scanned file(s).", file=sys.stderr)
    print("⚠ Matched on SHAPE after stripping comments and skipping non-fenced prose. "
          "Occurrences inside comments, and inline `PIPESTATUS` in prose, are MENTIONS and "
          "are deliberately not reported — this repo's own warning paragraph is one, and "
          "firing on it would be the defect rather than the find.", file=sys.stderr)
    print("⚠ Does not parse shell: a `#` inside a quoted string ends the line early, so it "
          "UNDER-reports there. Chosen over over-reporting on prose.", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
