#!/usr/bin/env python3
"""Assert that every repo path CLAUDE.md points at still exists.

⛔ Why this exists. CLAUDE.md is a map with no content of its own — its entire value is that
its pointers resolve. A pointer file rots the moment a file is renamed, and it rots
**silently**: nothing fails, and the next reader is sent to a path that is not there while
still believing the map. That is the failure this repository was founded to move into the
substrate — a rule ("keep the map current") that asks a human to remember something and
leaves no execution record when they do not.

★ The load-bearing case is ZERO EXTRACTED PATHS. If the regex stops matching — CLAUDE.md is
renamed, restructured, or its path syntax changes — a naive checker reports "0 missing" and
exits 0, and an instrument failure is rendered as a clean bill of health. That is
FOUNDING-THESIS §3 ("absence read as success") committed by the very check meant to prevent
it. Zero extractions therefore exits 2.

Convention: paths in CLAUDE.md are written repo-relative and always contain a `/`, so a bare
filename is never mistaken for a path. Templates (`prompts/<ROLE>.md`) and globs are skipped
by construction — they contain characters no real path here does.

Exit: 0 all pointers resolve · 1 at least one is dangling · 2 established nothing.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "CLAUDE.md"

# Backticked token, repo-relative, no template/glob/shell metacharacters.
TOKEN = re.compile(r"`([^`\s]+/[^`\s]*)`")
SKIP = set("<>*$()[]{}|")


def extract(text):
    out = []
    for m in TOKEN.finditer(text):
        tok = m.group(1)
        if SKIP & set(tok):
            continue
        if tok not in out:
            out.append(tok)
    return out


def main():
    # ⛔ Strict argument parsing, and it is a #26 fix rather than tidiness. This read
    # `"--self-test" in sys.argv` and therefore ACCEPTED ANYTHING: `--not-a-real-flag`,
    # `--repo /nonexistent`, `utter garbage` — all exited 0. An operator who typos a flag
    # got a clean pass from a checker that had silently ignored the instruction.
    # ⇒ A tool with no reachable failing state for misuse is the #26 class, and this one
    # was written BY the pane filing #26 instances, four hours before it audited others
    # for the same defect. argparse rejects an unknown flag with exit 2.
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true",
                    help="exercise the extractor's rejection cases before reporting")
    args = ap.parse_args()
    self_test = args.self_test

    if not DOC.is_file():
        print(f"VOID  CLAUDE.md not found at {DOC}", file=sys.stderr)
        print("      established nothing about pointer validity", file=sys.stderr)
        return 2

    paths = extract(DOC.read_text(encoding="utf-8"))

    if self_test:
        # ⚠ Prove the failure path. A control that has only ever passed is not a control.
        # These two must behave as stated or the checker cannot be trusted when it passes.
        assert extract("no paths here at all") == [], "extractor should find nothing"
        assert extract("`prompts/<ROLE>.md`") == [], "templates must be skipped"
        assert extract("`a/b.md` `a/b.md`") == ["a/b.md"], "must dedupe"
        missing_probe = not (ROOT / "definitely/not/here.md").exists()
        assert missing_probe, "existence probe cannot detect a missing file"
        print("self-test ok — extractor skips templates, dedupes, and the probe can fail")

    if not paths:
        print("VOID  extracted 0 paths from CLAUDE.md", file=sys.stderr)
        print("      the pointer syntax changed, or the file no longer carries a map;", file=sys.stderr)
        print("      this is an instrument failure, NOT a clean result", file=sys.stderr)
        return 2

    missing = [p for p in paths if not (ROOT / p).exists()]

    for p in paths:
        print(f"  {'ok  ' if p not in missing else 'GONE'}  {p}")
    print(f"\n{len(paths)} pointers checked, {len(missing)} dangling")
    print("⚠ Checks existence only. It does not establish that a pointer still leads to what "
          "CLAUDE.md says is there.")

    if missing:
        print("\nCLAUDE.md points at paths that do not exist:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
