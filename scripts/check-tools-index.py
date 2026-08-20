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
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

# ⇒ DEV5 wrote this block for #348; DEVOPS owns the file and this is the import site
# offered for review. The shared predicate lives in tools/ so the two guards cannot
# disagree about the same file — one module, referenced, never copied.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
try:
    import estatenames
except ImportError as _exc:                       # noqa: BLE001
    # ⛔ VOID, never a silent skip. A quarantine leg that quietly stops checking is the
    # exact defect the acknowledgement file exists against, and this file GATES EVERY PR
    # — a silent skip here reads as "all clear" on the whole repository.
    # ⚠ Known cost, accepted knowingly: this makes check-tools-index.py the 9th
    # instrument that cannot be pinned as a single file. `git show <ref>:scripts/…` piped
    # to python now raises here instead of running, and THAT IS THE POINT — it fails
    # loudly at exit 2 rather than running a checker with one leg silently missing.
    print("⛔ VOID: cannot import estatenames (%s) — the DERIVED estate leg did not run. "
          "This checked a CLOSED LIST only, so a new estate would read clean. Run from a "
          "checkout, not from a pinned single file." % _exc, file=sys.stderr)
    sys.exit(2)

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


# ⛔ QUARANTINE — a fourth state, and it is NOT a kind of drift.
#
# Measured 2026-08-20 (#307, TEAMLEAD + DEV2 + DEV4 independently): commit ac6a946 promoted
# `tools/teamlead/` wholesale out of a `/private/tmp/claude-501/…` scratch directory that MORE
# THAN ONE ESTATE wrote to. `w1226.py` line 1 is `# control-plane/api/handlers/workloads.py` —
# another product's application source, sitting in this fleet's instrument tree.
#
# ⛔ THE OPERATOR HAS RULED: QUARANTINE. Not indexed, not silenced, not deleted.
#
# ⇒ SO IT IS EVALUATED BEFORE THE DOCUMENTED/UNDOCUMENTED SPLIT, because *documented* is the
# wrong question about a file that may not belong. Reporting `w1226.py` as "missing a row"
# invites the repair that ADDS the row — and an index row is an ASSERTION THAT THE FILE
# BELONGS HERE. The complete index of a contaminated directory is a more confident wrong
# answer than the incomplete one. (DEV4, standing down #313 in favour of this; the framing
# is theirs and it is right.)
#
# ⚠ AND THE OBVIOUS PREDICATE DOES NOT WORK. A content grep for the estate's vocabulary —
# `akash|blazing|Blazing-Back|#1[0-2]\d\d` — matches **8 of 63 files in `tools/` itself**,
# measured: `reference-check.py`, `fleet-context.py`, `marker-reachability.py`,
# `named-referent-check.py` and others. Those instruments EXIST BECAUSE OF those incidents and
# cite them in their docstrings. ⇒ A grep cannot separate a tool that MENTIONS another estate
# from a tool that BELONGS to one — which is `tools/use-not-mention.py`'s question, asked
# about estates instead of commands. A quarantine built on vocabulary would impound a third of
# this fleet's own instruments and call it an estate finding.
#
# ⇒ SO THE PREDICATE IS ABOUT POSITION, NOT VOCABULARY: an estate identifier appearing in an
# executable STRING LITERAL — a path a tool opens, a repo a tool queries — never in a
# docstring or a comment. Measured across the four populations, instruments only:
#
#       tools/ top-level          1 of 33     (memory-index-check.py, a default path)
#       tools/teamlead/          10 of 19
#       tools/architect-sweeps/   0 of  3     <- the control: the predicate is not matching everything
#
# ⚠ WHAT IT STILL CANNOT DO. It is not a verdict about ownership and no exemption list is
# offered, because an exemption list is the silencing mechanism this whole ruling refuses.
# Each hit is A QUESTION FOR A HUMAN. The one top-level hit is real — that file's default path
# does point into another project's transcript directory — and it is NAMED rather than tuned
# away, because a threshold that clears it is a number chosen to make the output comfortable.
# ⚠ `control-plane/` DROPPED — DEVOPS measured zero unique detections for it across all
# three populations, and w1226.py matches on `akash` independently.
# ⛔ THE REST IS KEPT ON PURPOSE, against #348's "derive, do not enumerate". Measured at
# 0252d62: derived-only takes tools/teamlead/ from 9 detections to 5 — ctxwatch,
# repowatch, t_sentinel, w1226 name an estate with NO PATH, and a path-shaped predicate
# cannot see them. A shrink is under-detection. So the two legs are a UNION: this list
# for known names, estatenames for shapes nobody has listed yet.
ESTATE = re.compile(
    r"DigitalFrontier-infra|Borduas-Holdings|Blazing-Back|worker-blazing|akash",
    re.I)


def code_strings(path):
    """String literals in EXECUTABLE position — not docstrings, not comments.

    ⚠ A SyntaxError yields no strings, which reads as CLEAN. That is stated rather than
    guarded: this checker's job is the index, and a file that will not parse is a defect the
    test suites own. It does mean quarantine cannot see inside an unparseable file.
    """
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if path.suffix != ".py":
        # ⚠ Shell has no AST here. Strip whole-line and trailing comments — coarser than the
        # Python path, and it is the weaker leg of the two.
        return [re.sub(r"#.*$", "", line) for line in src.splitlines()]
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr) \
                    and ast.get_docstring(node, clean=False) is not None:
                docs.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


ACK_NAME = "QUARANTINE.txt"
ACK_ENTRY = re.compile(r"^\s*([A-Za-z0-9_./-]+\.(?:py|sh))\s*\|", re.M)


def read_ack(tools_dir):
    """Paths acknowledged as held. (set, None) or (None, why-it-established-nothing).

    ⛔ WHY A FILE AND NOT AN EXIT CODE — and this is the whole argument, so it is here rather
    than in a PR body that nobody will read again.
    #
    # The quarantine ruling was carried as PROSE in nine pane contexts and one merged doc, and
    # was ENFORCED by "the gate is red." Both legs failed at once. Prose dies at the next
    # compaction. And the red was not real: on `main` this checker globbed `tools/*.py`
    # non-recursively, so `tools/teamlead/` was never in its population and all four
    # `scripts/*.py` exited 0 — **the gate had been green the entire time it was being cited as
    # the marker.** Meanwhile the instrument that WOULD have reddened it could not merge,
    # because its own finding blocked it: a marker that cannot be committed is not a marker.
    #
    # ⇒ Determinism belongs in the substrate. A tracked file is a committed artifact: it
    # survives compaction, it is diffable, and it names who ruled what and when.

    ⛔ AND IT IS NOT AN ALLOWLIST, because acknowledgement is checked in BOTH directions. An
    entry for a path that is no longer held — deleted, or repaired — reds the gate. An allowlist
    only ever subtracts; this one rots loudly, which is the only thing that keeps it honest.

    ⚠ Listing a path here is NOT a claim that it belongs in this repository. It is a claim that
    the finding is KNOWN and its disposition is recorded.
    """
    ack = tools_dir / ACK_NAME
    if not ack.is_file():
        return None, f"tools/{ACK_NAME} is absent"
    try:
        text = ack.read_text(encoding="utf-8")
    except OSError:
        return None, f"tools/{ACK_NAME} is unreadable"
    # ⚠ NORMALISED TO tools/-RELATIVE, and both spellings are accepted. Written first with the
    # file holding `tools/teamlead/w1226.py` and the checker holding `teamlead/w1226.py`, which
    # produced the WORST possible output: 21 paths reported as unacknowledged AND 21 reported as
    # stale, in the same run, describing the same 21 files. Two loud, opposite, simultaneously
    # wrong findings — and each is individually plausible, so a reader could act on either.
    entries = {e[len("tools/"):] if e.startswith("tools/") else e
               for e in ACK_ENTRY.findall(text)}
    if not entries:
        # ⛔ Zero extractions is the load-bearing case here too: a format change would parse to
        # an empty set, every held path would read as UNACKNOWLEDGED, and the gate would red for
        # the wrong reason — or, with the comparison written the other way, go green over
        # everything. Neither is a reading; it is a parser failure wearing a verdict.
        return None, f"tools/{ACK_NAME} exists but no entry matched — the format changed"
    return entries, None


def adding_commits(root, directory):
    """How many distinct commits ADDED files under this directory? None if unmeasurable.

    ⛔ WHY A GIT QUESTION BELONGS IN AN INDEX CHECKER. `docs/ESTATE-BOUNDARY.md` names four
    states — LOCAL · FOREIGN · UNCLAIMED · QUARANTINED — and rules that **UNCLAIMED must never
    be collapsed into LOCAL**, because that collapse is the only thing between this reading and
    a confident wrong answer. A content predicate cannot detect UNCLAIMED: it is the ABSENCE of
    provenance evidence, and absence has no string to match. `boxwatch.py` is the specimen —
    it carries four hardcoded terminal UUIDs under another estate's role names and yet holds no
    estate identifier a scan can find, so a content test calls it clean and the index then
    requires it to be named, which asserts it is ours.

    ⇒ The signal that is NOT in the content is in the HISTORY. Measured 2026-08-20 at 280ac70:

          tools/                65 files added across 51 commits    accreted, file by file
          tools/teamlead/       22 files added across  1 commit     WHOLESALE (ac6a946)
          tools/architect-sweeps/ 3 files across 2 commits          accreted

    A directory that arrived in ONE commit out of a shared scratch directory has ONE provenance
    question, not N — which is why the operator ruled quarantine on the DIRECTORY and not on the
    ten files a scan happened to catch.

    ⚠ NEVER GUESSES. If git cannot answer — no repository, no history, a failed call — this
    returns None and the leg is reported NOT CHECKED. Defaulting to "accreted" would convert an
    unmeasured directory into an asserted-local one, which is the collapse this exists against.

    ⛔ A SHALLOW CLONE IS UNMEASURABLE, AND CHECKING `returncode` DOES NOT CATCH IT. Measured
    2026-08-20: `actions/checkout@v4` clones at **depth 1** by default, so `git log
    --diff-filter=A` returns ONE commit for EVERY directory and every one reads as WHOLESALE.
    Reproduced in a `--depth 1` clone of this branch: **all 35 top-level instruments** — the
    fleet's own tools — were reported UNCLAIMED, and the run exited 2. ⇒ The whole instrument
    tree read as another estate's, on every CI run.

    ★ `git log` DID NOT FAIL. It succeeded over a history containing one commit, so the
    `returncode` guard above was never reached and a truncated population answered confidently.
    That is this repository's most-filed defect class committed inside the guard written against
    it — and it is why the shallow test is a SEPARATE question, asked first, rather than an
    error case of the same call.
    """
    shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True, cwd=str(root))
    if shallow.returncode != 0 or shallow.stdout.strip() != "false":
        return None
    # ⚠ ...and a repository holding exactly one commit cannot distinguish the two either, whether
    # or not git calls it shallow. A fresh `git init` + one commit is the self-test's own fixture.
    total = subprocess.run(["git", "rev-list", "--count", "HEAD"],
                           capture_output=True, text=True, cwd=str(root))
    if total.returncode != 0 or total.stdout.strip() in ("", "0", "1"):
        return None
    try:
        r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "HEAD", "--",
                            str(directory.relative_to(root))],
                           capture_output=True, text=True, cwd=str(root), timeout=20)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    shas = {l for l in r.stdout.split() if l}
    return len(shas) if shas else None


def quarantined(directory, names):
    """[(name, the literal that triggered it)] for instruments referencing another estate."""
    out = []
    # ⛔ NOT `directory`. The question is "does this name an estate other than THIS
    # repository", and "this repository" is the one the CHECKER belongs to — not whatever
    # directory it was pointed at. Deriving from the target silently disabled the entire
    # derived leg whenever the target was not itself a git repo — which is every
    # --self-test fixture: identity incomplete -> foreign_in returns [] -> reads exactly
    # like "found nothing". ⚠ My own leg-4 plant could not catch this, because it planted
    # into the REAL tree where identity derives fine. DEVOPS's fixture runs outside a repo,
    # which is the one environment where the leg vanishes.
    ident = estatenames.local_identity(os.path.dirname(os.path.abspath(__file__)))
    if not ident.complete():
        # A leg with no comparand must not look like a leg that found nothing.
        print("⛔ VOID: cannot derive this repo's identity (%r) — the DERIVED estate leg "
              "did NOT run; this checked a closed list only." % (ident,), file=sys.stderr)
        sys.exit(2)
    for n in names:
        lits = code_strings(directory / n)
        named = next((l for l in lits if ESTATE.search(l)), None)
        if named:
            out.append((n, named.strip()[:72]))
            continue
        # The open-ended leg. Same literals, same executable position — only the
        # question differs: not "is this a name I know" but "does this name an estate
        # that is not this one". ⛔ Passed as a LIST: one leg needs adjacency, because
        # `gh -R owner/repo` reaches us as two separate string literals.
        der = estatenames.scan_strings(lits, ident)
        if der:
            kind, matched, _ = der[0]
            out.append((n, ("[derived %s] " % kind) + matched))
    return out


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

    held = set()            # names impounded at the TOP level (for the `extra` leg only)
    held_paths = set()      # every impounded path, tools/-relative — the ack file's population

    def impound(label, directory, names, rel=""):
        """Report quarantined files and REMOVE them from the naming population.

        ⛔ Removed, not merely flagged. If they stayed in, the very next leg would report them
        as missing a row, and the obvious repair for THAT is to add one — an assertion that the
        file belongs here, made by a maintainer clearing a red.
        """
        nonlocal failed
        quar = quarantined(directory, names)
        if not quar:
            return names
        # ⛔ QUARANTINE ALONE DOES NOT FAIL, and DEV2 is why. Their argument: the output says
        # "NOT reported as undocumented" and the exit code said DRIFTED — THE VERDICT
        # CONTRADICTED THE MESSAGE. Quarantine is not drift; it is precisely ESTABLISHED
        # NOTHING about whether these files belong, and this file's own vocabulary already has
        # a place for that. ⇒ The verdict now belongs to the ACKNOWLEDGEMENT legs below, and
        # exit 1 there means THE ACK FILE HAS DRIFTED FROM THE TREE — the same drift semantic
        # this checker has always had, applied to a third surface. It never means "these files
        # do not belong"; nothing here can establish that.
        out.append(f"  QUARANTINED  {label} — {len(quar)} of {len(names)} instrument(s) name"
                   f" another estate in EXECUTABLE position (not in a docstring):")
        for n, lit in quar:
            out.append(f"                 {n}  ->  {lit!r}")
        out.append("               ⛔ NOT reported as undocumented: presence in tools/ is not"
                   " evidence of belonging, and an index row would ASSERT that it is.")
        out.append("               ⛔ Do not index, do not delete, do not rewrite history —"
                   f" the disposition is the operator's, and it is recorded in tools/{ACK_NAME}.")
        # ⛔ WHOLESALE IMPORT ⇒ THE DIRECTORY IS THE UNIT, NOT THE FILE.
        survivors = [n for n in names if n not in {q for q, _ in quar}]
        adds = adding_commits(root, directory)
        if adds is None:
            unchecked.append(f"wholesale-import test for {label}")
            out.append(f"               ----  git history is absent, shallow, or one commit deep"
                       f" for {label} — the wholesale-import leg is NOT CHECKED, never assumed"
                       f" accreted and never assumed wholesale")
        elif adds == 1 and survivors:
            out.append(f"               ⛔ WHOLESALE: every file here arrived in ONE commit, so"
                       f" the provenance question is the DIRECTORY's, not each file's.")
            out.append(f"               UNCLAIMED ({len(survivors)}): {', '.join(survivors)}")
            out.append("               ⚠ No estate marker — and NO evidence they are ours either."
                       " UNCLAIMED is not LOCAL, and the index must not assert that it is.")
            # ⚠ BOTH SETS. Written first as `survivors` alone — the ten FOREIGN files were
            # already reported above, so they LOOKED accounted for, and the acknowledgement
            # population silently became 11 instead of 21. A count that is short by exactly the
            # files everyone is looking at is the easiest kind to read past.
            held_paths.update(f"{rel}/{n}" if rel else n
                              for n in survivors + [q for q, _ in quar])
            held.update(survivors)
            held.update(q for q, _ in quar)
            return []
        held_paths.update(f"{rel}/{n}" if rel else n for n, _ in quar)
        held.update(n for n, _ in quar)
        return [n for n in names if n not in held]

    actual = impound("tools/", tools_dir, actual)
    if not actual:
        return 2, out + ["  VOID  every top-level instrument is quarantined — the index leg"
                         " established nothing"], True
    out.append(f"  instruments on disk: {len(actual)}  ({', '.join(actual)})")
    # Named, never merely counted — see NOT_AN_INSTRUMENT.
    out.append("  ----  excluded from the population as tests: "
               + (", ".join(excluded) if excluded else "none")
               + "  (tests are not instruments and must not be indexed as ones)")

    for label, found in (("table row", rows), ("prose entry", prose)):
        missing = [t for t in actual if t not in found]
        # ⚠ A QUARANTINED FILE'S EXISTING ROW IS NOT AN ERROR AND IS LEFT ALONE. It is on
        # disk; only the naming REQUIREMENT was lifted. Reporting it as "names a file that is
        # not there" would be false, and the obvious repair — deleting the row — is a
        # disposition decision this check has no standing to prompt.
        extra = [t for t in found if t not in actual and t not in held]
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
        sub_actual = impound(f"tools/{d.name}/", d, sub_actual, rel=d.name)
        if not sub_actual:
            # ⚠ EVERY instrument impounded. The directory is still NAMED — a reader must be
            # able to find out it exists and why it is held — but there is nothing left to
            # index, and demanding rows for quarantined files is the repair this refuses.
            if not names_dir(text, d.name):
                failed = True
                out.append(f"  FAIL  tools/README.md never names `{d.name}/` — a QUARANTINED"
                           f" directory a reader cannot discover is the worst of both states")
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

    # ⛔ ACKNOWLEDGEMENT — three rules, and the third is what makes this a guard.
    if held_paths:
        acked, why = read_ack(tools_dir)
        if acked is None:
            unchecked.append("acknowledgement")
            failed = True
            out.append(f"  FAIL  {len(held_paths)} path(s) are held and {why} — the ruling is not"
                       f" a committed artifact, so nothing records that these are known")
        else:
            new = sorted(held_paths - acked)
            stale = sorted(acked - held_paths)
            known = sorted(held_paths & acked)
            if known:
                out.append(f"  HELD  {len(known)} acknowledged in tools/{ACK_NAME} — reported on"
                           f" every run, never silent, and NOT a claim that they belong here:")
                for n in known:
                    out.append(f"          {n}")
            if new:
                failed = True
                out.append(f"  FAIL  NOT acknowledged — this is NEW contamination, or a ruling"
                           f" that was never written down: {', '.join(new)}")
            if stale:
                failed = True
                out.append(f"  FAIL  tools/{ACK_NAME} acknowledges {len(stale)} path(s) that are"
                           f" no longer held — deleted, or repaired, and the file did not move:"
                           f" {', '.join(stale)}")
                out.append("        ⚠ A stale acknowledgement is how an allowlist quietly stops"
                           " describing its subject. It reds the gate on purpose.")
                # ⛔ AND THE OBVIOUS REPAIR IS THE WRONG ONE WHEN A LEG DID NOT RUN. If the
                # wholesale test was NOT CHECKED — a shallow clone — then paths held ONLY by
                # that leg cannot be derived, and they show up here as stale. Deleting them
                # "to fix the red" destroys a correct record using a reading that established
                # nothing. Named, because a maintainer clearing a gate reaches for the delete.
                if any("wholesale-import" in u for u in unchecked):
                    out.append("        ⛔ ...BUT a wholesale-import leg was NOT CHECKED in this"
                               " run (shallow clone?). Paths held only by that leg cannot be"
                               " derived here and will read as stale. DO NOT delete entries on"
                               " the strength of this run — re-run with full history first.")
    else:
        # ⚠ An ack file with nothing to acknowledge is also stale.
        acked, _ = read_ack(tools_dir)
        if acked:
            failed = True
            out.append(f"  FAIL  nothing is held, but tools/{ACK_NAME} still acknowledges"
                       f" {len(acked)} path(s): {', '.join(sorted(acked))}")

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
    import shutil
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

        # ⛔ QUARANTINE, BOTH DIRECTIONS — and the negative is the leg that carries it.
        (sub / "tainted.py").write_text('#\nREPO = "/x/code/DigitalFrontier-infra"\n')
        (sub / "README.md").write_text("# newdir\n\n`planted.py` — a.\n`tainted.py` — b.\n")
        rc, lines, _ = check(root)
        hit = (rc == 1
               and any("QUARANTINED" in l and "newdir" in l for l in lines)
               and any("tainted.py" in l and "DigitalFrontier" in l for l in lines))
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  quarantine: an estate literal in EXECUTABLE "
              f"position exits 1, names the file AND the literal (got {rc})")

        # ⛔ ...and it must NOT be reported as undocumented, even with its name removed from
        # the index — because the repair for "undocumented" is to ADD A ROW, and a row is an
        # assertion that the file belongs here.
        (sub / "README.md").write_text("# newdir\n\n`planted.py` — a.\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and not any("never names: tainted.py" in l for l in lines) \
              and any("QUARANTINED" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  a quarantined file is NEVER reported as missing "
              f"from its index (got {rc})")

        # ⛔⛔ THE KNOWN-NEGATIVE THAT DECIDES WHETHER THIS IS A PREDICATE OR A GREP.
        # A tool that MENTIONS another estate in its docstring — which is what a third of this
        # fleet's own instruments do, because they exist BECAUSE of those incidents — must not
        # be impounded. Measured before this control was written: the vocabulary grep matches
        # 8 of 63 files in `tools/` itself. Without this case, "everything is quarantined" and
        # "my regex works" are the same reading.
        (sub / "tainted.py").write_text(
            '#\n"""Built after the akash / Borduas-Holdings/Blazing-Back incident."""\n'
            '# see control-plane/api for the original\nX = 1\n')
        (sub / "README.md").write_text("# newdir\n\n`planted.py` — a.\n`tainted.py` — b.\n")
        rc, lines, _ = check(root)
        hit = rc == 0 and not any("QUARANTINED" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  quarantine KNOWN-NEGATIVE: a docstring/comment "
              f"MENTION of the same estate is NOT quarantined (got {rc})")
        (sub / "tainted.py").unlink()

        # ⛔ NO GIT ⇒ NOT CHECKED, NEVER "accreted". This fixture is not a repository, so the
        # wholesale leg cannot be answered — and an unanswerable provenance question defaulting
        # to "these files are ours" is the exact collapse docs/ESTATE-BOUNDARY.md forbids.
        (sub / "tainted.py").write_text('#\nREPO = "/x/code/DigitalFrontier-infra"\n')
        rc, lines, _ = check(root)
        hit = rc == 1 and any("wholesale-import leg is NOT CHECKED" in l for l in lines) \
              and not any("UNCLAIMED" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  no git history: the wholesale leg reports NOT "
              f"CHECKED and claims nothing (got {rc})")

        # ⛔ ...and WITH history, a directory that arrived in ONE commit holds its clean files as
        # UNCLAIMED rather than requiring them to be indexed. `boxwatch.py` is the live specimen:
        # another estate's role names, no estate string a scan can match.
        def git(*a):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a],
                           cwd=str(root), capture_output=True)
        # ⚠ TWO COMMITS MINIMUM, and the reason is the defect this control now also covers:
        # a repository holding exactly ONE commit cannot tell "everything arrived together"
        # from "only one commit is visible" — which is precisely what a shallow CI clone looks
        # like. So the fixture commits a placeholder FIRST, and the subdirectory arrives in a
        # second commit. That makes `newdir/` genuinely wholesale inside a history deep enough
        # to say so.
        git("init", "-q", "-b", "main")
        (root / ".keep").write_text("")
        git("add", ".keep")
        git("commit", "-q", "-m", "root")
        git("add", "-A")
        git("commit", "-q", "-m", "wholesale import of newdir")
        rc, lines, _ = check(root)
        hit = (rc == 1
               and any("WHOLESALE" in l for l in lines)
               and any("UNCLAIMED" in l and "planted.py" in l for l in lines)
               and not any("never names: planted.py" in l for l in lines))
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  WHOLESALE: a one-commit directory holds its clean "
              f"files UNCLAIMED, not LOCAL (got {rc})")

        # ⛔ THE KNOWN-NEGATIVE FOR THE WHOLESALE LEG: a directory built up over SEVERAL commits
        # keeps per-file quarantine. Without this, "one commit" and "any commit" are the same
        # reading and every directory would be impounded wholesale.
        (sub / "later.py").write_text("#\n")
        (sub / "README.md").write_text("# newdir\n\n`planted.py` a. `tainted.py` b. `later.py` c.\n")
        git("add", "-A")
        git("commit", "-q", "-m", "a second commit adds a file here")
        rc, lines, _ = check(root)
        hit = rc == 1 and not any("WHOLESALE" in l for l in lines) \
              and any("QUARANTINED" in l and "newdir" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  wholesale KNOWN-NEGATIVE: an accreted directory "
              f"keeps PER-FILE quarantine (got {rc})")
        (sub / "later.py").unlink()
        (sub / "tainted.py").unlink()
        (sub / "README.md").write_text("# newdir\n\n`planted.py` — a planted instrument.\n")
        # ⛔ THE SHALLOW PRODUCER, controlled. `actions/checkout@v4` clones at depth 1, and at
        # depth 1 EVERY directory reads as wholesale — measured, all 35 top-level instruments
        # reported UNCLAIMED on a real CI run. git does not fail there; it answers over a
        # truncated history, so a returncode guard cannot see it.
        shallow = Path(d) / "shallow"
        sr = subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{root}",
                             str(shallow)], capture_output=True, text=True)
        if sr.returncode == 0:
            n_shallow = adding_commits(shallow, shallow / "tools" / "newdir")
            hit = n_shallow is None
            ok &= hit
            print(f"  {'ok  ' if hit else 'FAIL'}  a SHALLOW clone is unmeasurable, not "
                  f"'one commit' — the leg refuses (got {n_shallow})")
        else:
            print("  ----  shallow control NOT EXERCISED: clone failed")

        shutil.rmtree(root / ".git")

        # ⛔ the TOP-LEVEL branch is separate code and needs its own case
        (t / "tainted.py").write_text('#\nR = "Borduas-Holdings/Blazing-Back"\n')
        rc, lines, _ = check(root)
        hit = (rc == 1 and any("QUARANTINED" in l and "tools/" in l for l in lines)
               and not any("no table row for: tainted.py" in l for l in lines))
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  top-level quarantine fires and does not also "
              f"demand a row (got {rc})")
        (t / "tainted.py").unlink()

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

        shutil.rmtree(sub)
        shutil.rmtree(fx)
        (t / "README.md").write_text(good)

        # ⛔ ACKNOWLEDGEMENT — all three transitions, plus the parser's own failure.
        # If it cannot produce all of these it is an allowlist, not a guard: an allowlist only
        # ever subtracts, and nothing ever tells you it has stopped describing its subject.
        #
        # ⚠ TWO planted files, not one, and that is not incidental. Written with one, cases 1
        # and 3 both returned exit 1 for the RIGHT-LOOKING reason and the WRONG one — with no
        # ack file the "absent" branch fires, and with an empty held set the "nothing is held"
        # branch does. Both are rc 1, so a control asserting only on the exit code would have
        # passed while testing neither leg it names.
        (t / "README.md").write_text(good)
        ack = t / ACK_NAME
        one, two = t / "tainted.py", t / "tainted2.py"
        for f in (one, two):
            f.write_text('#\nR = "Borduas-Holdings/Blazing-Back"\n')
        HDR = "# path | state | recorded | ruling\n"
        row = lambda n: f"{n} | FOREIGN | 2026-08-20 | planted by the self-test\n"

        ack.write_text(HDR + row("tainted.py"))
        rc, lines, _ = check(root)
        hit = rc == 1 and any("NOT acknowledged" in l and "tainted2.py" in l for l in lines) \
              and not any("no longer held" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  ack 1/5: a held path that is NOT listed exits 1 — "
              f"new contamination, or a ruling nobody wrote down (got {rc})")

        ack.write_text(HDR + row("tainted.py") + row("tainted2.py"))
        rc, lines, _ = check(root)
        hit = rc == 0 and any(l.startswith("  HELD") for l in lines) \
              and any(l.strip() == "tainted2.py" for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  ack 2/5: LISTED paths exit 0 and are still reported "
              f"BY NAME — acknowledged, never silent (got {rc})")

        # ⛔ THE LEG THAT MAKES IT A GUARD. Delete a listed path; touch nothing else.
        two.unlink()
        rc, lines, _ = check(root)
        hit = rc == 1 and any("no longer held" in l and "tainted2.py" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  ack 3/5: a listed path gone from the tree exits 1 "
              f"— the acknowledgement must not rot (got {rc})")

        # ⛔ ZERO EXTRACTIONS, one level down. A format change parses to an empty set, and the
        # comparison would then report every held path as unacknowledged — a real-looking
        # finding produced entirely by a parser failure.
        two.write_text('#\nR = "Borduas-Holdings/Blazing-Back"\n')
        ack.write_text("# the table moved to another format\n- tainted.py (FOREIGN, 2026-08-20)\n")
        rc, lines, _ = check(root)
        hit = rc == 1 and any("format changed" in l for l in lines) \
              and not any("NOT acknowledged" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  ack 4/5: an ack file parsing to ZERO entries says "
              f"the FORMAT CHANGED, not 'nothing is acknowledged' (got {rc})")

        # ⛔ THE STATED LIMIT, DEMONSTRATED RATHER THAN CLAIMED — and this control asserts the
        # tool gets it WRONG, on purpose. `ESTATE` is a CLOSED LIST of five names, so a novel
        # estate is not detected. TEAMLEAD refuted the opposite claim by execution: a plant of
        # "/Users/…/Contoso-Widgets/state" in executable position exited 0 (#348).
        #
        # ⚠ AND NO OTHER CONTROL HERE COULD HAVE FOUND THAT, because every one plants a name
        # drawn FROM the list. A control built out of an enumeration cannot test whether the
        # enumeration is complete — the same shape as a discriminator that reports N of N.
        #
        # ⇒ When #348's derived predicate lands, THIS CONTROL FAILS. That is the point: the
        # failure is the notification, and whoever sees it reads the paragraph above.
        # ⚠ CLEAN STATE FIRST. A stated-limit control asserting an ABSENCE is worthless if some
        # earlier case is already reddening the run — "not quarantined" and "not reached" print
        # the same. So the assertion is POSITIVE: the novel file must land in the NAMING
        # population and be reported as missing a row, which can only happen if quarantine
        # declined it.
        one.unlink(); two.unlink()
        ack.unlink()
        (t / "README.md").write_text(good)
        novel = t / "novel_estate.py"
        novel.write_text('#\nR = "/Users/someone/code/Contoso-Widgets/state"\n')
        rc, lines, _ = check(root)
        quarantined_it = any("novel_estate.py" in l and "->" in l for l in lines)
        in_population = any("no table row for" in l and "novel_estate.py" in l for l in lines)
        hit = rc == 1 and in_population and not quarantined_it
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  STATED LIMIT: a NOVEL estate name is NOT detected "
              f"and lands in the NAMING population — the vocabulary is a closed list (#348). "
              f"⚠ THIS CONTROL FAILS WHEN THAT IS FIXED, by design (got {rc})")
        novel.unlink()
        # ⚠ RESTORE BOTH. The next case unlinks `one` AND `two`; recreating only `one` made it
        # raise on a file I had already removed — the same shared-fixture bite recorded above the
        # gamma restore. A fixture is shared state and my insertion is not its last reader.
        ack.write_text(HDR + row("tainted.py"))
        for f in (one, two):
            f.write_text('#\nR = "Borduas-Holdings/Blazing-Back"\n')

        # ...and an ack file with nothing left to acknowledge is stale in the other direction
        one.unlink(); two.unlink()
        ack.write_text(HDR + row("tainted.py"))
        rc, lines, _ = check(root)
        hit = rc == 1 and any("still acknowledges" in l for l in lines)
        ok &= hit
        print(f"  {'ok  ' if hit else 'FAIL'}  ack 5/5: an ack file over an EMPTY held set is "
              f"stale too, not vacuously satisfied (got {rc})")
        ack.unlink()

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
    # ⛔ THE SUMMARY WORD MUST NOT SAY CLEAN OVER A HELD QUARANTINE. Exit 0 here means "no
    # UNKNOWN finding", never "no finding" — and a reader takes the summary, not the body.
    held_now = any(l.startswith("  HELD") for l in lines)
    print({0: ("  HELD (acknowledged quarantine — not clean)" if held_now else
               "  clean" if not partial else "  clean-so-far (see PARTIAL)"),
           1: "  DRIFTED", 2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
