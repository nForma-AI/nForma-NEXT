#!/usr/bin/env python3
"""Does the evidence place a file in THIS estate, or another one?

⛔ THE INCIDENT. `tools/teamlead/` was committed wholesale at `ac6a946` — "22 instruments
out of a temp directory and into version control" — from a temp directory more than one
estate had written to. 11 of 19 files carry issue numbers #1066-#1243 while this repo is
in the 300s, plus `akash` / `blazing` / `Borduas-Holdings/Blazing-Back` /
`/worker-blazing-rpg/exec`. One file, `w1226.py`, opens
`# control-plane/api/handlers/workloads.py` and is another product's application source.

⇒ This generalises the one-off grep that found it into a reading with a stated
POPULATION, PREDICATE and CHANNEL.

★ THE ISSUE RANGE IS DERIVED, NEVER HARDCODED. Hardcoding "this repo is under 400"
silently reclassifies every file on the day we reach #1000 — a calibration that decays
into a false verdict with no error. Instead the local vocabulary is read from this
repository's own history (`git log` subjects and bodies), sorted, and cut at its largest
interior gap. The dense run from #1 upward is what this estate demonstrably talks about;
anything beyond the gap is an outlier the repo has barely touched.

⚠ Measured 2026-08-20: 276 distinct issue numbers cited, 259 at or below 400, 17 above —
and the outliers are exactly the foreign citations. The gap does the work, not the number.

⛔ THREE STATES, NOT TWO. `UNCLAIMED` is not a convenience:

    LOCAL      positive evidence of this estate      -> in-range citations, no foreign vocabulary
    FOREIGN    positive evidence of another estate   -> out-of-range citations OR foreign vocabulary
    UNCLAIMED  NO provenance evidence either way     -> neither; the file simply does not say

A two-state reading forces UNCLAIMED into LOCAL, which is the collapse this repository
keeps filing: absence of a foreign marker is not presence of a local one. `boxwatch.py` is
the specimen — no foreign markers and no README row either.

⛔ AND IT CANNOT ESTABLISH DIRECTION. A file citing #1177 may be another estate's committed
here, or ours written *about* that estate, or genuinely dual-use. This tool reports that a
file's provenance evidence points elsewhere; it does NOT report who wrote it or where it
belongs. That limit is printed on every run, not buried in a README, because a verdict read
without its limit is the defect this exists to find.

Exit codes:
  0  no FOREIGN rows                (LOCAL and/or UNCLAIMED only)
  1  at least one FOREIGN row       (a finding)
  2  ESTABLISHED NOTHING            never read as clean
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import estatenames
    from codestrings import code_strings_from_source
except ImportError as exc:                        # noqa: BLE001
    print("⛔ VOID: cannot import estatenames/codestrings (%s) — the DERIVED estate leg did not "
          "run, so this scan checked a CLOSED LIST only and a new estate would read "
          "clean. Not a partial answer; a different question." % exc, file=sys.stderr)
    sys.exit(2)

# ⚠ KEPT, and the reason is measured, not sentimental. #348 says "derive, do not
# enumerate", and the derived legs in `estatenames` do deliver the open-ended half.
# But a bare NAME with no path is invisible to a path-shaped predicate: dropping this
# list took tools/teamlead/ from 9 detections to 5 (ctxwatch, repowatch, t_sentinel,
# w1226) — measured 2026-08-20 at 0252d62. A shrink is under-detection, so the two
# legs are a UNION. ⛔ `control-plane/api` is dropped: DEVOPS measured zero unique
# detections for it across all three populations, and w1226.py matches on `akash`
# independently.
FOREIGN_VOCAB = [
    "borduas-holdings", "blazing-back", "blazing", "akash", "worker-blazing-rpg",
    "tron", "digitalfrontier-infra",
]
ISSUE_RE = re.compile(r"#(\d{1,6})\b")
TEXT_EXT = {".py", ".sh", ".md", ".json", ".yml", ".yaml", ".txt", ""}


def sh(*args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:                        # noqa: BLE001
        return 1, "", str(e)


def local_issue_range(root):
    """The issue numbers THIS repository's own history talks about.

    ⛔ Derived, not declared. Returns (lo, hi, n_distinct) or None when the history
    yields no vocabulary at all — which is ESTABLISHED NOTHING, not "range is empty".
    """
    rc, out, _ = sh("git", "-C", root, "log", "--format=%s%n%b")
    if rc != 0 or not out.strip():
        return None
    nums = sorted({int(m) for m in ISSUE_RE.findall(out)})
    if len(nums) < 8:            # too little vocabulary to cut a gap in
        return None
    # largest interior gap: the dense run below it is this estate's range
    gaps = [(nums[i + 1] - nums[i], i) for i in range(len(nums) - 1)]
    span, idx = max(gaps)
    if span < 50:                # no separable outlier population
        return nums[0], nums[-1], len(nums)
    return nums[0], nums[idx], len(nums)


POSITION_FILTERED = {".py"}


def scannable(text, ext):
    """The text a verdict may be drawn from, and whether position filtering applied.

    ⛔ A DOCSTRING THAT MENTIONS AN ESTATE IS NOT A USE OF ONE. This tool classified whole
    file text, so five of its own seven self-trips were mentions — in a tool whose subject
    is use-vs-mention. DEVOPS had already solved it; `codestrings` is their filter,
    extracted rather than reimplemented (#405: the tenth implementation is the defect).

    ⚠ `.py` ONLY, by construction — there is no executable position in Markdown or JSON.
    The second return value exists so the CALLER can say so in its output; a reader must
    never take a clean prose scan for a position-filtered one.
    """
    if ext not in POSITION_FILTERED:
        return text, None, False
    lits = code_strings_from_source(text, ext)
    # ⛔ RETURN THE LIST, NOT ONLY THE JOIN. `scan_strings` has an ADJACENCY leg — a lone
    # `-R` whose NEXT literal is a forge ref — and joining literals with a separator
    # FABRICATES adjacency that does not exist in the source. Caught immediately: this
    # tool's own suite has `["grep", "-R", "docs/README.md"]` as a known-negative, and the
    # joined form read it as `-R docs/README.md`, a foreign forge ref. The join is still
    # returned for the substring and citation legs, which are position- but not order-sensitive.
    return "\n".join(lits), lits, True


def classify(text, lo, hi, ident=None, strings=None):
    """(verdict, reasons) for one file's content."""
    low = text.lower()
    foreign_terms = sorted({v for v in FOREIGN_VOCAB if v in low})
    # ⇒ The open-ended leg: an estate NOT on the list above, recognised by shape
    # rather than by name, compared against values read from this tree.
    # ⚠ `strings` when we have real literals; `[text]` only when there was nothing to split.
    derived = (estatenames.scan_strings(strings if strings is not None else [text], ident)
               if ident is not None else [])
    cited = sorted({int(m) for m in ISSUE_RE.findall(text)})
    out_of_range = [n for n in cited if n > hi]
    in_range = [n for n in cited if lo <= n <= hi]

    reasons = []
    if foreign_terms:
        reasons.append("vocabulary=" + ",".join(foreign_terms[:3]))
    if derived:
        reasons.append("derived=" + ",".join("%s:%s" % (k, m) for k, m, _ in derived[:3]))
    if out_of_range:
        reasons.append("cites>%d: %s" % (hi, ",".join(str(n) for n in out_of_range[:4])))
    if foreign_terms or out_of_range or derived:
        return "FOREIGN", reasons
    if in_range:
        return "LOCAL", ["cites in-range: " + ",".join(str(n) for n in in_range[:4])]
    return "UNCLAIMED", ["no provenance evidence either way"]


def files_under(root, path):
    rc, out, _ = sh("git", "-C", root, "ls-tree", "-r", "--name-only", "HEAD", path)
    if rc != 0:
        return None
    keep = []
    for f in out.splitlines():
        if os.path.splitext(f)[1] in TEXT_EXT:
            keep.append(f)
    return keep


def void(msg):
    print("⛔ VOID: %s" % msg, file=sys.stderr)
    print("   established NOTHING about provenance — this is UNKNOWN, never 'local'.",
          file=sys.stderr)
    return 2


# ⛔ EQUALITY OVER A KNOWN SET, not `"--self-test" in argv`. Membership ACCEPTS the flag
# without REJECTING anything else, so `--zzz` was silently discarded by the target filter
# below and the tool ran a full scan of the DEFAULT population — returning an exit code
# the caller reads as an answer to the question they thought they asked. That is
# population substitution arriving through the argument parser. ⚠ Worse in a scanner than
# in a checker, and worse again in combination: `--self-test --zzz` exited 0, so a real
# flag plus a typo produced a clean control result that ignored half its invocation.
# (#321's shape, measured here 2026-08-21. Kept INLINE rather than shared: an import is
# what makes an instrument un-pinnable as a single file, and this one still is.)
# ⇒ Joined, not written: no substring of this file matches the predicate it feeds.
FIXTURE_ESTATE = "-".join(("fixture", "estate", "not", "an", "owner"))

KNOWN_FLAGS = {"--self-test"}


def main(argv):
    unknown = [a for a in argv[1:] if a.startswith("-") and a not in KNOWN_FLAGS]
    if unknown:
        print("⛔ VOID: unrecognised flag(s): %s. Nothing was scanned — this is UNKNOWN, "
              "never 'clean'. Known flags: %s" % (", ".join(unknown),
                                                  ", ".join(sorted(KNOWN_FLAGS))),
              file=sys.stderr)
        return 2
    if "--self-test" in argv[1:]:
        return self_test()
    root = os.environ.get("EP_ROOT") or os.getcwd()
    targets = [a for a in argv[1:] if not a.startswith("-")] or ["tools/"]

    rc, _, _ = sh("git", "-C", root, "rev-parse", "--git-dir")
    if rc != 0:
        return void("not a git repository (root=%s)" % root)

    rng = local_issue_range(root)
    if rng is None:
        return void("could not derive a local issue range from this repo's history")
    lo, hi, n = rng
    print("local issue vocabulary: %d distinct, range #%d-#%d (derived from git log, "
          "cut at largest gap)" % (n, lo, hi))

    # ⛔ Derived HERE, and its absence is VOID. An incomplete identity gives the
    # derived leg no comparand, and a leg with no comparand reports nothing while
    # looking exactly like a leg that found nothing.
    ident = estatenames.local_identity(root)
    if not ident.complete():
        return void("cannot derive this repo's own identity (%r) — the derived estate "
                    "leg has no comparand and did NOT run" % (ident,))
    # ⇒ STAMP THE TREE STATE, not only the calibration. Every verdict below comes from
    # `git show HEAD:./<file>`, and the derived range is read from `git log` — BOTH move.
    # Measured today: the range went #1-#381 to #1-#523 in one session, so two runs of this
    # tool can disagree about the same file and neither be wrong.
    # ⛔ `docs/DEFECT-CLASSES.md`: a count without its sha is not comparable to the same count
    # from another run. This printed its calibration and never said which tree produced it.
    rc_h, head, _ = sh("git", "-C", root, "rev-parse", "--short", "HEAD")
    print("tree read: HEAD=%s — every verdict below is AS OF this commit; re-running after "
          "HEAD moves may reclassify a file without either reading being wrong."
          % (head.strip() if rc_h == 0 else "UNKNOWN"))
    print("local identity: repo=%s forge=%s (derived; the derived leg compares against "
          "these)" % (ident.repo_dir, ident.forge_repo))

    rows, found = [], False
    n_filtered = n_whole = 0
    for t in targets:
        fs = files_under(root, t)
        if fs is None:
            return void("git ls-tree failed for %s" % t)
        if not fs:
            return void("population is EMPTY for %s — nothing was examined" % t)
        for f in fs:
            rc2, blob, _ = sh("git", "-C", root, "show", "HEAD:./%s" % f)
            if rc2 != 0:
                rows.append(("UNREADABLE", f, ["git show failed"]))
                continue
            scan, lits, filtered = scannable(blob, os.path.splitext(f)[1])
            v, why = classify(scan, lo, hi, ident, lits)
            if filtered:
                n_filtered += 1
            else:
                n_whole += 1
            rows.append((v, f, why))
            if v == "FOREIGN":
                found = True

    for v, f, why in rows:
        mark = "⛔ " if v == "FOREIGN" else "   "
        print("%s%-10s %-46s %s" % (mark, v, f, "; ".join(why)))

    counts = {}
    for v, _, _ in rows:
        counts[v] = counts.get(v, 0) + 1
    print("\n" + " · ".join("%s %d" % (k, counts[k]) for k in sorted(counts)))
    # ⚠ In the OUTPUT, not only the PR: a reader must not take a clean prose scan for a
    # position-filtered one. The two populations are held to different predicates.
    print("⚠ POSITION FILTERING IS .py-ONLY: %d file(s) scanned in EXECUTABLE POSITION "
          "(docstrings and comments excluded); %d scanned as WHOLE TEXT, because there is no "
          "executable position in Markdown, JSON or plain text. ⇒ A mention in prose scores "
          "the same as a use there, and that half of this scan is NOT use-vs-mention clean."
          % (n_filtered, n_whole))
    print("⛔ DIRECTION IS NOT ESTABLISHED. FOREIGN means this file's provenance evidence "
          "points at another estate. It does NOT say whether it was written there and "
          "committed here, written here ABOUT there, or is genuinely dual-use.")
    print("⚠ UNCLAIMED is not LOCAL. It is the count of files carrying no provenance "
          "evidence in either direction.")
    return 1 if found else 0


def self_test():
    """Hermetic: no git, no network, no fleet. Drives classify() over synthetic content.

    ⚠ The identity is CONSTRUCTED, not derived, precisely so this stays hermetic —
    local_identity() shells out to git. The names below are the fixture's own.
    """
    ID = estatenames.Identity("nForma-NEXT", "-Users-o-code-nForma-NEXT", "nForma-NEXT")
    lo, hi = 1, 400
    cases = [
        ("in-range citation only",        "see #319 and #291",                  "LOCAL"),
        ("out-of-range citation",         "fixes #1226 in the handler",         "FOREIGN"),
        ("foreign vocabulary only",       "deploy to Akash provider",           "FOREIGN"),
        # ⇒ Was `# control-plane/api/handlers/x.py`, matching a LIST ENTRY. That entry is
        # dropped (DEVOPS measured zero unique detections for it), and the specimen now
        # exercises the DERIVED leg instead: an estate name never typed in this file.
        # ⛔ ASSEMBLED AT RUNTIME, AND DELIBERATELY NOT A PLAUSIBLE OWNER. Two reasons, and
        # the second is the one that cost a specimen. (1) A literal foreign path here makes
        # this file trip its OWN detector — the fixture becomes indistinguishable from a
        # dependency in any sweep. (2) A real-looking estate name, once committed, is BURNED
        # as a future control: it is now in the vocabulary of the thing under test.
        # ⇒ The fixture needs the SHAPE, never the OWNER. `FIXTURE_ESTATE` is not a company,
        # cannot be mistaken for one, and no `/code/<name>` literal appears in this file.
        ("foreign path, derived",         "p = '/Users/o/code/%s/x.py'" % FIXTURE_ESTATE,
                                                                                    "FOREIGN"),
        # ⛔ THE KNOWN-NEGATIVE, and the whole flood control in one row. Our OWN path is
        # the same shape as the row above. A predicate that reds here matches every path
        # in the tree and is worthless; without this row nothing would say so.
        ("our own path is NOT foreign",   "p = '/Users/o/code/nForma-NEXT/tools/x.py'", "UNCLAIMED"),
        ("no evidence either way",        "def main():\n    return 0\n",        "UNCLAIMED"),
        ("in-range AND foreign vocab",    "#319 for Borduas-Holdings",          "FOREIGN"),
        ("boundary: exactly hi",          "see #400",                           "LOCAL"),
        ("boundary: hi+1",                "see #401",                           "FOREIGN"),
    ]
    ok = True
    for name, text, want in cases:
        got, _ = classify(text, lo, hi, ID)
        flag = "PASS" if got == want else "FAIL"
        if got != want:
            ok = False
        print("  %-4s %-30s got=%-9s want=%s" % (flag, name, got, want))

    # ⛔ known-negative for the RANGE DERIVATION: too little vocabulary must refuse,
    # not invent a range. A deriver that always returns a range cannot report VOID.
    empty = local_issue_range("/nonexistent-path-for-selftest")
    print("  %-4s %-30s got=%s want=None" % ("PASS" if empty is None else "FAIL",
                                             "no repo -> refuses a range", empty))
    if empty is not None:
        ok = False

    print("\nall checks passed" if ok else "\n⛔ SELF-TEST FAILED")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
