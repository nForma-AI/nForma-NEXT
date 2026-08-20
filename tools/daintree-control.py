#!/usr/bin/env python3
"""Known-positive control for the Daintree fleet-status instrument.

⛔ Why this exists. A waker polls `terminal.getStatus`, wakes whatever is `waiting`, and
logs the cycle. If `getStatus` returned garbage — an empty list, a schema change, an auth
failure rendered as data — the waker would log a quiet cycle and its reader would see a
healthy fleet. **A blind instrument and a calm fleet produce the same output**, and the
failure direction is silence.

★ The control has to terminate on something known BY CONSTRUCTION, not by query.
Asserting "TEAMLEAD should be present" is itself a query against the thing under test.
But the agent running this check **is executing while it runs**, so:

    > At least one pane MUST report `working`, because I am one, right now.

If the instrument cannot see that, it cannot see anything, and every `waiting` it reports
is unfounded.

Exit: 0 the instrument is answering · 2 VOID — it established nothing.
      A VOID run must never be read as "the fleet is quiet".
"""
import json, os, subprocess, sys

CFG = os.environ.get("DAINTREE_CFG") or os.path.expanduser("~/.claude.json")
KNOWN_STATES = {"working", "waiting", "idle", "error", "exited"}


def endpoint():
    # DAINTREE_CFG overrides the config path. Present so this check can be proven to FAIL
    # against a broken instrument — a control that has only ever passed is not a control.
    try:
        cfg = json.load(open(CFG))
    except Exception as exc:
        print(f"⛔ VOID: cannot read {CFG}: {exc}\n   ADDABLE — FIXABLE HERE: the file is the user\u2019s own MCP config; check the path\n   and permissions before concluding anything about the fleet.", file=sys.stderr)
        sys.exit(2)
    srv = (cfg.get("mcpServers") or {}).get("daintree")
    if not srv:
        print("⛔ VOID: no daintree MCP server configured.\n   ADDABLE — NEEDS THE OPERATOR: ask them to add a `daintree` entry to\n   mcpServers in ~/.claude.json. ⚠ This is not a limit of this fleet: the\n   config was supplied in ninety seconds once anyone asked. This message was\n   read, quoted and BUILT AROUND for four hours because it named the absence\n   and not the remedy.", file=sys.stderr)
        sys.exit(2)
    return srv["url"], (srv.get("headers") or {}).get("Authorization", "")


def rpc(url, auth, method, params=None, sid=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    cmd = ["curl", "-s", "--max-time", "10", "-H", f"Authorization: {auth}",
           "-H", "Accept: application/json, text/event-stream",
           "-H", "Content-Type: application/json"]
    if sid:
        cmd += ["-H", f"Mcp-Session-Id: {sid}"]
    cmd += ["-X", "POST", url, "-d", json.dumps(body)]
    # ⛔ Every parse below can fail on a response that is not this protocol — a proxy
    # 502 page, a truncated body, a schema that dropped `result`. Measured against a
    # fake endpoint that completes the handshake and then returns each of those: the
    # previous version raised and exited **1** for three of eight scenarios, and 1 is
    # neither "answering" (0) nor "established nothing" (2). A caller branching on the
    # documented pair mis-handles the crash, and the crash arrives under exactly the
    # conditions this control exists for.
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        return {"error": {"message": f"cannot run curl: {exc}"}}
    out = proc.stdout
    if proc.returncode != 0 and not out.strip():
        return {"error": {"message": f"curl exited {proc.returncode}: "
                                     f"{(proc.stderr or '').strip()[:200] or 'no output'}"}}
    for line in out.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except ValueError as exc:
                return {"error": {"message": f"event-stream payload is not JSON: {exc}"}}
    if not out.strip():
        return {}
    try:
        return json.loads(out)
    except ValueError:
        return {"error": {"message": "response body is not JSON: "
                                     f"{out.strip()[:160]!r}"}}


def payload(res):
    """An application error arrives INSIDE a successful response — check for it.

    ⚠ Every exit from here is 2. A malformed response is *established nothing*, and
    the one thing this file must never do is let a shape it did not expect become an
    exit code that reads as a verdict.
    """
    if not res or res.get("error"):
        print(f"⛔ VOID: rpc error {res.get('error') if res else 'no response'}", file=sys.stderr)
        sys.exit(2)
    result = res.get("result")
    if not isinstance(result, dict):
        print(f"⛔ VOID: response carries no `result` object — got keys "
              f"{sorted(res)}. The schema moved, or this is not the endpoint it "
              f"claims to be.", file=sys.stderr)
        sys.exit(2)
    content = result.get("content")
    if not isinstance(content, list):
        print(f"⛔ VOID: `result.content` is {type(content).__name__}, not a list.",
              file=sys.stderr)
        sys.exit(2)
    text = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    try:
        obj = json.loads(text)
    except ValueError:
        print(f"⛔ VOID: tool content is not JSON: {text.strip()[:160]!r}", file=sys.stderr)
        sys.exit(2)
    if isinstance(obj, dict) and obj.get("code") and obj.get("message"):
        print(f"⛔ VOID: {obj['code']}: {obj.get('details') or obj['message']}", file=sys.stderr)
        sys.exit(2)
    return obj


def main():
    url, auth = endpoint()
    try:
        hs = subprocess.run(
            ["curl", "-sD", "-", "-o", "/dev/null", "--max-time", "10",
             "-H", f"Authorization: {auth}",
             "-H", "Accept: application/json, text/event-stream",
             "-H", "Content-Type: application/json", "-X", "POST", url,
             "-d", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                 "protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "control", "version": "1"}}})],
            capture_output=True, text=True).stdout
    except OSError as exc:
        print(f"⛔ VOID: cannot run curl: {exc}", file=sys.stderr)
        return 2
    sid = next((l.split(":", 1)[1].strip() for l in hs.splitlines()
                if l.lower().startswith("mcp-session-id:")), None)
    if not sid:
        print("⛔ VOID: handshake returned no session id", file=sys.stderr)
        return 2
    rpc(url, auth, "notifications/initialized", sid=sid)

    entries = payload(rpc(url, auth, "tools/call",
                          {"name": "terminal.getStatus", "arguments": {}}, sid))
    if isinstance(entries, dict):
        entries = entries.get("terminals") or entries.get("entries") or [entries]

    if len(entries) < 2:
        print(f"⛔ VOID: getStatus returned {len(entries)} entr(y/ies). Too small a population "
              f"to describe a fleet — this is UNKNOWN, not quiet.", file=sys.stderr)
        return 2

    states = [e.get("agentState") for e in entries if isinstance(e, dict)]
    unknown = {s for s in states if s and s not in KNOWN_STATES}
    if unknown:
        print(f"⛔ VOID: unrecognised agentState values {sorted(unknown)} — the schema moved "
              f"under the caller. Every state-based decision below it is unfounded.",
              file=sys.stderr)
        return 2

    # ★ The control proper: I am executing, so a working pane MUST exist.
    if "working" not in states:
        print(f"⛔ CONTROL FAILED — no pane reports `working`, yet this check is running in "
              f"one. The instrument cannot see a pane it must be able to see, so every "
              f"`waiting` it reports is unfounded. VOID, not quiet.\n"
              f"   states seen: {sorted(set(s for s in states if s))}", file=sys.stderr)
        return 2

    print(f"✅ control passes — {len(entries)} panes, states "
          f"{sorted(set(s for s in states if s))}, at least one `working` as required")
    return 0


if __name__ == "__main__":
    sys.exit(main())
