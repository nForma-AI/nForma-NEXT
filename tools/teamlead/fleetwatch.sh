#!/bin/bash
# Fleet watch built on tl.py — emits THREE distinct states, not one.
# Replaces the agentState-only monitor, which could not tell "idle" from
# "blocked on an instruction that never got submitted", and therefore
# recommended retasking — which DESTROYS the pending text.
export TL_WORKSPACE=f0aa822b0ba19b148e91b70cea17a11fa22d6a2eaa3b941db9eded67049ef215
TL=/private/tmp/claude-501/-Users-jonathanborduas-code-DigitalFrontier-infra/e4a7769d-4905-49e7-b80d-1c3df6c7f71f/scratchpad/nforma-contrib/tl.py
STATE=/tmp/fleetwatch-seen.txt
: > "$STATE"
LAST_REACH=""
while true; do
  OUT=$(python3 "$TL" fleet 2>&1)
  RC=$?
  if [ $RC -ne 0 ]; then
    # GUARD: instrument failure is reported, never silently treated as "nothing changed".
    NEW="unreachable"
    if [ "$NEW" != "$LAST_REACH" ]; then
      echo "FLEET UNOBSERVABLE at $(date -u +%H:%M:%SZ) — $(printf '%s' "$OUT" | head -1 | cut -c1-150). Idleness NOT tracked."
      LAST_REACH="$NEW"
    fi
    sleep 240; continue
  fi
  if [ "$LAST_REACH" = "unreachable" ]; then
    echo "FLEET OBSERVABLE again at $(date -u +%H:%M:%SZ) — tracking resumed."
  fi
  LAST_REACH="ok"
  printf '%s' "$OUT" | python3 /private/tmp/claude-501/-Users-jonathanborduas-code-DigitalFrontier-infra/e4a7769d-4905-49e7-b80d-1c3df6c7f71f/scratchpad/classify_fleet.py
  sleep 240
done
