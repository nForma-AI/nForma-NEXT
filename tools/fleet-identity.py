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
        sys.exit("no 'daintree' MCP server configured — nothing to resolve against.\n"
                 "   ADDABLE — NEEDS THE OPERATOR: add a `daintree` entry to mcpServers\n"
                 "   in ~/.claude.json. Until then use --registry-only, which answers\n"
                 "   role/name/when-named without any MCP.")
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


# Anything under this many seconds after process start is a name the LAUNCH set.
# Calibration: `claude -n X` wrote nameSince 2 MILLISECONDS after startedAt.
# Every post-hoc naming measured sat at 27s or beyond. 5s is two orders of
# magnitude above the launch case and two below the nearest non-launch case, so
# the threshold is not load-bearing -- but the raw delta is printed regardless,
# because a reader should be able to overrule the bucket.
LAUNCH_WINDOW_S = 5


DAINTREE_STATE = os.path.expanduser("~/Library/Application Support/Daintree/projects")


def panel_titles(cwd):
    """★ Leg 2 of the identity triple, WITHOUT the Daintree MCP.

    §4 requires `logical identity = Daintree panel name = Claude session name`.
    Legs 1 and 3 are readable from the transcript and the session registry. Leg 2
    was believed to need `terminal.list` over MCP -- and no `daintree` MCP server
    is configured on this machine, so the panel leg went UNVERIFIED for the whole
    session and was accepted on the operator's word instead.

    It does not need MCP. Daintree persists project state to
    ~/Library/Application Support/Daintree/projects/<hash>/state.json, which
    carries every pane's `title`, `titleMode` and `cwd`.

    ⚠ `titleMode` matters as much as `title`. "user" means the title is PINNED;
    "default" means agent auto-titling may overwrite it, so a correct title
    under "default" is correct-for-now and not an established identity.

    ⚠ This is a persisted view, not the live UI, so it can lag. The caller is
    given the file's mtime and must state it -- an identity read from a stale
    file is exactly the class of evidence this repo requires a timestamp on.
    """
    best, mtime = {}, None
    for path in glob.glob(os.path.join(DAINTREE_STATE, "*", "state.json")):
        try:
            doc = json.load(open(path))
        except Exception:
            continue
        panes = [t for t in doc.get("terminals", []) if t.get("cwd") == cwd]
        if not panes:
            continue
        mtime = os.path.getmtime(path)
        for t in panes:
            if t.get("title"):
                best[t["title"]] = t.get("titleMode")
    return best, mtime


def name_audit(row):
    """WHEN did this session's name arrive -- at launch, or afterwards?

    ⛔ Key absence is necessary and NOT sufficient, and the insufficiency is the
    whole point. `nameSource` absent collapses at least THREE mechanisms:

        (i)   named by `-n <name>` at launch
        (ii)  named by a real `/rename`
        (iii) a registry row patched by another process

    An earlier version of this function returned "explicit" for all three and
    was used to conclude that the `-n` recipe change had worked. It had not:
    the recipe post-dated the running fleet by thirteen minutes, and the names
    came from (iii). Two mechanisms, one reading -- the discriminates.py case,
    inside the fix for a previous instance of the same case.

    ★ `nameSince - startedAt` separates (i) from (ii)+(iii) by arithmetic. A
    launch flag cannot name a pane ten minutes after boot.

    ⛔ It does NOT separate (ii) from (iii). Both are "later", both leave the key
    absent, and the field holds only the most recent write -- measured, when an
    operator's `/rename` at +48min silently overwrote a registry patch at +12min
    and left no trace of the earlier one. So the bucket is `later`, never
    `/rename`. Naming the finer mechanism would be this same error one level
    down.
    """
    if row is None:
        return "no-registry-row", None
    if row.get("nameSource") is not None:
        return "derived", None
    since, start = row.get("nameSince"), row.get("startedAt")
    if not (since and start):
        return "explicit-when-unknown", None
    delta = (since - start) / 1000.0
    return ("at-launch" if delta < LAUNCH_WINDOW_S else "later"), delta


# ⛔ DERIVED, not enumerated. The first version matched a frozen list —
# TEAMLEAD|ARCHITECT|DEVOPS|DX|DEV[1-9] — and this fleet does not use one
# vocabulary: measured bootstraps include CODER2, CODER3, CODER4, CODER5 and
# TRIAGE, none of which the list could see. A session launched as TRIAGE read as
# having no bootstrap at all, while a session launched as CODER2 was labelled DX.
BOOTSTRAP_RE = re.compile(r"\bYou are ([A-Z][A-Z0-9_-]{1,20})\b")

# How many early user turns may carry the bootstrap. Bounded on purpose: the
# defect being fixed is an UNBOUNDED scan, and a large bound reintroduces it.
BOOTSTRAP_TURNS = 3


def bootstrap_role(path):
    """The role a session was LAUNCHED as, from its FIRST user turns.

    Distinct from any name it now carries: the name can be patched, the
    bootstrap cannot. A disagreement between the two is the finding.

    ⛔ The previous version scanned EVERY LINE of the transcript for the first
    `You are <ROLE>` and returned it — the docstring said "first user message",
    the code said "anywhere". Measured on five live sessions, **4 of 5 matches
    were another agent's identity**:

      4358eeaa  line 10820  a deja-vu recall hook quoting ANOTHER session's prompt
      ec0d07f0  line  1319  same hook, quoting session 6fc2dca8's prompt
      96827e4b  line  6414  same hook, quoting session 6150ffb2's prompt
      e4a7769d  line 14839  the session's own bash heredoc DISPATCHING a role
      c67ebcb4  line    14  the real bootstrap, in a user record

    ⚠ The contamination has a **sign**: recall hooks and outbound dispatch are
    what busy, well-connected agents do, so the agents most likely to be
    mislabelled are the ones doing the most cross-session work. A column reading
    "DX" gives no hint that the string came from someone else's session.

    Returns None when no bootstrap appears in the early turns — which happens,
    and honestly: a resumed transcript may simply not contain the message that
    started it. None means "not in this file", never "unnamed".
    """
    try:
        seen = 0
        for line in open(path, errors="replace"):
            if '"user"' not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            # An attachment carries text the agent never received as its own
            # instruction — that is exactly how another session's prompt got in.
            if rec.get("type") != "user" or rec.get("isSidechain"):
                continue
            msg = rec.get("message") or {}
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(b.get("text", "") for b in content
                                if isinstance(b, dict) and b.get("type") == "text")
            else:
                text = ""
            if not text.strip():
                continue
            m = BOOTSTRAP_RE.search(text)
            if m:
                return m.group(1)
            seen += 1
            if seen >= BOOTSTRAP_TURNS:
                return None
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


def _dt(v):
    """Seconds between process start and the name being written. Printed beside
    the bucket so a reader can overrule the threshold rather than trust it."""
    return "-" if v is None else (f"{v:.0f}s" if v < 600 else f"{v/60:.0f}m")


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
                         "named": name_audit(row)[0], "named_after_s": name_audit(row)[1],
                         "pid": (row or {}).get("pid"),
                         "status": (row or {}).get("status"),
                         "agrees": bool(row) and (row.get("name") == bootstrap_role(path)),
                         "self_reported": self_reported(path) if row is None else None})
    rows.sort(key=lambda r: (r["role"] or "~", r["session"]))
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    print("MODE: registry join (session -> role, name, when-named). "
          "Does NOT resolve WHICH pane runs WHICH session; that needs Daintree.")
    print(f"{'session':<10}{'ROLE':<11}{'name':<22}{'origin':<12}{'+s':>8}{'pid':>7}  agrees")
    for r in rows:
        flag = "OK" if r["agrees"] else ("DRIFT" if r["role"] and r["name"] else "-")
        fb = ""
        if r["self_reported"] is not None:
            fb = "  fallback=transcript " + (",".join(r["self_reported"]) or "(none)") + " UNRELIABLE"
        print(f"{fit(r['session'],10)}{fit(r['role'],11)}{fit(r['name'],22)}"
              f"{fit(r['named'],12)}{_dt(r['named_after_s']):>8}"
              f"{str(r['pid'] or '-'):>7}  {flag}{fb}")
    sys.stdout.flush()
    # ⛔ NOT `rev-parse --show-toplevel`. In a worktree that returns the WORKTREE
    # path, and Daintree records the pane's cwd as the MAIN tree -- so the lookup
    # silently found nothing and printed "LEG 2 UNAVAILABLE". Measured the first
    # time this tool was run from inside a worktree, by the change that added it.
    # `git worktree list --porcelain` names the main tree first, always.
    cwd = os.path.realpath(os.getcwd())
    wt = subprocess.run(["git", "-C", cwd, "worktree", "list", "--porcelain"],
                        capture_output=True, text=True).stdout
    top = next((ln[9:] for ln in wt.splitlines() if ln.startswith("worktree ")), "")
    panels, pmtime = panel_titles(top or cwd)
    if panels:
        roles = {r["role"] for r in rows if r["role"]}
        missing = sorted(roles - set(panels))
        loose = sorted(t for t, m in panels.items() if m != "user")
        stamp = time.strftime("%H:%M:%S", time.localtime(pmtime)) if pmtime else "?"
        print(f"\nLEG 2 (Daintree panel titles, from persisted state, measured {stamp}): "
              f"{len(panels)} panes for {os.path.basename(top or cwd)}", file=sys.stderr)
        print(f"  roles with no matching panel : {', '.join(missing) or 'none'}", file=sys.stderr)
        print(f"  titles NOT pinned (titleMode != user, so auto-titling may overwrite): "
              f"{', '.join(loose) or 'none'}", file=sys.stderr)
    else:
        print("\n⚠ LEG 2 UNAVAILABLE: no Daintree project state found for this repo. "
              "The panel leg is UNVERIFIED, not verified-absent.", file=sys.stderr)
    drifted = [r for r in rows if r["role"] and r["name"] and not r["agrees"]]
    derived = [r for r in rows if r["named"] == "derived"]
    later = [r for r in rows if r["named"] == "later"]
    print(f"\n{len(rows)} sessions. {len(drifted)} name/role disagreements, "
          f"{len(derived)} still auto-derived, {len(later)} named AFTER launch.", file=sys.stderr)
    print("⚠ 'at-launch' means the name came from the launch flag. 'later' means a /rename OR a\n"
          "  registry patch -- those two are NOT distinguishable here and must not be reported as\n"
          "  one. A 'later' count above zero means the recipe's -n is UNPROVEN for those panes.",
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
                         "named": name_audit(rrow)[0], "named_after_s": name_audit(rrow)[1],
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
