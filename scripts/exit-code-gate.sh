#!/bin/bash
# Run the hermetic test suites and classify each by exit code into THREE outcomes.
#
# ⛔ WHY THIS IS NOT `python3 "$f" || fail=1`. That shape has two outcomes, and #58 measured
# that the exit codes carry more than two states. `2` is this repository's "I established
# nothing"; it is ALSO what the Python runtime emits for a file it cannot open and what
# argparse emits for an argument it will not accept. Folding all of them into FAILED is
# operationally safe and epistemically FALSE: it reports a DEFECT where there was a REFUSAL,
# and a reader goes and fixes a test that was never broken.
#
# ⚠ FAIL-CLOSED-AND-WRONG IS THE MORE DANGEROUS PAIR, because nobody challenges a gate that
# erred toward caution. So the gate blocks on `2` — and says something different about it.
#
#     0        PASSED         the suite ran and concluded
#     2        UNESTABLISHED  the suite did not conclude. ⛔ NOT a pass. ⛔ NOT a failure.
#                             No claim about the code under test follows, either way.
#     other    FAILED         the suite ran and found a defect
#
# ⇒ And the GATE'S OWN exit obeys the same convention it enforces:
#     0  every suite concluded and passed
#     1  at least one suite FAILED                    (a finding)
#     2  no failures, but at least one UNESTABLISHED  (established nothing)
#     2  zero suites matched the glob                 (established nothing)
# All of 1 and 2 block a merge. The number is for the reader, not for the gate.
#
# ⛔ WHAT THIS STILL CANNOT DISTINGUISH, demonstrated by execution in --self-test rather
# than asserted here: a suite that exits 2 because IT decided it established nothing, and a
# suite that exits 2 because the runtime refused it — a bad flag, or a file that vanished
# between the glob and the run. Both read UNESTABLISHED. ARCHITECT's Tier 1 remedy on #58 is
# the only thing that separates them (a start marker emitted BEFORE argument parsing, whose
# ABSENCE proves the tool never ran), and it is not available here: measured 2026-08-20,
# 2 of 30 `tools/test_*.py` files touch `runmarker` at all. ⇒ A gate cannot read a marker
# that 28 of its subjects do not emit. Stated, not designed around.
#
# ⚠ THE POPULATION IS A GLOB WITH A PER-FILE OPT-OUT, and that is deliberate — see the
# comment above the caller in `.github/workflows/tools.yml`. A suite declaring
# `# SUITE-DEPENDS: <reason>` is not hermetic and is not gated here; it is SKIPPED and the
# skip is COUNTED, because a silently unrun suite is the failure this whole file exists
# against, one level down.
set -uo pipefail

# ⚠ PARAMETERISED OVER (DIRECTORY, GLOB, NOUN) because the SAME collapsed pair exists in two
# steps of one workflow. The suites step folded 2 into FAILED; the `repo scripts` step ran
# `python3 "$s"` under `set -e`, where 1 and 2 fail the job IDENTICALLY — so a checker that
# REFUSED and a checker that found a real defect are the same red. Writing the classifier
# twice is how the two copies drift; the second caller is also the first honest test of the
# first caller's abstraction.
DEFAULT_DIR="tools"
DEFAULT_GLOB="test_*.py"
DEFAULT_NOUN="hermetic suite"

gate() {
    local dir="$1" glob="${2:-$DEFAULT_GLOB}" noun="${3:-$DEFAULT_NOUN}"
    local pass=0 fail=0 unest=0 skipped=0 ran=0
    local failed_names="" unest_names=""
    local f b rc

    for f in "$dir"/$glob; do
        # ⚠ An unmatched glob in bash expands to the PATTERN, not to nothing.
        [ -f "$f" ] || continue
        # ⛔ never run ourselves: `*.sh` over scripts/ would recurse forever.
        [ "$(basename "$f")" = "$(basename "$0")" ] && continue
        if grep -q "^# SUITE-DEPENDS:" "$f"; then
            skipped=$((skipped + 1))
            continue
        fi
        ran=$((ran + 1))
        b=$(basename "$f" .py)
        echo "── $b"
        python3 "$f"
        rc=$?
        case "$rc" in
            0)
                pass=$((pass + 1))
                ;;
            2)
                unest=$((unest + 1))
                unest_names="$unest_names $b"
                echo "  ⚠ $b UNESTABLISHED (exit 2) — this '"$noun"' did not conclude."
                echo "     ⛔ Not a pass and not a failure: no claim about the code follows either way."
                ;;
            *)
                fail=$((fail + 1))
                failed_names="$failed_names $b"
                echo "  ⛔ $b FINDINGS (exit $rc) — it ran, concluded, and reported something"
                ;;
        esac
    done

    echo
    echo "  ran $ran ${noun}(s): $pass passed · $fail FINDINGS · $unest UNESTABLISHED"
    echo "  skipped $skipped declaring # SUITE-DEPENDS (not hermetic, gated nowhere here)"

    # ⛔ A glob that matches nothing runs zero suites. "All green" and "the loop never
    # executed" are the same output, so the count is the discriminator — and the state it
    # discriminates is ESTABLISHED NOTHING, which is exit 2 and not exit 1. This line used
    # to print those words and exit 1, which is the same collision one level up.
    if [ "$ran" -eq 0 ]; then
        echo "  ⛔ ESTABLISHED NOTHING — zero ${noun}s matched \"$glob\" under $dir/. Not a pass."
        return 2
    fi
    if [ "$fail" -gt 0 ]; then
        echo "  ⛔ FINDINGS:$failed_names"
        [ "$unest" -gt 0 ] && echo "  ⚠ UNESTABLISHED:$unest_names — reported, and NOT counted as failures"
        return 1
    fi
    if [ "$unest" -gt 0 ]; then
        echo "  ⚠ UNESTABLISHED:$unest_names"
        echo "  ⛔ BLOCKING on established-nothing. The board is not green: those suites never spoke."
        return 2
    fi
    echo "  clean"
    return 0
}

plant() {  # plant <path> <exit-code>
    printf '#!/usr/bin/env python3\nimport sys\nsys.exit(%s)\n' "$2" > "$1"
}

selftest() {
    # ⛔ THE CONTROLS ARE PLANTED, NOT DRAWN FROM THE SUITES. #58 named
    # `test_reference_check` as the standing known-positive for exit 2. Measured 2026-08-20
    # at 280ac70, from a clean checkout: it exits **1**, and it declares `# SUITE-DEPENDS`,
    # so the gating job never runs it at all. No suite in this repository exits 2 today.
    # ⇒ A control drawn from the measured population decays the moment the population is
    # repaired — which is exactly what happened to that one between the ruling and this
    # implementation. Planted suites do not decay.
    local d rc out ok=0
    d=$(mktemp -d)
    trap 'rm -rf "$d"' RETURN

    plant "$d/test_a_zero.py" 0
    plant "$d/test_b_one.py" 1
    plant "$d/test_c_two.py" 2
    plant "$d/test_d_dep.py" 0
    printf '# SUITE-DEPENDS: planted, never hermetic\n' >> "$d/test_d_dep.py"

    check() {  # check <label> <want-rc> <must-contain...>
        local label="$1" want="$2"; shift 2
        local pat hit=1
        [ "$rc" = "$want" ] || hit=0
        for pat in "$@"; do
            case "$out" in *"$pat"*) ;; *) hit=0 ;; esac
        done
        [ "$hit" = 1 ] || ok=1
        if [ "$hit" = 1 ]; then echo "  ok    $label (got $rc)"; else echo "  FAIL  $label (got $rc, want $want)"; fi
    }

    out=$(gate "$d" 2>&1); rc=$?
    check "a FINDINGS suite and an UNESTABLISHED one are reported SEPARATELY, rc=1" 1 \
          "test_b_one FINDINGS" "test_c_two UNESTABLISHED" "1 FINDINGS · 1 UNESTABLISHED"
    check "a # SUITE-DEPENDS suite is SKIPPED and the skip is COUNTED" 1 \
          "skipped 1 declaring"

    # ⛔ the known-negative in the direction that matters: exit 1 must NOT read UNESTABLISHED
    case "$out" in
        *"test_b_one UNESTABLISHED"*) echo "  FAIL  known-negative: an exit-1 suite was labelled UNESTABLISHED"; ok=1 ;;
        *) echo "  ok    known-negative: an exit-1 suite reads FINDINGS, never UNESTABLISHED" ;;
    esac

    # ⇒ with no genuine failure left, established-nothing must BLOCK on its own
    rm "$d/test_b_one.py"
    out=$(gate "$d" 2>&1); rc=$?
    check "UNESTABLISHED alone BLOCKS, and exits 2 rather than 1" 2 \
          "BLOCKING on established-nothing" "never spoke"
    # ⚠ MATCHED ON THE LABEL, NOT ON THE WORD. Written first as `*FAILED*`, this control
    # fired on its own summary counter — the line that says `0 FAILED` — and reported a
    # defect in the gate that was a defect in the control. The question is whether any
    # suite was LABELLED failed, not whether the string appears in a tally.
    case "$out" in
        *"FINDINGS (exit"*|*"⛔ FINDINGS:"*)
            echo "  FAIL  a run with no findings still LABELLED something FINDINGS"; ok=1 ;;
        *) echo "  ok    a run with no findings labels nothing FINDINGS (its 0-count tally is not a label)" ;;
    esac

    # ...and the repaired state passes, so the gate is not merely always-red
    rm "$d/test_c_two.py"
    out=$(gate "$d" 2>&1); rc=$?
    check "known-positive: only passing suites exit 0" 0 "clean" "1 passed"

    # ⛔ zero suites is ESTABLISHED NOTHING — exit 2, not 1, and never 0
    rm "$d/test_a_zero.py"
    out=$(gate "$d" 2>&1); rc=$?
    check "an empty population exits 2, not 0" 2 "ESTABLISHED NOTHING"

    # ⛔ THE STATED LIMIT, DEMONSTRATED RATHER THAN CLAIMED. argparse exits 2 for a rejected
    # argument. This suite RAN, concluded nothing about any code, and is indistinguishable
    # here from one that decided it established nothing. The control asserts the gate gets
    # it WRONG in the documented direction — so the day a marker makes it separable, this
    # line fails and someone reads the paragraph at the top of this file.
    printf '#!/usr/bin/env python3\nimport argparse\nargparse.ArgumentParser().parse_args(["--nope"])\n' \
        > "$d/test_e_argparse.py"
    out=$(gate "$d" 2>&1); rc=$?
    check "STATED LIMIT: a runtime exit 2 (argparse) is indistinguishable from ours" 2 \
          "test_e_argparse UNESTABLISHED"

    # ⛔ THE SECOND CALLER'S SHAPE, controlled. The `repo scripts` step passes a different
    # glob and a different noun; without this the parameterisation is asserted and untested,
    # and a glob that silently keeps matching `test_*.py` would look identical to one that
    # works — the whole population would just be the wrong population, reported confidently.
    rm -f "$d"/test_*.py
    plant "$d/probe_two.py" 2
    plant "$d/test_should_not_run.py" 1
    out=$(gate "$d" 'probe_*.py' 'repo check' 2>&1); rc=$?
    check "a non-default glob selects its OWN population and uses its own noun" 2 \
          "probe_two UNESTABLISHED" "repo check(s)"
    case "$out" in
        *test_should_not_run*) echo "  FAIL  the glob parameter was ignored — default population ran"; ok=1 ;;
        *) echo "  ok    a file outside the given glob is not run" ;;
    esac

    return $ok
}

# ⛔ $# IS CHECKED, NOT JUST $1. `case "${1:-}"` matched the flag and IGNORED everything after
# it, so `--self-test --zzz-not-a-flag` ran the control and exited 0 — a caller could pass a real
# flag and a typo together and read a clean control result that silently dropped half the
# invocation. That is membership-not-equality in a `case`, the same defect this PR fixes in two
# Python checkers, committed in the gate that checks for it. (Found by DEV5, on their own files
# first; I had only ever tested the garbage flag ALONE, so my gate would have passed this.)
case "${1:-}" in
    --self-test|--selftest)
        [ "$#" -eq 1 ] || { echo "  VOID  unrecognised argument(s) after $1: ${*:2} — established nothing" >&2; exit 2; }
        selftest
        exit $?
        ;;
    -h|--help)
        [ "$#" -eq 1 ] || { echo "  VOID  unrecognised argument(s) after $1: ${*:2} — established nothing" >&2; exit 2; }
        sed -n '2,46p' "$0"
        exit 0
        ;;
esac

# ⛔ THERE WAS NO ARGUMENT GUARD HERE AT ALL, and both of gate-selftests.sh's controls passed
# over it for two different wrong reasons. The first positional IS the directory, so
# `--zzz-not-a-flag` was accepted as a DIRECTORY NAME: the glob matched nothing, the run exited
# 2 as ESTABLISHED NOTHING, and the flag appeared in the message only because it had been
# interpolated as a PATH — `zero suites matched "test_*.py" under --zzz-not-a-flag/`.
#
# ⇒ So "exits non-zero" was satisfied by an unrelated cause, and "names the flag" by a
# coincidence of string interpolation. A leading `-` is never a directory here.
# (The two-cause point is DEV5's, found on their own tools first.)
for _a in "$@"; do
    case "$_a" in
        -*) echo "  VOID  unrecognised argument: $_a — established nothing" >&2; exit 2 ;;
    esac
done

DIR="${1:-$DEFAULT_DIR}"
GLOB="${2:-$DEFAULT_GLOB}"
NOUN="${3:-$DEFAULT_NOUN}"

echo
echo "$DIR/$GLOB — three outcomes, not two"
gate "$DIR" "$GLOB" "$NOUN"
exit $?
