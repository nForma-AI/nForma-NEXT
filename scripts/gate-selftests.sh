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
# ⛔ DERIVED, NOT ENUMERATED. Which subjects get their control run is a PROPERTY OF EACH FILE,
# never a list here or in the workflow. A list of "which instruments are gated" is correct on the
# day it is written and silently wrong on the next addition — the same defect this repository has
# now fixed at four separate layers in one night (a glob that did not recurse, a record derived
# from an index, an index derived from a predicate, a parser narrower than the record).
#
# ⇒ A subject either exposes a self-test and the gate RUNS it, or it DECLARES IN-FILE why it has
# none — following the `# SUITE-DEPENDS:` precedent in .github/workflows/tools.yml, whose whole
# argument was that the reason must travel with the thing it describes.
#
#     # NO-SELF-TEST: <the specific reason>
#
# ⚠ DECLARING IS NOT EXEMPTING. A declared subject is SKIPPED, COUNTED and NAMED on every run,
# because an exclusion nobody can see is how a checker's population quietly stops matching its
# subject. Silence is the failure mode; a visible skip can be argued with.
DECLARES_NONE="^# NO-SELF-TEST:"
# ⛔ TWO DECLARATIONS, DIFFERENT POWERS, AND THE DIFFERENCE IS THE WHOLE POINT.
#
#   # NO-SELF-TEST: <reason>    the subject IS STILL RUN. Only an UNESTABLISHED result is
#                               excused. A control that FAILS still reds the gate.
#   # NOT-EXECUTABLE: <reason>  the subject is not run at all — it is imported, never invoked.
#
# ⚠ I collapsed these into one and the self-test caught it within a minute. Hoisting the
# NO-SELF-TEST check above the invocation meant a declared subject was never run, so a FAILING
# control inside it could never be found: THE DECLARATION BECAME AN OFF SWITCH, which is exactly
# what the control `a declaration does NOT rescue a control that FAILS` exists to prevent. It
# fired on the person who wrote it.
#
# ⇒ NOT-EXECUTABLE is hoisted because a MODULE has no argv surface: `tools/runmarker.py` is
# imported, never run, and executing it exits 0 having done nothing — indistinguishable from a
# tool that ACCEPTED a bogus flag. That is a claim about the FILE'S KIND, not about its control,
# and it is the only reason to skip execution.
NOT_EXECUTABLE="^# NOT-EXECUTABLE:"
# ⛔ A TEST FILE IS NOT A SUBJECT — it IS the control, and it has no `--self-test` because there
# is nothing beneath it to control. Measured the hard way: pointing this gate at `tools/` with
# the default glob swept in 37 `test_*.py` suites and reported 93 SUBJECTS, of which 46
# "accepted a bogus flag" — every one a test file with no argument surface at all. ⇒ A real
# population defect, in the dry run of the gate built to catch population defects.
# ⚠ Same predicate `scripts/check-tools-index.py` uses for its instrument population, so the two
# cannot drift apart — and the exclusion is PRINTED on every run, never merely applied.
IS_A_TEST="^(test_.+|.+_test)\.(py|sh)$"
# ⛔ TWO BUDGETS, because the two invocations answer different questions and one ceiling hides
# the difference. A REFUSAL is an argument-parse decision and should be instant: a subject taking
# ten seconds to reject an unknown flag has already STARTED DOING ITS WORK, which is the finding,
# not a slow machine. A SELF-TEST legitimately takes longer — measured across the 44 tools/
# instruments: 82s total, index-watch alone at 20s because its own control clones a repository.
REFUSE_LIMIT="${REFUSE_TIMEOUT:-10}"
LIMIT="${SUBJ_TIMEOUT:-60}"

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
    local pass=0 broke=0 unest=0 unver=0 hung=0 declared=0 excluded=0 ran=0
    local broke_names="" unest_names="" unver_names="" hung_names="" declared_names="" why=""
    local excluded_names=""
    local f b rc grc

    local _saved_limit="$LIMIT"
    for f in "$dir"/$glob; do
        [ -f "$f" ] || continue
        [ "$(basename "$f")" = "$(basename "$0")" ] && continue
        b=$(basename "$f")
        if echo "$b" | grep -qE "$IS_A_TEST"; then
            excluded=$((excluded + 1)); excluded_names="$excluded_names $b"
            continue
        fi
        # ⛔ THE DECLARATION IS READ BEFORE ANY INVOCATION, not as a branch of the exit code.
        # A MODULE forces this: `tools/runmarker.py` is imported, never run, and has no argv
        # surface at all — running it exits 0 having done nothing, which is indistinguishable
        # from a tool that ACCEPTED a bogus flag. ⇒ A subject that declares it has no self-test
        # is never EXECUTED here, so declaring costs nothing and cannot trigger the work the
        # subject would otherwise do on an argument it does not understand.
        if grep -q "$NOT_EXECUTABLE" "$f"; then
            # ⛔ THE DECLARATION IS FALSIFIABLE, OR IT IS AN OFF SWITCH. NOT-EXECUTABLE is a claim
            # about the file's KIND — imported, never invoked — and a module does not have an
            # entry point. So the claim is CHECKED, not trusted: a file that declares it and
            # still carries `if __name__ == "__main__"` is asserting something false about
            # itself, and that reds the gate. Without this leg one comment line removes any
            # subject from the population, which is the thing every other leg here refuses.
            if grep -qE '^if __name__ *== *.__main__.' "$f"; then
                broke=$((broke + 1)); broke_names="$broke_names $b"
                echo "  ⛔ $b declares \`# NOT-EXECUTABLE:\` and HAS a __main__ entry point."
                echo "     The declaration is false about the file that carries it."
                continue
            fi
            why=$(sed -n 's/^# NOT-EXECUTABLE: //p' "$f" | head -1)
            declared=$((declared + 1)); declared_names="$declared_names $b(not-executable)"
            echo "  ---- $b is NOT EXECUTED, declared in-file: $why"
            continue
        fi
        ran=$((ran + 1))
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
        LIMIT="$REFUSE_LIMIT"
        run_it "$GARBAGE"
        grc=$?
        LIMIT="$_saved_limit"
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
        # ⛔ TWO PROBES, AND THE SECOND RESCUES WHAT THE FIRST CANNOT ASK. A subject with
        # REQUIRED arguments refuses `$GARBAGE` ALONE for the wrong reason — `discriminates.py`
        # exits 2 because `--a/--b` are missing, not because it read the flag. It refuses EVERY
        # invocation, so the probe is non-discriminating there and reporting it UNVERIFIABLE
        # charges the tool for a defect in the question. Measured: 7 of 45 were in exactly that
        # state, and none of them is defective.
        #
        # ⇒ `$FLAG $GARBAGE` is a COMPLETE, VALID invocation plus a typo, and it is askable of
        # every subject regardless of required arguments. So: the flag surface discriminates if
        # EITHER probe produces an attributable refusal. Only when NEITHER does is the subject
        # UNVERIFIABLE — and then the reason is named.
        attributable() {   # <rc> <output> -> 0 if this is a refusal OF THE ARGUMENT
            [ "$1" -eq 0 ] && return 1
            [ "$1" -eq 124 ] && return 1
            case "$2" in *unrecognised*|*unrecognized*|*VOID*) ;; *) return 1 ;; esac
            case "$2" in *"$GARBAGE"*) return 0 ;; *) return 1 ;; esac
        }
        LIMIT="$REFUSE_LIMIT"
        run_it "$FLAG" "$GARBAGE"
        brc=$?
        bout=$(cat "$LOG" 2>/dev/null); rm -f "$LOG"
        LIMIT="$_saved_limit"
        # ⛔ `$FLAG $GARBAGE` EXITING 0 IS A POSITIVE DEFECT AND THE FALLBACK MUST NOT LAUNDER
        # IT. The flag was matched and the remainder DISCARDED, so a control result there
        # describes an invocation only half read — regardless of how the other probe behaved.
        # ⚠ Written first as a plain OR over both probes, and the control caught the regression
        # within a minute: a subject refusing garbage ALONE was accepted while `--self-test
        # --zzz` exited 0. An OR is the right shape for "can it refuse at all" and the WRONG
        # shape for "did it read the whole invocation".
        if [ "$brc" -eq 0 ]; then
            unver=$((unver + 1)); unver_names="$unver_names $b"
            echo "  ⚠ $b UNVERIFIABLE — \`$FLAG $GARBAGE\` exits 0."
            echo "     ⛔ The flag is matched and the rest DISCARDED, so a control result here"
            echo "        describes an invocation that was only half read."
            continue
        fi
        if ! attributable "$grc" "$gout" && ! attributable "$brc" "$bout"; then
            unver=$((unver + 1)); unver_names="$unver_names $b"
            if [ "$grc" -eq 0 ] || [ "$brc" -eq 0 ]; then
                echo "  ⚠ $b UNVERIFIABLE — an unknown flag is ACCEPTED and it exits 0"
                echo "     (\`$GARBAGE\` -> $grc, \`$FLAG $GARBAGE\` -> $brc)."
                echo "     ⛔ So \`$FLAG\` exiting 0 establishes NOTHING about whether the"
                echo "        control ran: the flag may never have been recognised."
            else
                echo "  ⚠ $b UNVERIFIABLE — it exits nonzero on an unknown flag but never says it"
                echo "     is REFUSING it, and never NAMES it, on EITHER probe"
                echo "     (\`$GARBAGE\` -> $grc, \`$FLAG $GARBAGE\` -> $brc)."
                echo "     ⛔ Nonzero for an unrelated reason is indistinguishable from a refusal."
            fi
            continue
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
        run_it "$FLAG"
        rc=$?
        fout=$(cat "$LOG" 2>/dev/null); rm -f "$LOG"
        # ⛔ AN ARGPARSE REJECTION OF `--self-test` IS A DEFINITE ANSWER — "this tool has NO
        # self-test" — and must not be read as UNESTABLISHED. #58's collision live inside the
        # population being gated: DEV3 measured 12 tools with no self-test, of which EIGHT exit 2
        # because argparse refused the flag and FOUR exit 2 for a third reason. Same code, three
        # causes. ⇒ The REFUSAL TEXT separates them, and that is the CHEAPEST rung of
        # docs/DEFECT-CLASSES.md:1019 — not a better probe, but a property of the interface
        # answering the question directly.
        if [ "$rc" -eq 2 ]; then
            case "$fout" in
                *"unrecognized arguments: $FLAG"*|*"unrecognised argument"*"$FLAG"*)
                    if grep -q "$DECLARES_NONE" "$f"; then
                        why=$(sed -n 's/^# NO-SELF-TEST: //p' "$f" | head -1)
                        declared=$((declared + 1)); declared_names="$declared_names $b"
                        echo "  ---- $b has NO self-test (the flag is REJECTED), declared: $why"
                    else
                        unest=$((unest + 1)); unest_names="$unest_names $b"
                        echo "  ⚠ $b HAS NO SELF-TEST — it rejects \`$FLAG\` as unrecognised, a"
                        echo "     DEFINITE answer, not an unestablished one. ⛔ It needs a"
                        echo "        \`# NO-SELF-TEST: <reason>\` line, or a control."
                    fi
                    continue ;;
            esac
        fi
        if [ "$rc" -eq 124 ]; then
            hung=$((hung + 1)); hung_names="$hung_names $b"
            echo "  ⛔ $b TIMED OUT after ${LIMIT}s running its own control."
            continue
        fi
        case "$rc" in
            0) pass=$((pass + 1)) ;;
            2) if grep -q "$DECLARES_NONE" "$f"; then
                   why=$(sed -n 's/^# NO-SELF-TEST: //p' "$f" | head -1)
                   declared=$((declared + 1)); declared_names="$declared_names $b"
                   echo "  ---- $b has NO self-test, declared in-file: $why"
               else
                   unest=$((unest + 1)); unest_names="$unest_names $b"
                   echo "  ⚠ $b UNESTABLISHED (exit 2) — no self-test and NO \`# NO-SELF-TEST:\`"
                   echo "     declaration. ⛔ Undeclared absence is indistinguishable from a"
                   echo "        control that ran and concluded nothing."
               fi ;;
            *) broke=$((broke + 1)); broke_names="$broke_names $b"
               echo "  ⛔ $b CONTROL FAILED (exit $rc) — the checker's own control does not pass." ;;
        esac
    done

    echo
    echo "  ran $ran subject(s): $pass control(s) passed · $broke FAILED · $unest UNESTABLISHED · $unver UNVERIFIABLE · $hung TIMED OUT"
    echo "  declared NO self-test (skipped, COUNTED and NAMED, never silent):${declared_names:- none}"
    echo "  excluded as TESTS (a test IS the control, not a subject): $excluded"

    # ⛔ A FINDING OUTRANKS AN EMPTY POPULATION, and the order matters. The other way round, a
    # run whose only subject was a FALSE `# NOT-EXECUTABLE:` declaration returned 2 ESTABLISHED
    # NOTHING — a declared subject is never counted as RUN, so `ran` was 0 and a real finding was
    # reported by a summary saying nothing had been established. The control caught it: got 2,
    # wanted 1.
    if [ "$broke" -gt 0 ]; then
        echo "  ⛔ CONTROL FAILED:$broke_names"
        return 1
    fi
    # ⚠ `declared` counts as examined: a population of nothing but declared subjects HAS been read.
    if [ "$ran" -eq 0 ] && [ "$declared" -eq 0 ]; then
        echo "  ⛔ ESTABLISHED NOTHING — zero subjects matched \"$glob\" under $dir/. Not a pass."
        return 2
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
    # ⚠ The MESSAGE changed when the two-probe logic landed and the new one is more precise: a
    # subject accepting everything is caught by `$FLAG $GARBAGE` exiting 0, which says exactly
    # what is wrong — the flag was matched and the rest discarded.
    check "a subject accepting ANY flag is UNVERIFIABLE, not passing" 2 \
          "UNVERIFIABLE" "only half read"
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
    # ⚠ The expected MESSAGE changed when the classification got sharper, and the change is the
    # improvement: this planted subject REJECTS `--self-test` as unrecognised, so "has no
    # self-test" is a DEFINITE answer rather than an unestablished one. The exit code did not
    # move; what the run SAYS about it did.
    check "a subject with NO self-test and NO declaration blocks, and is told it HAS none" 2 \
          "HAS NO SELF-TEST" "DEFINITE answer" "BLOCKING"

    # ⛔ DECLARING IS NOT EXEMPTING — both directions, or the declaration is an off switch.
    { echo '#!/usr/bin/env python3'; echo '# NO-SELF-TEST: planted; it has no analyser to control'
      tail -n +2 "$d/d_none.py"; } > "$d/d_declared.py"
    rm -f "$d/d_none.py"
    out=$(gate "$d" 'd_declared.py' 2>&1); rc=$?
    check "a DECLARED absence does not block, and the REASON is printed" 0 \
          "declared: planted; it has no analyser to control"
    case "$out" in
        *"d_declared"*) echo "  ok    a declared subject is still NAMED — skipped, never silent" ;;
        *) echo "  FAIL  a declared subject vanished from the output"; ok=1 ;;
    esac
    case "$out" in
        *"1 control(s) passed"*) echo "  FAIL  a declared subject was counted as a PASSING control"; ok=1 ;;
        *) echo "  ok    known-negative: declaring is not passing — it is not counted as a control" ;;
    esac
    # ⚠ ...and the declaration must not rescue a subject whose control FAILS. Otherwise one
    # comment line turns a broken checker green, which is the off switch this repo refuses.
    { echo '#!/usr/bin/env python3'; echo '# NO-SELF-TEST: planted'
      tail -n +2 "$d/c_broken.py"; } > "$d/c_declared_broken.py"
    out=$(gate "$d" 'c_declared_broken.py' 2>&1); rc=$?
    check "a declaration does NOT rescue a control that FAILS" 1 "CONTROL FAILED"
    rm -f "$d/c_declared_broken.py" "$d/d_declared.py"
    printf '#!/usr/bin/env python3\n' > "$d/d_none.py"
    plant_py "$d/d_none.py" 'if a: void()' 'sys.exit(0)'

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
    check "a refusal that does not NAME the argument cannot be attributed to it, on EITHER probe" 2 \
          "never NAMES it, on EITHER probe"
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

    # ⛔ THE `# NO-SELF-TEST:` BUCKET MUST NOT ABSORB "HAS ONE I FAILED TO DISPATCH".
    # TEAMLEAD's warning, made mechanical, and it is the same shape as DEV3's withdrawn
    # `19 NO CONTROL` figure: **a count of what a probe did NOT find is a claim about the
    # PROBE.** `NO-SELF-TEST` names the world; the honest name would be
    # `NOT-DISPATCHED-BY-THIS-PROBE` unless the bucket is guarded.
    #
    # ⇒ The guard is ORDER: the flag surface is checked FIRST, so a subject that ACCEPTS
    # everything and exits 0 is UNVERIFIABLE before its declaration is ever read. Five live
    # specimens (daintree-control · established · estatenames · fleet-identity · runmarker)
    # accept `--zzz-not-a-flag` and exit 0 — `fleet-identity --self-test` prints its ORDINARY
    # REPORT TABLE, the flag never dispatched.
    plant_py "$d/a_good3.py" 'if a == ["--self-test"]: sys.exit(0)' 'if a: void()' 'sys.exit(0)'
    { echo '#!/usr/bin/env python3'
      echo '# NO-SELF-TEST: claims to have none, but accepts everything and exits 0'
      echo 'import sys'; echo 'sys.exit(0)'; } > "$d/i_undispatched.py"
    out=$(gate "$d" 'i_undispatched.py' 2>&1); rc=$?
    check "a DECLARATION does not rescue a subject whose flag surface accepts everything" 2 \
          "UNVERIFIABLE"
    # ⚠ MATCHED ON THE PER-SUBJECT LABEL, NOT ON THE WORD. Written first as a two-sided glob
    # over "declared" and the filename, it fired on the ALWAYS-PRINTED summary line
    # (`declared NO self-test … : none`) and reported a defect in the gate that was a defect in
    # the matcher. Third time tonight: a tally is not a label, and the question is whether THIS
    # SUBJECT was labelled declared. The gate was correct both times.
    case "$out" in
        *"---- i_undispatched"*)
            echo "  FAIL  the NO-SELF-TEST bucket absorbed an UNDISPATCHED flag"; ok=1 ;;
        *) echo "  ok    the bucket cannot absorb 'has one I failed to dispatch' — order guards it" ;;
    esac
    rm -f "$d/a_good3.py" "$d/i_undispatched.py"

    # ⛔ A TEST IS EXCLUDED AND THE EXCLUSION IS COUNTED. Planted because the real population
    # taught it: 37 test suites swept in as "subjects" and 46 of them reported as accepting a
    # bogus flag. ⚠ The count is asserted, not just the absence — an exclusion nobody can see is
    # how a checker's population quietly stops matching its subject.
    plant_py "$d/a_good2.py" 'if a == ["--self-test"]: sys.exit(0)' 'if a: void()' 'sys.exit(0)'
    printf '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n' > "$d/test_planted.py"
    out=$(gate "$d" '*.py' 2>&1); rc=$?
    case "$out" in
        *"test_planted"*) echo "  FAIL  a test file was run as a subject"; ok=1 ;;
        *"excluded as TESTS (a test IS the control, not a subject): 1"*)
            echo "  ok    a test file is EXCLUDED and the exclusion is COUNTED" ;;
        *) echo "  FAIL  the test exclusion was not counted"; ok=1 ;;
    esac
    rm -f "$d/a_good2.py" "$d/test_planted.py"

    # ⛔ NOT-EXECUTABLE, BOTH DIRECTIONS. It is the only declaration that skips EXECUTION, so it
    # is the only one that could become an off switch — and the second leg is what stops it.
    { echo '#!/usr/bin/env python3'; echo '# NOT-EXECUTABLE: a module; imported, never invoked'
      echo 'X = 1'; } > "$d/g_module.py"
    out=$(gate "$d" 'g_module.py' 2>&1); rc=$?
    # ⚠ EXPECTS 0, and the expectation was wrong before the return order was fixed. A population
    # of nothing but correctly-declared subjects HAS been examined and nothing failed — reporting
    # ESTABLISHED NOTHING there would be the overclaim in the other direction.
    check "a NOT-EXECUTABLE module is skipped WITHOUT being run, and named" 0 \
          "is NOT EXECUTED, declared in-file: a module; imported, never invoked"

    { echo '#!/usr/bin/env python3'; echo '# NOT-EXECUTABLE: claims to be a module'
      echo 'import sys'; echo 'if __name__ == "__main__":'; echo '    sys.exit(0)'; } > "$d/h_liar.py"
    out=$(gate "$d" 'h_liar.py' 2>&1); rc=$?
    check "a file claiming NOT-EXECUTABLE while carrying __main__ REDS — the declaration is checked" 1 \
          "declaration is false about the file that carries it"
    rm -f "$d/g_module.py" "$d/h_liar.py"

    # ⛔ THE TIMEOUT STATE, CONTROLLED — it exists because it FIRED on the real population, not
    # because it was imagined: pointing this gate at scripts/*.sh hung for over two minutes on
    # `fleet-preflight.sh --zzz-not-a-flag`. An untested timeout path in a gate that executes
    # its subjects is the same defect as an untested control anywhere else.
    printf '#!/usr/bin/env python3\nimport time\ntime.sleep(600)\n' > "$d/e_hangs.py"
    LIMIT=2
    out=$(gate "$d" 'e_hangs.py' 2>&1); rc=$?
    LIMIT="${SUBJ_TIMEOUT:-60}"
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
