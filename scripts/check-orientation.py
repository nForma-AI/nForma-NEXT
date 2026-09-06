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
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "CLAUDE.md"

# Backticked token, repo-relative, no template/glob/shell metacharacters.
TOKEN = re.compile(r"`([^`\s]+/[^`\s]*)`")
SKIP = set("<>*$()[]{}|")


def is_git_ref(tok):
    """Does this token resolve as a git ref in THIS repo?

    ⛔ Not a heuristic. CLAUDE.md's own first bullet tells every pane to read with
    `git show <ref>:<path>`, so refs will keep appearing in it — and `origin/main`
    satisfies TOKEN exactly as a path does (backticked, contains `/`, no metacharacter).
    Guessing by shape would misfile a real extension-less path; asking git cannot.

    ⚠ Consulted ONLY for a token that does not exist on disk. A path that exists is a
    path, whatever else shares its name.
    """
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", tok + "^{commit}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        # ⇒ Cannot establish "is a ref". Fail toward REPORTING it, never toward
        # silencing it: an unreportable token must stay visible as dangling.
        return False


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
        # ⛔ `assert` IS STRIPPED BY `python -O`, AND A STRIPPED CONTROL REPORTS PASS.
        # Measured 2026-09-06 by breaking one control on purpose:
        #     python3    --self-test  -> exit 1   the control works
        #     python3 -O --self-test  -> exit 0   ⛔ SKIPPED, and reported PASS
        # ⇒ Under -O the controls below DO NOT EXIST, so this run establishes NOTHING
        #   about them. 2 is this repository's word for that, and folding it into 0
        #   would be the exact failure these controls are here to catch.
        # ⚠ The stronger fix is to convert every assert into an explicit check that
        #   collects failures (tools/close-condition-scan.py does). This guard is the
        #   FLOOR: it cannot make the controls run, only refuse to call their absence
        #   a pass.
        if not __debug__:
            print("⛔ VOID — run WITHOUT -O. `assert` is stripped under -O, so the "
                  "controls below did not execute.", file=sys.stderr)
            print("   This established NOTHING about them. Exit 2, not a clean run.",
                  file=sys.stderr)
            return 2
        
        # ⚠ Prove the failure path. A control that has only ever passed is not a control.
        # These two must behave as stated or the checker cannot be trusted when it passes.
        assert extract("no paths here at all") == [], "extractor should find nothing"
        assert extract("`prompts/<ROLE>.md`") == [], "templates must be skipped"
        assert extract("`a/b.md` `a/b.md`") == ["a/b.md"], "must dedupe"
        # ⚠ Two-sided, and BOTH poles are named. A one-pole ref test would pass for a
        # function that answered True to everything.
        # ⚠ THE KNOWN-POSITIVE MUST NOT DEPEND ON A FETCHED REMOTE. This asserted
        # is_git_ref("origin/main"), which fails wherever that remote-tracking ref is
        # absent — a shallow clone, a remote not named "origin", or the vendored
        # installs of #502 — and it would fail for an ENVIRONMENTAL reason while
        # reading as a code defect. Same class as `$RANDOM` under dash and `timeout`
        # absent on macOS, both of which cost this session real landings.
        # ⇒ HEAD resolves in every git repo. origin/main is still exercised, but only
        #   where it exists, so its absence is a SKIP and never a false red.
        assert is_git_ref("HEAD"), \
            "KNOWN-POSITIVE FAILED: HEAD must resolve as a ref in any git repo"
        assert not is_git_ref("tools/README.md"), \
            "KNOWN-NEGATIVE FAILED: a real path must NOT be classified as a ref"
        if is_git_ref("origin/main"):
            print("self-test ok — origin/main present, the real CLAUDE.md token was exercised")
        else:
            print("self-test ok — ⚠ origin/main ABSENT here; classification tested via HEAD, "
                  "the CLAUDE.md token itself was NOT exercised")
        # ⚠ The pin leg's VOID must be reachable AND distinguishable from its pass.
        # ⛔ Do NOT test this by chmod-ing tools/README.md and running main(): the
        # No-CI leg enumerates that same file and returns 2 FIRST, so the run exits 2
        # for the other leg's reason and the pin branch is never entered. Measured —
        # it is why this control calls the function directly.
        import unittest.mock as _m
        with _m.patch.object(Path, "read_text", side_effect=OSError("forced")):
            void = check_pin_doctrine()
        assert void == "void", f"KNOWN-POSITIVE FAILED: unreadable README must be VOID, got {void!r}"
        assert void is not False, "VOID must not be the value the caller reads as a pass"
        live = check_pin_doctrine()
        assert live != "void", "KNOWN-NEGATIVE FAILED: a readable README must NOT be VOID"
        missing_probe = not (ROOT / "definitely/not/here.md").exists()
        assert missing_probe, "existence probe cannot detect a missing file"
        print("self-test ok — extractor skips templates, dedupes, and the probe can fail")

        # ── no_ci_hits(): the population widening (#272) ────────────────────────────
        # ⚠ Prove the failure path here too. Every one of these fails on a plausible
        # wrong implementation, and the fourth fails on the one this file shipped first.
        assert no_ci_hits("this repo has no CI today") == [(1, "this repo has no CI today")], \
            "a plain-prose claim must be FOUND"
        assert no_ci_hits("```\nsays: no CI\n```") == [], \
            "a claim inside a fence is a transcript — a MENTION, not an assertion"
        assert no_ci_hits("the `no CI` calibration decayed") == [], \
            "a claim inside an inline span is a citation — a MENTION"

        # ⛔⛔ THE REGRESSION CONTROL, AND IT TOOK THREE TRIES TO MAKE IT SHARP.
        # The first draft matched inline spans with `re.S`. Backticks are everywhere in
        # markdown, so an UNBALANCED one pairs with another far below and blanks
        # everything between. Measured on PR #572's tools/README.md: 72% of the file
        # erased, taking the claim this function exists to catch.
        #
        # ★ That draft PASSED the whole-corpus known-negative — a checker that reads
        # nothing reports zero findings, byte-identically to one that read everything.
        #
        # ⚠ Two earlier fixtures here were NOT controls: a well-formed fenced document
        # is stripped identically by the broken and the correct pattern, so both passed.
        # The trigger is an UNBALANCED backtick spanning the claim, which is why this
        # fixture is shaped the way it is and not the obvious way.
        unbalanced = "see `opt\n\nand this repo has no CI.\n\nand `end`\n"
        assert no_ci_hits(unbalanced) == [(3, "and this repo has no CI.")], \
            "an unbalanced backtick blanked a real claim below it"

        # Section scope: a correction anywhere in the section retracts the claim…
        assert no_ci_hits("## h\nthis repo has no CI\n\n⛔ STALE AS OF 2026-08-20\n") == [], \
            "a `⛔ STALE AS OF` block must retract the claim above it"
        # …and does NOT reach into a different section.
        two = "## a\nno CI here\n\n⛔ STALE AS OF x\n\n## b\nno CI here too\n"
        assert no_ci_hits(two) == [(7, "no CI here too")], \
            "a correction must not silence a claim in another section"
        print("self-test ok — no_ci_hits separates use from mention and survives fences")

    if not paths:
        print("VOID  extracted 0 paths from CLAUDE.md", file=sys.stderr)
        print("      the pointer syntax changed, or the file no longer carries a map;", file=sys.stderr)
        print("      this is an instrument failure, NOT a clean result", file=sys.stderr)
        return 2

    absent = [p for p in paths if not (ROOT / p).exists()]
    refs = [p for p in absent if is_git_ref(p)]
    missing = [p for p in absent if p not in refs]

    for p in paths:
        mark = "ok  " if p not in absent else ("ref " if p in refs else "GONE")
        print(f"  {mark}  {p}")
    print(f"\n{len(paths)} pointers checked, {len(missing)} dangling, "
          f"{len(refs)} git ref(s) — a ref is not a path and cannot dangle")
    print("⚠ Checks existence only. It does not establish that a pointer still leads to what "
          "CLAUDE.md says is there.")

    ci_claim = check_no_ci_claim()
    unpinned = check_pin_doctrine()

    # ⛔ VOID IS NOT A PASS AND NOT A FAILURE. If the tracked-*.md population could not
    # be enumerated, this script established NOTHING about the No-CI claim — and 2 is
    # this repository's word for that. Folding it into 0 would report "claim and world
    # agree" on a run that never opened a file.
    if ci_claim == "void":
        print("\n⛔ established nothing about the No-CI claim — exit 2, NOT a clean run.",
              file=sys.stderr)
        return 2
    if unpinned == "void":
        print("\n⛔ established nothing about the pin doctrine — exit 2, NOT a clean run.",
              file=sys.stderr)
        return 2
    decayed = ci_claim == "decayed"

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
def _tracked_markdown():
    """Every tracked `*.md` path, or None when the population cannot be established.

    ⛔ RETURNS None RATHER THAN FALLING BACK TO A FILESYSTEM WALK, and the refusal is
    the design. `ROOT.rglob("*.md")` descends into `.claude/worktrees/`, where ELEVEN
    sibling checkouts each hold their own CLAUDE.md at their own age. So the fallback
    does not scan a WIDER population than git — it scans a DIFFERENT one, in which
    every stale sibling asserts the falsified claim and the checker fires forever on
    files nobody is editing.

    ⇒ A checker whose population silently changes under it is worse than one that
    refuses, because the verdict keeps arriving and stops meaning anything.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--", "*.md"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    names = [n for n in out.stdout.split("\0") if n]
    return names or None


# ⛔ ORDER MATTERS, AND `re.S` ON THE INLINE SPAN IS A MEASURED DEFECT, NOT A STYLE
# CHOICE. The first draft of this widening used one pattern `"[^"]*"|`[^`]*`` with
# re.S. Backticks are everywhere in markdown, so that pairs a fence-opening backtick
# with one thousands of characters later and blanks everything between. Measured on
# PR #572's tools/README.md: **72% of the file erased**, taking with it the very claim
# this function exists to catch.
#
# ★ AND THE KNOWN-NEGATIVE STILL PASSED. A checker that reads nothing reports zero
# findings, byte-identically to one that read everything and found nothing. ⇒ The clean
# run was not evidence. Only the known-positive separated them — which is this
# repository's own rule about preferring the control whose failure mode is a false PASS.
_FENCE = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.S | re.M)
_INLINE = re.compile(r"`[^`\n]*`")          # ⚠ no re.S: an inline span cannot cross a line
_DQUOTE = re.compile(r'"[^"]*"', re.S)
_CLAIM = re.compile(r"\bno CI\b|[Zz]ero workflow", re.I)
# ⚠ A TIGHT, ENUMERATED SET. Loose words ("no longer", "superseded") would let ordinary
# prose silence a live claim. These four are the markers this corpus actually uses.
_CORRECTED = re.compile(r"~~|FALSE|STALE AS OF|INVERTED")


def _blank(m):
    """Blank a span, preserving line count and column offsets.

    ⛔ Collapsing a multi-line span to a single space renumbers every line beneath it,
    so the `file:line` this module prints would be precise-looking and false — the
    failure `goals/` names as citing by position instead of by content.
    """
    return re.sub(r"[^\n]", " ", m.group(0))


def _strip_mentions(text):
    """Fences (transcripts, sample output), then inline spans, then quotes."""
    return _DQUOTE.sub(_blank, _INLINE.sub(_blank, _FENCE.sub(_blank, text)))


def no_ci_hits(text):
    """[(lineno, line)] for un-struck 'no CI' assertions in one markdown document.

    ⛔ THE EXCLUSION IS SECTION-SCOPED, NOT PER-LINE, AND THE CORPUS FORCES IT. This
    repository retracts a decayed claim in TWO shapes, measured 2026-08-23 on main:

        CLAUDE.md                       inline   ⛔ **~~No CI.~~ FALSE since 2026-08-20**
        goals/devops-…-fleet.md:140     a BLOCK  claim on 140, `⛔ STALE AS OF` on 143

    A per-line test sees the first and not the second, so widening the population
    without widening the exclusion reports a correctly-corrected file as a live defect —
    the remedy manufacturing its own false positives (#36) one layer above where this
    module already documents doing exactly that.

    ⚠ THE COST, STATED: a section holding one corrected claim and one live claim masks
    the live one. That is a real false negative, and it is the price of not red-flagging
    every correctly-corrected file. ⇒ Read a clean section as *this section carries a
    correction*, never as *this section makes no claim*.
    """
    lines = _strip_mentions(text).splitlines()
    heads = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("#")]
    hits = []
    for i, ln in enumerate(lines):
        if not _CLAIM.search(ln):
            continue
        lo = max([h for h in heads if h <= i], default=0)
        hi = min([h for h in heads if h > i], default=len(lines))
        if _CORRECTED.search("\n".join(lines[lo:hi])):
            continue
        hits.append((i + 1, ln.strip()))
    return hits


def check_no_ci_claim():
    """'decayed' | 'clean' | 'void' — does any tracked .md still assert 'no CI'?

    ⛔ THE POPULATION WAS `CLAUDE.md` ALONE, AND THAT WAS THE DEFECT (#272).

    #272's close condition declared a POPULATION of *every tracked `*.md` that asserts
    this repository has no CI* and a CHANNEL of this script — which opened one file. The
    gap was written into that issue as its own proxy test (*"a NEW file asserting no-CI
    would satisfy every criterion and leave the defect live"*), and then it arrived: PR
    #572 reinstates the struck sentence in `tools/README.md`, a file this checker did
    not open.

    ★ A catcher binds only over the population its CHANNEL can see (#573). Declaring the
    wider population does not widen it — the declaration and the glob are two states
    that must be shown to agree, not one.
    """
    wf = sorted((ROOT / ".github" / "workflows").glob("*.y*ml")) \
        if (ROOT / ".github" / "workflows").is_dir() else []

    files = _tracked_markdown()
    if files is None:
        print(f"\n  workflow files present : {len(wf)}")
        print("  ⛔ VOID — could not enumerate tracked *.md (no git, or not a work tree).")
        print("     The No-CI claim is UNCHECKED, not absent. Established nothing.")
        return "void"

    asserted = []
    for name in files:
        try:
            text = (ROOT / name).read_text(errors="replace")
        except OSError:
            # ⛔ An unreadable member is not an absent claim. One file we could not open
            # means the population was not covered, so the whole verdict is void.
            print(f"\n  ⛔ VOID — {name} is unreadable; the population was not covered.")
            return "void"
        asserted += [(name, n, ln) for n, ln in no_ci_hits(text)]

    print(f"\n  workflow files present : {len(wf)}"
          f"{'  (' + ', '.join(f.name for f in wf) + ')' if wf else ''}")
    print(f"  tracked *.md scanned   : {len(files)}")
    print(f"  un-struck 'no CI' lines: {len(asserted)}")
    if wf and asserted:
        print(f"\n⛔ {len(asserted)} tracked file(s) still assert this repository has no CI, "
              f"and it has {len(wf)} workflow file(s). The claim has DECAYED (#272):",
              file=sys.stderr)
        for name, n, ln in asserted:
            print(f"    {name}:{n}: {ln[:88]}", file=sys.stderr)
        # ⛔ STATE THE ACCEPTED FORM ON THE FAILURE PATH. `tools/README.md`'s sweep put
        # this instrument in the ⛔ column — *"says un-struck, never shows `~~…~~` or
        # FALSE"* — and the finding there is that a guard which prints only a COUNT
        # makes the author go hunting for the shape it wants. Enumerating the offending
        # lines above reprints the author's own text for free; these two lines add the
        # form, quoted from the corpus so the example is real and not invented.
        print("\n   ⇒ ACCEPTED FORMS — retract in place, do not delete (both are live "
              "on main):", file=sys.stderr)
        print("     inline   ⛔ **~~No CI.~~ FALSE since 2026-08-20 — CI exists and GATES.**",
              file=sys.stderr)
        print("     a block  put `⛔ **STALE AS OF <date>**` under the claim, in the same "
              "section", file=sys.stderr)
        return "decayed"
    if not wf and asserted:
        print("  ⇒ claim and world agree: no workflows, claim stands")
    elif wf and not asserted:
        print("  ⇒ claim and world agree: workflows exist, no un-struck claim")
    else:
        print("  ⚠ no workflows and no claim — nothing asserted, nothing to check")
    return "clean"

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
        # ⛔ NOT `False`. This returned False, and the caller reads False as "not
        # unpinned" — so an unreadable README scored as a PASS. #502 C5 named it:
        # "this repository's own silence-as-success failure, inside the instrument
        # built to catch it." The No-CI leg six lines up already returns "void" for
        # exactly this state; this leg simply had not been given the same word.
        return "void"

    # ⛔ TWO forms are endorsed by this README, each with its own ✅. Keying on one
    # of them fires on the REPAIRED state — measured: deleting only the archive line
    # while keeping the runmarker line left the doctrine intact and exited 1. That is
    # the failure mode this check's own docstring says to prefer AGAINST.
    _ENDORSED = (
        re.compile(r"git\s+archive\s+\S+\s+tools/[^\n]*\|\s*tar"),
        re.compile(r"git\s+show\s+\S*:tools/[^\n]*runmarker"),
    )

    def _endorsed_pin_line(t):
        """A pin form counts only on a line that also carries ✅.

        ⛔ Presence alone is satisfiable by a MENTION: a line reading
        "⛔ Never use: git archive <ref> tools/ | tar -x" passed the previous
        version while the doctrine said the opposite. The docstring above already
        calls the ⛔/✅ glyphs "load-bearing content rather than formatting" —
        this reads the polarity it was already relying on. Position, not care.
        """
        for line in t.splitlines():
            if "✅" in line and any(p.search(line) for p in _ENDORSED):
                return True
        return False

    required = [
        ("an ✅-marked pin form (either endorsed one)", _endorsed_pin_line),
        ("why it is needed (runmarker)",
         lambda t: bool(re.search(r"import\s+runmarker", t))),
    ]
    absent = [label for label, ok in required if not ok(text)]

    print("\n  pin doctrine in tools/README.md (#291):")
    for label, ok in required:
        print(f"  {'ok  ' if ok(text) else 'GONE'}  {label}")
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
