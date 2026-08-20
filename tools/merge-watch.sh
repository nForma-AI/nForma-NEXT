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

emit() { printf '%s\n' "$*"; }

last=""
seen=""      # rows already reported. ⛔ Without this every merge re-reports the
             # standing backlog, and "an alarm that fires forever on one event
             # trains its reader to ignore it" — tools/README.md, violated by this
             # file three minutes after that line was indexed.
first=1
while true; do
  sha=$(git ls-remote origin refs/heads/main 2>/dev/null | cut -f1)
  if [ -z "$sha" ]; then
    emit "VOID merge-watch: could not reach origin — ESTABLISHED NOTHING about main, not clean. ADDABLE — FIXABLE HERE: network or gh/git auth."
    sleep 120; continue
  fi
  if [ "$sha" = "$last" ]; then sleep 60; continue; fi
  last="$sha"
  # ⚠ The FIRST pass is a BASELINE, not a merge finding. `last` starts empty so any
  # sha differs, and labelling that emission "FINDING at <sha>" claims the merge
  # caused a backlog that predates it. Different proposition, same words.
  if [ "$first" = 1 ]; then tag="BASELINE"; else tag="FINDING at ${sha:0:7}"; fi
  git fetch -q --prune origin 2>/dev/null

  # ⛔ Control first. A scan whose instrument cannot fire is not a clean scan.
  if ! python3 tools/stranded-branches.py --self-test >/dev/null 2>&1; then
    emit "VOID merge-watch: stranded-branches --self-test FAILED at ${sha:0:7} — its scan below would establish nothing. No finding is emitted from a broken instrument."
    continue
  fi

  out=$(python3 tools/stranded-branches.py 2>&1); rc=$?
  case "$rc" in
    0) : ;;
    1) printf '%s\n' "$out" | grep '^NO-UPSTREAM-MATCH' | while read -r _ ref rest; do
         row="stranded:$ref"; case "$seen" in *"$row"*) ;; *) emit "$tag: $ref has commits with no upstream patch-match. NOT proof of loss — recovery-by-recommit reads identically."; seen="$seen|$row" ;; esac
       done ;;
    2) emit "VOID merge-watch: stranded-branches ESTABLISHED NOTHING at ${sha:0:7} (exit 2) — not clean." ;;
    *) emit "UNDOCUMENTED merge-watch: stranded-branches exit $rc at ${sha:0:7}, which it does not document. Treat as established-nothing." ;;
  esac

  wt=$(bash scripts/fleet-worktree.sh check 2>&1); wrc=$?
  case "$wrc" in
    0) : ;;
    1) printf '%s\n' "$wt" | grep -E '^  (DUP|OUTSIDE|MISSING)' | while read -r st role path; do
         row="wt:$st:$role"; case "$seen" in *"$row"*) ;; *) emit "$tag: worktree $st for $role — $path"; seen="$seen|$row" ;; esac
       done ;;
    2) emit "VOID merge-watch: fleet-worktree ESTABLISHED NOTHING at ${sha:0:7} (exit 2) — not clean." ;;
    *) emit "UNDOCUMENTED merge-watch: fleet-worktree exit $wrc at ${sha:0:7}. Treat as established-nothing." ;;
  esac
  first=0
done
