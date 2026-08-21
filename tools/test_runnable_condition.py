#!/usr/bin/env python3
"""Hermetic suite for tools/runnable-condition.py. No git, no network, no fleet.

⛔ WHY THIS FILE EXISTS, and it is a correction to a merged claim. #399's commit message
named `scripts/gate-selftests.sh` as this instrument's caller, per criterion 4 as amended
in #381 ("shown to FAIL on real data BY A CALLER THAT STILL RUNS IT"). Measured afterwards:

    gate-selftests.sh   SUBJ_DIR defaults to `scripts`, ran 4 subjects, none under tools/
    the tools/ gate     ./scripts/exit-code-gate.sh tools 'test_*.py'  -- PAIRED SUITES ONLY
    test_runnable_condition.py                                          DID NOT EXIST

⇒ So its --self-test had NO CALLER AT ALL. I verified the script existed and that a workflow
referenced it, and never checked the POPULATION that script draws -- criterion 5's population
leg, missed by the pane that had ruled on it twice that evening.
"""
import importlib.util, os, sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "runnable_condition", os.path.join(_here, "runnable-condition.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

FAILED = 0


def check(name, got, want):
    global FAILED
    if got != want:
        print(f"  FAIL  {name}: got {got!r}, want {want!r}")
        FAILED += 1
    else:
        print(f"  PASS  {name}: got {got!r}, want {want!r}")


def main():
    print("NFORMA-RUN test_runnable_condition", file=sys.stderr)

    # --- the positive direction
    check("command + arrow result", rc.classify(
        "## Done when\n```\ngh issue list --label x   ->   empty\n```")[0], "RUNNABLE")
    check("command + exit code", rc.classify(
        "**Done when:**\n```\npython3 tools/x.py --self-test   exit 0\n```")[0], "RUNNABLE")
    # ⛔ the closed-list regression: the first predicate enumerated command names and could
    #    not see grep. A vocabulary over an open-ended noun (#348).
    check("grep is not in any list and must still count", rc.classify(
        "## Done when\n```\ngrep -c 'x' file.js   ->   0\n```")[0], "RUNNABLE")
    check("a path-bearing diff counts", rc.classify(
        "## Done when\n```\ndiff /tmp/a /tmp/b   ->   empty\n```")[0], "RUNNABLE")

    # --- the negative direction, which is what makes the positive mean anything
    check("prose agreement", rc.classify(
        "## Done when\nthe fleet agrees the situation has improved.")[0], "ASSERTED")
    # ⛔ the over-widening regression: "the count must be zero." matched as `the` + an arg.
    check("a two-word sentence is not a command line", rc.classify(
        "## Done when\nthe count must be zero.")[0], "ASSERTED")
    check("command with no stated result", rc.classify(
        "## Done when\n```\ngh issue list\n```")[0], "ASSERTED")
    check("stated result with no command", rc.classify(
        "## Done when\nthe count must reach zero eventually.")[0], "ASSERTED")
    # ⛔ use vs mention (#36): prose that TALKS about running something
    check("a mention of gh is not an invocation", rc.classify(
        "## Done when\nsomeone runs gh issue list and is satisfied.")[0], "ASSERTED")
    # ⛔ population: a command ABOVE the clause is not the condition
    check("a command above the clause does not count", rc.classify(
        "```\ngh pr list -> empty\n```\n\n## Done when\nwe are happy.")[0], "ASSERTED")

    # --- the third state must be reachable, or the other two are a boolean wearing three names
    check("no clause at all", rc.classify("just a body.")[0], "NO-CONDITION")

    # --- the tool's own runtime controls must fire, or its verdicts establish nothing
    (pos, neg, none), got = rc.controls()
    check("runtime controls fire in all three directions", (pos, neg, none), (True, True, True))

    print(f"\n{'all checks passed' if not FAILED else f'{FAILED} FAILED'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
