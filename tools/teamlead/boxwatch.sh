#!/bin/bash
# Snapshot every agent input box every 20s; log ONLY transitions (empty -> text).
SP="$(cd "$(dirname "$0")" && pwd)"
LOG="$SP/boxwatch.log"
declare -A last
for i in $(seq 1 90); do
  out=$("$SP/dt.sh" tools/call '{"name":"terminal.getStatus","arguments":{"terminalIds":["terminal-da3db0b6-8277-4979-847e-da94eaaddbef","terminal-bf43c03c-5be4-4819-8b6a-d0cb4136cf7c","terminal-4fbc5a7d-3c48-481c-95e7-0d7879899e74","terminal-74df2764-5a9a-4a08-8c90-4f877a3bcba0"],"includeOutput":{"lines":4,"stripAnsi":true}}}' 2>/dev/null \
        | jq -r '.result.content[0].text' 2>/dev/null)
  [ -z "$out" ] && { echo "$(date -u +%H:%M:%SZ) INVALID getStatus-failed" >> "$LOG"; sleep 20; continue; }
  printf '%s' "$out" | python3 -c '
import json,sys,time
d=json.load(sys.stdin)
for t in (d.get("terminals") or d):
    ro=t.get("recentOutput") or ""
    if isinstance(ro,list): ro="\n".join(ro)
    box=[l.strip() for l in ro.split("\n") if l.strip().startswith("❯")]
    txt=box[-1][1:].strip() if box else ""
    print(f"{t[\"terminalId\"][9:17]}\t{t.get(\"agentState\")}\t{txt[:70]}")
' > "$SP/.bw.now" 2>/dev/null
  while IFS=$'\t' read -r id st txt; do
    if [ -n "$txt" ] && [ "${last[$id]}" != "$txt" ]; then
      echo "$(date -u +%H:%M:%SZ) APPEARED $id state=$st :: $txt" >> "$LOG"
    fi
    last[$id]="$txt"
  done < "$SP/.bw.now"
  sleep 20
done
