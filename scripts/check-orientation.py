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

    decayed = check_no_ci_claim()
    unpinned = check_pin_doctrine()

    if missing:
        print("\nCLAUDE.md points at paths that do not exist:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1
    return 1 if (decayed or unpinned) else 0


# ⛔ A DATED CLAIM NEEDS A RE-MEASURING CALLER, NOT A WARNING TO THE READER (#272).
#
# CLAUDE.md's "No CI" line carried a date, a SHA, a method, AND the sentence
# "re-measure before relying on either" — all four — and still stood false for ~7
# hours. ⇒ Dating a measurement tells a reader it CAN decay. It does not tell them
# it HAS, and no reader in seven hours discharged the obligation the caveat handed
# them.
#
# ★ Worse: the commit that falsified it CITED it as its justification — "this
# repository had no CI, so 23 instruments had never run" (239639a). A measurement
# is most likely to be falsified by work it caused, which is exactly the case
# nobody re-checks: the author of the fix already knows, and the files asserting
# the claim are not in the fix's blast radius.
#
# ⚠ Scope, stated: this re-measures ONE claim. It is not a general calibration
# checker and must not be read as one — every other dated fact in CLAUDE.md still
# relies on a reader.
def check_no_ci_claim():
    """True if CLAUDE.md still asserts 'no CI' while workflows exist."""
    wf = sorted((ROOT / ".github" / "workflows").glob("*.y*ml")) \
        if (ROOT / ".github" / "workflows").is_dir() else []
    try:
        text = (ROOT / "CLAUDE.md").read_text(errors="replace")
    except OSError:
        print("\n⛔ CLAUDE.md unreadable — the No-CI claim is UNCHECKED, not absent.",
              file=sys.stderr)
        return False
    # An asserted claim, not a struck one. `~~No CI.~~` and a line marked FALSE are
    # corrections; they must not trip this.
    # ⛔⛔ STRIP QUOTED SPANS FIRST — MULTI-LINE. A correction must QUOTE the false
    # claim to explain it, so a corrected file necessarily contains the string this
    # checker hunts. Measured: the first version of this function fired on this
    # repository's own correction, matching the commit message it cites
    # ("…had no CI, so 23 instruments…") — the population of false positives is
    # created by the remedy (#36), in a detector written by the author of that
    # finding, the same day.
    #
    # ★ Same rule as use-not-mention.py's command_positions(): remove quoted spans,
    # then match what remains. A quotation cannot survive its own removal.
    # ⚠ Spans are stripped across NEWLINES because the citation that fooled this
    # opens on one line and closes on another — a per-line strip does not reach it.
    QUOTED = re.compile(r'"[^"]*"', re.S)
    stripped = QUOTED.sub(" ", text)
    asserted = [ln for ln in stripped.splitlines()
                if re.search(r"\bno CI\b|[Zz]ero workflow", ln)
                and "~~" not in ln and "FALSE" not in ln]
    print(f"\n  workflow files present : {len(wf)}"
          f"{'  (' + ', '.join(f.name for f in wf) + ')' if wf else ''}")
    print(f"  un-struck 'no CI' lines: {len(asserted)}")
    if wf and asserted:
        print("\n⛔ CLAUDE.md still asserts this repository has no CI, and it has "
              f"{len(wf)} workflow file(s). The claim has DECAYED (#272):", file=sys.stderr)
        for ln in asserted:
            print(f"    {ln.strip()[:96]}", file=sys.stderr)
        return True
    if not wf and asserted:
        print("  ⇒ claim and world agree: no workflows, claim stands")
    elif wf and not asserted:
        print("  ⇒ claim and world agree: workflows exist, no un-struck claim")
    else:
        print("  ⚠ no workflows and no claim — nothing asserted, nothing to check")
    return False


def check_pin_doctrine():
    """True if tools/README.md has LOST the correct directory-pin form (#291).

    ⛔ THIS KEYS ON THE PRESENCE OF THE CORRECT FORM, NEVER ON THE ABSENCE OF THE
    BROKEN ONE, and that choice is the whole point of the check.

    The obvious control — grep for `git show <ref>:tools/x.py > /tmp/x.py` and fail
    if found — is VOID. Naming a broken command requires writing it down, so after
    the fix the document that FORBIDS the form is the top hit for it. Measured
    2026-08-20 at origin/main: a sweep for the broken string returned 2 hits and
    BOTH were mentions — tools/README.md's own counter-example, and a quoted
    pointer message in tools/pointer-verified.py. The author of that sweep (DEV2)
    began drafting a fix for the counter-example inside the block forbidding it.
    ⇒ The population of false positives is created by the remedy (#36), which is
    the same trap check_no_ci_claim() above documents hitting, hours earlier.

    ★ The rule this generalises to: PREFER THE CONTROL WHOSE FAILURE MODE IS A
    FALSE PASS OVER ONE THAT IS GUARANTEED TO FIRE ON THE REPAIRED STATE. An
    absence-check gets LOUDER the better the documentation gets; a presence-check
    degrades quietly and only ever under-reports.

    ⚠ STATED WEAKNESS, not a defect to fix: presence can also be satisfied by a
    MENTION — a future counter-example containing `git archive` would pass this.
    That is strictly weaker than a semantic check and cannot be repaired at this
    layer; markdown has no call graph, so tools/use-not-mention.py has nothing to
    resolve. The ⛔/✅ glyphs carry the polarity instead, which is why they are
    load-bearing content rather than formatting.
    """
    doc = ROOT / "tools" / "README.md"
    try:
        text = doc.read_text(errors="replace")
    except OSError:
        print("\n⛔ tools/README.md unreadable — the pin doctrine is UNCHECKED, "
              "not absent.", file=sys.stderr)
        return False

    required = [
        ("the ✅ directory-pin form", re.compile(r"git\s+archive\s+\S+\s+tools/[^\n]*\|\s*tar")),
        ("why it is needed (runmarker)", re.compile(r"import\s+runmarker")),
    ]
    absent = [label for label, pat in required if not pat.search(text)]

    print("\n  pin doctrine in tools/README.md (#291):")
    for label, pat in required:
        print(f"  {'ok  ' if pat.search(text) else 'GONE'}  {label}")
    if absent:
        print("\n⛔ tools/README.md no longer states how to pin a marker-carrying "
              "tool. Every pane that pins a single file gets ImportError, exit 1 "
              "and ZERO markers — a failure that surfaces as NOTHING MEASURED "
              "rather than as nothing found (#291):", file=sys.stderr)
        for label in absent:
            print(f"    missing: {label}", file=sys.stderr)
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
