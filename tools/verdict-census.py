#!/usr/bin/env python3
"""Has each indexed instrument EVER produced a verdict? Answered by running them.

⛔ Why this exists — #2. Two existing properties presuppose execution: *did the read succeed*
catches a confident EMPTY answer, *did it read the right things* catches a confident WRONG one.
Neither can see a check that has never spoken at all. `tools/README.md` indexes fifteen
instruments and records, for each, what its exit codes MEAN — and nothing anywhere records
whether any of them has ever emitted one.

★ **The answer is produced by execution, never by reading the index.** An index entry is a claim
that an instrument exists; this runs it and reports what came back. That distinction is the whole
point of #2, and asserting verdict-history from a table would reproduce the defect.

⛔ FOUR STATES, and collapsing any pair loses the finding #2 is about:

    VERDICT-SEEN        ran, and exited a code its own docstring documents as a CONCLUSION
    ESTABLISHED-NOTHING ran, and refused a verdict — exit 2 by this repo's convention.
                        ⚠ A refused verdict is NOT a verdict. It is the honest form of silence.
    NO-VERDICT-VOCAB    ran, but documents NO exit codes at all, so "did it conclude?" cannot
                        be read from its contract. ⚠ Unanswerable is not the same as "no".
    NEVER-RUN           did not conclude: crashed, timed out, or exited a code it does not
                        document. ⛔ This is the state #2 says is invisible to everything else.

⇒ `NEVER-RUN` and `ESTABLISHED-NOTHING` are deliberately separate, per #2's acceptance criteria
and #58: one exit code carrying both is the defect, not the reporting of it.

⛔ THE KNOWN-POSITIVE IS OUTSIDE THE MEASURED POPULATION. The population is `tools/`; the control
is a set of SYNTHETIC fixtures written at self-test time, one per state. Keying it on a tool that
happens to be broken today would make this pass only while that breakage survives — #26's sharp
subtype, and the mistake `index-watch.py` shipped with before #139.

⚠ What this does NOT do. It does not decide what to do about a never-run check — that is #2's
premise, not its remedy, and is explicitly out of scope on the issue. It does not judge whether a
verdict was CORRECT. It runs each instrument with no arguments and a timeout: an instrument whose
real verdict needs flags may report ESTABLISHED-NOTHING here and be healthy in use, which is
reported rather than hidden.

Exit: 0 every indexed instrument classified, none NEVER-RUN
      1 at least one NEVER-RUN or NO-VERDICT-VOCAB — a finding
      2 established nothing (the index could not be read, or it named no instruments)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "tools" / "README.md"
ROW = re.compile(r"^\|\s*`([A-Za-z0-9_.-]+\.py)`\s*\|", re.M)
# "Exit: 0 clean · 1 findings · 2 established nothing"  ->  {0,1,2}
EXIT_DOC = re.compile(r"^Exit(?:\s+codes)?:\s*(.+?)(?:\n\n|\n\"\"\")", re.M | re.S)
CODE = re.compile(r"\b(\d)\b")
# This repo's single carried convention: 2 means "established nothing", never "all clear".
REFUSAL = 2
TIMEOUT = 90

VERDICT, NOTHING, NOVOCAB, NEVERRUN, SLOW = (
    "VERDICT-SEEN", "ESTABLISHED-NOTHING", "NO-VERDICT-VOCAB", "NEVER-RUN", "NO-VERDICT-IN-TIME")


def documented_codes(src):
    m = EXIT_DOC.search(src)
    if not m:
        return None
    return {int(c) for c in CODE.findall(m.group(1))}


def classify(path, timeout=TIMEOUT):
    """(state, detail). Runs the instrument with no arguments."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return NEVERRUN, f"unreadable: {e}"
    codes = documented_codes(src)
    try:
        r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                           timeout=timeout, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        # ⛔ NOT NeverRun. A timeout is a property of the bound I chose, not of the instrument.
        # Measured: stranded-branches.py concludes in ~45s and was reported NEVER-RUN under a 25s
        # bound — a wrong verdict about someone else's tool, manufactured by my own parameter.
        return SLOW, (f"no verdict within {timeout}s — raise --timeout before reading this as"
                      f" never-run; the bound is mine, not the instrument's")
    except OSError as e:
        return NEVERRUN, f"could not execute: {e}"

    # ⛔ A traceback is not a verdict, whatever code it exits with. Checked BEFORE the exit
    # code, because a crash that happens to exit 1 would otherwise read as a conclusion.
    if "Traceback (most recent call last)" in (r.stderr or ""):
        last = [l for l in (r.stderr or "").strip().splitlines() if l.strip()][-1][:90]
        return NEVERRUN, f"crashed: {last}"

    if codes is None:
        return NOVOCAB, f"exited {r.returncode}; docstring documents no exit codes"
    if r.returncode not in codes:
        return NEVERRUN, f"exited {r.returncode}, not in its documented set {sorted(codes)}"
    if r.returncode == REFUSAL:
        return NOTHING, "exit 2 — refused a verdict (this is the honest form of silence)"
    return VERDICT, f"exit {r.returncode} — a documented conclusion"


def census(index=None, tools_dir=None, timeout=TIMEOUT):
    # timeout is threaded into the notes below so the reader sees the bound that produced them
    index = index or INDEX
    tools_dir = tools_dir or (ROOT / "tools")
    out, rows = [], []
    try:
        text = index.read_text(encoding="utf-8")
    except OSError as e:
        return 2, [f"  VOID  cannot read {index}: {e} — established nothing"], []
    names = sorted(set(ROW.findall(text)))
    if not names:
        return 2, ["  VOID  the index named no instruments — the table format changed, or it is"
                   " gone. Established nothing."], []

    for n in names:
        p = tools_dir / n
        if not p.is_file():
            rows.append((n, NEVERRUN, "indexed but absent from the directory"))
            continue
        rows.append((n, *classify(p, timeout)))

    width = max(len(n) for n, _, _ in rows)
    for n, st, detail in rows:
        out.append(f"  {st:<20} {n:<{width}}  {detail}")

    tally = {s: sum(1 for _, x, _ in rows if x == s)
             for s in (VERDICT, NOTHING, NOVOCAB, SLOW, NEVERRUN)}
    out.append("")
    out.append("  " + " · ".join(f"{k} {v}" for k, v in tally.items()))
    out.append("  note  verdict-history is measured BY EXECUTION here, not read from the index")
    out.append("  note  each instrument was run with NO ARGUMENTS; one whose real verdict needs"
               " flags may show ESTABLISHED-NOTHING and be healthy in use")
    out.append("  note  this does not judge whether a verdict was CORRECT, only that one was"
               " produced")
    out.append(f"  note  NO-VERDICT-IN-TIME is a statement about the {timeout}s bound, NOT about"
               " the instrument — re-run it alone with a longer --timeout before concluding")
    rc = 1 if (tally[NEVERRUN] or tally[NOVOCAB] or tally[SLOW]) else 0
    return rc, out, rows


def _fixture(d, name, body, exit_doc=True):
    doc = 'Exit: 0 a verdict · 2 established nothing.' if exit_doc else 'No exit documentation.'
    p = Path(d) / name
    p.write_text(f'#!/usr/bin/env python3\n"""Fixture.\n\n{doc}\n"""\n{body}\n')
    return p


def self_test():
    """⛔ The control is SYNTHETIC and lives outside `tools/`.

    A control drawn from the measured population — "instrument X is broken today, so a NEVER-RUN
    proves I work" — is silenced the moment X is repaired. That is #26's sharp subtype, and it is
    the defect `index-watch.py` shipped with until #139.
    """
    import tempfile
    ok = True
    cases = [
        ("verdict.py",  "raise SystemExit(0)",                       True,  VERDICT),
        ("refusal.py",  "raise SystemExit(2)",                       True,  NOTHING),
        ("novocab.py",  "raise SystemExit(0)",                       False, NOVOCAB),
        ("crash.py",    "raise ValueError('boom')",                  True,  NEVERRUN),
        ("undoc.py",    "raise SystemExit(7)",                       True,  NEVERRUN),
    ]
    with tempfile.TemporaryDirectory() as d:
        for name, body, doc, want in cases:
            p = _fixture(d, name, body, doc)
            got, detail = classify(p, timeout=30)
            hit = got == want
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  {name:<12} -> {got:<20} (want {want})")

        # ⛔ a crash that exits 1 must NOT read as a verdict
        p = _fixture(d, "crash1.py", "import sys\nraise ValueError('boom')", True)
        got, _ = classify(p, timeout=30)
        hit = got == NEVERRUN
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a traceback is not a verdict even when the exit "
              f"code is documented (got {got})")

        # ⛔ a timeout must NOT be reported as never-run — the bound is the caller's
        p = _fixture(d, "slow.py", "import time\ntime.sleep(30)\nraise SystemExit(0)", True)
        got, detail = classify(p, timeout=2)
        hit = got == SLOW and "bound is mine" in detail
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a slow instrument is NO-VERDICT-IN-TIME, not "
              f"NEVER-RUN (got {got})")

        # ⛔ an index naming nothing is VOID, never "all instruments fine"
        idx = Path(d) / "README.md"
        idx.write_text("# no table here\n")
        rc, lines, _ = census(index=idx, tools_dir=Path(d), timeout=30)
        hit = rc == 2 and any("VOID" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an index naming no instruments exits 2 VOID, not 0"
              f" (got {rc})")
    return 0 if ok else 3


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        print("  VOID  unrecognised arguments — established nothing", file=sys.stderr)
        return 2
    if a.self_test:
        return self_test()
    rc, lines, _ = census(timeout=a.timeout)
    print("\nverdict census — tools/README.md's index, measured by running it")
    for l in lines:
        print(l)
    print({0: "  every indexed instrument produced or honestly refused a verdict",
           1: "  FINDING", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
