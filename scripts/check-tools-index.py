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

⛔ THE POPULATION WAS A GLOB, AND THE GLOB DID NOT RECURSE. Measured 2026-08-20 (#307):
`tools/*.py` saw 32 instruments; `tools/**/*.py` holds 84 files. Every file in `tools/teamlead/`
— including `waker.py`, the process that decides when panes get woken — was invisible to the
index that exists to surface it, and three successive TEAMLEADs did the work those instruments
already did. ⇒ **A checker whose population is narrower than its subject reports clean about the
part it can see, and the part it cannot see is exactly where the drift accumulates.**

⚠ WIDENING THE GLOB ALONE WOULD HAVE BEEN WORSE THAN THE BLINDNESS. `tools/**/*.py` demands a
fleet-instrument row for `w1226.py` (a verbatim copy of another repository's request handler) and
for six tests written against issue numbers this repository has never had. That is this file's own
NOT_AN_INSTRUMENT warning at directory scale: an index made complete by admitting things that are
not instruments is true about a subject it has damaged. And `tools/architect-sweeps/README.md`
states in writing that it sits **outside this population by construction** — a blanket recursion
silently overrules another role's documented decision.

⇒ SO THE POPULATION IS PER-DIRECTORY, AND EACH DIRECTORY DECLARES ITS OWN INDEX.
      tools/*.py|*.sh          the fleet instruments — table row + prose entry + non-empty
      tools/<sub>/*.py|*.sh    NAMED in tools/<sub>/README.md, and `<sub>/` NAMED in tools/README.md
      tools/testdata/          fixtures — excluded by directory, and PRINTED on every run

⚠ THE SUBDIRECTORY LEG IS DELIBERATELY WEAKER and saying so is load-bearing: it asks whether a
file is *named*, never whether the naming is *true*. A directory can pass this check with a
README that describes its contents wrongly. It is the floor that makes a file findable, not a
claim that anyone has read it — and the top-level three-surface contract is not being extended
downward, because these subdirectories hold snapshots of other people's toolkits, not instruments
this fleet built and measured.

⚠ NON-`.py` INSTRUMENTS ARE NOW IN THE POPULATION (`.sh`). Before this, `merge-watch.sh` had a
row and a prose entry that nothing checked, and `boxwatch.sh`/`dt.sh`/`fleetwatch.sh` were
uncounted. The old output said so on every run — "a shell or non-.py instrument is invisible
here" — which made it a **stated and unfixed** gap for a day rather than an unknown one.

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
# ⛔ NOT every .py in tools/ is an instrument. #77 landed the first TEST file there, and the
# check failed correctly for the wrong reason: the INDEX had not drifted, the POPULATION had.
# Adding a table row for a test would have silenced the check by putting a non-instrument into
# the instrument index — making the claim true by damaging the thing it describes.
# ⚠ The exclusion is PRINTED ON EVERY RUN, named rather than counted. An exclusion nobody can
# see is how a checker's population quietly stops matching its subject, which is the defect this
# file exists against — and a real instrument mis-named `test_*.py` would be silently dropped
# unless a reader can see what was removed. (Found by TEAMLEAD, running it by hand after a merge.)
NOT_AN_INSTRUMENT = re.compile(r"^(?:test_.+|.+_test)\.(?:py|sh)$")

# ⛔ Fixtures are excluded BY DIRECTORY and the exclusion is printed, for the same reason
# NOT_AN_INSTRUMENT is printed. `tools/testdata/` holds `pipe-exit-positive.sh` — an input a
# tool reads, not a tool. Demanding a README for it would push a maintainer to write one, which
# is how a fixture directory becomes indistinguishable from an instrument directory.
FIXTURE_DIRS = {"testdata", "__pycache__"}
INSTRUMENT_SUFFIX = re.compile(r"\.(?:py|sh)$")

ROW = re.compile(r"^\|\s*`([A-Za-z0-9_.-]+\.(?:py|sh))`\s*\|", re.M)
# `**`name.py`** — …` — a prose entry opening the "what each one is for" paragraph.
PROSE = re.compile(r"^\*\*`([A-Za-z0-9_.-]+\.(?:py|sh))`\*\*", re.M)
# The hand-maintained count in the opening sentence: "Six tools, each built because …"
# ⛔ The alternation is built from WORDS, never from `[A-Za-z]+`. A permissive word match makes
# this leg conditional on deleting the NOUN rather than the COUNT: "The tools, …" would match,
# parse to None, and be reported as a malformed count — so #27's other remedy, taken the obvious
# way, would trip the checker built to offer it. A stated-but-false property is worse than an
# unstated one. Anything that is not a number simply does not match, and falls through to
# NOT CHECKED. (Found by ARCHITECT on PR #51, by exercising the three natural phrasings.)
COUNT = re.compile(r"^(?:(" + "|".join(WORDS) + r")|(\d+))\s+tools\b", re.M | re.I)

# ⛔ A LOOSE second pass, because "no numeral matched" is a COLLAPSED PAIR otherwise:
#     (a) there is no count      -> the no-count policy is being followed
#     (b) there is a count in a shape COUNT does not anchor -> the policy is violated AND the
#         count is unguarded, which is the state a reader most needs to know about
# Reported identically before this, so a WRONG count could sit in the header and the run would
# print NOT CHECKED and exit 0. Measured: "There are nine tools here" against twelve on disk
# passed clean, as did "**Twelve** tools" — and this file bolds nearly every emphasis, so the
# bolded form is the LIKELIEST reintroduction here. (Found by DEV2, closing #27.)
LOOSE = re.compile(r"\b(?:(" + "|".join(list(WORDS)[1:]) + r")|(\d+))\b[^.\n]{0,24}?\b(?:tools|instruments)\b",
                   re.I)


def names_dir(text, name):
    """Does an index REFER to a subdirectory, in code voice?

    ⚠ Backticks are required on purpose. `teamlead` appears in ordinary prose all over this
    repository — it is a role name — so a bare substring test would report every index as
    naming a directory it has never mentioned. The check must not be satisfiable by the word.
    """
    return re.search(r"`(?:tools/)?" + re.escape(name) + r"/?`", text) is not None


def instruments_in(d):
    """(instruments, excluded-as-tests) for one directory, non-recursive."""
    every = sorted(p.name for p in d.iterdir()
                   if p.is_file() and INSTRUMENT_SUFFIX.search(p.name))
    return ([n for n in every if not NOT_AN_INSTRUMENT.match(n)],
            [n for n in every if NOT_AN_INSTRUMENT.match(n)])


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
        return 2, [f"  VOID  no tools/ directory under {root} — established nothing"], True
    if not index.is_file():
        return 2, [f"  VOID  {index} is not readable — established nothing"], True

    actual, excluded = instruments_in(tools_dir)
    every = actual + excluded
    text = index.read_text(encoding="utf-8")
    rows = ROW.findall(text)
    prose = PROSE.findall(text)

    # ⛔ Absence of a finding must not be reported as a clean result.
    if not actual:
        return 2, [f"  VOID  tools/ holds no instrument .py files ({len(every)} file(s) present,"
                   f" {len(excluded)} excluded as tests) — established nothing"], True
    if not rows:
        return 2, ["  VOID  no table rows matched in tools/README.md — the index format changed,"
                   " or the table is gone. Established nothing."], True

    failed = False
    unchecked = []          # legs that established NOTHING, so the summary cannot claim them
    out.append(f"  instruments on disk: {len(actual)}  ({', '.join(actual)})")
    # Named, never merely counted — see NOT_AN_INSTRUMENT.
    out.append("  ----  excluded from the population as tests: "
               + (", ".join(excluded) if excluded else "none")
               + "  (tests are not instruments and must not be indexed as ones)")

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

    # ⛔ A ROW AND A FILE BOTH EXISTING IS SATISFIED BY A FILE WITH NOTHING IN IT.
    #
    # Measured 2026-08-20 (#226): a 218-line instrument was committed as git's EMPTY
    # blob e69de29b and this checker exited 0 on it, because every leg above asks
    # "is the NAME present" and none asks "is there an INSTRUMENT". The tool's own
    # --self-test also exited 0, and so did a live run: `python3 <empty file>` exits
    # 0 under every runtime, since there is no statement to fail. Three green checks
    # over nothing.
    #
    # ⇒ The floor is > 0 BYTES, and the reason for that specific floor is that it is
    # THE ONLY ONE THAT NEEDS NO JUSTIFICATION. Any larger N — 10 bytes, 5 lines, "has
    # a shebang" — is a number chosen by whoever wrote the check, which is the
    # calibration-wearing-the-grammar-of-a-rule defect this repository keeps filing.
    # Zero is not a threshold; it is the boundary between a file and no file.
    #
    # ⚠ STATED, so nobody reads this as more than it is. It does NOT catch: a 1-byte
    # file, a file of only comments, or a syntactically valid no-op. Those are real and
    # a bigger arbitrary number would not honestly cover them either — it would only
    # move the line to a place with no argument behind it. Naming the gap beats
    # inventing a constant.
    empty = [n for n in actual if (tools_dir / n).stat().st_size == 0]
    if empty:
        failed = True
        out.append(f"  FAIL  indexed but EMPTY (0 bytes): {', '.join(empty)}"
                   f" — the index verified the FILENAME, not the instrument")
    else:
        out.append(f"  ok    every indexed tool is non-empty ({len(actual)})")

    m = COUNT.search(text)
    if not m:
        head = text.split("\n\n")[0] + "\n\n" + (text.split("\n\n") + [""])[1]
        loose = LOOSE.search(head)
        if loose:
            failed = True
            out.append(f"  FAIL  no anchored numeral, but {loose.group(0)!r} looks like a count this"
                       " check cannot verify — an UNGUARDED count is not the same as no count")
        else:
            unchecked.append("header count")
            out.append("  ----  no hand-maintained numeral found — that leg NOT CHECKED"
                       " (dropping it is #27's other valid remedy, not a defect)")
    else:
        stated = parse_count(m.group(1) or m.group(2))
        if stated != len(actual):
            failed = True
            out.append(f"  FAIL  header says {m.group(1)} ({stated}); the directory holds {len(actual)}")
        else:
            out.append(f"  ok    header count agrees ({stated})")

    # ⛔ SUBDIRECTORIES — the #307 leg. A directory the top index never names is a directory
    # a reader is told by omission does not exist, which is the same failure as a missing row
    # one level up. Both halves are required: the top index must NAME the directory, and the
    # directory must NAME its own contents. Either alone leaves instruments unfindable.
    fixtures = []
    for d in sorted(p for p in tools_dir.iterdir() if p.is_dir()):
        if d.name in FIXTURE_DIRS or d.name.startswith("."):
            fixtures.append(d.name)
            continue
        sub_actual, sub_excluded = instruments_in(d)
        if not sub_actual and not sub_excluded:
            continue
        out.append(f"  tools/{d.name}/: {len(sub_actual)} instrument(s)"
                   f"  ({', '.join(sub_actual) if sub_actual else 'none'})")
        if sub_excluded:
            out.append(f"  ----  excluded there as tests: {', '.join(sub_excluded)}")
        if not sub_actual:
            continue
        if not names_dir(text, d.name):
            failed = True
            out.append(f"  FAIL  tools/README.md never names `{d.name}/` — the top index tells a"
                       f" reader by omission that its {len(sub_actual)} instrument(s) do not exist")
        sub_index = d / "README.md"
        if not sub_index.is_file():
            failed = True
            out.append(f"  FAIL  tools/{d.name}/ holds instruments and has NO README.md —"
                       f" nothing indexes them at any level")
            continue
        sub_text = sub_index.read_text(encoding="utf-8")
        sub_missing = [n for n in sub_actual if f"`{n}`" not in sub_text]
        sub_empty = [n for n in sub_actual if (d / n).stat().st_size == 0]
        if sub_missing:
            failed = True
            out.append(f"  FAIL  tools/{d.name}/README.md never names: {', '.join(sub_missing)}")
        if sub_empty:
            failed = True
            out.append(f"  FAIL  named but EMPTY (0 bytes): "
                       + ", ".join(f"{d.name}/{n}" for n in sub_empty))
        if not sub_missing and not sub_empty:
            out.append(f"  ok    tools/{d.name}/README.md names all {len(sub_actual)}, none empty")
    out.append("  ----  excluded as fixture directories: "
               + (", ".join(fixtures) if fixtures else "none")
               + "  (an input a tool reads is not a tool)")

    # Every tool prints what its numbers do NOT establish, on every run.
    out.append("  note  this checks PRESENCE of a row, never whether the row is ACCURATE —"
               " a wrong description passes")
    out.append("  note  a SUBDIRECTORY instrument is held to a WEAKER contract than a top-level"
               " one: NAMED in its own README, not row + prose + count. Findable, not reviewed.")
    # ⛔ The SUMMARY WORD must not assert more than the run measured. `clean` folds VERIFIED
    # together with ESTABLISHED-NOTHING, which is criterion 3's defect in goals/README.md — and
    # printing the unchecked leg above does not fix it, because a reader takes the summary.
    # Same class as #8's "genuinely free": an instrument may report what it saw; it may not name
    # a conclusion it did not measure. Exit stays 0 — nothing FAILED, and the run did establish
    # something, so exit 2 (`established nothing`) would be the opposite overclaim.
    if unchecked and not failed:
        out.append(f"  PARTIAL  rows and prose verified; {len(unchecked)} leg(s) established"
                   f" NOTHING: {', '.join(unchecked)} — not 'clean'")
    return (1 if failed else 0), out, bool(unchecked)


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

        rc, _, _ = check(root)
        ok &= (rc == 0)
        print(f"  {'ok  ' if rc == 0 else 'FAIL'}  known-positive: a correct index exits 0 (got {rc})")

        # the drift this exists to catch: a tool lands, the index does not move
        (t / "gamma.py").write_text("#\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("gamma.py" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  known-negative: a new tool with no row exits 1 and "
              f"names it (got {rc})")

        (t / "gamma.py").unlink()

        # ⛔ the byte-floor's own known-negative: an INDEXED tool truncated to 0 bytes.
        # This is the #226 case reproduced — every name is present and the file is empty.
        (t / "alpha.py").write_text("")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("EMPTY" in l and "alpha.py" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  byte-floor: an indexed 0-byte tool exits 1 and "
              f"names it (got {rc})")
        (t / "alpha.py").write_text("#\n")
        # ⚠ restore gamma: a later case in this same fixture deletes it, and removing
        # it here made that case fail on a file I had already unlinked. The fixture is
        # shared state and my insertion is not the last reader of it.
        (t / "gamma.py").write_text("#\n")

        # ⛔ an UNGUARDED count must not read as NO count — the third state
        (t / "gamma.py").unlink()
        (t / "README.md").write_text(good.replace(
            "Two tools, each built", "**Two** tools, each built"))
        rc, lines, _ = check(root)
        hit = rc == 1 and any("looks like a count" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  third state: a count this check cannot anchor exits 1 "
              f"rather than reporting NOT CHECKED (got {rc})")

        # ...and a genuinely absent count still reports NOT CHECKED and passes
        (t / "README.md").write_text(good.replace("Two tools, each built", "Each built"))
        rc, lines, _ = check(root)
        hit = rc == 0 and any("NOT CHECKED" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  no count at all still exits 0 as NOT CHECKED (got {rc})")

        # ⛔ a TEST file must be excluded, not reported as an undocumented instrument
        (t / "README.md").write_text(good)
        (t / "test_alpha.py").write_text("#\n")
        rc, lines, _ = check(root)
        hit = rc == 0 and any("excluded from the population as tests: test_alpha.py" in l
                              for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a test file is excluded AND named in the output "
              f"(got {rc})")

        # ⛔ ...and if the exclusion swallows the whole population, that is VOID, never clean.
        # An empty population passing every check is #1's class: a guard aimed at nothing.
        for f in ("alpha.py", "beta.py"):
            (t / f).unlink()
        rc, lines, _ = check(root)
        hit = rc == 2 and any("established nothing" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an all-excluded population exits 2, not 0 (got {rc})")
        for f in ("alpha.py", "beta.py"):
            (t / f).write_text("#\n")
        (t / "test_alpha.py").unlink()

        # ⛔ a run with an unchecked leg must not summarise as `clean`
        (t / "README.md").write_text(good.replace("Two tools, each built", "Each built"))
        rc, lines, partial = check(root)
        hit = rc == 0 and partial and any("established" in l and "NOTHING" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an unchecked leg reports PARTIAL, not clean "
              f"(got rc={rc} partial={partial})")

        # ⛔ #307's KNOWN-NEGATIVE, and the condition TEAMLEAD gated the fix on: a tool planted
        # in a NEW SUBDIRECTORY must be REPORTED, not silently outside the population. Under the
        # old `tools/*.py` glob every assertion in this block passes at rc == 0 — which is what
        # made the blindness survive 84 files and three role-holders. A fix to a POPULATION is
        # unverified until the check has been shown to fail on something the old population
        # could not see; agreeing with `ls` again proves only that `ls` did not move.
        (t / "README.md").write_text(good)
        sub = t / "newdir"
        sub.mkdir()
        (sub / "planted.py").write_text("#\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("newdir" in l and "never names" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  planted subdir: a directory the top index never "
              f"names exits 1 and names it (got {rc})")

        # ⚠ naming the directory is not indexing its contents — the second half must still fire
        (t / "README.md").write_text(good + "\nSee `newdir/` for more.\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("NO README.md" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a NAMED subdir with no index of its own still "
              f"exits 1 (got {rc})")

        # ...and an index that exists but omits the tool is #27's drift, one level down
        (sub / "README.md").write_text("# newdir\n\nSome instruments live here.\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("never names: planted.py" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a subdir README that omits its own tool exits 1 "
              f"and names it (got {rc})")

        # ...and the repaired state PASSES, so the leg is not merely always-red
        (sub / "README.md").write_text("# newdir\n\n`planted.py` — a planted instrument.\n")
        rc, lines, _ = check(root)
        hit = rc == 0 and any("names all 1" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  known-positive: a fully indexed subdir exits 0 "
              f"(got {rc})")

        # ⛔ THE WORD ALONE MUST NOT SATISFY IT. Every subdirectory here is named after a role,
        # and role names are the most common nouns in this repository — a bare substring test
        # would report the index as naming a directory it has never referred to.
        (t / "README.md").write_text(good + "\nThe newdir experiment is over.\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("never names `newdir/`" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  an unbackticked mention does not count as naming "
              f"the directory (got {rc})")
        (t / "README.md").write_text(good + "\nSee `newdir/` for more.\n")

        # a FIXTURE directory is excluded by name, and the exclusion is VISIBLE
        fx = t / "testdata"
        fx.mkdir()
        (fx / "positive.sh").write_text("#\n")
        rc, lines, _ = check(root)
        hit = rc == 0 and any("fixture directories: testdata" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  testdata/ is excluded AND named in the output "
              f"(got {rc})")

        # ⛔ the `.sh` widening's own known-negative. Before this, a top-level shell instrument
        # had no row requirement at all: the run PRINTED that it was invisible and exited 0.
        (t / "delta.sh").write_text("#\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("delta.sh" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a top-level .sh with no row exits 1 and names it "
              f"(got {rc})")
        (t / "delta.sh").unlink()

        import shutil
        shutil.rmtree(sub)
        shutil.rmtree(fx)
        (t / "README.md").write_text(good)

        # instrument failure must not read as a pass
        (t / "README.md").write_text("# Fleet instruments\n\nnothing here\n")
        rc, _, _ = check(root)
        ok &= (rc == 2)
        print(f"  {'ok  ' if rc == 2 else 'FAIL'}  void: an unparseable index exits 2, not 0 (got {rc})")
    return 0 if ok else 3


def main(argv):
    root = Path(__file__).resolve().parent.parent
    args = argv[1:]
    # ⚠ BOTH SPELLINGS. Most instruments here take `--self-test`; this one took `--selftest`,
    # and a reviewer reaching for the majority spelling got the VOID path — an unrecognised
    # argument — which is indistinguishable from a clean refusal unless you read stderr.
    # `tools/index-watch.py` calls `--selftest`, so it stays; the alias is added, not swapped.
    if args in (["--selftest"], ["--self-test"]):
        return selftest()
    # ⚠ An unrecognised argument must not be silently ignored into a pass (ARCHITECT, PR #47).
    if args:
        print(f"  VOID  unrecognised argument(s): {' '.join(args)} — established nothing",
              file=sys.stderr)
        return 2
    rc, lines, partial = check(root)
    print("\ntools/README.md vs tools/")
    for l in lines:
        print(l)
    print({0: "  clean" if not partial else "  clean-so-far (see PARTIAL)",
           1: "  DRIFTED", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
