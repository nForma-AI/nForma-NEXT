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
        names, depth, shape = fleet_context.session_depth(p)
        failures += not check("shape", shape, "interleaved")

        print("known-negative — a compaction is ONE agent, depth stands:")
        p = os.path.join(d, "compacted.jsonl")
        write_transcript([v * 1000 for v in COMPACTED_K], p)
        names, depth, shape = fleet_context.session_depth(p)
        failures += not check("shape", shape, "compaction-step")
        # The point of not suppressing: the reported depth is the post-compaction
        # figure, which is the correct one and the one supervision acts on.
        failures += not check("depth is post-compaction", depth, COMPACTED_K[-1] * 1000)

        print("a steady session is neither:")
        p = os.path.join(d, "steady.jsonl")
        write_transcript([100_000 + 1_000 * i for i in range(40)], p)
        names, depth, shape = fleet_context.session_depth(p)
        failures += not check("shape", shape, "single")

        print("an all-zero usage record is not a depth of zero:")
        p = os.path.join(d, "zeroes.jsonl")
        write_transcript([0], p)
        names, depth, shape = fleet_context.session_depth(p)
        failures += not check("depth", depth, None)
        failures += not check("shape", shape, "no-reading")

        print("a zero mixed into a real series must not move the midpoint:")
        # Measured: one spurious 0 dragged a window minimum to 0, shifted the
        # cluster midpoint by 46k, and split a single compaction into two crossings.
        p = os.path.join(d, "zero_mixed.jsonl")
        series = [v * 1000 for v in COMPACTED_K[:25]] + [0] + [v * 1000 for v in COMPACTED_K[25:]]
        write_transcript(series, p)
        names, depth, shape = fleet_context.session_depth(p)
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

    print()
    if failures:
        print(f"{failures} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
