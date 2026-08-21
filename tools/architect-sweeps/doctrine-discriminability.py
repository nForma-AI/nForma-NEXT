#!/usr/bin/env python3
"""Can two historical versions of a role prompt be told apart at all?

⛔ Why this exists as a FILE. It was an inline heredoc when it produced the number that
justified `tools/doctrine-version.py`'s containment matcher — "7 distinct versions, 0
mutually-contained pairs". That number is cited in #29 and in the tool's own docstring,
and the code that produced it existed only in one session's transcript.

⇒ A number in a durable artifact whose instrument is one session from gone is a number
with no reproducible source. That is `goals/README.md`'s own rule about instruments living
outside version control, applied to a measurement rather than to a tool.

⚠ A containment matcher can only discriminate versions where NEITHER is a substring of
the other. If any pair collides, `doctrine-version.py` must report AMBIGUOUS rather than
resolve to the convenient one — this establishes whether that path is ever reachable.

Exit: 0 all versions mutually distinguishable · 1 at least one colliding pair
      2 established nothing (no versions resolved)
"""
import argparse
import subprocess, sys

def git(*a):
    r = subprocess.run(("git",) + a, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    # ⛔ #506: this took sys.argv[1] raw, so `--help` was consumed as the PATH and the tool tried
    # to read a file named "--help", exiting 2 -- which this repo's convention reads as
    # "established nothing". Asking an instrument what it does must never be a measurement outcome.
    ap.add_argument("path", nargs="?", default="prompts/ARCHITECT.md",
                    help="the doctrine file to check (default: prompts/ARCHITECT.md)")
    path = ap.parse_args().path
    log = git("log", "--all", "--format=%H", "--", path)
    if not log:
        print(f"VOID  no history for {path} — established nothing", file=sys.stderr)
        return 2
    blobs = {}
    for c in log.split():
        b = git("rev-parse", f"{c}:{path}")
        if b:
            blobs.setdefault(b.strip(), []).append(c[:7])
    bodies = {b: git("cat-file", "-p", b) or "" for b in blobs}
    if not bodies:
        print("VOID  no blobs resolved — established nothing", file=sys.stderr)
        return 2
    collisions = [(a, b) for a in bodies for b in bodies
                  if a != b and bodies[a] and bodies[a] in bodies[b]]
    print(f"{path}: {len(bodies)} distinct versions")
    for b, commits in blobs.items():
        print(f"  {b[:7]}  {bodies[b].count(chr(10)):>4} lines  first seen {commits[-1]}")
    print(f"\ncolliding pairs: {len(collisions)}")
    for a, b in collisions:
        print(f"  ⛔ {a[:7]} is a substring of {b[:7]} — NOT discriminable")
    print("⚠ Establishes only that a CONTAINMENT matcher can separate these versions.")
    print("  It says nothing about whether any transcript contains one to match.")
    return 1 if collisions else 0

if __name__ == "__main__":
    sys.exit(main())
