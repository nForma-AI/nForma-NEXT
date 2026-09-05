#!/usr/bin/env python3
# NOT-EXECUTABLE: a module. tools/README.md: 'not an instrument; a module. It is imported, never run.' No __main__, no argv surface.
"""Two stderr markers that separate *never ran* from *ran and established nothing*.

⛔ THE DEFECT, measured (#58). Three different things produce `exit 2`, and the
caller cannot tell them apart:

    python3 tools/missing.py        -> 2   the RUNTIME refused the file
    tool.py --bad-flag              -> 2   argparse rejected the ARGUMENTS
    our own "established nothing"   -> 2   the CONVENTION

⚠ And the exit code is not even reliably reachable. Measured twice in one session
by one agent: `tool.py | head` returns HEAD's status, so a subject exiting 1 reads
as 0. `${PIPESTATUS[0]}` is empty in zsh. ⇒ The convention in tools/README.md --
"exit 2 means established nothing and must never be read as all clear" -- is
correct and UNENFORCEABLE as written, because two of the three producers of 2 are
outside this repository's control.

★ WHY STDERR, AND IT IS THE WHOLE DESIGN. `cmd | head` consumes STDOUT. stderr is
not piped -- it goes straight to the terminal, untouched, and survives exactly the
construct that destroys the exit code. So the sentinel that survives a pipe is a
stderr sentinel, and it costs nothing.

⇒ It also keeps DATA-PRODUCING tools honest. ci-log-clean.py emits a cleaned log
on stdout; a marker injected there would corrupt the artifact it exists to
produce. On stderr it cannot.

THE STATE TABLE, and three states from two markers:

    no RUN line                    -> NEVER RAN. The runtime refused the file.
                                      The exit code is meaningless.
    RUN, no RESULT                 -> STARTED AND DIED. A crash, or arguments
                                      rejected. Distinguishable because RUN is
                                      emitted BEFORE argument parsing.
    RUN + RESULT: <state>          -> ran to a controlled conclusion; the state
                                      is the tool's own verdict.

⛔ Emitting RUN before argparse is the load-bearing detail. It is what separates
"the runtime refused the file" from "the tool rejected your flags" -- two things
that are byte-identical at exit 2 today.

⚠ WHAT THIS DOES NOT DO. It does not make the exit code correct, and it is not a
substitute for reading it. A caller that checks neither is unchanged. This removes
the exit code's monopoly; it does not remove the need to look.

Usage:
    from runmarker import begin, result, guard
    begin("grant-check")            # FIRST, before argparse
    ...
    result("ESTABLISHED-NOTHING")   # on every controlled path
"""
import subprocess
import sys

PREFIX_RUN = "NFORMA-RUN"
PREFIX_RESULT = "NFORMA-RESULT"


def tree_distance():
    """How far is THIS WORKING TREE behind `origin/main`? "" when unmeasurable.

    ⛔ WHY THE MARKER CARRIES IT. #205: nine panes share one working tree, and that tree has
    been pinned at `a163854` for two days — **365 commits behind**, with `CLAUDE.md` differing by
    25 lines and `goals/` by 2046. Every reading taken there is a reading of a two-day-old
    repository, and nothing said so.

    ⇒ AND CI CANNOT DETECT IT, STRUCTURALLY. A workflow checks out fresh, so a gate NEVER sees a
    pane's working tree. That is why #205 outlived every other missing-caller gap tonight: each
    of those was closed by adding a caller in CI, and this one cannot be. The caller has to run
    WHERE THE STALENESS LIVES — and 13 instruments already import this module, so they are it.

    ★ `tools/doctrine-uncommitted.py` fires on exactly this condition and has reported it to
    nobody for two days: `git grep -l` finds four references — the tool, its test, its docs, its
    ledger. A detector with no caller and a rule with no enforcement fail identically.

    ⚠ COSTS 14ms, measured. And it is REPORTED, NEVER ENFORCED: a stale tree is not an error and
    this must not turn one into a failure. It is the label a reading always needed — the same
    move as `ON <local|CI>` in the gate summary, applied to the tree instead of the machine.
    """
    try:
        r = subprocess.run(["git", "rev-list", "--count", "HEAD..origin/main"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    n = r.stdout.strip()
    if r.returncode != 0 or not n.isdigit():
        # ⛔ UNMEASURABLE IS NOT ZERO. No repository, no `origin/main`, a failed call — each
        # would read as "current" if this returned 0, which is the confident-wrong-answer this
        # whole convention exists against.
        return " tree=UNKNOWN"
    return "" if n == "0" else f" tree={n}-behind-origin/main"


def begin(tool):
    """Emit the start marker. ⛔ Call before argument parsing, or the marker cannot
    separate a rejected flag from a refused file."""
    print(f"{PREFIX_RUN} {tool}{tree_distance()}", file=sys.stderr, flush=True)


def result(state):
    """Emit the terminal marker. Call on EVERY path the tool controls -- a path
    that returns without one is indistinguishable from a crash, which is the
    correct reading only if it actually crashed."""
    print(f"{PREFIX_RESULT} {state}", file=sys.stderr, flush=True)


def guard(tool, main_fn):
    """Run main_fn with the markers around it.

    argparse raises SystemExit from inside parse_args, which is why BAD-ARGS is
    reported here rather than at each call site: the tool never regains control."""
    begin(tool)
    try:
        code = main_fn()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        result("BAD-ARGS" if code == 2 else f"EXIT-{code}")
        return code
    return code
