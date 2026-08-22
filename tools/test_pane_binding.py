#!/usr/bin/env python3
"""Pins pane-binding.py's verdicts and the exit state that could not occur.

Written from the DOCSTRING:

    BOUND      both legs — the pane resolves to a named session
    PARTIAL-A  leg A only — Daintree knows the id, the registry does not
    UNBOUND    leg A absent — nothing on this pane can be joined
    Exit: 0 every pane BOUND · 1 at least one is not · 2 established nothing · 3 self-test failed
    "It reports; it never infers."

⛔ Two findings.

**Exit 0 was unreachable.** Requiring *every* pane to be BOUND means one closed pane from a
past session — the state files hold 30 — makes a clean verdict impossible forever. A success
state that cannot occur is the mirror of a falsifier that cannot fire, and it trains its
reader to ignore the exit code. `PARTIAL` is the actionable state: the join was **attempted**
and half-landed. `UNBOUND` means no leg at all — a pane nobody tried to bind.

**And the docstring's central claim had expired.** It said *"the join has never been observed
working because no pane has yet held both at once"* and *"a register built today would have
ZERO exact joins fleet-wide."* Re-measured 2026-08-20: **13 BOUND**, including every fleet
role. ★ This file is its own known-positive control for the launcher fix — *"BOUND rows
appearing is the evidence the fix worked"* — and the rows appeared while the prose around
them still described the pre-fix world.

Run: python3 tools/test_pane_binding.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_here = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(_here, "pane-binding.py")
_spec = importlib.util.spec_from_file_location("pb", TOOL)
pb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pb)


def build(tmp, terminals, registry_rows):
    d = os.path.join(tmp, "daintree", "proj")
    s = os.path.join(tmp, "sessions")
    os.makedirs(d)
    os.makedirs(s)
    json.dump({"terminals": terminals}, open(os.path.join(d, "state.json"), "w"))
    for pid, row in registry_rows.items():
        json.dump(row, open(os.path.join(s, f"{pid}.json"), "w"))
    return os.path.join(tmp, "daintree"), s


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0

    print("verdicts — it reports, it never infers:")
    reg = {"aaa": {"name": "DEV3"}}
    f += not check("both legs -> BOUND",
                   pb.verdict({"session": "aaa", "title": "DEV3", "pane": "p"}, reg)[0], "BOUND")
    f += not check("leg A only -> PARTIAL-A",
                   pb.verdict({"session": "zzz", "title": "X", "pane": "p"}, reg)[0], "PARTIAL-A")
    f += not check("no leg A -> UNBOUND",
                   pb.verdict({"session": None, "title": "DEV3", "pane": "p"}, reg)[0], "UNBOUND")
    print("  (a matching TITLE must not create a binding — that is the unreliable join)")
    f += not check("title match without leg A is still UNBOUND",
                   pb.verdict({"session": None, "title": "DEV3", "pane": "p"}, reg)[0], "UNBOUND")

    with tempfile.TemporaryDirectory() as tmp:
        print("★ exit 0 must be REACHABLE — a closed pane is not a failure:")
        # BOUND + UNBOUND, no PARTIAL. Under the old rule this was permanently exit 1.
        d, s = build(tmp,
                     [{"id": "t1", "title": "DEV3", "agentSessionId": "aaa"},
                      {"id": "t2", "title": "old-closed-pane"}],
                     {"111": {"sessionId": "aaa", "name": "DEV3"}})
        f += not check("bound + unbound, no partial", pb.report(d, s), 0)

    with tempfile.TemporaryDirectory() as tmp:
        print("PARTIAL is the actionable state and does exit 1:")
        d, s = build(tmp,
                     [{"id": "t1", "title": "DEV3", "agentSessionId": "aaa"},
                      {"id": "t2", "title": "probe", "agentSessionId": "no-such-session"}],
                     {"111": {"sessionId": "aaa", "name": "DEV3"}})
        f += not check("one half-landed join", pb.report(d, s), 1)

    with tempfile.TemporaryDirectory() as tmp:
        print("absent state is VOID, never an empty fleet:")
        try:
            pb.report(os.path.join(tmp, "nope"), tmp)
            f += not check("raised Void", False, True)
        except pb.Void:
            f += not check("raised Void", True, True)

    with tempfile.TemporaryDirectory() as tmp:
        print("an unparseable state file refuses a partial population:")
        d = os.path.join(tmp, "d", "proj")
        os.makedirs(d)
        open(os.path.join(d, "state.json"), "w").write("{not json")
        try:
            pb.panes(os.path.join(tmp, "d"))
            f += not check("raised Void", False, True)
        except pb.Void:
            f += not check("raised Void", True, True)

    print("the self-test still proves every verdict reachable:")
    p = subprocess.run([sys.executable, TOOL, "--self-test"], capture_output=True, text=True)
    f += not check("exit", p.returncode, 0)
    f += not check("all five", "5 of 5" in (p.stdout + p.stderr), True)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
