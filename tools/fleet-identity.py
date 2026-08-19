#!/usr/bin/env python3
"""Resolve a Claude session (transcript) to the Daintree pane that is running it.

⛔ Why the PANE join is not a one-liner. terminal.list has no shared key:

  terminal.list  -> id, title, worktreeId          ... and NO session id
  transcript     -> session id, self-reported name ... and NO pane id

⚠ CORRECTED: an earlier version of this paragraph said "there is no shared key"
flatly. That is true of terminal.list and FALSE of the session registry --
~/.claude/sessions/<pid>.json carries sessionId AND name, and sessionId IS the
transcript filename. The over-broad claim cost real work: it was read as a
property of the system, so the name join was rebuilt by content matching when an
exact join was already available. Session -> NAME is exact. Session -> PANE is
what still needs content.

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


def _daintree_configured():
    """Non-fatal probe. daintree_endpoint() exits; a fallback path needs to ask
    without dying, so the two are separate questions and separate functions."""
    try:
        cfg = json.load(open(CFG))
    except Exception:
        return False
    srv = (cfg.get("mcpServers") or {}).get("daintree")
    return bool(srv and (srv.get("headers") or {}).get("Authorization"))


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


SESSIONS = os.path.expanduser("~/.claude/sessions")


def registry():
    """Authoritative session name/identity, keyed by sessionId.

    ⛔ This is the shared key the module docstring says does not exist. That
    statement is true of `terminal.list` and false of the session registry:
    ~/.claude/sessions/<pid>.json carries BOTH `sessionId` (which IS the
    transcript filename) and `name`. So session -> name is an exact join and
    needs no content matching. Only session -> PANE still does.

    ⚠ This column used to be parsed out of the transcript (`customTitle` /
    `agentName`). That source is documented above as unreliable -- one file
    records ALTERNATE TEAMLEAD/DEV2 for ~100 cycles -- and reading it as "the
    current name" reported a rename that never happened. The registry does not
    have that failure mode: it is written by the owning process, not narrated
    by the agent.
    """
    out = {}
    for path in glob.glob(os.path.join(SESSIONS, "*.json")):
        try:
            row = json.load(open(path))
        except Exception:
            continue                      # one unreadable row is not a failed run
        sid = row.get("sessionId")
        if sid:
            out[sid] = row
    return out


def name_audit(row):
    """Did this session's name come from a rename, or was it auto-derived?

    ⛔ The predicate is KEY ABSENCE, not a value. A successful rename REMOVES
    `nameSource`; it never sets it to "user". The strings "auto" and "user" do
    occur in the CLI binary and are the obvious thing to test for -- a checker
    written against them never fires on any row this system produces, and
    reports a clean fleet forever. Measured on nine panes renamed in place.
    """
    if row is None:
        return "no-registry-row"
    src = row.get("nameSource")
    return "explicit" if src is None else src


def bootstrap_role(path):
    """The role a session was LAUNCHED as, from its first user message.

    Distinct from any name it now carries: the name can be patched, the
    bootstrap cannot. A disagreement between the two is the finding.
    """
    try:
        for line in open(path, errors="replace"):
            m = re.search(r"You are (TEAMLEAD|ARCHITECT|DEVOPS|DX|DEV[1-9])\b", line)
            if m:
                return m.group(1)
    except OSError:
        pass
    return None


def control(reg):
    """Known-positive by construction: this process runs INSIDE a session, so
    that session MUST be joinable. If the join is broken, this returns False.

    ⛔ The control this replaces was "the table printed N rows", which both the
    working and the broken version produce -- a non-discriminating control, of
    exactly the kind discriminates.py exists to refuse. Returns None when the
    control cannot be run at all, which is a third state and not a pass.
    """
    me = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not me:
        return None
    return me in reg


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


def fit(v, w):
    """Pad or CLIP to exactly w. A bare f-string width pads but never clips, so a
    long value silently merges with the next column: 'deepagents-nextjs-11' +
    'derived' rendered as 'deepagents-nextjs-11derived', which reads as a single
    value and hides the audit field entirely."""
    v = "-" if v in (None, "") else str(v)
    return (v[:w - 2] + "..") if len(v) > w else v.ljust(w)


def registry_report(reg, as_json):
    """⚠ DIFFERENT QUESTION from the pane join, and it says so.

    Answers: which role was this session launched as, what name does it carry
    now, and did that name come from a rename? It does NOT answer which pane is
    running it -- that still needs Daintree. Per tools/README.md 1b, an
    instrument that changes its question must say so in its output, or its
    diffs are fabrications.
    """
    rows = []
    for proj in glob.glob(os.path.expanduser("~/.claude/projects/*")):
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            if time.time() - os.path.getmtime(path) > 3 * 3600:
                continue
            sid = os.path.basename(path)[:-6]
            row = reg.get(sid)
            rows.append({"session": sid[:8],
                         "role": bootstrap_role(path),
                         "name": (row or {}).get("name"),
                         "named": name_audit(row),
                         "pid": (row or {}).get("pid"),
                         "status": (row or {}).get("status"),
                         "agrees": bool(row) and (row.get("name") == bootstrap_role(path)),
                         "self_reported": self_reported(path) if row is None else None})
    rows.sort(key=lambda r: (r["role"] or "~", r["session"]))
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    print("MODE: registry join (session -> role, name, name-origin). "
          "Does NOT resolve which pane runs a session; that needs Daintree.")
    print(f"{'session':<10}{'ROLE':<11}{'name':<22}{'origin':<16}{'pid':>7}  agrees")
    for r in rows:
        flag = "OK" if r["agrees"] else ("DRIFT" if r["role"] and r["name"] else "-")
        fb = ""
        if r["self_reported"] is not None:
            fb = "  fallback=transcript " + (",".join(r["self_reported"]) or "(none)") + " UNRELIABLE"
        print(f"{fit(r['session'],10)}{fit(r['role'],11)}{fit(r['name'],22)}"
              f"{fit(r['named'],16)}{str(r['pid'] or '-'):>7}  {flag}{fb}")
    sys.stdout.flush()
    drifted = [r for r in rows if r["role"] and r["name"] and not r["agrees"]]
    derived = [r for r in rows if r["named"] not in ("explicit", "no-registry-row")]
    print(f"\n{len(rows)} sessions. {len(drifted)} name/role disagreements, "
          f"{len(derived)} still auto-derived (never renamed).", file=sys.stderr)
    print("⚠ 'explicit' means the nameSource KEY IS ABSENT. It is never the string 'user'.",
          file=sys.stderr)


def main():
    as_json = "--json" in sys.argv
    reg = registry()

    ctl = control(reg)
    if ctl is False:
        print("⛔ CONTROL FAILED: this process's own session "
              f"({os.environ.get('CLAUDE_CODE_SESSION_ID','?')[:8]}) is not in the registry join. "
              "The join is broken or the registry is unreadable. Every row below would be "
              "unreliable, so none is printed. This is 'established nothing', not 'nothing found'.",
              file=sys.stderr)
        return 2
    if ctl is None:
        print("⚠ CONTROL NOT RUN: CLAUDE_CODE_SESSION_ID unset, so the join has no "
              "known-positive. Output below is UNVERIFIED.", file=sys.stderr)

    if "--registry-only" in sys.argv or not _daintree_configured():
        if "--registry-only" not in sys.argv:
            print("⚠ No 'daintree' MCP server configured -- falling back to the registry join. "
                  "Pane resolution is UNAVAILABLE, not empty.", file=sys.stderr)
        registry_report(reg, as_json)
        return 0

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
    if len(panes) < 2:
        # Not "nothing to resolve" — the resolver has no population to
        # discriminate over, which is a different statement and must not be
        # reported as a clean run.
        print(f"⛔ POPULATION TOO SMALL: terminal.list returned {len(panes)} pane(s) "
              f"({', '.join(str(p.get('title')) for p in panes) or 'none'}). "
              "Identity is UNRESOLVABLE, not unambiguous. The pane list has been "
              "measured collapsing from 13 to 1 mid-session; retry later.",
              file=sys.stderr)
        return 2
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
            # ⛔ A single-candidate population makes every match unambiguous by
            # construction: with one pane the runner-up is 0, so any score clears
            # a "beats the runner-up" bar. Measured — the pane list collapsed from
            # 13 to 1 while this tool was live, and every session would have
            # resolved to that one pane with full confidence.
            #
            # Requiring a real runner-up is not enough either: it must be possible
            # for a DIFFERENT pane to have won. So the population itself is the
            # precondition, and it is checked before any row is called resolved.
            resolved = (len(scroll) >= 2
                        and best >= 4
                        and best >= 2 * max(second, 1))
            sid = os.path.basename(path)[:-6]
            rrow = reg.get(sid)
            rows.append({"session": sid[:8],
                         "pane": title.get(tid) if resolved else None,
                         "hits": best, "runner_up": second,
                         "resolved": resolved,
                         "role": bootstrap_role(path),
                         "name": (rrow or {}).get("name"),
                         "named": name_audit(rrow),
                         # transcript parse is the FALLBACK now, not the source
                         "self_reported": self_reported(path) if rrow is None else None})
    rows.sort(key=lambda r: -r["hits"])

    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"{'session':<10}{'ROLE':<11}{'name':<22}{'origin':<16}"
              f"{'PANE':<16}{'hits':>5}{'2nd':>5}  verdict")
        for r in rows:
            v = "RESOLVED" if r["resolved"] else ("ambiguous" if r["hits"] else "no match")
            fb = ""
            if r["self_reported"] is not None:
                sr = ",".join(r["self_reported"]) or "(none)"
                fb = f"  fallback=transcript {sr} UNRELIABLE"
                if len(r["self_reported"]) > 1:
                    fb += " ⚠file cannot name itself"
            print(f"{fit(r['session'],10)}{fit(r['role'],11)}{fit(r['name'],22)}"
                  f"{fit(r['named'],16)}{fit(r['pane'],16)}{r['hits']:>5}"
                  f"{r['runner_up']:>5}  {v}{fb}")
        n = sum(1 for r in rows if r["resolved"])
        print(f"\n{n} of {len(rows)} sessions resolved to a pane. "
              f"Unresolved means UNKNOWN, not unattached.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
