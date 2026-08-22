#!/usr/bin/env python3
"""Pins the exact session→pane join, and that a content match never impersonates it.

⛔ Why this exists. `fleet-identity.py` joins sessions to panes by CONTENT — rare tokens from
recent output against pane scrollback — because when it was written **no pane carried
Daintree's `agentSessionId`**. `pane-binding.py` recorded that as permanent: *"the join has
never been observed working because no pane has yet held both legs at once."*

Re-measured 2026-08-20: **13 panes are exactly bound, including every fleet role.** The
premise expired and the workaround outlived it. Wiring the exact join in moved this tool from
**5 of 12** sessions resolved to **10 of 12**, and the rows it gained are the ones content
matching could not reach — a pane with a single token hit is unresolvable by overlap and
unambiguous by binding.

★ An exact binding and a content match are **different kinds of evidence** and are reported as
different verdicts. Collapsing them would hide which rows rest on token overlap. And where both
exist and disagree, the disagreement is printed — two joins disagreeing is a finding, and
silently preferring one is how a wrong identity becomes a fact.

Run: python3 tools/test_fleet_identity_exact.py
"""
import importlib.util
import json
import os
import sys
import tempfile

_here = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(_here, "fleet-identity.py")
_spec = importlib.util.spec_from_file_location("fi", TOOL)
fi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fi)


def with_state(tmp, projects):
    """projects: {name: terminals-list}. Returns the root to point DAINTREE_STATE at."""
    root = os.path.join(tmp, "projects")
    for name, terminals in projects.items():
        d = os.path.join(root, name)
        os.makedirs(d)
        json.dump({"terminals": terminals}, open(os.path.join(d, "state.json"), "w"))
    return root


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0
    # ⚠ Presence check FIRST. A version without these functions raises AttributeError
    # at the first call and aborts before every remaining assertion — a break that
    # stops early under-reports, which is the quieter cousin of one that prints
    # nothing. Third time in this suite family; guard, then report all of it.
    missing = [n for n in ("exact_bindings", "pane_verdict") if not hasattr(fi, n)]
    if missing:
        for n in missing:
            print(f"  FAIL  {n} is absent — this version cannot express the exact join")
        print(f"\n{len(missing)} FAILED (the rest of the suite needs them and was not run)")
        return 1
    orig = fi.DAINTREE_STATE
    try:
        with tempfile.TemporaryDirectory() as tmp:
            fi.DAINTREE_STATE = with_state(tmp, {"p1": [
                {"id": "term-1", "title": "DEV3", "agentSessionId": "sess-aaa"},
                {"id": "term-2", "title": "DEV4"},                      # no leg A
                {"id": "term-3", "agentSessionId": "sess-ccc"},          # bound, untitled
            ]})
            b = fi.exact_bindings()

            print("★ the exact join is read from the field Daintree CHOSE at launch:")
            f += not check("bound pane", b.get("sess-aaa"), ("term-1", "DEV3"))
            f += not check("bound but untitled is still bound", b.get("sess-ccc"),
                           ("term-3", None))

            print("★ a pane without the field is ABSENT — never guessed from its title:")
            # DEV4's title matches a real role. Title agreement is precisely the
            # unreliable join this tool exists to refuse.
            f += not check("no fabricated binding for DEV4",
                           any(v[1] == "DEV4" for v in b.values()), False)
            f += not check("population size", len(b), 2)

        with tempfile.TemporaryDirectory() as tmp:
            print("an unparseable state file yields no binding and does not crash:")
            root = with_state(tmp, {"good": [{"id": "t", "title": "T",
                                             "agentSessionId": "s1"}]})
            bad = os.path.join(root, "bad")
            os.makedirs(bad)
            open(os.path.join(bad, "state.json"), "w").write("{not json")
            fi.DAINTREE_STATE = root
            b = fi.exact_bindings()
            f += not check("good project still read", b.get("s1"), ("t", "T"))
            f += not check("nothing invented from the bad one", len(b), 1)

        with tempfile.TemporaryDirectory() as tmp:
            print("an absent Daintree root is an empty map, not an exception:")
            fi.DAINTREE_STATE = os.path.join(tmp, "nope")
            f += not check("empty", fi.exact_bindings(), {})

        print("terminals missing an id are not bindings:")
        with tempfile.TemporaryDirectory() as tmp:
            fi.DAINTREE_STATE = with_state(tmp, {"p": [{"agentSessionId": "s", "title": "X"}]})
            f += not check("skipped", fi.exact_bindings(), {})
    finally:
        fi.DAINTREE_STATE = orig

    print("★ precedence, tested as BEHAVIOUR — a source-text assertion is not one:")
    pv = fi.pane_verdict
    f += not check("exact wins", pv("DEV3", True, "DEV3", 9)[0], "EXACT")
    f += not check("exact wins with NO content match at all", pv("DEV4", False, None, 1)[0],
                   "EXACT")
    f += not check("content match alone is RESOLVED, not EXACT",
                   pv(None, True, "DEV3", 9)[0], "RESOLVED")
    f += not check("neither -> ambiguous when there were hits",
                   pv(None, False, None, 3)[0], "ambiguous")
    f += not check("neither, no hits -> no match", pv(None, False, None, 0)[0], "no match")

    print("★ and a DISAGREEMENT is surfaced, never silently resolved:")
    v, dis = pv("TEAMLEAD", True, "DEV2", 7)
    f += not check("flagged", dis, True)
    f += not check("names the loser", "DEV2" in v, True)
    f += not check("still reports EXACT", v.startswith("EXACT"), True)
    f += not check("agreement is not a disagreement", pv("DEV3", True, "DEV3", 9)[1], False)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
