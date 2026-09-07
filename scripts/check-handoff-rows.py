#!/usr/bin/env python3
# SUITE-DEPENDS: runs each snapshot row's command, and most of them are `gh` — network
# plus auth. MEASURED on a runner (run 34139504952): with no token every `gh` row
# produced empty stdout, and the FIRST version of this file scored that as MISMATCH.
# ⛔ That is "could not measure" reported as "found a defect" — the one conflation this
# estate exists to prevent, in the tool written to prevent it. Fixed below; the marker
# stays because the dependency is real and a network gate is a flake source.
"""The snapshot block says every line names the command that produces it. Nobody checked.

`docs/HANDOFF.md` opens its "What is true right now" block with a standing claim:

    Measured <instant> on `origin/main`. **Every line names the command that
    produces it** -- run those, do not cite this block.

⛔ THE DEFECT THAT MOTIVATED THIS, measured 2026-09-07 (#637). PR #636 changed one
row's command to `--by-state`, a flag whose own `--help` says it prints "only
`<STATE> <issue-number>` lines". It prints no totals at all. So the row carried
three CORRECT values under a command that cannot produce any of them, and shipped:

    close conditions  NONE 13 · BURIED 0 · BODY 90   ...close-condition-scan.py --by-state

⚠ THE VALUES WERE RIGHT AND THE MECHANISM WAS BROKEN -- in the one block whose
entire stated purpose is that the mechanism is named. Two-sided controls had been
run on the SET that PR added and none on the ROW it edited, because the number on
it was already known-good. A review bot caught it; no instrument here could.

★ WHY FOUR VERDICTS AND NOT PASS/FAIL, which is the whole design. This block is
DATED. Its numbers are SUPPOSED to go stale -- `merged PRs` moves hourly. A checker
that reported every stale number as a defect would bury the one row that is
actually broken under six that are merely old. So staleness and brokenness are
different verdicts, separated by SHAPE:

    CHECKED     the command ran and emitted exactly this value
    DRIFTED     it emitted a value of the RIGHT SHAPE and a different one
                -> the snapshot is old. Expected. Not a defect.
    MISMATCH    it emitted NOTHING OF THAT SHAPE -- no such label, no `N of M`
                -> the row names a command that cannot produce its value. THE DEFECT.
    UNRUNNABLE  a `<placeholder>` stands where a value must go, or the command
                could not be executed at all
                -> established nothing. Never read as clean.

⇒ MISMATCH is the verdict this exists for. DRIFTED is the noise it exists to keep
out of the way of MISMATCH.

WHAT THIS CANNOT DO. It cannot tell whether a value was ever correct, only whether
the named command emits that shape now. A row whose command was ALWAYS wrong and
whose number was always wrong reads MISMATCH, which is right; a row whose command
is wrong but which coincidentally emits a matching shape reads DRIFTED, which is
wrong and is the known hole. It also runs the commands, so a row needing the forge
reads UNRUNNABLE without a token -- unmeasured, not passing.

Exit: 0 nothing but CHECKED/DRIFTED · 1 at least one MISMATCH · 2 established
nothing (no block, no rows) · 3 the known-positive control failed.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from runmarker import guard, result  # noqa: E402

HANDOFF = "docs/HANDOFF.md"

# ⇒ The command starts at the first shell head. This is what makes the row splittable
# at all: `main CI rollup    success gh run list ...` has ONE space before `gh`, so a
# whitespace split cannot find the boundary and a command-head search can.
HEAD = re.compile(r"(?:^|\s)((?:gh|python3|grep|git|sed|awk)\s.*)$")
PLACEHOLDER = re.compile(r"<[a-z][a-z-]*>")
# ⛔ BOTH ORDERS, and it is not a nicety. close-condition-scan prints `NONE  (13)`
# and close-mechanism prints `    13  NO-CONDITION` -- label-first and count-first,
# two instruments in the same block. A matcher that knew only one order reported
# MISMATCH on a row whose command was fine, which is the false positive that would
# have discredited the whole check on its second use.
LABEL_FIRST = re.compile(r"\b([A-Z][A-Z-]{2,})[ \t]+\(?(\d+)\)?")
COUNT_FIRST = re.compile(r"\b(\d+)[ \t]+([A-Z][A-Z-]{2,})\b")


def labelled(text):
    """Every (LABEL, count) pair, in whichever order the emitter wrote it."""
    return ([(l, n) for l, n in LABEL_FIRST.findall(text)]
            + [(l, n) for n, l in COUNT_FIRST.findall(text)])
N_OF_M = re.compile(r"\b(\d+)\s+of\s+(\d+)\b")


def rows(text):
    """Every row of the FIRST fenced block after the 'what is true right now' heading.

    ⚠ The first block only. A later fence in this file holds the STRUCK previous
    snapshot, and re-checking a snapshot that is explicitly marked dead would
    manufacture findings out of a record kept on purpose."""
    m = re.search(r"^##\s+What is true right now\s*$", text, re.M | re.I)
    if not m:
        return []
    fence = re.search(r"^```\n(.*?)^```", text[m.end():], re.M | re.S)
    if not fence:
        return []
    out = []
    for line in fence.group(1).splitlines():
        h = HEAD.search(line)
        if not h:
            continue  # a continuation note, not a row
        cmd = h.group(1).strip()
        # ⚠ A trailing `(...)` set off by two spaces is an ANNOTATION -- the `gating
        # job` row already carries one. Passing it to the shell would turn a row's
        # prose into a syntax error and report UNRUNNABLE for a working command.
        cmd = re.sub(r"\s{2,}\(.*\)\s*$", "", cmd).strip()
        prefix = line[: h.start(1)].rstrip()
        parts = [p for p in re.split(r"\s{2,}", prefix.strip()) if p]
        if len(parts) < 2:
            continue
        out.append((parts[0], " ".join(parts[1:]), cmd))
    return out


def claims(value):
    """The value, decomposed into things an output can be searched for.

    Order matters: a labelled reading is tried first, because `NONE 13` must not be
    read as the bare integers 13 -- the label is what makes the shape checkable."""
    lab = labelled(value)
    if lab:
        return [("label", l, int(n)) for l, n in lab]
    nm = N_OF_M.search(value)
    if nm:
        return [("n_of_m", int(nm.group(1)), int(nm.group(2)))]
    ints = re.findall(r"\b(\d+)\b", value)
    if ints:
        return [("int", None, int(i)) for i in ints]
    return [("word", None, value.strip())]


def judge(claim, out):
    """CHECKED / DRIFTED / MISMATCH for one claim against one command's output."""
    kind, label, want = claim
    if kind == "label":
        # the label, then an integer within a short window -- `NONE  (13)` and
        # `NONE 13` are the same shape; `NONE` with no number is not the shape.
        found = [int(n) for l, n in labelled(out) if l == label]
        if not found:
            return "MISMATCH", f"{label} never appears followed by a number"
        if want in found:
            return "CHECKED", f"{label} {want}"
        return "DRIFTED", f"{label} {found[0]} now, {want} recorded"
    if kind == "n_of_m":
        seen = N_OF_M.findall(out)
        if not seen:
            return "MISMATCH", f"no `N of M` anywhere in the output; row claims {label} of {want}"
        if (str(label), str(want)) in seen:
            return "CHECKED", f"{label} of {want}"
        return "DRIFTED", f"{seen[0][0]} of {seen[0][1]} now, {label} of {want} recorded"
    if kind == "int":
        ints = re.findall(r"\b\d+\b", out)
        if not ints:
            return "MISMATCH", f"the output contains no integer at all; row claims {want}"
        if str(want) in ints:
            return "CHECKED", str(want)
        return "DRIFTED", f"{ints[0]} now, {want} recorded"
    if out.strip() == "":
        return "MISMATCH", f"empty output; row claims {want!r}"
    return ("CHECKED", want) if want in out else ("DRIFTED", f"{want!r} not in the output")


WORST = {"CHECKED": 0, "DRIFTED": 1, "UNRUNNABLE": 2, "MISMATCH": 3}


def check_row(name, value, cmd, runner):
    if PLACEHOLDER.search(cmd):
        return "UNRUNNABLE", [f"`{PLACEHOLDER.search(cmd).group(0)}` stands where a value must go"]
    out, err, rc = runner(cmd)
    # ⇒ THREE INDEPENDENT SIGNALS THAT NOTHING WAS ESTABLISHED, deliberately from
    # different mechanisms so one being wrong does not silence the other two:
    #   · exit 2 is THIS ESTATE'S convention -- "established nothing", never all-clear
    #   · exit 124 is OUR OWN timeout, raised as an exception and converted here
    #   · exit 127 is the RUNTIME saying the command does not exist
    #   · empty stdout is the COMMAND saying it produced no value
    # A row whose command could not reach its data must never read as a finding about
    # the row. MISMATCH accuses the document; UNRUNNABLE accuses nothing.
    if rc in (2, 124, 127):
        return "UNRUNNABLE", [f"exit {rc} — established nothing"
                              + (f": {err.strip().splitlines()[0][:90]}" if err.strip() else "")]
    if out.strip() == "":
        return "UNRUNNABLE", ["no output on stdout"
                              + (f"; stderr says: {err.strip().splitlines()[0][:90]}"
                                 if err.strip() else " and nothing on stderr either")]
    if "NFORMA-RESULT ESTABLISHED-NOTHING" in err:
        return "UNRUNNABLE", ["the subject declared ESTABLISHED-NOTHING on stderr"]
    verdicts = [judge(c, out) for c in claims(value)]
    worst = max(verdicts, key=lambda v: WORST[v[0]])[0]
    return worst, [f"{v} — {why}" for v, why in verdicts]


def shell(cmd):
    """⛔ STDOUT AND STDERR ARE RETURNED SEPARATELY, and that is the fix for the defect
    a runner found. The first version concatenated them, so `gh` with no token —
    empty stdout, an auth error on stderr — became "output that contains no integer",
    which is MISMATCH. Values are written to stdout; explanations of failure are
    written to stderr. Judging a value against stderr is judging it against prose."""
    # ⛔ TimeoutExpired is an EXCEPTION, not a returncode. Uncaught, one hung `gh`
    # takes the whole check down mid-run and every row after it goes unreported --
    # a crash where the honest answer is "this row established nothing".
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "", "timed out after 300s", 124
    return p.stdout, p.stderr, p.returncode


def _timeout_probe():
    """Run a command that WILL exceed the cap, so the exception path is exercised.

    ⚠ Deliberately not `sleep 300` -- a self-test that takes five minutes is a
    self-test nobody runs. The cap is monkeypatched down, which tests the same
    `except` clause the real cap reaches."""
    real = subprocess.run

    def capped(cmd, **kw):
        kw["timeout"] = 0.05
        return real(cmd, **kw)

    subprocess.run = capped
    try:
        return shell("sleep 5")
    finally:
        subprocess.run = real


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=HANDOFF)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        rc = self_test()
        result("SELF-TEST-PASS" if rc == 0 else "SELF-TEST-FAILED")
        return rc

    if not os.path.isfile(a.file):
        print(f"⛔ ESTABLISHED NOTHING — {a.file!r} is not a file. VOID.")
        result("ESTABLISHED-NOTHING")
        return 2
    with open(a.file, encoding="utf-8") as fh:
        text = fh.read()
    rs = rows(text)
    if not rs:
        print(f"⛔ ESTABLISHED NOTHING — no snapshot rows found in {a.file}. VOID: zero rows "
              f"read and zero defects print the same clean line.")
        result("ESTABLISHED-NOTHING")
        return 2

    print(f"── HANDOFF ROWS ── {len(rs)} row(s) in {a.file}, each run as written")
    tally = {}
    bad = []
    for name, value, cmd in rs:
        verdict, why = check_row(name, value, cmd, shell)
        tally[verdict] = tally.get(verdict, 0) + 1
        mark = {"CHECKED": "✅", "DRIFTED": "⚠", "MISMATCH": "⛔", "UNRUNNABLE": "⚠"}[verdict]
        print(f"  {mark} {verdict:10} {name}")
        for w in why:
            print(f"                 {w}")
        if verdict == "MISMATCH":
            bad.append((name, cmd))
    print("\n  " + " · ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    if not bad:
        print("⇒ no row names a command that cannot produce its value.")
        print("⚠ DRIFTED is not a defect: the block is dated and its numbers are meant to age.")
        print("⚠ UNRUNNABLE established NOTHING about that row — it is not a pass.")
        result("CLEAN" if tally.get("UNRUNNABLE", 0) == 0 else "PARTIAL")
        return 0
    print("⛔ these rows name a command that emits NOTHING OF THAT SHAPE:")
    for name, cmd in bad:
        print(f"     {name}  ->  {cmd}")
    result("FINDINGS")
    return 1


def self_test():
    """⛔ Two-sided, and the known-NEGATIVE is the real #636 row.

    A checker that returned MISMATCH for everything would satisfy a suite made only
    of defects, and one that returned CHECKED for everything would satisfy a suite
    made only of clean rows. Both poles are here and both are NAMED in the output."""
    if not __debug__:
        print("⛔ ESTABLISHED NOTHING — run without -O. Assertions are this suite.")
        return 2

    # (label, value, command, canned output, expected verdict, why this case exists)
    # (label, value, command, stdout, stderr, rc, expected)
    cases = [
        ("✅ KNOWN-POSITIVE  the row as it stands on main today",
         "NONE 13 · BURIED 0 · BODY 90", "python3 tools/close-condition-scan.py",
         "NONE  (13)\nBURIED  (0)\nBODY    (90)", "CHECKED"),

        ("⛔ KNOWN-NEGATIVE  the exact #636 defect: --by-state emits no totals",
         "NONE 13 · BURIED 0 · BODY 90", "python3 tools/close-condition-scan.py --by-state",
         "NONE 583\nNONE 582\nBODY 631\nBODY 601", "MISMATCH"),

        ("⚠ a stale number under a WORKING command is DRIFTED, not a defect",
         "ASSERTED 34 · RUNNABLE 25 · NO-CONDITION 44", "python3 tools/runnable-condition.py",
         "ASSERTED  (35)\nRUNNABLE  (25)\nNO-CONDITION  (44)", "DRIFTED"),

        ("⛔ `N of M` claimed, and the command emits no `N of M` at all",
         "21 of 103", "python3 tools/close-mechanism.py",
         "    13  NO-CONDITION\n     8  OPERATOR", "MISMATCH"),

        ("✅ COUNT-FIRST: `    13  NO-CONDITION` is the same shape as `NONE  (13)`",
         "NO-CONDITION 13 · OPERATOR 8", "python3 tools/close-mechanism.py",
         "    13  NO-CONDITION    ⛔ no pane can close these\n"
         "     8  OPERATOR        ⛔ no pane can close these", "CHECKED"),

        ("⛔ CONTROL count-first does not make every number match every label",
         "NO-CONDITION 99", "python3 tools/close-mechanism.py",
         "    13  NO-CONDITION", "DRIFTED"),

        ("✅ a bare integer that the command does emit",
         "454", "gh pr list --json number --jq length", "454", "CHECKED"),

        ("⚠ a bare integer the command does not emit, but it emits integers",
         "454", "gh pr list --json number --jq length", "455", "DRIFTED"),

        ("⛔ a bare integer where the command emits NO integer — mechanism gone",
         "454", "gh pr list --json number", "[]\nno results", "MISMATCH"),

        ("✅ a bare word",
         "success", "gh run list --json conclusion", '[{"conclusion":"success"}]', "CHECKED"),

        ("⚠ UNRUNNABLE: a placeholder stands where a value must go",
         "76s", "gh run view <id> --json jobs", "unused", "UNRUNNABLE"),
    ]
    # ⛔ THE CASES A RUNNER HANDED ME, and I could not have written them from here.
    # Locally every command runs; there was no way to construct "the command cannot
    # reach its data" until CI supplied an environment with no token. The first version
    # scored all three as MISMATCH. See [run 34139504952].
    cases = [(l, v, c, o, "", 0, w) for l, v, c, o, w in cases] + [
        ("⚠ CI's case: `gh` with no token — empty stdout, an auth error on stderr",
         "454", "gh pr list --json number --jq length",
         "", "gh: To use GitHub CLI in automation, set the GH_TOKEN environment variable", 4,
         "UNRUNNABLE"),

        ("⚠ exit 2 is THIS ESTATE'S 'established nothing' — never a finding about the row",
         "NONE 13 · BURIED 0 · BODY 90", "python3 tools/close-condition-scan.py",
         "⛔ ESTABLISHED NOTHING — the query returned no issues.", "", 2, "UNRUNNABLE"),

        ("⚠ the subject's own stderr marker is a SECOND, independent unrunnable signal",
         "NONE 13", "python3 tools/close-condition-scan.py",
         "some prose but no verdict", "NFORMA-RESULT ESTABLISHED-NOTHING", 0, "UNRUNNABLE"),

        ("⛔ CONTROL a non-zero exit that is a FINDING (1) is still judged, not excused",
         "NONE 13", "python3 tools/close-condition-scan.py", "NONE  (13)", "", 1, "CHECKED"),

        ("⛔ CONTROL stderr is NOT searched for the value — prose is not a measurement",
         "454", "gh pr list --json number --jq length", "0", "the answer is 454", 0, "DRIFTED"),

        ("⚠ a command that HANGS is UNRUNNABLE, not a crash that eats every later row",
         "454", "gh pr list --json number --jq length", "", "timed out after 300s", 124,
         "UNRUNNABLE"),
    ]
    ok = True
    for label, value, cmd, out, err, rc, want in cases:
        got, why = check_row("row", value, cmd,
                             lambda _c, o=out, e=err, r=rc: (o, e, r))
        good = got == want
        ok &= good
        print(f"{'✅' if good else '❌'} {label}\n     want {want:10} got {got}")
        if not good:
            for w in why:
                print(f"       {w}")

    # ⛔ A control OUTSIDE the case table: the parser itself must refuse a file with
    # no block rather than report it clean. `_extra` is incremented HERE rather than
    # written as a literal, because a hand-written total has twice reported N/N while
    # N+1 controls ran.
    _extra = 0
    _extra += 1
    no_block = rows("# a file\n\nnothing here at all\n")
    good = no_block == []
    ok &= good
    print(f"{'✅' if good else '❌'} ⛔ CONTROL a file with no snapshot block yields NO rows "
          f"(so the caller reports VOID, not clean) — got {len(no_block)}")

    _extra += 1
    parsed = rows("## What is true right now\n\n```\n"
                  "merged PRs        454    gh pr list --json number --jq length\n"
                  "main CI rollup    success gh run list --limit 1 --json conclusion\n"
                  "                         ⚠ a continuation note, not a row\n"
                  "```\n")
    want = [("merged PRs", "454", "gh pr list --json number --jq length"),
            ("main CI rollup", "success", "gh run list --limit 1 --json conclusion")]
    good = parsed == want
    ok &= good
    print(f"{'✅' if good else '❌'} ✅ CONTROL the splitter finds the command head with ONE "
          f"space before it, and drops the continuation line")
    if not good:
        print(f"       got {parsed!r}")

    _extra += 1
    ann = rows("## What is true right now\n\n```\n"
               "no close path   NO-CONDITION 13   python3 tools/close-mechanism.py  "
               "(21 of 104; the sum is ours)\n```\n")
    good = ann and ann[0][2] == "python3 tools/close-mechanism.py"
    ok &= bool(good)
    print(f"{'✅' if good else '❌'} ✅ CONTROL a trailing `(...)` annotation is stripped from "
          f"the command — got {ann[0][2]!r}" if ann else "❌ no row parsed")

    # ⛔ THE REAL subprocess PATH, not the fake runner. The case above proves judge()
    # handles rc 124; only this proves shell() converts the EXCEPTION into it. Same
    # defect, two layers -- and the fake runner can never reach the second.
    _extra += 1
    _o, _e, _rc = _timeout_probe()
    good = (_rc == 124 and _o == "")
    ok &= good
    print(f"{'✅' if good else '❌'} ⚠ CONTROL shell() converts a real TimeoutExpired into "
          f"rc 124 with empty stdout — got rc={_rc}, stdout={_o!r}")

    n = len(cases) + _extra
    print(f"\n{'all ' + str(n) + ' checks passed' if ok else 'FAILED'}")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(guard("check-handoff-rows", main))
