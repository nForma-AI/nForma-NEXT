#!/bin/bash
# Run each subject's OWN control, and refuse to believe a control that cannot fail.
#
# ⛔ WHY THIS IS A SEPARATE GATE FROM exit-code-gate.sh. That one asks "did the check pass?"
# This one asks "does the check still WORK?" — and #321 measured that nothing was asking it:
# `.github/workflows/tools.yml` runs `scripts/*.py` bare on every PR, so four checkers GATE
# every merge while the controls that prove they can still produce a verdict have never run in
# CI once. `tools/test_*.py` covers the instruments in tools/; `scripts/` has no test files at
# all — its checkers carry their controls INSIDE themselves as `--self-test`, and that was the
# only surface nothing invoked.
#
# ⛔ AND "RUN --self-test AND CHECK FOR 0" IS NOT ENOUGH. Measured 2026-08-21:
#
#     check-goal-conformance.py  --zzz-not-a-flag  ->  rc=0, silent
#     validate-recipe.py         --zzz-not-a-flag  ->  rc=0, silent
#     check-orientation.py       --zzz-not-a-flag  ->  rc=2   (argparse)
#     check-tools-index.py       --zzz-not-a-flag  ->  rc=2   VOID, and it NAMES the argument
#
# ⇒ Two of four accept ANY argument and exit 0. For those two, `--self-test` exiting 0 proves
# nothing: rename the flag, misspell it, or delete the self-test's dispatch entirely, and the
# gate stays GREEN while the control silently stops running. **A control whose invocation
# cannot fail is not being invoked.** That is #26 aimed one level up — at the calling
# convention rather than at the analyser.
#
# ⇒ SO EVERY SUBJECT GETS A KNOWN-NEGATIVE FOR ITS OWN FLAG, at gate time, on every run:
#
#     garbage flag exits NONZERO   the flag surface discriminates -> the --self-test result means something
#     garbage flag exits 0         it does not -> UNESTABLISHED, whatever --self-test said
#
#     0        PASSED         the control ran and passed
#     2        UNESTABLISHED  no self-test, or one that established nothing
#     other    FINDINGS       the control ran and FAILED — the checker is broken
#
# ⚠ WHAT THIS STILL CANNOT DO, stated because the gap is real and a threshold would hide it:
# it cannot tell a control that PASSED from one that passed VACUOUSLY. `--self-test` exiting 0
# over zero assertions looks identical to one exiting 0 over thirty.
# `tools/architect-sweeps/known-negative.py` is the instrument for that question — it sabotages
# an analyser and re-runs its control — and it is not run here because it is a sweep, not a
# gate. ⇒ This gate establishes that the control was REACHED, never that it was SUFFICIENT.
# ⛔ THIS GATE IS AN EXECUTION SURFACE, AND THAT IS THE THING TO BE CAREFUL ABOUT.
# It runs every subject TWICE, once with an argument its author never anticipated. That is safe
# for a read-only checker and NOT safe in general. Measured 2026-08-21: pointing it at
# `scripts/*.sh` hung for over two minutes with no output — `fleet-preflight.sh` is a FLEET
# OPERATION, not a checker, and an unrecognised flag does not stop it from doing its work.
#
# ⇒ THE POPULATION IS DELIBERATELY NOT A WIDE GLOB. `scripts/*.py` is the set of read-only
# checkers this exists for. Widening it to shell is an explicit decision about each script, not
# a glob away — "enforce over the population, not a literal list" is the right rule for an
# index and the WRONG one for something that executes its subjects.
#
# ⚠ And a timeout is defence in depth, not the fix. A hung subject is reported as TIMED OUT and
# blocks; it is never folded into pass or fail, because "did not terminate" is a different fact
# from "concluded no".
set -uo pipefail

GARBAGE="--zzz-not-a-flag"
FLAG="--self-test"
LIMIT="${SUBJ_TIMEOUT:-30}"

# ⚠ NO `timeout(1)`. It is absent on macOS by default and its absence exits 127 — which this
# repository has already recorded once as a wrong reading. Portable poll instead; 124 matches
# GNU timeout's convention so a reader who knows that tool is not surprised.
# ⚠ LOG IS SET BY EVERY CALL. Written first as a second, UNPROTECTED `run_it_capture` so the
# refusal text could be read — which put an untimed invocation AHEAD of the timed one and hung
# this script's own self-test for two minutes on the sleeping subject its TIMEOUT control plants.
# ⇒ The fix to the two-cause leg defeated the timeout leg, in the file that documents both. One
# invocation, protected, capturing.
LOG=""
limited() {
    LOG=$(mktemp)
    "$@" >"$LOG" 2>&1 &
    local pid=$! i=0
    while kill -0 "$pid" 2>/dev/null; do
        if [ "$i" -ge "$LIMIT" ]; then
            kill -9 "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
            return 124
        fi
        sleep 1
        i=$((i + 1))
    done
    wait "$pid"
}

gate() {
    local dir="$1" glob="${2:-*.py}"
    local pass=0 broke=0 unest=0 unver=0 hung=0 ran=0
    local broke_names="" unest_names="" unver_names="" hung_names=""
    local f b rc grc

    for f in "$dir"/$glob; do
        [ -f "$f" ] || continue
        [ "$(basename "$f")" = "$(basename "$0")" ] && continue
        ran=$((ran + 1))
        b=$(basename "$f")
        case "$f" in
            *.sh) run_it() { limited bash "$f" "$@"; } ;;
            *)    run_it() { limited python3 "$f" "$@"; } ;;
        esac

        # ⛔ THE KNOWN-NEGATIVE FIRST. If the flag surface cannot refuse, nothing after it counts.
        # ⛔ THE OUTPUT IS READ, NOT JUST THE CODE. An exit code alone is a ONE-BIT answer to a
        # TWO-CAUSE question: a subject that IGNORES the flag and then fails for its own
        # unrelated reason exits non-zero and passes a code-only check. Measured on my own
        # `exit-code-gate.sh`, which had no argument guard: the flag was taken as a DIRECTORY,
        # the glob matched nothing, and it exited 2 as ESTABLISHED NOTHING — non-zero, for a
        # cause with nothing to do with the flag. (DEV5 found this class on their own tools and
        # it landed here unchanged.)
        #
        # ⚠ SO THE REFUSAL MUST NAME THE ARGUMENT, and say it is refusing. Requiring only the
        # NAME is not enough either: that same run printed `--zzz-not-a-flag` inside its error,
        # as an interpolated PATH. Both halves, or the control is satisfiable by coincidence.
        # ⇒ This is a MESSAGE CONTRACT on subjects, stated rather than assumed: all six current
        # subjects already satisfy it, so it costs nothing today and closes the ambiguity.
        run_it "$GARBAGE"
        grc=$?
        gout=$(cat "$LOG" 2>/dev/null); rm -f "$LOG"
        # ⚠ THE TIMEOUT BRANCH IS FIRST. 124 is non-zero, so a hung subject would otherwise
        # fall into the refusal-text checks below and be classified by a message it never
        # printed. Ordering, not a guard — the guard existed and I still had to reason about it.
        if [ "$grc" -eq 124 ]; then
            hung=$((hung + 1)); hung_names="$hung_names $b"
            echo "  ⛔ $b TIMED OUT after ${LIMIT}s on \`$GARBAGE\` — it did not terminate."
            echo "     ⚠ Not a pass and not a failure. A subject that keeps working on an"
            echo "        argument it does not recognise is not a read-only checker."
            continue
        fi
        if [ "$grc" -ne 0 ] && [ "$grc" -ne 124 ]; then
            case "$gout" in
                *unrecognised*|*unrecognized*|*VOID*) ;;
                *)  unver=$((unver + 1)); unver_names="$unver_names $b"
                    echo "  ⚠ $b UNVERIFIABLE — it exits $grc on \`$GARBAGE\` but never says it"
                    echo "     is REFUSING it. ⛔ Non-zero for an unrelated reason is"
                    echo "        indistinguishable from a refusal when only the code is read."
                    continue ;;
            esac
            case "$gout" in
                *"$GARBAGE"*) ;;
                *)  unver=$((unver + 1)); unver_names="$unver_names $b"
                    echo "  ⚠ $b UNVERIFIABLE — it refuses without NAMING \`$GARBAGE\`, so the"
                    echo "        refusal cannot be attributed to the argument under test."
                    continue ;;
            esac
        fi
        if [ "$grc" -eq 0 ]; then
            unver=$((unver + 1))
            unver_names="$unver_names $b"
            echo "  ⚠ $b UNVERIFIABLE — it accepts \`$GARBAGE\` and exits 0."
            echo "     ⛔ So \`$FLAG\` exiting 0 establishes NOTHING: the flag may never have"
            echo "        been recognised. Fix the argument surface before trusting the control."
            continue
        fi

        # ⛔ THE THIRD INVOCATION, and it is a state I did not have until DEV5 measured it on
        # their own files: a real flag AND a typo together. A `case "$1"` or an `in argv`
        # membership test accepts the flag and silently drops the rest, so the caller reads a
        # clean control result for an invocation half of which was ignored. Testing the garbage
        # flag ALONE cannot see it — and my own two gates failed this when I checked.
        run_it "$FLAG" "$GARBAGE"
        brc=$?
        rm -f "$LOG"
        if [ "$brc" -eq 0 ]; then
            unver=$((unver + 1))
            unver_names="$unver_names $b"
            echo "  ⚠ $b UNVERIFIABLE — \`$FLAG $GARBAGE\` exits 0."
            echo "     ⛔ The flag is matched and the rest DISCARDED, so a control result here"
            echo "        describes an invocation that was only half read."
            continue
        fi

        run_it "$FLAG"
        rc=$?
        rm -f "$LOG"
        if [ "$rc" -eq 124 ]; then
            hung=$((hung + 1)); hung_names="$hung_names $b"
            echo "  ⛔ $b TIMED OUT after ${LIMIT}s running its own control."
            continue
        fi
        case "$rc" in
            0) pass=$((pass + 1)) ;;
            2) unest=$((unest + 1)); unest_names="$unest_names $b"
               echo "  ⚠ $b UNESTABLISHED (exit 2) — no self-test, or one that concluded nothing." ;;
            *) broke=$((broke + 1)); broke_names="$broke_names $b"
               echo "  ⛔ $b CONTROL FAILED (exit $rc) — the checker's own control does not pass." ;;
        esac
    done

    echo
    echo "  ran $ran subject(s): $pass control(s) passed · $broke FAILED · $unest UNESTABLISHED · $unver UNVERIFIABLE · $hung TIMED OUT"

    if [ "$ran" -eq 0 ]; then
        echo "  ⛔ ESTABLISHED NOTHING — zero subjects matched \"$glob\" under $dir/. Not a pass."
        return 2
    fi
    if [ "$broke" -gt 0 ]; then
        echo "  ⛔ CONTROL FAILED:$broke_names"
        return 1
    fi
    if [ "$hung" -gt 0 ]; then
        echo "  ⛔ TIMED OUT:$hung_names — blocking. \"Did not terminate\" is not \"concluded no\"."
        return 2
    fi
    if [ "$unver" -gt 0 ] || [ "$unest" -gt 0 ]; then
        [ -n "$unver_names" ] && echo "  ⚠ UNVERIFIABLE:$unver_names"
        [ -n "$unest_names" ] && echo "  ⚠ UNESTABLISHED:$unest_names"
        echo "  ⛔ BLOCKING. A gate whose control cannot be shown to run is a gate nobody has checked."
        return 2
    fi
    echo "  all controls reached and passing"
    return 0
}

selftest() {
    # ⛔ PLANTED, because the live population cannot produce three of the four states and a
    # control drawn from it would go silent the day the repo is repaired.
    local d rc out ok=0
    # ⚠ A HEREDOC, NOT printf '%s'. Written first as a `$REFUSE` variable interpolated with
    # `%s`: printf interprets escapes in the FORMAT string only, so every `\n` in the argument
    # stayed literal and each planted subject became one line of gibberish that failed to parse.
    # Three controls then failed for a reason that had nothing to do with what they test.
    plant_py() {
        local path="$1"; shift
        {
            echo '#!/usr/bin/env python3'
            echo 'import sys'
            echo 'a = sys.argv[1:]'
            echo 'def void():'
            echo '    print("  VOID  unrecognised argument(s): %s — established nothing" % " ".join(a))'
            echo '    sys.exit(2)'
            printf '%s\n' "$@"
        } > "$path"
    }
    d=$(mktemp -d)
    trap 'rm -rf "$d"' RETURN

    # accepts the flag AND refuses garbage — the only shape whose 0 means anything
    # ⚠ THE PLANTED SUBJECTS NOW SATISFY THE MESSAGE CONTRACT, and three of them did not when
    # it was added — the contract failed its own fixtures first, which is the right order.
    plant_py "$d/a_good.py" 'if a == ["--self-test"]: sys.exit(0)' 'if a: void()' 'sys.exit(0)'
    # accepts ANYTHING — the #47 defect, and the reason this gate exists
    printf '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n' > "$d/b_permissive.py"
    # refuses garbage, and its control FAILS
    plant_py "$d/c_broken.py" 'if a == ["--self-test"]: sys.exit(3)' 'if a: void()' 'sys.exit(0)'
    # refuses garbage, and has no self-test at all
    plant_py "$d/d_none.py" 'if a: void()' 'sys.exit(0)'

    check() {
        local label="$1" want="$2"; shift 2
        local pat hit=1
        [ "$rc" = "$want" ] || hit=0
        for pat in "$@"; do case "$out" in *"$pat"*) ;; *) hit=0 ;; esac; done
        [ "$hit" = 1 ] || ok=1
        if [ "$hit" = 1 ]; then echo "  ok    $label (got $rc)"; else echo "  FAIL  $label (got $rc, want $want)"; fi
    }

    out=$(gate "$d" 'a_good.py' 2>&1); rc=$?
    check "known-positive: a subject that refuses garbage and passes its control exits 0" 0 \
          "all controls reached and passing" "1 control(s) passed"

    # ⛔ THE LEG THIS GATE EXISTS FOR. b_permissive PASSES a naive `--self-test && echo ok`.
    out=$(gate "$d" 'b_permissive.py' 2>&1); rc=$?
    check "a subject accepting ANY flag is UNVERIFIABLE, not passing" 2 \
          "UNVERIFIABLE" "establishes NOTHING"
    case "$out" in
        *"1 control(s) passed"*) echo "  FAIL  a permissive subject was counted as a PASS"; ok=1 ;;
        *) echo "  ok    a permissive subject is never counted as a pass" ;;
    esac

    out=$(gate "$d" 'c_broken.py' 2>&1); rc=$?
    check "a FAILING control exits 1 and is named — distinct from UNESTABLISHED" 1 \
          "CONTROL FAILED" "c_broken"
    case "$out" in
        *"c_broken UNESTABLISHED"*) echo "  FAIL  a failing control was labelled UNESTABLISHED"; ok=1 ;;
        *) echo "  ok    known-negative: a failing control never reads UNESTABLISHED" ;;
    esac

    out=$(gate "$d" 'd_none.py' 2>&1); rc=$?
    check "a subject with NO self-test is UNESTABLISHED and blocks, never a silent pass" 2 \
          "UNESTABLISHED" "BLOCKING"

    # ⛔ THE TWO-CAUSE LEG, CONTROLLED IN BOTH ITS FORMS. Neither of these is caught by reading
    # the exit code, and the second is not caught by requiring the flag NAME either — it was the
    # exact shape my own exit-code-gate.sh had, where the flag reached the message as a PATH.
    printf '#!/usr/bin/env python3\nimport sys\nif sys.argv[1:] == ["--self-test"]: sys.exit(0)\nsys.exit(2)\n' > "$d/g_silent.py"
    out=$(gate "$d" 'g_silent.py' 2>&1); rc=$?
    check "non-zero WITHOUT saying it refuses is UNVERIFIABLE, not a discriminating flag surface" 2 \
          "never says it" "unrelated reason"
    rm -f "$d/g_silent.py"

    printf '#!/usr/bin/env python3\nimport sys\nif sys.argv[1:] == ["--self-test"]: sys.exit(0)\nprint("  VOID  something went wrong — established nothing")\nsys.exit(2)\n' > "$d/h_unnamed.py"
    out=$(gate "$d" 'h_unnamed.py' 2>&1); rc=$?
    check "a refusal that does not NAME the argument cannot be attributed to it" 2 \
          "without NAMING"
    rm -f "$d/h_unnamed.py"

    # ⛔ THE THIRD INVOCATION, CONTROLLED. A subject that REFUSES garbage alone but accepts the
    # flag PLUS garbage passes every other leg here — it was the shape my own two gates had.
    plant_py "$d/f_half_read.py" 'if a and a[0] == "--self-test": sys.exit(0)' 'if a: void()' 'sys.exit(0)'
    out=$(gate "$d" 'f_half_read.py' 2>&1); rc=$?
    check "a subject accepting FLAG+garbage is UNVERIFIABLE, even though garbage ALONE is refused" 2 \
          "only half read"
    case "$out" in
        *"1 control(s) passed"*) echo "  FAIL  a half-reading subject was counted as a PASS"; ok=1 ;;
        *) echo "  ok    known-negative: refusing garbage alone is NOT sufficient to pass" ;;
    esac
    rm -f "$d/f_half_read.py"

    # ⛔ THE TIMEOUT STATE, CONTROLLED — it exists because it FIRED on the real population, not
    # because it was imagined: pointing this gate at scripts/*.sh hung for over two minutes on
    # `fleet-preflight.sh --zzz-not-a-flag`. An untested timeout path in a gate that executes
    # its subjects is the same defect as an untested control anywhere else.
    printf '#!/usr/bin/env python3\nimport time\ntime.sleep(600)\n' > "$d/e_hangs.py"
    LIMIT=2
    out=$(gate "$d" 'e_hangs.py' 2>&1); rc=$?
    LIMIT="${SUBJ_TIMEOUT:-30}"
    check "a subject that does not TERMINATE is TIMED OUT and blocks, never a pass" 2 \
          "TIMED OUT" "did not terminate"
    case "$out" in
        *"e_hangs UNESTABLISHED"*|*"e_hangs CONTROL FAILED"*)
            echo "  FAIL  a hung subject was folded into an exit-code state"; ok=1 ;;
        *) echo "  ok    known-negative: a hung subject is never folded into pass or fail" ;;
    esac
    rm -f "$d/e_hangs.py"

    out=$(gate "$d" 'nothing_matches_*.py' 2>&1); rc=$?
    check "an empty population exits 2, not 0" 2 "ESTABLISHED NOTHING"

    return $ok
}

# ⛔ $# CHECKED, NOT JUST $1 — see the identical note in exit-code-gate.sh. `--self-test` plus a
# typo ran the control and exited 0, in the very gate whose job is to refuse exactly that.
case "${1:-}" in
    --self-test|--selftest|-h|--help)
        [ "$#" -eq 1 ] || { echo "  VOID  unrecognised argument(s) after $1: ${*:2} — established nothing" >&2; exit 2; } ;;
esac
case "${1:-}" in
    --self-test|--selftest) selftest; exit $? ;;
    -h|--help) sed -n '2,44p' "$0"; exit 0 ;;
    "") ;;
    *) echo "  VOID  unrecognised argument: $1 — established nothing" >&2; exit 2 ;;
esac

echo
echo "subject controls — do the gates' own controls still run?"
gate "${SUBJ_DIR:-scripts}" "${SUBJ_GLOB:-*.py}"
exit $?
