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

_spec = importlib.util.spec_from_file_location(
    "fleet_state", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-state.py"))
fleet_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_state)


def write(turns, path, title="DEVOPS"):
    """One AGENT TURN per element — with the user turn that ends it.

    ⛔ This helper used to emit consecutive assistant records with NOTHING between
    them, which is a transcript that cannot occur: an agent does not produce two
    turns without an intervening user turn. That made every fixture agree with a
    parser unit — one turn per assistant MESSAGE — that no real corpus supports,
    and the fixtures then defended the unit against correction.

    ⚠ The boundary is a REAL user turn. A tool_result also arrives as role="user";
    see _is_real_user_turn in fleet-state.py and the control below.
    """
    with open(path, "w") as fh:
        fh.write(json.dumps({"type": "custom-title", "customTitle": title}) + "\n")
        for i, t in enumerate(turns):
            if i:
                fh.write(json.dumps({"type": "user", "message": {"role": "user", "content": [
                    {"type": "text", "text": "continue"}]}}) + "\n")
            fh.write(json.dumps({"message": {"role": "assistant", "content": [
                {"type": "text", "text": t}]}}) + "\n")


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


WORK = "Ran the migration, 4 files changed, tests green."


def test_tool_result_is_not_a_turn_boundary():
    """A USER RECORD IS NOT A USER TURN.

    In this harness a tool result is delivered as ``role="user"``. Using "a record
    with role user" as the turn boundary fires once per TOOL CALL, which is the unit
    that made "end every turn with a STATE: line" unsatisfiable: an agent turn
    interleaves prose with tool calls, so only the final block can carry a
    declaration. Measured on a live transcript: 829 message-units vs 275 real turns.
    """
    def _u(blocks):
        return {"type": "user", "message": {"role": "user", "content": blocks}}
    def _a(text):
        return {"type": "assistant", "message": {"role": "assistant",
                "content": [{"type": "text", "text": text}]}}
    base = [
        _u([{"type": "text", "text": "do the thing"}]),
        _a("starting"),
        _u([{"type": "tool_result", "content": "ok"}]),
        _a("still going"),
        _u([{"type": "tool_result", "content": "ok"}]),
        _a("done\nSTATE: FREE — nothing queued"),
    ]
    fd, path = tempfile.mkstemp(suffix=".jsonl"); os.close(fd)
    def put(recs):
        with open(path, "w") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
    ok = True
    try:
        put(base)
        _, t = fleet_state.assistant_texts(path)
        ok &= check("tool_results do not split a turn", len(t), 1)
        ok &= check("declared at the turn's end", fleet_state.declared_state(t[0])[0], "FREE")

        put(base[:-1] + [_a("done, no declaration")])
        _, t2 = fleet_state.assistant_texts(path)
        ok &= check("same shape, no declaration", fleet_state.declared_state(t2[0])[0], None)

        put(base + [_u([{"type": "text", "text": "next"}]), _a("more")])
        _, t3 = fleet_state.assistant_texts(path)
        ok &= check("a REAL user turn does split", len(t3), 2)
    finally:
        os.unlink(path)
    return ok


def test_freshness_marker_binds_to_the_payload():
    """A freshness marker must be ADJACENT to the thing whose freshness it describes.

    ⛔ The row used to put the age in its own COLUMN beside the detail:

        DEV5  WORKING  this turn   context ~98%; ...

    A reader re-associates by PROXIMITY, so that reads as "DEV5 is at 98% NOW".
    Measured: TEAMLEAD read exactly that and was one step from compacting a pane
    sitting at 38% — it had compacted AFTER declaring. The marker was true of the
    LINE and false of the NUMBER INSIDE IT. (Placement fix ruled by DEV2.)
    """
    ok = True
    c = fleet_state.declared_clause(0, 9, "context ~98%")
    ok &= check("payload is quoted", '"context ~98%"' in c, True)
    ok &= check("marker precedes and binds", c.startswith("declared this turn:"), True)
    # ⛔ KNOWN-NEGATIVE: the marker must NOT be separable from the payload. If a
    # caller could render them apart, the column defect returns.
    ok &= check("one string, not a pair", isinstance(c, str), True)
    ok &= check("older declaration says so",
                fleet_state.declared_clause(14, 20, "x").startswith("declared 14 turns ago:"), True)
    ok &= check("never-declared is not 'this turn'",
                "this turn" in fleet_state.declared_clause(None, 20, "x"), False)
    # ⛔ DX's specimen, from review of #417 — the quotes DO the binding, so an
    # unescaped inner quote destroys the boundary the function exists to give.
    c2 = fleet_state.declared_clause(0, 9, 'said "done" already')
    ok &= check("inner quote is escaped", '\\"done\\"' in c2, True)
    ok &= check("exactly two UNESCAPED quotes remain",
                len([i for i, ch in enumerate(c2)
                     if ch == '"' and (i == 0 or c2[i-1] != "\\")]), 2)
    # ⚠ DX flagged the newline case as PROBABLY MOOT and did not establish
    # reachability. Guarded anyway; the guard costs nothing.
    ok &= check("newline cannot split the clause",
                "\n" in fleet_state.declared_clause(0, 9, "multi\nline"), False)
    ok &= check("a backslash does not fake an escape",
                fleet_state.declared_clause(0, 9, 'a\\b').endswith('"a\\\\b"'), True)
    return ok


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

        print("⛔ a freshness marker must bind to the payload, not sit in a column:")
        failures += not test_freshness_marker_binds_to_the_payload()

        print("⛔ a tool_result arrives as role=user — it must NOT end a turn:")
        failures += not test_tool_result_is_not_a_turn_boundary()

        print("empty/tool-only turns are not turns:")
        p = os.path.join(d, "g.jsonl")
        write(["STATE: WORKING — mid-task", "   ", "\n"], p)
        _, texts = fleet_state.assistant_texts(p)
        failures += not check("text turns counted", len(texts), 1)

        # ⛔ THE CONTROL'S OWN POPULATION, #365. main() skips sessions with no fleet role
        # name — correctly, the table is per-role — but the KNOWN-POSITIVE control ("at
        # least one session must declare") was checking only the sessions that survived
        # that filter. Measured 2026-09-06 on the live fleet: a roleless session DID
        # declare, was discarded by the filter, and the tool concluded "the parser is
        # broken" — refuted by the very session it had thrown away.
        # ⇒ Both poles, because the point is that the two causes must READ DIFFERENTLY.
        import io, contextlib
        home = os.path.join(d, "fakehome")
        proj = os.path.join(home, ".claude", "projects", "p")
        os.makedirs(proj)
        _saved_home = os.environ.get("HOME")

        print("★ a ROLELESS session that DECLARES refutes 'the parser is broken':")
        write([WORK, "STATE: FREE — nothing queued"], os.path.join(proj, "roleless.jsonl"),
              title="nforma-next-dc")
        os.environ["HOME"] = home
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = fleet_state.main()
        failures += not check("exit", rc, 2)
        failures += not check("names the roleless declarer",
                              "ROLELESS session(s) DID" in err.getvalue(), True)
        failures += not check("does NOT blame the parser",
                              "this parser is broken" in err.getvalue(), False)

        print("★ the KNOWN-NEGATIVE — nobody declares at all, role-named or not:")
        os.remove(os.path.join(proj, "roleless.jsonl"))
        write([WORK, WORK], os.path.join(proj, "silent.jsonl"), title="nforma-next-dc")
        err2 = io.StringIO()
        with contextlib.redirect_stderr(err2), contextlib.redirect_stdout(io.StringIO()):
            rc2 = fleet_state.main()
        failures += not check("exit", rc2, 2)
        failures += not check("says role-named OR NOT",
                              "role-named or not" in err2.getvalue(), True)
        failures += not check("no roleless declarer claimed",
                              "ROLELESS session(s) DID" in err2.getvalue(), False)
        if _saved_home is not None:
            os.environ["HOME"] = _saved_home

    print()
    if failures:
        print(f"{failures} FAILED")
        return 1
    print("all checks passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())