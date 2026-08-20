#!/usr/bin/env bash
# Fixture for scan_shell_subshell. Positives and negatives in ONE file, because a
# fixture holding only positives cannot distinguish "detects the defect" from
# "fires on every while loop".
#
# ⛔ MUST NOT FIRE on this comment block. `cmd | while` written here is a MENTION.

fail=0
warn=0
seen=""
bad()  { printf 'FAIL %s\n' "$1"; fail=$((fail+1)); }
note() { printf 'warn %s\n' "$1"; warn=$((warn+1)); }
emit() { printf 'a\nb\nc\n'; }

# ── POSITIVE 1: assigns directly in the body, reads after ────────────────────
emit | while read -r x; do
  seen="$seen $x"
done
echo "seen:$seen"

# ── POSITIVE 2: body assigns NOTHING; the counter moves inside a FUNCTION ────
# This is the shape that matters. A matcher reading only the loop body sees no
# assignment at all and reports nothing, which is how the live instance survived.
emit | while read -r x; do
  bad "$x"
done
echo "fail=$fail"

# ── POSITIVE 3: same, via a different function, guarded by a test ────────────
printf '2\n' | while read -r n; do
  [ "$n" -gt 0 ] && note "$n things"
done
echo "warn=$warn"

# ── NEGATIVE 1: process substitution — the loop runs in THIS shell ───────────
total=0
while read -r x; do
  total=$((total + 1))
done < <(emit)
echo "total=$total"

# ── NEGATIVE 2: the loop only prints; nothing to lose ────────────────────────
emit | while read -r x; do
  printf 'saw %s\n' "$x"
done

# ── NEGATIVE 3: assigns, but nothing reads it after `done` ───────────────────
emit | while read -r x; do
  scratch="$x"
done
