#!/usr/bin/env bash
# ⛔ FIXTURE for #375. The first block is the MEASURED SPECIMEN, verbatim from the
# report — not a reconstruction. DEVOPS ran it while citing pipe-exit-scan an hour
# earlier, and read six subjects as accepting a bogus flag; the true codes were
# 2, 2, 2, 2, 0, 0, and two of those zeros were real defects.

for s in tools/*.py; do
  python3 "$s" --self-test --zzz-not-a-flag >/dev/null 2>&1
  printf "  %-34s rc=%s\n" "$(basename $s)" "$?"
done

# a second shape of the same defect: the span closes, then the read
f "$(g)" "$?"

# ── KNOWN-NEGATIVES. None of these may fire. ──
# the `$?` is INSIDE the substitution: it is the PREVIOUS command's status, correct.
x=$(foo $?)
# captured to a variable BEFORE any substitution — #375's stated known-negative.
python3 tool.py >/dev/null 2>&1
RC=$?
printf "  %-34s rc=%s\n" "$(basename x)" "$RC"
# arithmetic expansion is not a command substitution.
echo $((1+2)) $?
