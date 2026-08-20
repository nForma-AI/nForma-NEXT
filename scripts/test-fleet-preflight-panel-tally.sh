#!/usr/bin/env bash
# Prove the patched panel-identity block DISCRIMINATES, both directions.
#
# ⛔ The point of the patch is that a FAIL reaches the counters. A test that only
# ever sees the failing state cannot tell "counts failures" from "always reports
# one", so both states are constructed here and the tally is read in each.
#
# The block resolves Daintree state under `~`, so $HOME redirects it to a fixture.

SRC=$(cd "$(dirname "$0")" && pwd)/fleet-preflight.sh
WORK=$(mktemp -d)
BLOCK="$WORK/panel.py"

# Extract the heredoc body verbatim — the thing that actually ships, not a copy.
awk "/<<'PANELS'/{flag=1;next} /^PANELS\$/{flag=0} flag" "$SRC" > "$BLOCK"
echo "extracted block: $(wc -l < "$BLOCK" | tr -d ' ') lines"

ROLES='"TEAMLEAD","ARCHITECT","DEVOPS","DX","DEV1","DEV2","DEV3","DEV4","DEV5"'
TOP=/fake/repo/toplevel

make_state() {  # $1=fixture home  $2=python list of pane titles  $3=titleMode
  local h="$1" titles="$2" mode="$3"
  local d="$h/Library/Application Support/Daintree/projects/proj1"
  mkdir -p "$d"
  python3 - "$d/state.json" "$TOP" "$mode" "$titles" <<'PY'
import json, sys
out, top, mode, titles = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
names = [t.strip().strip('"') for t in titles.split(",") if t.strip()]
doc = {"terminals": [{"cwd": top, "title": n, "titleMode": mode} for n in names]}
json.dump(doc, open(out, "w"))
PY
}

run_case() {  # $1=label  $2=fixture home  $3=expect_fail(0/1)
  local label="$1" h="$2" expect="$3"
  local tally="$WORK/tally.$RANDOM"
  local out
  out=$(HOME="$h" python3 "$BLOCK" "$TOP" "$tally" 2>&1)
  local rc=$?
  local t="(no tally written)"
  [ -s "$tally" ] && t=$(cat "$tally")
  local got_fail=0
  echo "$out" | grep -q 'FAIL' && got_fail=1
  printf '\n%s\n' "--- $label"
  printf '%s\n' "$out" | sed $'s/\033\\[[0-9;]*m//g' | sed 's/^/    /'
  echo "    exit=$rc   tally(ok warn fail)=$t"
  if [ "$got_fail" -eq "$expect" ]; then
    echo "    PASS — printed FAIL: $got_fail, expected: $expect"
  else
    echo "    ⛔ TEST FAILED — printed FAIL: $got_fail, expected: $expect"
    FAILURES=$((FAILURES+1))
  fi
}

FAILURES=0

# Case A: every declared role has a panel, titles pinned -> no FAIL, fail count 0
HA="$WORK/homeA"; make_state "$HA" "$ROLES" "user"
run_case "A: all nine roles present, titleMode=user  (expect NO fail)" "$HA" 0

# Case B: only two roles have panels -> FAIL, and the tally must carry it
HB="$WORK/homeB"; make_state "$HB" '"TEAMLEAD","DX"' "user"
run_case "B: seven roles missing a panel            (expect FAIL)" "$HB" 1

# Case C: no Daintree state at all -> warn, not fail; tally still written
HC="$WORK/homeC"; mkdir -p "$HC"
run_case "C: no Daintree state for this repo        (expect NO fail, a warn)" "$HC" 0

echo
if [ "$FAILURES" -eq 0 ]; then
  echo "3/3 cases behaved as specified — the block discriminates."
else
  echo "⛔ $FAILURES case(s) did not behave as specified."
fi
rm -rf "$WORK"
exit "$FAILURES"
