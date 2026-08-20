#!/usr/bin/env python3
"""Run one mutation against a test suite and report a verdict you can trust.

⛔ WHY THIS IS A FILE. I rebuilt this as an ad-hoc bash function three times in one
session and got its argument order wrong on the third, which printed
``NOT APPLIED (71 matches)`` three times instead of three false SURVIVED verdicts.
That near-miss is the whole argument: **a mutation harness that fails silently reports
your tests as strong when it never tested them.** A broken observation instrument gives
you an error; a broken verification instrument gives you confidence.

Four safeguards, each earned by a specific wrong claim:

1. **BASELINE MUST BE GREEN.** If the suite is already failing, "1 failed" after the
   mutation proves nothing. Measured: a red baseline once made an untested guard look
   discriminating.
2. **THE MUTATION MUST APPLY.** ``old`` must occur EXACTLY once. Zero means a stale
   anchor (silently a no-op); more than one means you mutated somewhere you did not read.
   Both render as "SURVIVED".
3. **THE FILE MUST CHANGE ON DISK.** A replacement that produces identical bytes — e.g.
   old == new after normalisation — passes check 2 and still tests nothing.
4. **THE TARGET MUST MOVE.** Optional ``--target`` names the test that SHOULD die. A
   mutation that reds some *other* test is a displaced positive: the suite noticed, but
   not for the reason you think, and a false SURVIVED sends you rewriting a correct test.

Restoration is in a ``finally``: the working tree is returned even on an exception or a
KeyboardInterrupt. ⚠ Commit before mutating anyway — ``git checkout --`` has destroyed
uncommitted work in this repo three times.

Usage:
    mutate.py --file F --old STR --new STR --tests PYTEST_ARGS [--target TEST_ID] [--label L]
    mutate.py --spec mutations.json          # a list of the same objects, run in sequence

Exit: 0 = every mutation was KILLED (good). 1 = at least one SURVIVED or was INVALID.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KILLED, SURVIVED, INVALID = "KILLED", "SURVIVED", "INVALID"


def _pytest(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-q", "--no-header"],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def run_one(file: str, old: str, new: str, tests: list[str], target: str | None, label: str) -> tuple[str, str]:
    """Return (verdict, detail). Never leaves the tree mutated."""
    path = Path(file)
    if not path.is_file():
        return INVALID, f"no such file: {file}"
    original = path.read_text(encoding="utf-8")

    # 1 — baseline must be green, or the whole comparison is meaningless.
    rc, out = _pytest(tests)
    if rc != 0:
        return INVALID, f"BASELINE IS NOT GREEN (rc={rc}); a red suite cannot show a kill\n{out[-400:]}"

    # 2 — the anchor must be unambiguous.
    n = original.count(old)
    if n != 1:
        return INVALID, f"anchor occurs {n} times, need exactly 1 — {'stale anchor' if n == 0 else 'ambiguous'}"

    backup = Path(tempfile.mkdtemp()) / path.name
    shutil.copy2(path, backup)
    try:
        path.write_text(original.replace(old, new), encoding="utf-8")

        # 3 — the bytes on disk must actually differ.
        if path.read_text(encoding="utf-8") == original:
            return INVALID, "file is byte-identical after replacement — nothing was mutated"

        rc, out = _pytest(tests)
        if rc == 0:
            return SURVIVED, "the suite still passes with the mutation applied — it does not test this"

        # 4 — did the RIGHT test die?
        if target and target not in out:
            return INVALID, (
                f"the suite went red but {target!r} is not among the failures — displaced positive. "
                f"Something else noticed; do not read this as your test working.\n{out[-400:]}"
            )
        first = next((ln for ln in out.splitlines() if ln.strip().startswith("FAILED")), out.strip().splitlines()[-1])
        return KILLED, first.strip()
    finally:
        shutil.copy2(backup, path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", help="JSON file: a list of {file, old, new, tests, target?, label?}")
    ap.add_argument("--file")
    ap.add_argument("--old")
    ap.add_argument("--new")
    ap.add_argument("--tests", nargs="*", default=[])
    ap.add_argument("--target")
    ap.add_argument("--label", default="mutation")
    a = ap.parse_args()

    if a.spec:
        specs = json.loads(io.open(a.spec, encoding="utf-8").read())
    else:
        if not (a.file and a.old is not None and a.new is not None and a.tests):
            ap.error("need --spec, or all of --file --old --new --tests")
        specs = [{"file": a.file, "old": a.old, "new": a.new, "tests": a.tests, "target": a.target, "label": a.label}]

    bad = 0
    for s in specs:
        verdict, detail = run_one(s["file"], s["old"], s["new"], s["tests"], s.get("target"), s.get("label", "mutation"))
        mark = "✅" if verdict == KILLED else "⛔"
        print(f"{mark} {verdict:<9} {s.get('label', 'mutation')}\n     {detail}")
        if verdict != KILLED:
            bad += 1
    print(f"\n{len(specs) - bad}/{len(specs)} mutations KILLED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
