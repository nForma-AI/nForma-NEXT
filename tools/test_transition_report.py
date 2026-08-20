#!/usr/bin/env python3
"""Pins the transition auditor against the four ways it could be wrong and still print.

Why this file exists
--------------------
This auditor's output is a list of accusations — "you transitioned and announced nothing" —
so every one of its failure modes produces a plausible page. Three are near-misses of the
rule it enforces:

  * firing on every FREE turn instead of on the CHANGE, which turns a five-turn wait into
    five violations and makes the report unreadable exactly when the fleet is busiest;
  * opening the send-window at the file start, so one message hours ago excuses every
    transition since;
  * counting WORKING as announceable, which the protocol deliberately does not require.

The fourth is the one this fleet has already committed once, in the reader this tool imports:
matching `STATE:` as a **keyword** rather than as the final line. Measured on the live fleet
while building this — one pane carries the string `STATE: WORKING` on five lines and has
declared zero times, because all five are quotations in messages *about* the protocol. A
keyword scan reports that pane as the compliant one.

Run: python3 tools/test_transition_report.py
"""
import importlib.util
import json
import os
import sys
import tempfile

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE, and the dangerous
# class is the COMMON one: Python invalidates a .pyc on mtime + SIZE, so a
# SIZE-PRESERVING mutation (==/!=, a flag flip, a token swap) applied in the same
# second leaves both unchanged and the cache is served. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "transition_report", os.path.join(_HERE, "transition-report.py"))
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)


def check(name, got, want):
    ok = got == want
    print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
    return ok


def decls(*states):
    """(line, state, detail) triples one line apart, which is all the auditor reads."""
    return [(i * 10, s, "") for i, s in enumerate(states)]


def main():
    failures = 0

    # ── 1. A repeat is not a transition ──────────────────────────────────────────────
    # The protocol says send on TRANSITION precisely so a waiting agent sends once.
    got = [(t["prev"], t["state"]) for t in tr.transitions(decls("FREE", "FREE", "FREE"))]
    failures += not check("three FREE turns are one transition", got, [(None, "FREE")])

    got = [(t["prev"], t["state"]) for t in
           tr.transitions(decls("WORKING", "FREE", "FREE", "WORKING", "BLOCKED"))]
    failures += not check(
        "only the changes", got,
        [(None, "WORKING"), ("WORKING", "FREE"), ("FREE", "WORKING"), ("WORKING", "BLOCKED")])

    # ── 2. The first declaration is a transition, and is marked as such ──────────────
    ts = tr.transitions(decls("BLOCKED", "WORKING"))
    failures += not check("first declaration flagged", [t["first"] for t in ts], [True, False])

    # ── 3. WORKING is not announceable ──────────────────────────────────────────────
    rows = tr.audit(decls("FREE", "WORKING"), [])
    failures += not check("WORKING produces no row", [r["state"] for r in rows], ["FREE"])

    # ── 4. The send-window opens at the PREVIOUS declaration, not at the file start ──
    # WORKING@0, FREE@10, BLOCKED@20. A send at line 5 lands in (0,10] — it belongs to the
    # FREE transition and must NOT also excuse the BLOCKED at 20. Otherwise a single message,
    # ever, is permanent cover for every silence that follows it.
    #
    # ⚠ The first expectation here was written as {"FREE": 1, "BLOCKED": 0} against
    # decls("FREE","WORKING","BLOCKED") and failed: line 5 is *after* that FREE, not before
    # it. The test was wrong and the tool was right. Kept as a comment because the near-miss
    # is the thing worth pinning — "the window before a declaration" and "the window after
    # it" are one off-by-one apart and produce plausible reports either way.
    d = decls("WORKING", "FREE", "BLOCKED")
    rows = tr.audit(d, [(5, "TEAMLEAD")])
    by_state = {r["state"]: len(r["sends"]) for r in rows}
    failures += not check("early send covers its own transition only",
                          by_state, {"FREE": 1, "BLOCKED": 0})

    rows = tr.audit(d, [(15, "TEAMLEAD")])
    by_state = {r["state"]: len(r["sends"]) for r in rows}
    failures += not check("send inside the window counts", by_state, {"FREE": 0, "BLOCKED": 1})

    # A send exactly ON the declaration line counts — the tool call precedes the text that
    # closes the turn, and both can share a record boundary.
    rows = tr.audit(decls("WORKING", "FREE"), [(10, "TEAMLEAD")])
    failures += not check("send on the boundary line counts",
                          [len(r["sends"]) for r in rows], [1])

    # ── 5. scan(): positional declarations, and SendMessage recipients ───────────────
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "s.jsonl")
        with open(p, "w") as fh:
            fh.write(json.dumps({"type": "custom-title", "customTitle": "DEVOPS"}) + "\n")
            # A turn that QUOTES the protocol. The quotation is on its own line and starts
            # at column 0 — which is the only shape that discriminates, and the shape the
            # live fleet actually produces.
            #
            # ⛔ The first version of this fixture wrote the mention mid-sentence
            # ("Peers should write STATE: BLOCKED when stuck."). A keyword scan grafted in
            # as a mutation SURVIVED it, because `STATE_RE.match` is line-anchored and a
            # mid-sentence mention fails a keyword scan too. The test asserted the right
            # thing about the wrong input and would have passed forever.
            fh.write(json.dumps({"message": {"role": "assistant", "content": [
                {"type": "text",
                 "text": "Reminder, the format is:\n"
                         "STATE: BLOCKED — <the decision, in one line>\n"
                         "I am not blocked myself; carrying on."}
            ]}}) + "\n")
            # a real declaration, in a turn that also sent a message
            fh.write(json.dumps({"message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "SendMessage",
                 "input": {"to": "TEAMLEAD", "message": "QUEUE EMPTY"}},
                {"type": "text", "text": "Handing off.\nSTATE: FREE — nothing queued"}
            ]}}) + "\n")
        names, d, sends = tr.scan(p)
        failures += not check("quoted STATE is not a declaration",
                              [s for _, s, _ in d], ["FREE"])
        failures += not check("recipient captured", [to for _, to in sends], ["TEAMLEAD"])
        failures += not check("roster name read", names, ["DEVOPS"])

        rows = tr.audit(d, sends)
        failures += not check("same-turn send pairs with the declaration",
                              [len(r["sends"]) for r in rows], [1])

    print()
    if failures:
        print(f"{failures} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
