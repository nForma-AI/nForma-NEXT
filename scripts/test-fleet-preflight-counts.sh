#!/usr/bin/env bash
# Assert that every FAIL fleet-preflight.sh PRINTS also reaches its summary.
#
# ⛔ Two defects of one class have now been found in this script, and both had the
# same signature: a FAIL in the body, "0 fail" in the summary. The summary is what
# an operator reads. A verdict that does not reach it did not happen.
#
#   1. panel identity   — an embedded python3 heredoc printed its own FAIL string
#                         and exited 0, so the shell counter never moved.
#   2. worktree coverage — `cmd | while read` ran the loop in a SUBSHELL, so
#                         bad()'s increment died with the subshell.
#
# Leg 1 is BEHAVIOURAL: it demonstrates the subshell mechanism, both directions,
# so the test fails if bash ever stops behaving this way and the rationale rots.
# Leg 2 is STRUCTURAL: it asserts the fixed shape is actually in the shipped file.
#
# ⚠ Leg 2 is a shape check, not a proof of correctness — it cannot tell whether the
# counted verdict is the RIGHT one, only that it is counted at all.
#
# Exit: 0 both legs pass · 1 a leg failed

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
TARGET="$SCRIPT_DIR/fleet-preflight.sh"
failures=0

echo "target: $TARGET"
[ -f "$TARGET" ] || { echo "⛔ VOID: target absent — this test established nothing"; exit 1; }

# ── Leg 1: the mechanism, both directions ────────────────────────────────────
echo
echo "leg 1 — does a pipe discard counter increments? (both directions)"
fail=0
bad() { printf '    FAIL  %s\n' "$1" >/dev/null; fail=$((fail+1)); }
emit() { printf 'MISSING architect -\nMISSING devops -\nMISSING dx -\n'; }

fail=0
emit | while read -r st r _; do case "$st" in MISSING) bad "$r";; esac; done
piped=$fail

fail=0
while read -r st r _; do case "$st" in MISSING) bad "$r";; esac; done < <(emit)
substituted=$fail

echo "    cmd | while ............ printed 3, counted $piped"
echo "    while ... < <(cmd) ..... printed 3, counted $substituted"
if [ "$piped" -eq 0 ] && [ "$substituted" -eq 3 ]; then
  echo "    PASS — the pipe loses them, process substitution keeps them"
else
  echo "    ⛔ FAIL — expected piped=0 substituted=3, got piped=$piped substituted=$substituted"
  failures=$((failures+1))
fi

# ── Leg 2: the shipped file uses the surviving form ──────────────────────────
echo
echo "leg 2 — does the shipped preflight use the form that survives?"
if grep -q 'fleet-worktree.sh check 2>&1 | while' "$TARGET"; then
  echo "    ⛔ FAIL — worktree loop still pipes into while; its FAILs will not be counted"
  failures=$((failures+1))
else
  echo "    ok — no 'check | while' pipe in the worktree section"
fi
if grep -q 'done < <(scripts/fleet-worktree.sh check' "$TARGET"; then
  echo "    ok — worktree loop reads from process substitution"
else
  echo "    ⛔ FAIL — expected process substitution in the worktree section"
  failures=$((failures+1))
fi
if grep -q 'panel_tally' "$TARGET"; then
  echo "    ok — panel identity block has a tally channel back to the shell"
else
  echo "    ⛔ FAIL — panel identity block has no tally channel; its FAIL will not be counted"
  failures=$((failures+1))
fi

echo
if [ "$failures" -eq 0 ]; then
  echo "both legs pass — printed FAILs reach the summary."
else
  echo "⛔ $failures leg(s) failed."
fi
exit "$failures"
