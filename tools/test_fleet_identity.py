#!/usr/bin/env python3
"""Pins bootstrap_role against the two ways it was wrong at once.

Why this file exists
--------------------
`bootstrap_role` claimed, in its docstring, to read "the first user message". It scanned
every line of the transcript and returned the first `You are <ROLE>` it found anywhere.
Measured on five live sessions, 4 of 5 matches were **another agent's identity** — three
arriving through a recall hook that injects other sessions' prompts as attachments, one
from the session's own outbound dispatch text.

It was also matching a **frozen list** of role names. This fleet runs at least two
vocabularies: the bootstraps actually found include CODER2..CODER5 and TRIAGE, none of
which the list contained. So a session launched as TRIAGE read as having no bootstrap,
while a session launched as CODER2 was labelled DX.

Two defects pushing the same way: toward a confident, wrong identity.

Run: python3 tools/test_fleet_identity.py
"""
import importlib.util
import json
import os
import sys
import tempfile

_spec = importlib.util.spec_from_file_location(
    "fleet_identity", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-identity.py"))
fleet_identity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_identity)


def user(text, sidechain=False):
    return {"type": "user", "isSidechain": sidechain,
            "message": {"role": "user", "content": text}}


def assistant(text):
    return {"type": "assistant", "message": {"role": "assistant",
                                             "content": [{"type": "text", "text": text}]}}


def attachment(text):
    """How another session's prompt actually arrives: a hook injects it."""
    return {"type": "attachment", "isSidechain": False,
            "attachment": {"type": "hook_system_message", "content": text}}


def write(records, path):
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        print("★ the regression — a recall hook quoting ANOTHER session's prompt:")
        p = os.path.join(d, "a.jsonl")
        write([user("You are TRIAGE, an IMPLEMENTER reporting to TEAMLEAD."),
               assistant("Working."),
               attachment('deja-vu: you have been here — "You are DEVOPS, an IMPLEMENTER…"'),
               assistant("Continuing.")], p)
        failures += not check("own bootstrap wins", fleet_identity.bootstrap_role(p), "TRIAGE")

        print("★ outbound dispatch — the session telling SOMEONE ELSE who they are:")
        p = os.path.join(d, "b.jsonl")
        write([user("Pick up where you left off."),
               assistant('cmd = """You are DEVOPS, an IMPLEMENTER reporting to TEAMLEAD."""')], p)
        failures += not check("dispatch is not identity", fleet_identity.bootstrap_role(p), "")

        print("derive, do not enumerate — a vocabulary the old frozen list could not see:")
        for launched in ("CODER2", "TRIAGE", "MAINTAINER"):
            p = os.path.join(d, f"c-{launched}.jsonl")
            write([user(f"You are {launched}, a persistent implementation agent.")], p)
            failures += not check(launched, fleet_identity.bootstrap_role(p), launched)

        print("a transcript with no bootstrap is None — and None is not a name:")
        p = os.path.join(d, "d.jsonl")
        write([user("TEAMLEAD — GITHUB OUTAGE DIRECTIVE (2026-08-17). Resume."),
               assistant("Ack.")], p)
        failures += not check("resumed transcript", fleet_identity.bootstrap_role(p), "")

        print("★ the scan is BOUNDED — a bootstrap arriving late is not a bootstrap:")
        # The defect being fixed was an unbounded scan. A bound that is too generous
        # reintroduces it, so this pins that the bound is real rather than decorative.
        late = [user("hello"), user("still going"), user("more"), user("more"),
                user("You are IMPOSTOR, definitely your real identity.")]
        p = os.path.join(d, "e.jsonl")
        write(late, p)
        failures += not check("late declaration ignored", fleet_identity.bootstrap_role(p), "")

        print("sidechain turns are not the session's own instructions:")
        p = os.path.join(d, "f.jsonl")
        write([user("You are SUBAGENT, do this narrow thing.", sidechain=True),
               user("You are DX, an IMPLEMENTER reporting to TEAMLEAD.")], p)
        failures += not check("sidechain skipped", fleet_identity.bootstrap_role(p), "DX")

        # ⛔ THESE TWO ASSERTIONS PINNED A COLLAPSE. Until now "missing file" and
        # "read it, no bootstrap" both expected None, so the suite encoded as correct
        # the very two-states-one-output shape this tool family exists to catch — the
        # same way the old depth_bands assertion pinned its own.
        print("an unreadable path establishes nothing, and does not raise:")
        failures += not check("missing file is None (COULD NOT READ)", fleet_identity.bootstrap_role(
            os.path.join(d, "nope.jsonl")), None)
        # ⚠ Identity, not truthiness. Both are falsy, so `if role:` merges them again —
        # which is how the original collapse survived every green run.
        write([user("Pick up where you left off."), assistant("ok")], p)
        f_read = fleet_identity.bootstrap_role(p)
        f_gone = fleet_identity.bootstrap_role(os.path.join(d, "nope.jsonl"))
        failures += not check("read-but-absent is not the same value as unreadable",
                              f_read is f_gone, False)
        failures += not check("and the falsy test cannot tell them apart",
                              (not f_read) == (not f_gone), True)

    print()
    if failures:
        print(f"{failures} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
