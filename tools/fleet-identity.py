#!/usr/bin/env python3
"""Resolve a Claude session (transcript) to the Daintree pane that is running it.

⛔ Why this is not a one-liner. There is no shared key:

  terminal.list  -> id, title, worktreeId          ... and NO session id
  transcript     -> session id, self-reported name ... and NO pane id

The only overlapping field is the *name*, and it is unreliable on both sides:
  - pane side: two panes carried the title IMPLEMENTER3 simultaneously;
  - transcript side: one file's title records ALTERNATE
    TEAMLEAD/DEV2/TEAMLEAD/DEV2 for ~100 cycles, so "the last record" is not
    "the current name" — reading it that way reported that TEAMLEAD had been
    renamed to DEV2 while both panes were live and correctly named.

So this joins on CONTENT: rare tokens from a session's recent assistant output
must appear in exactly one pane's scrollback. Verified against the failing case —
the session whose file says DEV2 resolves to the TEAMLEAD pane, 14 hits to 5.

⚠ Limits, stated rather than discovered:
  - A quiet pane whose scrollback is mostly UI chrome scores low and resolves
    `ambiguous`. That is reported, never guessed. It matters least: panes near a
    context threshold are busy by definition, which is what makes them match.
  - Scrollback is a trailing window (1000 lines max), so a session idle for a
    long time can age out of its own pane's buffer.
  - `no match` means unresolved. It does NOT mean the session has no pane.

The Daintree token is read from the user's own MCP config. It is never embedded.
"""
import collections, glob, json, os, re, subprocess, sys, time

CFG = os.path.expanduser("~/.claude.json")


def daintree_endpoint():
    try:
        cfg = json.load(open(CFG))
    except Exception as exc:
        sys.exit(f"cannot read {CFG}: {exc}")
    srv = (cfg.get("mcpServers") or {}).get("daintree")
    if not srv:
        sys.exit("no 'daintree' MCP server configured — nothing to resolve against")
    auth = (srv.get("headers") or {}).get("Authorization")
    if not auth:
        sys.exit("daintree server has no Authorization header configured")
    return srv["url"], auth


def rpc(url, auth, method, params=None, sid=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    cmd = ["curl", "-s", "-H", f"Authorization: {auth}",
           "-H", "Accept: application/json, text/event-stream",
           "-H", "Content-Type: application/json"]
    if sid:
        cmd += ["-H", f"Mcp-Session-Id: {sid}"]
    cmd += ["-X", "POST", url, "-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if ln.startswith("data: "):
            return json.loads(ln[6:])
    return json.loads(out) if out.strip() else {}


def payload(res):
    """An application error arrives INSIDE a successful response. Check it."""
    if res.get("error"):
        sys.exit(f"RPC error: {res['error']}")
    obj = json.loads("".join(c.get("text", "") for c in res["result"].get("content", [])))
    if isinstance(obj, dict) and obj.get("code") and obj.get("message"):
        sys.exit(f"{obj['code']}: {obj.get('details') or obj['message']}")
    return obj


def rare_tokens(path, limit=120):
    """Tokens unlikely to appear in another pane: issue refs, comma-numbers,
    short hashes, long identifiers. Drawn from the most recent assistant turns."""
    texts = []
    for line in open(path, errors="replace"):
        if '"assistant"' not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                    texts.append(block["text"])
    blob = " ".join(texts[-8:])
    pat = r"#\d{3,5}|\b\d{2,3},\d{3}\b|\b[a-f0-9]{7,8}\b|\b[A-Za-z][A-Za-z_-]{11,}\b"
    return list(set(re.findall(pat, blob)))[:limit]


def self_reported(path):
    """Every DISTINCT title the file claims. >1 means the file cannot name its
    own session — not that the session was renamed."""
    names = []
    for line in open(path, errors="replace"):
        if '"custom-title"' not in line and '"agent-name"' not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        n = rec.get("customTitle") or rec.get("agentName")
        if n and n not in names:
            names.append(n)
    return names


def main():
    as_json = "--json" in sys.argv
    url, auth = daintree_endpoint()
    handshake = subprocess.run(
        ["curl", "-sD", "-", "-o", "/dev/null", "-H", f"Authorization: {auth}",
         "-H", "Accept: application/json, text/event-stream", "-H", "Content-Type: application/json",
         "-X", "POST", url, "-d", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "fleet-identity", "version": "1"}}})],
        capture_output=True, text=True).stdout
    sid = next((ln.split(":", 1)[1].strip() for ln in handshake.splitlines()
                if ln.lower().startswith("mcp-session-id:")), None)
    rpc(url, auth, "notifications/initialized", sid=sid)

    panes = payload(rpc(url, auth, "tools/call",
                        {"name": "terminal.list", "arguments": {}}, sid))["terminals"]
    title = {p["id"]: p.get("title") for p in panes}
    scroll = {}
    for p in panes:
        res = rpc(url, auth, "tools/call",
                  {"name": "terminal.getOutput",
                   "arguments": {"terminalId": p["id"], "maxLines": 1000}}, sid)
        try:
            obj = payload(res)
        except SystemExit:
            continue                      # one unreadable pane is not a failed run
        scroll[p["id"]] = obj if isinstance(obj, str) else (
            obj.get("output") or obj.get("text") or json.dumps(obj))

    rows = []
    for proj in glob.glob(os.path.expanduser("~/.claude/projects/*")):
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            if time.time() - os.path.getmtime(path) > 3 * 3600:
                continue
            toks = rare_tokens(path)
            if len(toks) < 5:
                continue                  # too little signal to claim anything
            score = collections.Counter(
                {tid: sum(1 for t in toks if t in s) for tid, s in scroll.items()})
            ranked = score.most_common(2)
            tid, best = ranked[0]
            second = ranked[1][1] if len(ranked) > 1 else 0
            resolved = best >= 4 and best >= 2 * max(second, 1)
            rows.append({"session": os.path.basename(path)[:8],
                         "pane": title.get(tid) if resolved else None,
                         "hits": best, "runner_up": second,
                         "resolved": resolved,
                         "self_reported": self_reported(path)})
    rows.sort(key=lambda r: -r["hits"])

    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"{'session':<10}{'PANE':<16}{'hits':>5}{'2nd':>5}  {'verdict':<11}self-reported")
        for r in rows:
            v = "RESOLVED" if r["resolved"] else ("ambiguous" if r["hits"] else "no match")
            sr = ",".join(r["self_reported"]) or "(none)"
            warn = "  ⚠file cannot name itself" if len(r["self_reported"]) > 1 else ""
            print(f"{r['session']:<10}{str(r['pane'] or '-'):<16}{r['hits']:>5}"
                  f"{r['runner_up']:>5}  {v:<11}{sr}{warn}")
        n = sum(1 for r in rows if r["resolved"])
        print(f"\n{n} of {len(rows)} sessions resolved to a pane. "
              f"Unresolved means UNKNOWN, not unattached.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
