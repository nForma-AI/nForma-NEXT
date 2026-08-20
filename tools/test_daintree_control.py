#!/usr/bin/env python3
"""Pins daintree-control.py's exit contract against responses it did not expect.

The docstring states the contract:

    Exit: 0 the instrument is answering · 2 VOID — it established nothing.
          A VOID run must never be read as "the fleet is quiet".

⛔ Measured against a fake endpoint that completes the handshake and then returns each
realistic outage shape: **three of eight scenarios exited 1 with a traceback** — a proxy
502 page, a JSON-RPC response with no `result`, and tool content that is not JSON.

**1 is neither "answering" nor "established nothing".** A caller branching on the
documented pair mis-handles it, and it arrives under precisely the conditions this
control exists for: an instrument that has stopped answering while looking like it is.

The fake server is here rather than in a fixture directory because a control's test needs
to be runnable with no network, no MCP server, and no credentials.

Run: python3 tools/test_daintree_control.py
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daintree-control.py")


def tool_result(obj):
    return json.dumps({"jsonrpc": "2.0", "id": 1,
                       "result": {"content": [{"type": "text", "text": json.dumps(obj)}]}})


BODIES = {
    # (content-type, body) returned for tools/call
    "html": ("text/html", "<html><body>502 Bad Gateway</body></html>"),
    "no_result": ("application/json", json.dumps({"jsonrpc": "2.0", "id": 1})),
    "content_not_json": ("application/json", json.dumps(
        {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "not json"}]}})),
    "content_not_list": ("application/json", json.dumps(
        {"jsonrpc": "2.0", "id": 1, "result": {"content": "oops"}})),
    "app_error": ("application/json", tool_result({"code": "AUTH", "message": "bad token"})),
    "one_entry": ("application/json", tool_result([{"agentState": "working"}])),
    "unknown_state": ("application/json", tool_result(
        [{"agentState": "compacting"}, {"agentState": "working"}])),
    "no_state_field": ("application/json", tool_result([{"id": "a"}, {"id": "b"}])),
    "all_waiting": ("application/json", tool_result(
        [{"agentState": "waiting"}, {"agentState": "waiting"}])),
    "healthy": ("application/json", tool_result(
        [{"agentState": "waiting"}, {"agentState": "working"}])),
}


def make_handler(mode):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            method = body.get("method")
            if method == "initialize":
                data = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}).encode()
                self.send_response(200)
                self.send_header("Mcp-Session-Id", "fake-session")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if method == "notifications/initialized":
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            ctype, text = BODIES[mode]
            data = text.encode()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass
    return H


def run_against(mode, tmpdir):
    srv = HTTPServer(("127.0.0.1", 0), make_handler(mode))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        cfg = os.path.join(tmpdir, f"{mode}.json")
        with open(cfg, "w") as fh:
            json.dump({"mcpServers": {"daintree": {
                "type": "http", "url": f"http://127.0.0.1:{srv.server_address[1]}/mcp",
                "headers": {"Authorization": "Bearer fake"}}}}, fh)
        env = dict(os.environ, DAINTREE_CFG=cfg)
        p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, env=env)
        return p.returncode, p.stdout + p.stderr
    finally:
        srv.shutdown()
        srv.server_close()


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0
    with tempfile.TemporaryDirectory() as d:
        print("★ the crash paths — a malformed response must VOID, never traceback:")
        for mode in ("html", "no_result", "content_not_json", "content_not_list"):
            rc, out = run_against(mode, d)
            f += not check(f"{mode} exit", rc, 2)
            f += not check(f"{mode} no traceback", "Traceback" in out, False)

        print("the failure paths that already worked must keep working:")
        for mode in ("app_error", "one_entry", "unknown_state", "all_waiting"):
            rc, _ = run_against(mode, d)
            f += not check(f"{mode} exit", rc, 2)

        print("★ entries with no agentState at all are VOID, not a quiet fleet:")
        rc, out = run_against("no_state_field", d)
        f += not check("exit", rc, 2)
        f += not check("does not claim a pass", "control passes" in out, False)

        print("a healthy instrument answers:")
        rc, out = run_against("healthy", d)
        f += not check("exit", rc, 0)
        f += not check("says it passes", "control passes" in out, True)

        print("config failures are VOID too, and stay VOID:")
        bad = os.path.join(d, "nothing.json")
        p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                           env=dict(os.environ, DAINTREE_CFG=bad))
        f += not check("missing config exit", p.returncode, 2)
        noserver = os.path.join(d, "noserver.json")
        with open(noserver, "w") as fh:
            json.dump({"mcpServers": {}}, fh)
        p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                           env=dict(os.environ, DAINTREE_CFG=noserver))
        f += not check("no daintree server exit", p.returncode, 2)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
