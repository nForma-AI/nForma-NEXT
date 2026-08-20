#!/usr/bin/env python3
"""Pins the shared-file detector against the two shapes it must tell apart.

Why this file exists
--------------------
The detector's first version claimed, in its own comment, to exclude compactions.
It did not, and nothing tested the claim. On the live fleet it flagged 5 sessions
and all 5 were compactions — a 100% false positive rate on the one event every
long session eventually has, suppressing the depth number the supervision loop
exists to read.

Removing a false positive is only half a fix. A detector that no longer fires is
indistinguishable from a detector that no longer detects, and the failure it was
built for (an unattributable depth reported as a fact) is the more expensive one.
So the known-positive below is not synthetic: it is a real 40-reading window from
a real transcript where two panes wrote to one file, rounded to 1k. If a future
change silences it, this fails.

Run: python3 tools/test_fleet_context.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "fleet_context", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-context.py"))
fleet_context = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_context)

# Real, measured. e4a7769d, window at index 7211: a ~350k series and an ~850k
# series alternating within seconds, 14 crossings. Two panes, one file.
INTERLEAVED_K = [348, 348, 848, 349, 849, 849, 350, 353, 353, 353, 353, 354, 354,
                 354, 850, 355, 355, 355, 851, 851, 851, 357, 357, 357, 852, 852,
                 852, 853, 360, 360, 360, 361, 361, 361, 858, 858, 858, 363, 859, 366]

# Real, measured. c67ebcb4's tail across its own compaction: nine readings at
# ~875-880k, then a reset to 70k climbing to 86k. One crossing, never back.
COMPACTED_K = [875, 876, 876, 876, 876, 877, 878, 879, 880, 70, 70, 70, 72, 72,
               72, 73, 73, 73, 73, 73, 73, 74, 74, 74, 75, 75, 77, 77, 77, 78,
               78, 78, 80, 80, 80, 82, 82, 82, 86, 86]


def write_transcript(readings, path, title="ROLE"):
    """A real transcript, read by the real function — not a re-implementation."""
    with open(path, "w") as fh:
        fh.write(json.dumps({"type": "custom-title", "customTitle": title}) + "\n")
        for v in readings:
            fh.write(json.dumps({"message": {"role": "assistant", "usage": {
                "input_tokens": v, "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0, "output_tokens": 0}}}) + "\n")


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        # The fixtures must actually reach the detector's precondition. A window
        # whose spread fell under the gate would take every path below straight to
        # "single" and every assertion would pass while testing nothing.
        for label, series in (("interleaved", INTERLEAVED_K), ("compacted", COMPACTED_K)):
            spread = (max(series) - min(series)) * 1000
            if spread <= 100_000 or len(series) < 8:
                print(f"  FAIL  fixture {label} no longer reaches the detector "
                      f"(spread={spread}, n={len(series)}) — the tests below are vacuous")
                failures += 1

        print("known-positive — two panes in one file MUST stay flagged:")
        p = os.path.join(d, "interleaved.jsonl")
        write_transcript([v * 1000 for v in INTERLEAVED_K], p)
        names, depth, shape, _bands, _kind = fleet_context.session_depth(p)
        failures += not check("shape", shape, "interleaved")

        print("known-negative — a compaction is ONE agent, depth stands:")
        p = os.path.join(d, "compacted.jsonl")
        write_transcript([v * 1000 for v in COMPACTED_K], p)
        names, depth, shape, _bands, _kind = fleet_context.session_depth(p)
        failures += not check("shape", shape, "compaction-step")
        # The point of not suppressing: the reported depth is the post-compaction
        # figure, which is the correct one and the one supervision acts on.
        failures += not check("depth is post-compaction", depth, COMPACTED_K[-1] * 1000)

        print("a steady session is neither:")
        p = os.path.join(d, "steady.jsonl")
        write_transcript([100_000 + 1_000 * i for i in range(40)], p)
        names, depth, shape, _bands, _kind = fleet_context.session_depth(p)
        failures += not check("shape", shape, "single")

        print("an all-zero usage record is not a depth of zero:")
        p = os.path.join(d, "zeroes.jsonl")
        write_transcript([0], p)
        names, depth, shape, _bands, _kind = fleet_context.session_depth(p)
        failures += not check("depth", depth, None)
        failures += not check("shape", shape, "no-reading")

        print("a zero mixed into a real series must not move the midpoint:")
        # Measured: one spurious 0 dragged a window minimum to 0, shifted the
        # cluster midpoint by 46k, and split a single compaction into two crossings.
        p = os.path.join(d, "zero_mixed.jsonl")
        series = [v * 1000 for v in COMPACTED_K[:25]] + [0] + [v * 1000 for v in COMPACTED_K[25:]]
        write_transcript(series, p)
        names, depth, shape, _bands, _kind = fleet_context.session_depth(p)
        failures += not check("shape", shape, "compaction-step")

        print("★ FLATLINE is derivable and must not claim a cause:")
        # The backstop for a protocol the running fleet never received. It needs no
        # adoption — transcript mtime already exists on every pane — and it must not
        # say WHY, because flat is finished, blocked, crashed, waiting, or holding
        # unread messages, and this cannot tell them apart.
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "fleet-context.py")).read()
        failures += not check("the flag exists", "--flatline" in src, True)
        failures += not check("it is OFF by default", 'default=0.0' in src, True)
        failures += not check("and it refuses to name a cause",
                              "this cannot tell which" in src, True)

    failures += _bands_checks()
    failures += _name_checks()


    print()

    if failures:
        print(f"{failures} FAILED")
        return 1
    print("all checks passed")
    return 0


# ── depth_bands: the SET of depths on a shared file, and the refuted attribution ──────
# ⛔ The obvious repair for a shared transcript was to pair each usage reading with the
# nearest preceding NAME record and attribute it. Measured on e4a7769d, last 60 readings:
#
#     D423 D423 D423 D847 D847 D847 T425 T848 T426 T854 T854 T854 ...
#
# Cleanly bimodal — 423-444k and 847-884k, no overlap — and BOTH NAMES APPEAR IN BOTH
# BANDS. So nearest-name attribution assigns at chance. The bands are recoverable; the
# assignment is not, and the tool must report the first without claiming the second.
# ── classify_names: a rename is not an ambiguity ─────────────────────────────────────
# ⛔ `⚠name-ambiguous(IMPLEMENTER4/DEV4)` and `⚠name-ambiguous(TEAMLEAD/DEV2)` printed
# identically and are OPPOSITE: one agent renamed, versus two agents interleaved. Reading
# the rename as ambiguity sent me looking for a third, unaddressable writer — I published
# that speculation and then found 78 live sessions with no IMPLEMENTER in any of them.
def _name_checks():
    f = 0
    f += not check("a rename never returns to an earlier name",
                   fleet_context.classify_names(["A", "A", "B", "B", "B"]), "rename")
    f += not check("alternation is concurrent",
                   fleet_context.classify_names(["A", "B", "A", "B", "A"]), "concurrent")
    f += not check("one name is single",
                   fleet_context.classify_names(["A", "A", "A"]), "single")
    # ⚠ The near-miss: a single late recurrence is enough to make it NOT a rename, because
    # a renamed session cannot emit its old name again.
    f += not check("one recurrence defeats the rename reading",
                   fleet_context.classify_names(["A", "A", "B", "B", "A"]), "concurrent")
    # ⚠ Three names in sequence is still a rename chain, not ambiguity.
    f += not check("a three-step rename chain is still a rename",
                   fleet_context.classify_names(["A", "B", "B", "C", "C"]), "rename")
    f += not check("empty history is single", fleet_context.classify_names([]), "single")
    return f


def _bands_checks():
    f = 0
    H, L = 880_000, 435_000
    interleaved = [H, L, H, H, L, L, H, L, H, L, H, H, L, L, H, L]
    b = fleet_context.depth_bands(interleaved, recent=60)
    f += not check("two bands recovered from an interleaved series", len(b), 2)
    f += not check("low band", (b[0][0], b[0][1]), (L, L))
    f += not check("high band", (b[1][0], b[1][1]), (H, H))

    # ⚠ A unimodal series must yield NO bands. Inventing a split on one agent's file
    # would put "ASK BOTH" on a session with one writer.
    flat = [700_000 + i * 900 for i in range(20)]
    f += not check("unimodal series yields no bands", fleet_context.depth_bands(flat), [])

    # ⚠ A lone outlier is not a band — otherwise one stray reading manufactures a second
    # agent. Two low values against fourteen high ones must not split.
    outlier = [880_000] * 14 + [200_000, 201_000]
    f += not check("a lone pair is not a band", fleet_context.depth_bands(outlier), [])

    # ⚠ Too few readings establishes nothing.
    f += not check("too few readings", fleet_context.depth_bands([H, L, H]), [])

    # ⛔ min_gap WAS PRESENT AND UNTESTED, and a mutation exposed it: disabling the check
    # left every assertion green. The `flat` case above is rejected by the OUTLIER guard,
    # not by min_gap — with equal gaps `max()` returns the first, so `lo` has one element
    # and the length test fires first. A rule no test can reach is the vacuous-guard class,
    # in the suite for a tool about instruments that do not fire.
    #
    # This series has a 60k gap with SIX readings either side: the outlier guard admits it,
    # so only min_gap can reject it. Two agents 60k apart is noise in one series, not a
    # second writer.
    near = [700_000, 701_000, 702_000, 703_000, 704_000, 705_000,
            765_000, 766_000, 767_000, 768_000, 769_000, 770_000]
    f += not check("a gap below min_gap is not a band boundary",
                   fleet_context.depth_bands(near), [])
    # …and the same shape with a real separation MUST still split, or the guard is just off.
    far = [430_000, 431_000, 432_000, 433_000, 434_000, 435_000,
           870_000, 871_000, 872_000, 873_000, 874_000, 875_000]
    f += not check("a gap above min_gap still splits",
                   len(fleet_context.depth_bands(far)), 2)
    return f

if __name__ == "__main__":
    sys.exit(main())

