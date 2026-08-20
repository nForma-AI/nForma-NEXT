#!/bin/bash
# dt.sh <method> [params-json]  -- one-shot Daintree MCP JSON-RPC call
SP="$(cd "$(dirname "$0")" && pwd)"
KEY=$(cat "$SP/dtkey")
URL=http://127.0.0.1:45454/mcp
METHOD="$1"
PARAMS="${2:-{\}}"
[ -z "$2" ] && PARAMS='{}'
H=(-H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
SID=$(curl -s -m 20 -D - -o /dev/null -X POST "$URL" "${H[@]}" \
  -d '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"teamlead","version":"1"}}}' \
  | tr -d '\r' | awk 'tolower($1)=="mcp-session-id:"{print $2}')
[ -z "$SID" ] && { echo "NO SESSION ID"; exit 1; }
curl -s -m 20 -X POST "$URL" "${H[@]}" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null
printf '{"jsonrpc":"2.0","id":1,"method":"%s","params":%s}' "$METHOD" "$PARAMS" > "$SP/.req.json"
curl -s -m 90 -X POST "$URL" "${H[@]}" -H "Mcp-Session-Id: $SID" --data-binary "@$SP/.req.json" \
  | tr -d '\r' | sed 's/^data: //' | grep -v '^event:' | grep -v '^$'
