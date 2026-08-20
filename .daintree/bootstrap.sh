#!/usr/bin/env bash
# Identity handshake for a fleet pane. Called by the recipe's launch prompt so the
# prompt itself can carry THE JOB.
#
# ⛔ WHY THIS FILE EXISTS. Measured 2026-08-20 on the shipped recipe: across the
# nine agent panes, 1,500-1,700 bytes of IDENTICAL handshake text and 76 bytes of
# assignment -- 12% of the launch prompt was the job, and 7 of 9 panes launched
# with no work at all. The ceremony is not wrong; it was crowding out the reason
# the pane exists.
#
# ⚠ It prints; it does not decide. The ROLE-READY line is still the agent's to
# emit, because a script cannot attest that a file was adopted.
set -uo pipefail

fail=0
say() { printf '%s\n' "$*"; }

[ -n "${NFORMA_ROLE:-}" ]        || { say "⛔ NFORMA_ROLE is unset"; fail=1; }
[ -n "${NFORMA_ROLE_PROMPT:-}" ] || { say "⛔ NFORMA_ROLE_PROMPT is unset"; fail=1; }

say "NFORMA_ROLE=${NFORMA_ROLE:-<unset>}"
say "NFORMA_ROLE_PROMPT=${NFORMA_ROLE_PROMPT:-<unset>}"
say "NFORMA_GOAL=${NFORMA_GOAL:-<none>}"

top=$(git rev-parse --show-toplevel 2>/dev/null) || { say "⛔ not a git repo"; fail=1; }
branch=$(git branch --show-current 2>/dev/null)
say "repo=$(basename "${top:-?}") branch=${branch:-<detached>}"

# ⛔ Read the prompt AT A REVISION, never from the working tree. Measured: the
# shared checkout sat 37 commits behind main and every pointer resolved into it,
# so two roles reviewed a 652-line file while main carried 698. The conjunction
# test passed on both halves -- pointer present, file opened -- and the content
# was stale. That is a third delivery failure: arrived, and wrong version.
if [ -n "${NFORMA_ROLE_PROMPT:-}" ]; then
  if blob=$(git rev-parse "origin/main:${NFORMA_ROLE_PROMPT}" 2>/dev/null); then
    say "doctrine=${blob:0:12}  (origin/main:${NFORMA_ROLE_PROMPT})"
    say "--- read it with: git show origin/main:${NFORMA_ROLE_PROMPT}"
  else
    say "⛔ ${NFORMA_ROLE_PROMPT} does not resolve at origin/main — do NOT fall back"
    say "   to the working tree; a stale copy is the failure this line prevents."
    fail=1
  fi
fi

if [ "$fail" -ne 0 ]; then
  say ""
  say "⛔ HANDSHAKE INCOMPLETE — say so ABOVE your ROLE-READY line, in words."
  say "   An earlier recipe said 'print exactly one line and nothing else', and six"
  say "   panes stayed silent about an unexecutable step because silence was the"
  say "   compliant output. Reporting a failure and signalling readiness are"
  say "   different channels."
fi
exit "$fail"
