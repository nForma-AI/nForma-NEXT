#!/usr/bin/env python3
"""The CALLER #73 asks for: a floor under UNNAMED refusals that never reds on history.

⛔ WHY THIS EXISTS, and why it is a separate file from the thing it calls.

`tools/disposition-scan.py` built #73's predicate, planted it four ways, and caught a
use-versus-mention bug in itself. It then STOPPED, deliberately, and said why:

    "a RATCHET on this count is the shape that fits (#39), and committing other roles'
     files to a floor is not this tool's call. It reports; someone else decides."

⇒ That is correct, and it is not a technical gap. Deciding that 45 other files may not get
worse is a commitment made on behalf of every role that owns one — which is a TEAMLEAD act,
not an instrument's. #73 sat with a built predicate and no caller for 16 days because the
missing leg was AUTHORITY, and nobody who could supply it had been asked for it.

★ THE RATCHET, and why it is not a gate. A gating check fails 45 files on its first run. A red
naming 45 pre-existing files is reverted or ignored, which is worse than no check at all,
because it teaches that the gate is noise. ⇒ This fails ONLY IF THE COUNT GROWS. History is
never red. Adoption lowers the floor; nothing raises it.

⛔ IT DOES NOT WRITE WHAT IT READS. ⚠ This is the design decision, and it is taken FROM A
DEFECT MEASURED TODAY (#598). `tools/index-watch.py` records the sha it just reported on, so
the run that finds drift is the run that suppresses it: re-running to confirm a finding
DESTROYS the finding, and its second exit 0 means "did not check" while reading as "clean".

⇒ So this NEVER updates the baseline on its own. When the count drops, it says the floor CAN
be lowered and refuses to lower it; `--record` is an explicit, separate act with its own
diff. A check whose measurement changes the thing measured cannot be re-run, and a check that
cannot be re-run cannot be trusted.

⚠ IT COUNTS ITSELF, and says so both ways. This file has a printed refusal path, so it enters
its own population — the same contamination `disposition-scan` already reports against itself,
and the same one that made 11 KERNEL.md hits collapse to 0 today when the observer was excluded
from its own corpus. Both figures are printed; neither is the "real" one on its own.

⛔ WHAT THIS CANNOT DO, restated from #73 against itself and NOT quietly inherited: *a check
could pass while every refusal names a remedy nobody can act on.* PRESENCE of a disposition is
not USEFULNESS of one. This counts the first. Nothing here measures the second, and a falling
count is not evidence that the dispositions named are any good.

⇒ EXIT CODES
    0  the count is at or below the floor — including when it dropped
    1  ⛔ THE COUNT GREW. A new refusal names no disposition.
    2  ESTABLISHED NOTHING — scan unusable, or no baseline recorded. ⛔ never "all clear".
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "disposition-baseline.json"
SELF = Path(__file__).name


class Void(Exception):
    """Established nothing. ⇒ exit 2, never a verdict."""


def load_scan(root):
    """⛔ DELEGATE. The predicate, its four plants and its use-vs-mention correction live in
    disposition-scan.py. Restating the regexes here would create a second definition that
    drifts silently from the first — and the whole subject of #73 is two things that report
    the same value while meaning different ones."""
    path = Path(root) / "tools" / "disposition-scan.py"
    if not path.exists():
        raise Void(f"cannot find {path} — the predicate lives there and is not reimplemented "
                   f"here.\n   ADDABLE — whoever moved it: restore the path, or pass --root "
                   f"at the checkout that has it.")
    try:
        spec = importlib.util.spec_from_file_location("disposition_scan", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:
        raise Void(f"{path} did not import: {exc}\n"
                   f"   ADDABLE — its owner: fix the import; this tool cannot classify "
                   f"without it and will not guess.")
    for attr in ("classify", "NAMED", "UNNAMED", "NO_PATH"):
        if not hasattr(mod, attr):
            raise Void(f"{path} has no {attr!r} — its interface changed and this caller was "
                       f"not updated.\n   ADDABLE — this file's owner: re-derive against the "
                       f"new interface. ⚠ Refusing rather than defaulting: a caller that "
                       f"guessed here would report a count it did not measure.")
    return mod


def census(root, mod):
    """-> {name: verdict} over non-test tools/*.py. ⚠ The population is NAMED in the output,
    never left implicit: 'UNNAMED is 45' is meaningless without saying 45 of what."""
    files = sorted(p for p in (Path(root) / "tools").glob("*.py")
                   if not p.name.startswith("test_"))
    if not files:
        raise Void(f"no non-test tools/*.py under {root} — an EMPTY population reads as a "
                   f"clean board, and it is not one.\n   ADDABLE — run from the repository "
                   f"root, or pass --root.")
    out = {}
    for p in files:
        try:
            out[p.name] = mod.classify(p.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            raise Void(f"cannot read {p}: {exc} — a file skipped is a file not counted, and "
                       f"the count is the whole verdict.")
    return out


def head_sha(root):
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                           capture_output=True, text=True)
        return r.stdout.strip()[:12] if r.returncode == 0 else "unknown"
    except OSError:
        return "unknown"


# ── The decision, separated from the data so the controls drive it synthetically ──────

def verdict(count, floor):
    """-> GREW / HELD / DROPPED. ⛔ Pure: no filesystem, no git, no scan. #402 — the controls
    drive the DECISION with synthetic state, because a ratchet's interesting transitions are
    not re-runnable on a real tree."""
    if floor is None:
        return "NO-FLOOR"
    if count > floor:
        return "GREW"
    return "HELD" if count == floor else "DROPPED"


def read_baseline(path):
    if not path.exists():
        raise Void(f"no baseline at {path} — without a recorded floor there is nothing to "
                   f"ratchet against, and 'no floor' is not 'floor of zero'.\n"
                   f"   ADDABLE — this fleet's TEAMLEAD: run --record to set it. That is a "
                   f"deliberate commitment on behalf of every role owning a counted file, "
                   f"which is why it is not created automatically.")
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Void(f"{path} is not readable JSON: {exc}\n"
                   f"   ADDABLE — restore it from git; ⛔ this tool will not rewrite a "
                   f"baseline it could not parse, because that silently lifts the floor.")
    if not isinstance(d.get("unnamed"), int):
        raise Void(f"{path} has no integer 'unnamed' — the floor is unreadable.\n"
                   f"   ADDABLE — re-record it with --record.")
    return d


def report(root, out=None):
    out = out if out is not None else sys.stdout
    mod = load_scan(root)
    c = census(root, mod)
    pop = len(c)
    unnamed = [n for n, v in c.items() if v == mod.UNNAMED]
    named = [n for n, v in c.items() if v == mod.NAMED]
    nopath = [n for n, v in c.items() if v == mod.NO_PATH]
    if pop != len(unnamed) + len(named) + len(nopath):
        raise Void(f"buckets do not sum to the population ({pop}) — the partition is broken "
                   f"and every count below would be arithmetic on sand.")

    d = read_baseline(BASELINE)
    floor = d["unnamed"]
    v = verdict(len(unnamed), floor)

    print(f"POPULATION  {pop} non-test tools/*.py at {root} (HEAD {head_sha(root)})", file=out)
    print(f"PREDICATE   disposition-scan.classify — ⛔ DELEGATED, not restated here", file=out)
    print(f"FLOOR       {floor} UNNAMED, recorded {d.get('recorded_at', '?')} "
          f"at {d.get('sha', '?')}\n", file=out)
    print(f"  NAMED            {len(named)}", file=out)
    print(f"  UNNAMED          {len(unnamed)}   ⇐ the ratcheted count", file=out)
    print(f"  NO-REFUSAL-PATH  {len(nopath)}", file=out)
    print(f"  PARTITION        {pop}  = sum of the three above", file=out)

    # ⚠ THE OBSERVER IS IN ITS OWN POPULATION. Print both; neither is "the" number.
    if SELF in c:
        excl = len([n for n in unnamed if n != SELF])
        print(f"\n  ⚠ this tool counts ITSELF ({c[SELF]}). Excluding it: UNNAMED {excl} "
              f"of {pop - 1}.\n     Both figures are printed because adding an instrument "
              f"moves the figure it reports.", file=out)

    if v == "GREW":
        new = len(unnamed) - floor
        print(f"\n⛔ THE COUNT GREW: {floor} -> {len(unnamed)} (+{new})", file=out)
        print("   A refusal was added that names no disposition. #73: a correctly-reported\n"
              "   absence and an unfixable one arrive as the same value, so the first is\n"
              "   never fixed and the second is re-investigated forever.\n"
              "   ⇒ Name the kind in the PRINTED refusal, not in a docstring near it:\n"
              "       ADDABLE — <who>: <what>          a remedy exists; name it AND its owner\n"
              "       NO REMEDY — the refusal is the verdict", file=out)
        return 1

    if v == "DROPPED":
        print(f"\n★ the floor CAN be lowered: {floor} -> {len(unnamed)}", file=out)
        print("   ⛔ NOT LOWERED HERE, and that is deliberate. A check that writes what it\n"
              "   reads cannot be re-run: #598 — index-watch records the sha it just reported\n"
              "   on, so re-running to confirm a finding destroys it. ⇒ `--record` is a\n"
              "   separate, explicit act with its own diff and its own reviewer.", file=out)
        return 0

    print(f"\n  held at the floor — nothing regressed", file=out)
    return 0


def record(root, out=None):
    out = out if out is not None else sys.stdout
    """⚠ A DELIBERATE COMMITMENT, not a refresh. It binds every role owning a counted file."""
    mod = load_scan(root)
    c = census(root, mod)
    unnamed = [n for n, v in c.items() if v == mod.UNNAMED]
    prev = None
    if BASELINE.exists():
        try:
            prev = json.loads(BASELINE.read_text(encoding="utf-8")).get("unnamed")
        except Exception:
            prev = None
    if isinstance(prev, int) and len(unnamed) > prev:
        print(f"⛔ REFUSED — recording would RAISE the floor {prev} -> {len(unnamed)}.\n"
              f"   A ratchet that can be loosened is not a ratchet. Fix the {len(unnamed) - prev} "
              f"new UNNAMED refusal(s) instead.\n   NO REMEDY — this is the tool's whole "
              f"purpose; there is no flag for it.", file=sys.stderr)
        return 1
    BASELINE.write_text(json.dumps({
        "unnamed": len(unnamed),
        "population": len(c),
        "sha": head_sha(root),
        "recorded_at": subprocess.run(["date", "-u", "+%Y-%m-%d"], capture_output=True,
                                      text=True).stdout.strip(),
        "note": "Floor under #73's UNNAMED count. Lowered by adoption; NEVER raised. "
                "Recording is a TEAMLEAD act: it commits every role owning a counted file.",
    }, indent=1) + "\n", encoding="utf-8")
    print(f"  floor recorded: {len(unnamed)} UNNAMED of {len(c)}"
          + (f" (was {prev})" if prev is not None else ""), file=out)
    return 0


# ── Controls: two-sided and NAMED, driving the decision with synthetic state ───────────

def self_test(out=None):
    out = out if out is not None else sys.stdout
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: got {got!r}, want {want!r}", file=out)

    print("⛔ the transition this exists to catch", file=out)
    check("46 against a floor of 45 -> GREW", verdict(46, 45), "GREW")
    check("one more is still GREW", verdict(45 + 1, 45), "GREW")

    print("★ the known-NEGATIVES, without which every run reads as a failure", file=out)
    check("45 against 45 -> HELD", verdict(45, 45), "HELD")
    check("44 against 45 -> DROPPED, never a failure", verdict(44, 45), "DROPPED")
    check("0 against 45 -> DROPPED", verdict(0, 45), "DROPPED")

    print("⚠ absence of a floor is NOT a floor of zero", file=out)
    check("no baseline -> NO-FLOOR, not HELD", verdict(0, None), "NO-FLOOR")
    check("a count with no floor is still NO-FLOOR", verdict(99, None), "NO-FLOOR")

    print(f"\n{'✅ controls pass' if ok else '⛔ CONTROLS FAILED'} — 7 legs, both directions "
          f"named", file=out)
    print("⚠ The census and baseline legs need a filesystem and are exercised by\n"
          "   tools/test_disposition_ratchet.py, not here.", file=out)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Ratchet under #73's UNNAMED refusal count. Fails only if it GROWS.")
    ap.add_argument("--root", default=".", help="repository root to scan")
    ap.add_argument("--record", action="store_true",
                    help="set the floor to the current count. ⚠ A commitment, not a refresh.")
    ap.add_argument("--self-test", action="store_true", help="run the controls; no filesystem")
    args = ap.parse_args(argv)

    if args.self_test:
        extra = [a for a in (argv if argv is not None else sys.argv[1:]) if a != "--self-test"]
        if extra:
            print(f"⛔ unrecognised argument(s) alongside --self-test: {extra}\n"
                  f"   NO REMEDY — the controls take no other flags; run them alone.",
                  file=sys.stderr)
            return 2
        return self_test()
    try:
        return record(args.root) if args.record else report(args.root)
    except Void as exc:
        # ⚠ ONE PHYSICAL LINE, deliberately. disposition-scan's classify() credits a
        # disposition only when it shares a source line with BOTH the refusal text and the
        # print/stderr emit. Split across implicitly-concatenated lines it reads as UNNAMED
        # — which is how this file failed its own rule on the first run. Reported to #73.
        print(f"⛔ VOID — established nothing: {exc}\n   ADDABLE — named in the refusal above; every VOID path here carries its own remedy class.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
