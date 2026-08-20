#!/usr/bin/env python3
"""Refuse a `gh api` list reading that is a silent prefix of its own population.

⛔ THE DEFECT, measured by another agent and then found in my own merge decisions.
`gh api …/check-runs` returns **30 of 54** by default. It is not an error: the
response still carries `total_count: 54`, and a filter over `.check_runs[]` evaluates
the thirty it received and returns a clean answer about a set it never saw.

    it hid a REQUIRED-CHECK FAILURE
    and made two instruments by one author contradict each other about one PR

⚠ `per_page=100` is the reflex and it is not the check. It fails silently the moment a
repo exceeds 100 — safe by repo size, which is the defence this fleet keeps refusing
elsewhere. **The check is comparing the count the API states against the array it
sent.**

★ WHY THIS IS A TOOL AND NOT A CONVENTION. The rule lived in a wiki page and in a
friction report for hours while I merged pull requests by reading `check-runs`
directly. I audited afterwards — `total_count == length` on all thirteen queries, so
no merge rested on a truncated list — and that was **repo size, not care**. A rule you
have read and still not applied is a rule that needed to be executable.

⛔ WHAT IT DOES NOT DO. It does not paginate for you. Fetching the rest is a different
decision with a different cost, and quietly making it would hide the very truncation
this exists to surface. It tells you the reading is incomplete and refuses; the caller
chooses.

Usage:
    python3 tools/gh-complete.py repos/OWNER/REPO/commits/SHA/check-runs
    python3 tools/gh-complete.py <path> --key check_runs --jq '.[].conclusion'

Exit: 0 complete, JSON on stdout · 1 TRUNCATED — the reading is a prefix
      2 established nothing (call failed, or the shape is not a counted list)
"""
import json
import re
import subprocess
import sys

# Envelopes gh returns for counted lists. The key holding the array differs per
# endpoint, so it is derived from the payload rather than assumed.
COUNT_KEYS = ("total_count",)


def run_gh(path, extra=None):
    cmd = ["gh", "api", path] + (extra or [])
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        raise RuntimeError(f"cannot run gh: {exc}")
    if p.returncode != 0:
        raise RuntimeError(f"gh exited {p.returncode}: {(p.stderr or '').strip()[:200]}")
    if not p.stdout.strip():
        raise RuntimeError("gh returned no output — that is not an empty list")
    try:
        return json.loads(p.stdout)
    except ValueError as exc:
        raise RuntimeError(f"response is not JSON: {exc}")


def array_key(doc, override=None):
    """The one list-valued key beside the count. Refuses when it is ambiguous."""
    if override:
        if not isinstance(doc.get(override), list):
            raise RuntimeError(f"--key {override!r} is not a list in this response")
        return override
    lists = [k for k, v in doc.items() if isinstance(v, list)]
    if len(lists) != 1:
        raise RuntimeError(
            f"cannot tell which key holds the population: {lists or 'none'}. "
            f"Pass --key. Guessing here would be the same error one level up."
        )
    return lists[0]


def assess(doc, key=None):
    """(complete, stated, received, key). Raises when the shape is not a counted list."""
    if not isinstance(doc, dict):
        raise RuntimeError(
            "response is a bare array, so it carries no stated total and completeness "
            "CANNOT be established from it — this tool refuses rather than assuming"
        )
    stated = next((doc[k] for k in COUNT_KEYS if isinstance(doc.get(k), int)), None)
    if stated is None:
        raise RuntimeError(
            f"no total_count in the response (keys: {sorted(doc)[:8]}). Without a stated "
            f"population there is nothing to compare the array against."
        )
    k = array_key(doc, key)
    return stated == len(doc[k]), stated, len(doc[k]), k


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__.strip().split("Usage:")[1], file=sys.stderr)
        return 2
    path = args[0]
    key = None
    if "--key" in args:
        i = args.index("--key")
        if i + 1 >= len(args):
            print("⛔ --key needs a value", file=sys.stderr)
            return 2
        key = args[i + 1]
    passthrough = []
    if "--jq" in args:
        i = args.index("--jq")
        if i + 1 >= len(args):
            print("⛔ --jq needs a value", file=sys.stderr)
            return 2
        passthrough = ["--jq", args[i + 1]]

    try:
        doc = run_gh(path)
        complete, stated, received, k = assess(doc, key)
    except RuntimeError as exc:
        print(f"⛔ VOID: {exc}", file=sys.stderr)
        print("   established nothing — this is NOT an empty list and NOT a complete one.",
              file=sys.stderr)
        return 2

    if not complete:
        print(
            f"⛔ TRUNCATED: {path} states total_count={stated} and sent {received} "
            f"in `{k}`.\n"
            f"   Any filter over those {received} answers about a set it never saw. A "
            f"truncated list of this shape once HID A REQUIRED-CHECK FAILURE.\n"
            f"   ⚠ `per_page=100` is a reflex, not a fix — it fails the same way past 100. "
            f"Decide deliberately how to fetch the rest; this tool will not do it silently.",
            file=sys.stderr,
        )
        return 1

    if passthrough:
        p = subprocess.run(["gh", "api", path] + passthrough, capture_output=True, text=True)
        sys.stdout.write(p.stdout)
        return 0 if p.returncode == 0 else 2
    json.dump(doc, sys.stdout)
    print(f"\ngh-complete: {stated} of {stated} in `{k}` — the reading is whole",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
