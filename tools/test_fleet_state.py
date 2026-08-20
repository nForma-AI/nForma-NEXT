#!/usr/bin/env python3
"""Pins the STATE-line reader against the distinction it exists to make.

Why this file exists
--------------------
The reader took the LAST assistant turn and asked whether it ended in a declaration.
Measured on the live fleet: one session had emitted 61 STATE lines, all 61 positionally
last in their turn, and the tool reported that no session in the fleet carried one. Its
most recent turn was mid-work.

**A per-turn declaration read as a per-session property is almost never true**, because a
working agent is between reports. The repair walks back to the most recent turn that did
declare and ages it. The risk the repair creates is the opposite one: walking back far
enough turns a keyword scan into the very thing the positional rule was built to prevent,
so the third case below is as load-bearing as the first.

Run: python3 tools/test_fleet_state.py
"""
import importlib.util
import json
import os
import sys
import tempfile

_spec = importlib.util.spec_from_file_location(
    "fleet_state", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-state.py"))
fleet_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_state)


def write(turns, path, title="DEVOPS"):
    with open(path, "w") as fh:
        fh.write(json.dumps({"type": "custom-title", "customTitle": title}) + "\n")
        for t in turns:
            fh.write(json.dumps({"message": {"role": "assistant", "content": [
                {"type": "text", "text": t}]}}) + "\n")


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


WORK = "Ran the migration, 4 files changed, tests green."


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        print("the regression — declared earlier, working since:")
        p = os.path.join(d, "a.jsonl")
        write([WORK, "Waiting on the key.\nSTATE: BLOCKED — need the escrow decision", WORK, WORK], p)
        names, texts = fleet_state.assistant_texts(p)
        state, detail, back = fleet_state.latest_declaration(texts)
        failures += not check("state", state, "BLOCKED")
        failures += not check("turns_ago", back, 2)
        failures += not check("detail", detail, "need the escrow decision")

        print("declared on the latest turn — turns_ago must be 0, not truthy-but-wrong:")
        p = os.path.join(d, "b.jsonl")
        write([WORK, "STATE: FREE — nothing queued"], p)
        _, texts = fleet_state.assistant_texts(p)
        state, _, back = fleet_state.latest_declaration(texts)
        failures += not check("state", state, "FREE")
        failures += not check("turns_ago", back, 0)

        print("★ the positional rule must SURVIVE the walk-back — a mention is not a declaration:")
        # The whole design of this parser is that a turn DISCUSSING blockage does not count.
        # Walking back through history is exactly where that rule is easiest to lose.
        p = os.path.join(d, "c.jsonl")
        # ⚠ The fixture must contain a line that BEGINS with the token, or it does not
        # exercise the rule: a first draft used "…reply STATE: BLOCKED — naming…" mid-line,
        # which the anchored regex rejects on its own. Breaking the parser into a full scan
        # left that version green — a known-positive that was not positive.
        write([WORK,
               "The prompt requires every turn to end with a line like:\n\n"
               "STATE: BLOCKED — the decision you need, and from whom\n\n"
               "I am quoting it, not declaring it. I am not blocked.",
               WORK], p)
        _, texts = fleet_state.assistant_texts(p)
        state, _, back = fleet_state.latest_declaration(texts)
        failures += not check("state (quoted mention)", state, None)
        failures += not check("turns_ago", back, None)

        print("two declarations — the NEWER one wins:")
        p = os.path.join(d, "e.jsonl")
        write(["STATE: BLOCKED — old blocker", WORK, "STATE: WORKING — moved on", WORK], p)
        _, texts = fleet_state.assistant_texts(p)
        state, detail, back = fleet_state.latest_declaration(texts)
        failures += not check("state", state, "WORKING")
        failures += not check("turns_ago", back, 1)

        print("never declared is None, and None is not FREE:")
        p = os.path.join(d, "f.jsonl")
        write([WORK, WORK, WORK], p)
        _, texts = fleet_state.assistant_texts(p)
        state, _, back = fleet_state.latest_declaration(texts)
        failures += not check("state", state, None)
        failures += not check("turns_ago", back, None)

        print("empty/tool-only turns are not turns:")
        p = os.path.join(d, "g.jsonl")
        write(["STATE: WORKING — mid-task", "   ", "\n"], p)
        _, texts = fleet_state.assistant_texts(p)
        failures += not check("text turns counted", len(texts), 1)

    print()
    if failures:
        print(f"{failures} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
