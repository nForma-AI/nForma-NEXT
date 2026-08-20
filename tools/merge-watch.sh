#!/usr/bin/env bash
# Read-only monitor: run the merge-time instruments WHEN MAIN MOVES.
#
# ★ PLACEMENT IS THE POINT, NOT THE SCHEDULE. `stranded-branches.py` already had a
# caller — at LAUNCH — and the regression it exists to catch arrives at MERGE time,
# hours before the next launch. A clock would be no better: the defect is not
# periodic, it is *caused by* an event. ⇒ So the cadence IS the event. This polls
# `git ls-remote origin main` and runs the instruments only when the SHA changes.
#
# ⛔ BOUNDS, from the operator grant of 2026-08-20. All four, and the third is the
# one that shapes the code:
#   read-only          it observes; it never merges, pushes, closes, edits or writes to a pane
#   no authorization   every line is a FINDING. Never a task, never a grant, never an imperative.
#   silence == RAN     emit on findings, emit on VOID, emit on any UNDOCUMENTED exit code.
#   own instruments    stranded-branches.py and fleet-worktree.sh only.
#
# ★ AND THE CONTROL A FIX CANNOT SILENCE. Before trusting a scan, this asserts the
# instrument's OWN `--self-test` passes. That test is synthetic and does not decay —
# unlike a known-positive drawn from live fleet state, which the fleet repairing
# itself will quietly turn negative. (An orchestrator declared exactly that defect
# in its own watch an hour ago: its positive was propped up by the defect it
# detects, and both arms went to zero when seven panes read their files.)
set -u
if ! top=$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null) || ! cd "$top"; then
  printf '%s\n' "VOID merge-watch: not inside a git repository — the watch never started, and this line exists because a Monitor streams STDOUT only. A silent death here would be indistinguishable from a quiet fleet. ADDABLE — FIXABLE HERE: run it from a checkout."
  exit 2
fi

# ⛔ HEARTBEAT — silence must mean DEAD, not QUIET. Bound 3 of the operator grant.
#
# Without this, the quiet path below is `sleep 60; continue` and emits NOTHING, so a
# reader cannot separate three states:
#
#   running, main has not moved   -> silence
#   killed / crashed              -> silence
#   never started                 -> silence
#
# ★ THE BEAT MUST COME FROM INSIDE THIS LOOP. A separate pinger proves a PINGER is
# alive — a liveness signal for the wrong process, which keeps beating after the
# watch it reports on has died. Only the thing that stops when the work stops is
# worth listening to.
#
# ⚠ IT IS A FLOOR ON EMISSION RATE, NOT AN EXTRA STREAM. Any line proves liveness,
# so `emit` resets the timer and a busy watch never beats at all. The cost is paid
# only during silence, which is exactly when the information is worth paying for.
#
# ⛔ COST, stated because a heartbeat is noise you are CHOOSING to accept:
#   300s -> 288 lines per fully quiet 24h.   60s -> 1440, too many to read, and an
#   unread channel is worse than none because it still looks like one.
#   HEARTBEAT_SECS tunes it. 0 disables it and restores the old blind quiet.
HEARTBEAT_SECS="${HEARTBEAT_SECS:-300}"
last_emit=$(date +%s)

emit() { printf '%s\n' "$*"; last_emit=$(date +%s); }

# ⚠ Distinguishable from a finding BY PREFIX so no parser counts proof-of-life as an
# event. Carries the tool name because a stream may be multiplexed, and a timestamp
# because "the last line I saw" is not a time.
heartbeat() {
  [ "$HEARTBEAT_SECS" -eq 0 ] 2>/dev/null && return 0
  now=$(date +%s)
  if [ $(( now - last_emit )) -ge "$HEARTBEAT_SECS" ]; then
    emit "HEARTBEAT merge-watch $(date -u '+%Y-%m-%dT%H:%M:%SZ') alive; last-seen-main=${last:0:7}; nothing to report since previous line"
  fi
}

# ⛔ Sleep in CHUNKS, beating between them. A bare `sleep 60` makes the configured
# interval a LIE for any value under 60 — the loop cannot emit while blocked, so the
# interval silently becomes max(interval, sleep). ⚠ An operator who sets 30 and
# receives one line per 60s has been handed a number that does not describe the
# system: the calibration defect this repository keeps filing, in the parameter of
# the fix for it.
nap() {
  _left="$1"
  while [ "$_left" -gt 0 ]; do
    _chunk=$(( _left < 5 ? _left : 5 ))
    sleep "$_chunk"
    _left=$(( _left - _chunk ))
    heartbeat
  done
}

# ⛔ DECLARE THE INTERVAL BEFORE ANY SILENCE. Without this line the absence of a
# beat is THREE states and a consumer cannot separate them:
#
#   no beat, interval declared and elapsed  -> DEAD
#   no beat, heartbeats DISABLED (0)        -> nothing established
#   no beat, watch never started            -> nothing established
#
# ★ THE ABSENCE OF A MARKER ESTABLISHES NOTHING — `goals/RESERVED-ACTIONS.md` on the
# conversion test, and the same shape here: the rule was correct about what a beat
# PROVES and silent about what its absence proves. A detector on the two-state
# reading calls a DISABLED watch dead and a NEVER-STARTED one dead, and that reading
# sends someone to restart a monitor that was never meant to run.
if [ "$HEARTBEAT_SECS" -eq 0 ] 2>/dev/null; then
  emit "STARTED merge-watch $(date -u '+%Y-%m-%dT%H:%M:%SZ') heartbeat=DISABLED — silence from this watch establishes NOTHING about its liveness, by configuration."
else
  emit "STARTED merge-watch $(date -u '+%Y-%m-%dT%H:%M:%SZ') heartbeat=${HEARTBEAT_SECS}s — expect a line at least this often; longer silence means DEAD, not quiet."
fi

last=""
seen=""      # rows already reported. ⛔ Without this every merge re-reports the
             # standing backlog, and "an alarm that fires forever on one event
             # trains its reader to ignore it" — tools/README.md, violated by this
             # file three minutes after that line was indexed.
             #
             # ⛔ AND IT WAS INERT UNTIL 2026-08-20, MEASURED IN PRODUCTION. The two
             # loops below read from a PIPE, and in bash the last stage of a pipeline
             # runs in a SUBSHELL — so `seen="$seen|$row"` mutated a copy that was
             # discarded at the `done`. The guard ran, matched nothing, and re-emitted
             # the entire backlog on every merge. Armed on a pane at 15:32Z, it
             # re-reported all 7 standing rows at the first merge six minutes later.
             #
             # ★ AND THE TEST THAT WOULD HAVE CAUGHT IT PASSES IN THE WRONG SHELL:
             #     bash -c 'seen=""; printf "a\n" | while read x; do seen=$x; done; echo "[$seen]"'  -> []
             #     zsh  -c 'seen=""; printf "a\n" | while read x; do seen=$x; done; echo "[$seen]"'  -> [a]
             #   zsh runs the last pipeline stage in the CURRENT shell. This repo's
             #   interactive shell is zsh and this script's shebang is bash, so a
             #   developer verifying the dedupe by hand sees it work. ⇒ Fixed with
             #   `done < <(...)`, which keeps the loop in the parent under bash.
first=1
while true; do
  # ⛔ At the TOP, so it covers every path below — the quiet `continue`, the
  # unreachable-origin `continue`, AND the self-test-failed `continue`. On that last
  # path `last` is already set, so the next iteration goes quiet: a watch stuck
  # failing its own control would otherwise be silent, which is the state most worth
  # hearing about.
  heartbeat
  pass_start=$(date +%s)
  sha=$(git ls-remote origin refs/heads/main 2>/dev/null | cut -f1)
  if [ -z "$sha" ]; then
    emit "VOID merge-watch: could not reach origin — ESTABLISHED NOTHING about main, not clean. ADDABLE — FIXABLE HERE: network or gh/git auth."
    nap 120; continue
  fi
  if [ "$sha" = "$last" ]; then nap 60; continue; fi
  last="$sha"
  # ⚠ The FIRST pass is a BASELINE, not a merge finding. `last` starts empty so any
  # sha differs, and labelling that emission "FINDING at <sha>" claims the merge
  # caused a backlog that predates it. Different proposition, same words.
  if [ "$first" = 1 ]; then tag="BASELINE"; else tag="FINDING at ${sha:0:7}"; fi
  git fetch -q --prune origin 2>/dev/null

  # ⛔ Control first. A scan whose instrument cannot fire is not a clean scan.
  # ⛔ A CONTROL GATES ONLY ITS OWN SUBJECT. This block used `continue`, which
  # restarted the loop and silently skipped the fleet-worktree scan below — so a
  # stranded-branches control failure suppressed a DIFFERENT population's findings,
  # and the VOID line named only stranded-branches. A reader could not tell that
  # worktree checking had been skipped at all.
  #
  # ⚠ Latent, not live: --self-test exits 0 today. Reachable, not occurring.
  #
  # ★ #164 item 2 warns that "a merge that silently drops one population's findings
  # is worse than two watchers" — and that was ALREADY TRUE between this file's own
  # two subjects, one level below where the requirement was aimed. `continue` was
  # doing double duty as *skip this check* and *skip this iteration*. Found by DEV1
  # reading the source; I wrote it.
  sb_ok=1
  if ! python3 tools/stranded-branches.py --self-test >/dev/null 2>&1; then
    emit "VOID merge-watch: stranded-branches --self-test FAILED at ${sha:0:7} — its scan is suppressed and establishes nothing. ⚠ The fleet-worktree scan below STILL RAN; its findings are unaffected."
    sb_ok=0
  fi

  out=""; rc=0
  if [ "$sb_ok" = 1 ]; then out=$(python3 tools/stranded-branches.py 2>&1); rc=$?; fi
  case "$([ "$sb_ok" = 1 ] && echo "$rc" || echo skip)" in
    skip|0) : ;;
    1) while read -r _ ref rest; do
         row="stranded:$ref"; case "$seen" in *"$row"*) ;; *) emit "$tag: $ref has commits with no upstream patch-match. NOT proof of loss — recovery-by-recommit reads identically."; seen="$seen|$row" ;; esac
       done < <(printf '%s\n' "$out" | grep '^NO-UPSTREAM-MATCH') ;;
    2) emit "VOID merge-watch: stranded-branches ESTABLISHED NOTHING at ${sha:0:7} (exit 2) — not clean." ;;
    *) emit "UNDOCUMENTED merge-watch: stranded-branches exit $rc at ${sha:0:7}, which it does not document. Treat as established-nothing." ;;
  esac

  wt=$(bash scripts/fleet-worktree.sh check 2>&1); wrc=$?
  case "$wrc" in
    0) : ;;
    1) while read -r st role path; do
         row="wt:$st:$role"; case "$seen" in *"$row"*) ;; *) emit "$tag: worktree $st for $role — $path"; seen="$seen|$row" ;; esac
       done < <(printf '%s\n' "$wt" | grep -E '^  (DUP|OUTSIDE|MISSING)') ;;
    2) emit "VOID merge-watch: fleet-worktree ESTABLISHED NOTHING at ${sha:0:7} (exit 2) — not clean." ;;
    *) emit "UNDOCUMENTED merge-watch: fleet-worktree exit $wrc at ${sha:0:7}. Treat as established-nothing." ;;
  esac
  # ⛔ THE BLIND SPOT, SELF-MEASURED. Beats cannot fire during an instrument pass —
  # the loop is inside stranded-branches.py, MEASURED at 124s on this repository at
  # 120 merged refs, and it grows with the board. So a HEALTHY watch is silent for
  # the length of its own scan.
  # ⚠ If that silence exceeds HEARTBEAT_SECS the watch reports itself dead while
  # working, and a reader acting on it would kill a live monitor. The interval is
  # therefore NOT free to choose: it must exceed the longest pass. This does not
  # guess that bound — it measures each pass and says so when violated, because the
  # scan duration is a property of board size and will drift past any constant.
  pass_secs=$(( $(date +%s) - pass_start ))
  if [ "$HEARTBEAT_SECS" -gt 0 ] 2>/dev/null && [ "$pass_secs" -ge "$HEARTBEAT_SECS" ]; then
    emit "UNDERCALIBRATED merge-watch: that pass took ${pass_secs}s, >= HEARTBEAT_SECS=${HEARTBEAT_SECS}. A healthy scan outran its own liveness interval, so silence during a pass is now indistinguishable from death. NOT a finding about main. FIXABLE HERE: raise HEARTBEAT_SECS above ${pass_secs}."
  fi
  first=0
done
