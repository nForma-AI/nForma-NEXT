#!/usr/bin/env python3
"""Assert that tools/README.md lists every instrument the directory actually holds.

⛔ Why this exists. `tools/README.md` is the index a reader consults to find out what can be
measured here. Three surfaces in it describe the contents of one directory — a header count, a
table, and a per-tool prose section — and all three are maintained by hand. **A hand-maintained
description of a directory drifts on the next addition, and its drift produces no error.** The
edit succeeds, nothing fails, and the reader is told by omission that a tool does not exist.

★ This was predicted and then observed, which is why the check is derived rather than a fix.
#27 was filed when the header said "Five" against six files, with `fleet-state.py` in none of the
three surfaces. The repair edited that exact line — "Five" -> "Six" — added a row for a newly
landed tool, and **left `fleet-state.py` missing**. The count went from wrong-by-one to
wrong-by-one at a new value, re-committed by an author looking directly at it. A count corrected
by hand is not a count that has been checked.

⇒ The consequence is not tidiness. `fleet-state.py` is the consumer for the `STATE:` line every
role prompt requires on every turn. An agent asking "does anything read the line I am required to
emit?" consults this index and is told **no**. A consumer nobody knows exists is operationally
indistinguishable from one that does not.

★ The load-bearing case is ZERO EXTRACTIONS. If the table syntax changes, or the file is renamed
or restructured, a naive checker finds no rows, compares nothing, reports "0 missing" and exits 0
— rendering an instrument failure as a clean bill of health. That is FOUNDING-THESIS §3 (absence
read as success) committed by the check meant to prevent it. Zero extractions therefore exits 2.

⚠ The numeral leg is CONDITIONAL BY DESIGN. #27 offered two remedies — drop the hand-maintained
numeral, or check it. If a future edit drops it, that is the other valid remedy and not a defect,
so a missing numeral is reported as NOT CHECKED rather than as a failure. The row and prose legs
are unconditional and are what actually carries this check.

Exit: 0 every surface agrees with the directory
      1 at least one surface disagrees
      2 established nothing (no tools found, no rows found, or the index is unreadable)
"""
import re
import sys
from pathlib import Path

WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}

# `| `name.py` | …` — a table row naming a tool.
ROW = re.compile(r"^\|\s*`([A-Za-z0-9_.-]+\.py)`\s*\|", re.M)
# `**`name.py`** — …` — a prose entry opening the "what each one is for" paragraph.
PROSE = re.compile(r"^\*\*`([A-Za-z0-9_.-]+\.py)`\*\*", re.M)
# The hand-maintained count in the opening sentence: "Six tools, each built because …"
COUNT = re.compile(r"^([A-Za-z]+|\d+)\s+tools\b", re.M | re.I)


def parse_count(tok):
    if tok.isdigit():
        return int(tok)
    return WORDS.get(tok.lower())


def check(root):
    """Return (exit_code, lines). Pure enough to test against a fixture tree."""
    out = []
    tools_dir = root / "tools"
    index = tools_dir / "README.md"

    if not tools_dir.is_dir():
        return 2, [f"  VOID  no tools/ directory under {root} — established nothing"]
    if not index.is_file():
        return 2, [f"  VOID  {index} is not readable — established nothing"]

    actual = sorted(p.name for p in tools_dir.glob("*.py"))
    text = index.read_text(encoding="utf-8")
    rows = ROW.findall(text)
    prose = PROSE.findall(text)

    # ⛔ Absence of a finding must not be reported as a clean result.
    if not actual:
        return 2, ["  VOID  tools/ holds no .py files — nothing to index, established nothing"]
    if not rows:
        return 2, ["  VOID  no table rows matched in tools/README.md — the index format changed,"
                   " or the table is gone. Established nothing."]

    failed = False
    out.append(f"  tools/*.py on disk : {len(actual)}  ({', '.join(actual)})")

    for label, found in (("table row", rows), ("prose entry", prose)):
        missing = [t for t in actual if t not in found]
        extra = [t for t in found if t not in actual]
        if missing:
            failed = True
            out.append(f"  FAIL  no {label} for: {', '.join(missing)}")
        if extra:
            failed = True
            out.append(f"  FAIL  {label} names a file that is not there: {', '.join(extra)}")
        if not missing and not extra:
            out.append(f"  ok    every tool has a {label} ({len(found)})")

    m = COUNT.search(text)
    if not m:
        out.append("  ----  no hand-maintained numeral found — that leg NOT CHECKED"
                   " (dropping it is #27's other valid remedy, not a defect)")
    else:
        stated = parse_count(m.group(1))
        if stated is None:
            failed = True
            out.append(f"  FAIL  header count {m.group(1)!r} is not a number this check can read")
        elif stated != len(actual):
            failed = True
            out.append(f"  FAIL  header says {m.group(1)} ({stated}); the directory holds {len(actual)}")
        else:
            out.append(f"  ok    header count agrees ({stated})")

    # Every tool prints what its numbers do NOT establish, on every run.
    out.append("  note  this checks PRESENCE of a row, never whether the row is ACCURATE —"
               " a wrong description passes")
    out.append("  note  only tools/*.py is indexed; a shell or non-.py instrument is invisible here")
    return (1 if failed else 0), out


def selftest():
    """Prove the failing path fires. A control that has only ever passed is not a control.

    ⚠ The fixture is built to fail in the REPAIRED state, per #26: the input is a correct index
    plus one newly added tool, which is exactly the drift that occurred twice on this file. A
    known-positive drawn from a currently-broken repo would go silent the moment the repo is
    fixed.
    """
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        t = root / "tools"
        t.mkdir()
        for name in ("alpha.py", "beta.py"):
            (t / name).write_text("#\n")
        good = ("# Fleet instruments\n\nTwo tools, each built because a reading was wrong.\n\n"
                "| tool | question | exit codes |\n|---|---|---|\n"
                "| `alpha.py` | q | 0 |\n| `beta.py` | q | 0 |\n\n"
                "## What each one is for\n\n**`alpha.py`** — a.\n\n**`beta.py`** — b.\n")
        (t / "README.md").write_text(good)

        rc, _ = check(root)
        ok &= (rc == 0)
        print(f"  {'ok  ' if rc == 0 else 'FAIL'}  known-positive: a correct index exits 0 (got {rc})")

        # the drift this exists to catch: a tool lands, the index does not move
        (t / "gamma.py").write_text("#\n")
        rc, lines = check(root)
        hit = rc == 1 and any("gamma.py" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  known-negative: a new tool with no row exits 1 and "
              f"names it (got {rc})")

        # instrument failure must not read as a pass
        (t / "README.md").write_text("# Fleet instruments\n\nnothing here\n")
        rc, _ = check(root)
        ok &= (rc == 2)
        print(f"  {'ok  ' if rc == 2 else 'FAIL'}  void: an unparseable index exits 2, not 0 (got {rc})")
    return 0 if ok else 3


def main(argv):
    root = Path(__file__).resolve().parent.parent
    args = argv[1:]
    if args == ["--selftest"]:
        return selftest()
    # ⚠ An unrecognised argument must not be silently ignored into a pass (ARCHITECT, PR #47).
    if args:
        print(f"  VOID  unrecognised argument(s): {' '.join(args)} — established nothing",
              file=sys.stderr)
        return 2
    rc, lines = check(root)
    print("\ntools/README.md vs tools/")
    for l in lines:
        print(l)
    print({0: "  clean", 1: "  DRIFTED", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
