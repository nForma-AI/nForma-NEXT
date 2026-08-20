#!/usr/bin/env python3
"""Pins pane-census.py's refusal behaviour, and gives it a CALLER.

⛔ WHY THIS EXISTS. Criterion 4 was amended in #381: an instrument must be shown to
fail on real data **BY A CALLER THAT STILL RUNS IT** — *"a demonstration that happened
once and cannot happen again is a SCREENSHOT."* #372 measured 11 instruments whose
controls sit outside the gating path; `pane-census.py` was one of 7 with no paired
suite at all. Its `--self-test` is real and nothing ran it, so it satisfied criterion 4
by screenshot: I pasted output into a PR and the CI never touched it.

⚠ HERMETIC BY CONSTRUCTION, and that is the point rather than a convenience. This drives
`census()` — which is pure, taking rows and transcript ids — with FIXTURES. It never
contacts the daintree MCP, never reads ~/.claude/projects, and never depends on how many
panes happen to be open. A suite that needs a live fleet is not gating; it is a second
screenshot on a timer.
⇒ No `# SUITE-DEPENDS:` marker: this suite has no external dependency to declare.

Its stated contract, pinned below:

    Exit: 0 sources agree · 1 a divergence is NAMED · 2 established nothing
    "A census that silently returns 8 is the defect. One that returns 8 and declares
     UNESTABLISHED is the fix."
    "Liveness is the thing being MEASURED, so it cannot also be the membership test."
    Identity key is the pane id, never the display name.

★ THE LOAD-BEARING CHECK IS NOT THAT IT COUNTS 9. It is that it REFUSES. Six of the
eight checks below assert a refusal; only one asserts a count. An instrument that
returned the right number and never refused would pass a suite built the other way
round, and would be the exact defect #310 filed.

Run: python3 tools/test_pane_census.py
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    spec = importlib.util.spec_from_file_location(
        "pc", os.path.join(HERE, "pane-census.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rows(*titles):
    return [{"id": f"terminal-{i}", "title": t} for i, t in enumerate(titles)]


FLEET = ("TEAMLEAD", "ARCHITECT", "DEVOPS", "DX",
         "DEV1", "DEV2", "DEV3", "DEV4", "DEV5")


def main():
    pc = load()
    fails = 0

    def check(label, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label} (got {got!r}, want {want!r})")

    nine = rows(*FLEET)
    tr9 = [f"s{i}" for i in range(9)]

    # 1. The only case that may report a number.
    rc, lines = pc.census(nine, tr9)
    check("agreement -> exit 0", rc, 0)
    check("agreement states N of N", any("9 of 9" in l for l in lines), True)

    # 2. ⛔ THE SHIPPED DEFECT: a pane alive with no transcript. The census must not
    #    quietly adopt the smaller number, which is what the monitor did for hours.
    rc, lines = pc.census(nine, tr9[:8])
    check("8 transcripts vs 9 panes -> exit 1", rc, 1)
    check("...and NAMES the divergence, not a count",
          any("SOURCE DISAGREEMENT" in l for l in lines)
          and any("UNESTABLISHED" in l for l in lines), True)
    check("...and never prints a bare total on a divergence",
          any("9 of 9" in l for l in lines), False)

    # 3. ⚠ The transcript set is a DIFFERENT POPULATION, not a lagging one: measured
    #    10 transcripts against 9 panes, including worktree-scoped sessions that are
    #    not panes while omitting a pane that wrote none. Errors in BOTH directions
    #    partially cancel, so the total looked plausible at 8 and again at 9.
    rc, _ = pc.census(nine, tr9 + ["extra-not-a-pane"])
    check("MORE transcripts than panes also refuses", rc, 1)

    # 4. The collision TEAMLEAD hypothesised. Not tonight's cause, still reachable.
    dup = [dict(r) for r in nine]
    dup[0]["title"] = "DEV4"
    rc, lines = pc.census(dup, tr9)
    check("duplicate title -> collision NAMED", rc == 1
          and any("DISPLAY-NAME COLLISION" in l for l in lines), True)
    check("...and states the count a NAME-keyed reader would have got",
          any("reports 8 where the id count is 9" in l for l in lines), True)

    # 5a. ⛔ THE IDENTITY KEY, pinned by a case that DISCRIMINATES it.
    #     Found by sabotage: replacing `ids = [r["id"]...]` with `[r["title"]...]` —
    #     #310's actual defect — passed every other check in this file. The refusal
    #     paths were pinned and the PROPERTY THE TOOL EXISTS FOR was not.
    #     ⇒ Two panes, DISTINCT ids, SAME title. Id-keyed sees 2; name-keyed sees 1,
    #     which is the silent collapse. Nothing else in this suite separates them.
    two_same_name = [{"id": "terminal-a", "title": "DEV4"},
                     {"id": "terminal-b", "title": "DEV4"}]
    rc, lines = pc.census(two_same_name, ["s0", "s1"])
    #     ⚠ The discriminator is NOT the printed total: `len(ids)` is the LIST length and
    #     is 2 under either keying. My first attempt at this check asserted on that and
    #     passed under the sabotage — a control that cannot fail, in the suite added to
    #     stop exactly that. The property that differs is whether the ids are UNIQUE:
    #     id-keyed sees two distinct ids, name-keyed sees one repeated.
    check("id-keyed: distinct ids sharing a title are NOT a duplicate-id fault",
          any("DUPLICATE PANE ID" in l for l in lines), False)
    check("...while the TITLE collision is still reported",
          any("DISPLAY-NAME COLLISION" in l for l in lines), True)

    # 4b. ⛔ SET COMPARISON, where the namespaces agree. `is X in the set?` is a MATCHER
    #     and fails in two directions; `does A equal B?` presupposes no matcher. Four
    #     content probes failed across the fleet the same night and a multiset comparison
    #     survived all four. terminal.list `id` and terminal.getStatus `terminalId` share
    #     a namespace, so this leg can name WHICH pane is unaccounted for — a count can
    #     only say that one is.
    same = [r["id"] for r in nine]
    rc, lines = pc.census(nine, tr9, same)
    check("set comparison: identical id-sets -> agree", rc, 0)
    check("...and says the symmetric difference is empty",
          any("symmetric difference empty" in l for l in lines), True)

    missing = same[:-1]                      # getStatus cannot see the last pane
    rc, lines = pc.census(nine, tr9, missing)
    check("set comparison: a pane in list and not status -> refuses", rc, 1)
    check("...and NAMES the id, not just a count",
          any("NOT in getStatus : terminal-8" in l for l in lines), True)

    extra = same + ["terminal-ghost"]        # getStatus sees one that list does not
    rc, lines = pc.census(nine, tr9, extra)
    check("set comparison: divergence in the OTHER direction also refuses", rc, 1)
    check("...and names the ghost",
          any("terminal-ghost" in l for l in lines), True)

    # 5. The identity key itself.
    rc, lines = pc.census(nine[:1] + nine[:1], tr9[:2])
    check("duplicate pane id -> the key is unsound", rc == 1
          and any("DUPLICATE PANE ID" in l for l in lines), True)

    # 6. ⛔ VOID is not zero. Both paths, because "could not ask" and "nothing there"
    #    are the pair this repository keeps collapsing.
    check("cannot enumerate -> 2, never 0", pc.census(None, [])[0], 2)
    check("zero panes is a broken query -> 2", pc.census([], [])[0], 2)

    # 7. ⛔ THE SUITE'S OWN KNOWN-NEGATIVE. A suite that cannot fail is not a caller,
    #    it is a screenshot with a schedule. Feed census() a shape it MUST reject and
    #    assert the suite would have caught a census that accepted it.
    rc_bad, _ = pc.census(nine, tr9[:8])
    check("suite can fail: a divergence must NOT read as agreement", rc_bad == 0, False)

    print()
    if fails:
        print(f"{fails} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
