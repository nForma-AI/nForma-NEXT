#!/usr/bin/env python3
# ⚠ r-string: this docstring contains `\$?`, which is an invalid escape in a
# normal string and emits a SyntaxWarning on import — an error in a future Python.
r"""Find exit codes read through a pipe — the measurement that isn't one.

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
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runmarker import guard, result  # noqa: E402

import glob, json, os, re, subprocess, sys, time

# `cmd | cmd ; echo $?`  — the status read belongs to the LAST pipeline element.
#
# ⛔ THIS PATTERN ALONE FIRES ON THE CORRECT IDIOM. `cmd | look; cmd >/dev/null; echo $?`
# — run piped to see it, re-run redirected to measure it — is the RIGHT form, and the
# regex spans both commands and reports it. Its sibling tools/pretooluse-guard.py already
# had the refinement and this file did not: two matchers for one idiom in one directory,
# disagreeing, with the naive one wired to the scanner people actually read.
#
# ⚠ A guard that fires on an agent doing the right thing is the worst kind: it teaches the
# agent to stop doing it. So the regex is now a PREFILTER and the verdict comes from
# reading segment order.
AFTER_PIPE = re.compile(r"\|[^|&;]+[;&][^#\n]*\$\?")
DOLLAR_Q = re.compile(r"\$\?")


def pipeline_status_read(line):
    """Does `$?` here read the status of a PIPELINE?

    Split on separators and ask whether the segment IMMEDIATELY BEFORE the read is
    piped. Ported from tools/pretooluse-guard.py, which had it first.
    """
    segs = re.split(r"(?<![|&])[;&](?![&|])|&&", line)
    for i, seg in enumerate(segs):
        if not DOLLAR_Q.search(seg):
            continue
        prev = next((s for s in reversed(segs[:i]) if s.strip()), "")
        if "|" in prev:
            return True
    return False
# `${PIPESTATUS[n]}` — bash-only. Empty in zsh, and empty is not zero.

# ── Lost VARIABLE STATE, the sibling defect ──────────────────────────────────
#
# ⛔ `cmd | while read ...; done` runs the loop body in a SUBSHELL. Every
# assignment inside dies when the subshell exits, so the loop can print N verdicts
# and increment a counter N times while the caller still reads 0.
#
# Measured in this repository: fleet-preflight.sh printed 8 worktree FAILs and its
# summary said `1 fail`. The matcher above scanned that file and reported nothing,
# because nothing was wrong with an EXIT CODE — the loss was variable state.
#
# ★ The body often assigns NOTHING ITSELF. That instance called `bad "$r ..."`, and
# `bad()` was defined at the top of the file and did the increment. A matcher that
# reads only the loop body is blind to exactly the case worth catching, so function
# bodies are resolved one level deep.
#
# ⚠ Deliberately NOT flagged, because both are harmless and common:
#   · a loop whose only effect is printing
#   · a loop whose variables are never read after `done`
# Flagging those would produce a count that reads as work-to-do, which this file's
# own selftest calls worse than no scanner at all.
PIPE_INTO_WHILE = re.compile(r"\|\s*while\b")
FUNC_DEF = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*\{")
ASSIGN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:=(?!=)|\+=)")
ARITH = re.compile(r"\(\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\+\+|--|[-+*/%]?=)")


def _assigned_in(lines):
    """Variable names assigned anywhere in these lines."""
    out = set()
    for ln in lines:
        code = strip_comment(ln)
        for m in ASSIGN.finditer(code):
            out.add(m.group(1))
        for m in ARITH.finditer(code):
            out.add(m.group(1))
    return out


def _function_assignments(lines):
    """name -> variables it assigns. Brace-depth scan; good enough for shell that
    indents, and it UNDER-reports rather than over-reports on shell that does not."""
    funcs, i, n = {}, 0, len(lines)
    while i < n:
        m = FUNC_DEF.match(strip_comment(lines[i]))
        if not m:
            i += 1
            continue
        name, depth, body, j = m.group(1), 0, [], i
        while j < n:
            code = strip_comment(lines[j])
            depth += code.count("{") - code.count("}")
            body.append(lines[j])
            j += 1
            if depth <= 0:
                break
        funcs[name] = _assigned_in(body)
        i = j
    return funcs


def scan_shell_subshell(path):
    """Pipes into `while` whose body mutates state the caller reads afterwards."""
    hits = []
    try:
        lines = open(path, errors="replace").read().splitlines()
    except OSError:
        return hits
    funcs = _function_assignments(lines)
    for n0, raw in enumerate(lines):
        code = strip_comment(raw)
        if not PIPE_INTO_WHILE.search(code):
            continue
        # body runs to the matching `done`
        depth, j, body = 0, n0, []
        while j < len(lines):
            c = strip_comment(lines[j])
            depth += len(re.findall(r"\b(?:do|if|case)\b", c))
            depth -= len(re.findall(r"\b(?:done|fi|esac)\b", c))
            body.append(lines[j])
            j += 1
            if depth <= 0 and j > n0:
                break
        mutated = _assigned_in(body[1:])
        for name, assigned in funcs.items():
            if re.search(r"(?:^|[\s;&|(])" + re.escape(name) + r"(?:[\s;&|)]|$)",
                         " ".join(strip_comment(b) for b in body[1:])):
                mutated |= assigned
        # ⚠ A variable the loop declares and never exports is not state the caller
        # loses — only names read AFTER `done` count.
        after = "\n".join(strip_comment(l) for l in lines[j:])
        leaked = sorted(v for v in mutated
                        if re.search(r"\$\{?" + re.escape(v) + r"\b", after))
        if leaked:
            hits.append((n0 + 1, raw.strip(),
                         "`cmd | while` runs the body in a SUBSHELL — "
                         f"{', '.join(leaked[:4])} is assigned there and read after `done`, "
                         "so the caller sees the pre-loop value. Use `done < <(cmd)`"))
    return hits


PIPESTATUS = re.compile(r"\$\{PIPESTATUS\[")
FENCE = re.compile(r"^\s*```\s*(bash|sh|shell|console)\s*$", re.I)
FENCE_END = re.compile(r"^\s*```\s*$")



HEREDOC = re.compile(r"<<-?\s*'?\"?([A-Za-z_][A-Za-z0-9_]*)'?\"?\n(.*?)^\1\s*$", re.S | re.M)


def executable_part(cmd):
    """⛔ Strip heredoc BODIES. Measured on 204 real agent commands: the dominant
    false positive is a command that WRITES DOCUMENTATION ABOUT the idiom — a
    README paragraph, a fixture, a commit message, a friction report. Every one is
    a mention being written, not a pipeline being run. Same use/mention split as
    the prose exclusion, one layer in: a heredoc body is content, the shell around
    it is code.
    """
    return HEREDOC.sub("\n", cmd)


TRANSCRIPTS = os.path.expanduser("~/.claude/projects")


def scan_transcripts(limit_hours=None, project=None):
    """The population the defect actually lives in: agent shell invocations.

    ⛔ Matches ONLY on `tool_use` records whose `name` is Bash, reading the
    `command` field. Never assistant text. That is not a heuristic — it is the
    use/mention discriminator as a key lookup: a command field is an EFFECT, prose
    is a DESCRIPTION, and no wording can make one look like the other.

    Measured by DEV2 over this fleet's transcripts: 32 real invocations across 7 of
    9 sessions, against 18 prose mentions in the same corpus. A text scan would
    report 50 — a 56% over-report, every one of them a sentence about the trap.

    ⛔ AND THAT NUMBER WAS TAKEN OVER A POPULATION THIS FUNCTION DOES NOT SCAN.
    It globs ~/.claude/projects/* — EVERY repository this machine has worked on —
    while the sentence above says "this fleet's transcripts". Re-measured 2026-08-20:

        scope                          hits   sessions   project dirs
        every project on the machine   1,317        82            27
        this fleet's project dir         251        15             4

    The largest single contributor is an unrelated project. ⇒ `--project SUBSTR`
    scopes it, and every run now prints the scope and the population, because a rate
    without its denominator is the defect two of this repository's own tools were
    already caught quoting.
    """
    hits = []
    per = {}
    for proj in glob.glob(os.path.join(TRANSCRIPTS, "*")):
        base = os.path.basename(proj)
        if project and project not in base:
            continue
        before = len(hits)
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            if limit_hours and time.time() - os.path.getmtime(path) > limit_hours * 3600:
                continue
            try:
                fh = open(path, errors="replace")
            except OSError:
                continue
            for ln, line in enumerate(fh, 1):
                if '"tool_use"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                for b in (rec.get("message") or {}).get("content") or []:
                    if not (isinstance(b, dict) and b.get("type") == "tool_use"
                            and b.get("name") == "Bash"):
                        continue
                    cmd = (b.get("input") or {}).get("command") or ""
                    body = executable_part(cmd)
                    for src in body.splitlines():
                        code = strip_comment(src)
                        if AFTER_PIPE.search(code) and pipeline_status_read(code):
                            hits.append((os.path.basename(path)[:8], ln, src.strip(),
                                         "$? read after a pipeline, in an EXECUTED command"))
                        elif PIPESTATUS.search(code):
                            hits.append((os.path.basename(path)[:8], ln, src.strip(),
                                         "PIPESTATUS in an EXECUTED command"))
        if len(hits) > before:
            per[base] = len(hits) - before
    return hits, per


HEREDOC_HELP = "--transcripts    scan agent shell invocations instead of committed files"

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
        if AFTER_PIPE.search(code) and pipeline_status_read(code):
            hits.append((n, raw.strip(), "$? read after a pipeline — that is the LAST element's status"))
        elif PIPESTATUS.search(code):
            hits.append((n, raw.strip(), "PIPESTATUS — bash-only; expands EMPTY in zsh, and empty is not zero"))
    # ⛔ Second matcher, second defect. Kept as its own pass because it needs the
    # WHOLE file (function bodies, and what is read after the loop), which the
    # line-at-a-time loop above structurally cannot see.
    hits.extend(scan_shell_subshell(path))
    hits.sort(key=lambda h: h[0])
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
        if AFTER_PIPE.search(code) and pipeline_status_read(code):
            hits.append((n, raw.strip(), "$? read after a pipeline, inside a ```bash block — docs teach this"))
        elif PIPESTATUS.search(code):
            hits.append((n, raw.strip(), "PIPESTATUS inside a ```bash block"))
    return hits


SELFTEST_POSITIVE = "tools/testdata/pipe-exit-positive.sh"
# ⛔ Its own fixture, holding POSITIVES AND NEGATIVES together: a fixture of only
# positives cannot distinguish "detects the defect" from "fires on every while loop".
SELFTEST_SUBSHELL = "tools/testdata/subshell-positive.sh"
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
    # ── the subshell matcher, both directions in one fixture ─────────────────
    sub = scan_shell_subshell(SELFTEST_SUBSHELL)
    if len(sub) == 3:
        print(f"  ok    subshell known-positive: 3 findings in {SELFTEST_SUBSHELL}")
        for n, s_, _ in sub:
            print(f"          L{n}: {s_[:64]}")
        print("  ok    subshell known-negative: 0 of 3 negatives fired "
              "(process substitution, print-only loop, unread variable)")
    else:
        print(f"  FAIL  subshell matcher: {len(sub)} findings, expected exactly 3. "
              f"Fewer means the failing path does not fire; more means it fires on a "
              f"loop that loses nothing, which is the worse direction.")
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
    # ⛔ `--self-test` is the directory convention; six tools use it and this file
    # was the only `--selftest`. A known-positive reachable only under a name
    # nobody would guess is worse than an absent one, because its existence has
    # been ASSERTED. A reviewer pointed the tool at the fixture, got the normal
    # scan, and nearly recorded that as a clean negative.
    if "--self-test" in sys.argv or "--selftest" in sys.argv:
        return selftest()
    if "--transcripts" in sys.argv:
        project = None
        if "--project" in sys.argv:
            i = sys.argv.index("--project")
            if i + 1 >= len(sys.argv):
                print("⛔ --project needs a value", file=sys.stderr)
                return 2
            project = sys.argv[i + 1]
        hits, per = scan_transcripts(project=project)
        if not per and project:
            print(f"⛔ no project directory matched {project!r} — ESTABLISHED NOTHING, "
                  f"not a clean scan.", file=sys.stderr)
            return 2
        for sid, ln, src, why in hits:
            print(f"{sid}:{ln}\n    {src}\n    ⇒ {why}")
        # ⛔ Print the population. This function globs EVERY project on the machine,
        # and the docstring above it called that "this fleet's transcripts" until
        # 2026-08-20. A rate without its denominator is the defect this repository
        # has now caught two of its own tools quoting.
        top = max(per.items(), key=lambda kv: kv[1]) if per else ("-", 0)
        print(f"\nscope                  {project or 'ALL PROJECTS on this machine'}",
              file=sys.stderr)
        print(f"project dirs with hits {len(per)}", file=sys.stderr)
        print(f"largest contributor    {top[1]}  {top[0][-44:]}", file=sys.stderr)
        print(f"{len(hits)} occurrence(s) in EXECUTED commands across agent transcripts.",
              file=sys.stderr)
        if not project and len(per) > 1:
            print(f"⚠ UNSCOPED — every repository this machine has worked on, not this "
                  f"fleet. Pass --project SUBSTR to scope it, and quote the corpus and the "
                  f"date beside any rate taken from it: this corpus grows.", file=sys.stderr)
        print("⚠ OCCURRENCES, not defects. Some will be in contexts where the exit code was "
              "not load-bearing; this establishes the rate, not that every one produced a "
              "wrong reading.", file=sys.stderr)
        print("⛔ Matched on `tool_use`.`command` ONLY — never assistant prose. The same "
              "corpus holds prose mentions of this exact idiom, including this repo's own "
              "convention documenting it, and a text scan over it over-reports by ~56%.",
              file=sys.stderr)
        _rc = 1 if hits else 0
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
            continue          # fixtures are scanned only by --self-test
        if is_shell(p):
            scanned += 1
            findings += [(p, *h) for h in scan_shell(p)]
        elif p.endswith(".md"):
            scanned += 1
            findings += [(p, *h) for h in scan_markdown(p)]
    if scanned == 0:
        print("⛔ zero scannable files — ESTABLISHED NOTHING, not clean.", file=sys.stderr)
        return 2

    # ★ The control runs on EVERY scan, not only under a flag. `0 findings` is the
    # output this tool almost always produces, and it is indistinguishable between
    # "nothing matched" and "the matcher is broken" unless something known-positive
    # fires in the same run. Cheap: three regex applications against a tracked file.
    kp = [h for h in scan_shell(SELFTEST_POSITIVE) if "MUST NOT" not in h[1]]
    if len(kp) < 3:
        print(f"⛔ CONTROL FAILED: the known-positive fixture matched {len(kp)} of 3 "
              "idioms. The matcher cannot fire, so a finding count from this run — "
              "including zero — establishes NOTHING. No verdict is emitted.",
              file=sys.stderr)
        return 3

    for path, n, src, why in findings:
        print(f"{path}:{n}")
        print(f"    {src}")
        print(f"    ⇒ {why}")
    print(f"\n{len(findings)} finding(s) across {scanned} scanned file(s). "
          f"known-positive fired {len(kp)}/3.", file=sys.stderr)
    print("⛔ SCOPE: COMMITTED FILES ONLY. Every observed instance of this defect — six, "
          "four roles, one day — was an ad-hoc shell command, and NONE was in a committed "
          "file. So `0 findings` means NO COMMITTED FILE CONTAINS IT. It is not evidence "
          "about the population the defect actually lives in, which this tool structurally "
          "cannot see. ⇒ ADDABLE — NEEDS A DIFFERENT INSTRUMENT: a PreToolUse hook is the "
          "only surface where those commands exist; matcher committed at "
          "tools/pretooluse-guard.py. ⛔ ITS FIRE RATE CITATION IS RETRACTED: '1.5% "
          "fleet-wide (25 of 1720)' was taken over every project on this machine, not "
          "this fleet, and the 1,720 corpus does not reproduce (179,216 today). "
          "Re-measured 2026-08-20: 0.70% scoped to this fleet, 0.59% unscoped. The 80% "
          "precision was hand-classified 4-true/1-false on 204 commands from ONE "
          "session and is a different, unrepaired denominator problem. Mechanism "
          "untested, not installed.", file=sys.stderr)
    print("⚠ Matched on SHAPE after stripping comments and skipping non-fenced prose. "
          "Occurrences inside comments, and inline `PIPESTATUS` in prose, are MENTIONS and "
          "are deliberately not reported — this repo's own warning paragraph is one, and "
          "firing on it would be the defect rather than the find.", file=sys.stderr)
    print("⚠ Does not parse shell: a `#` inside a quoted string ends the line early, so it "
          "UNDER-reports there. Chosen over over-reporting on prose.", file=sys.stderr)
    return 1 if findings else 0


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
    sys.exit(guard("pipe-exit-scan", _entry))
