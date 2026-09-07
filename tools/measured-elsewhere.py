#!/usr/bin/env python3
"""A goal file can pass FOR-THIS-REPO while every fact in it was measured somewhere else.

⛔ THE FINDING, filed by an outside installer who vendored this fleet into a foreign
repository (#502 D) and asked for a read on it. `onboard.md` step 3 says to re-scope each
goal's `**Repository:**` line. Doing exactly that makes `scripts/check-goal-conformance.py`
report FOR-THIS-REPO for all five role goals -- while their BODIES still describe
nForma-NEXT. In the reporter's target repo the certified-in-scope goals asserted:

    "This repository has no test infrastructure at all -- no pytest.ini, no
     pyproject.toml, no conftest.py ... no test files of any kind"
        -> actual: pytest, 233 test files, pyproject.toml, conftest.py, a coverage gate

    "No cloud provider, no Kubernetes, no deployment system ... no runtime to observe"
        -> actual: 19 k8s manifests, three production clusters, Prometheus/Loki/Grafana

★ AND THE FILES ARE ALREADY HONEST ABOUT IT. Those paragraphs carry
`[measured: nForma-NEXT 2026-08-19]`. The provenance is written down. NOTHING READS IT.

⇒ THAT IS THE WHOLE GAP: check-goal-conformance separates DECLARED scope from MENTIONED
scope, and cannot separate DECLARED scope from MEASURED scope. This reads the second.

MEASURED HERE, 2026-09-07:
    107 [measured: ...] tags across goals/*.md
     80 OWN · 19 ELSEWHERE (all Blazing-Back) · 8 UNDATED
      5 of 5 goals declare github.com/nForma-AI/nForma-NEXT
      0 files parse the bracketed tag; 12 merely contain the word "measured:"
        -- use vs mention, and a grep for the word says the opposite of the truth

⛔ AND A LINE-BASED READER UNDERCOUNTS THIS CORPUS BY SIX. My first pass used
`grep -ohE '\[measured:[^]]*\]'` and got 101; this tool reads 107. The gap is exactly the
six tags that SPAN A LINE BREAK — grep matches within a line and cannot see them:

    dev-implementation.md:442        [measured: Blazing-Back ⏎ 2026-08-19]
    devops-substrate-and-fleet.md:281 [measured: Blazing-Back 2026-08-19; corroborated ⏎ nForma-NEXT …]

⇒ 107 − 6 = 101, exactly. The corpus did not change; the READER did. ★ And the six are not
a random sample — a tag long enough to wrap is a tag carrying provenance detail, which is
the kind most worth reading. So the pattern here is multiline by construction, not by
accident, and a reimplementation with `grep` would silently reproduce the undercount.

⇒ So even in the ORIGIN estate, 19 of 107 tagged claims were measured in a sibling repo.
⚠ THAT IS NOT A DEFECT AND MUST NOT BE REPORTED AS ONE. A goal may legitimately cite a
sibling estate's measurement; the point is that the count should be KNOWABLE. After a
vendoring re-scope it becomes ~101 of 101, and the same checker still says FOR-THIS-REPO.

WHAT THIS DOES NOT DO:
  · it does not read the CLAIM, only the TAG. An untagged paragraph measured elsewhere is
    invisible here, and tagging is a convention nothing enforces -- so every count is a
    LOWER BOUND on foreign-measured content, never a total.
  · it does not judge whether citing a sibling measurement is appropriate. ELSEWHERE is a
    location, not a verdict.
  · it inherits its notion of "this repo" from check-goal-conformance, IMPORTED rather than
    copied (#345): a second reading of one noun drifts from the first.

Exit: 0 every tagged claim was measured in the declared repo · 1 at least one was measured
elsewhere · 2 established nothing (no goals, no tags, or the repo identity is unknown) ·
3 a control failed.
"""
import argparse
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from runmarker import guard, result  # noqa: E402

# ⛔ IMPORTED, NOT COPIED (#345). `scripts/check-goal-conformance.py` is hyphenated, so a
# plain `import` cannot reach it -- which is exactly the friction that produces a copy.
# ⇒ The two tools must not be able to disagree about what "this repo" is.
_spec = importlib.util.spec_from_file_location(
    "_cgc", os.path.join(HERE, "..", "scripts", "check-goal-conformance.py"))
_cgc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cgc)
declared_scope = _cgc.declared_scope
this_repo = _cgc.this_repo

# `[measured: <repo> <rest>]` -- the repo token is the first word, and everything after it
# is free text (a date, a session, an issue, a retraction).
TAG = re.compile(r"\[measured:\s*([^\s\],]+)([^\]]*)\]", re.I)
# ⚠ A date ANYWHERE in the tail counts. `dated-claims.py` makes the same call for the same
# reason: a tag reading `<date>` is a placeholder that was never filled in.
DATED = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def tags(text):
    """[(repo_token, tail)] for every provenance tag, in document order."""
    return [(m.group(1), m.group(2)) for m in TAG.finditer(text)]


def classify(repo_token, tail, declared):
    """OWN · ELSEWHERE · UNDATED · UNREADABLE, for one tag.

    ⚠ UNDATED is checked BEFORE the repo comparison and reported separately, because a
    tag reading `[measured: nForma-NEXT <date>]` names the right repo and establishes
    nothing about when -- two different failures that a single verdict would merge."""
    if declared is None:
        return "UNREADABLE", "the file declares no parseable Repository"
    token = repo_token.strip().lower()
    same = token == declared[1].lower() or token == f"{declared[0]}/{declared[1]}".lower()
    if not DATED.search(tail):
        where = "here" if same else f"in {repo_token}"
        return "UNDATED", f"measured {where}, but the tag carries no ISO date"
    return ("OWN", repo_token) if same else ("ELSEWHERE", repo_token)


def scan(paths):
    """[(path, declared, [(verdict, detail, line_no)])] -- or None if nothing was read."""
    mine = this_repo()
    out = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        declared = declared_scope(text)
        rows = []
        for m in TAG.finditer(text):
            v, d = classify(m.group(1), m.group(2), declared)
            rows.append((v, d, text[: m.start()].count("\n") + 1))
        out.append((p, declared, rows))
    return out, mine


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.join(HERE, "..", "goals"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        rc = self_test()
        result("SELF-TEST-PASS" if rc == 0 else "SELF-TEST-FAILED")
        return rc

    if not os.path.isdir(a.dir):
        print(f"⛔ ESTABLISHED NOTHING — {a.dir!r} is not a directory.")
        result("ESTABLISHED-NOTHING")
        return 2
    paths = sorted(os.path.join(a.dir, f) for f in os.listdir(a.dir) if f.endswith(".md"))
    if not paths:
        print(f"⛔ ESTABLISHED NOTHING — no .md files in {a.dir!r}. Zero files read and "
              f"zero foreign measurements print the same clean line.")
        result("ESTABLISHED-NOTHING")
        return 2

    rows, mine = scan(paths)
    total = sum(len(r) for _, _, r in rows)
    if total == 0:
        print(f"⛔ ESTABLISHED NOTHING — {len(paths)} file(s) read, ZERO provenance tags "
              f"found. The convention is unenforced, so its ABSENCE is not evidence that "
              f"the claims were measured here.")
        result("ESTABLISHED-NOTHING")
        return 2

    print(f"── MEASURED ELSEWHERE ── {total} provenance tag(s) in {len(paths)} goal file(s)")
    print(f"   THIS REPO   {mine[0] + '/' + mine[1] if mine else 'UNKNOWN — origin unreadable'}")
    print("   PREDICATE   does each `[measured: <repo> …]` tag name the repo the FILE "
          "declares?\n")
    tally = {}
    elsewhere = []
    for p, declared, rs in rows:
        if not rs:
            continue
        c = {}
        for v, _, _ in rs:
            c[v] = c.get(v, 0) + 1
            tally[v] = tally.get(v, 0) + 1
        dec = f"{declared[0]}/{declared[1]}" if declared else "⛔ NO PARSEABLE DECLARATION"
        print(f"  {os.path.basename(p):38} {dec}")
        print(f"      " + " · ".join(f"{k} {v}" for k, v in sorted(c.items())))
        for v, d, ln in rs:
            if v in ("ELSEWHERE", "UNDATED", "UNREADABLE"):
                mark = "⛔" if v == "ELSEWHERE" else "⚠"
                print(f"      {mark} :{ln:<5} {v:10} {d}")
                if v == "ELSEWHERE":
                    elsewhere.append((os.path.basename(p), ln, d))
    print("\n  " + " · ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    print("⚠ ELSEWHERE IS A LOCATION, NOT A VERDICT. A goal may legitimately cite a sibling\n"
          "   estate's measurement; what this makes knowable is HOW MANY, and where.")
    print("⚠ AND EVERY COUNT IS A LOWER BOUND. This reads the TAG, never the claim — an\n"
          "   untagged paragraph measured elsewhere is invisible, and nothing enforces "
          "tagging.")
    if not elsewhere:
        result("CLEAN")
        return 0
    result("FINDINGS")
    return 1


def self_test():
    """⛔ TWO-SIDED AND NAMED. The known-negative is the case that motivated the tool:
    a file whose DECLARED scope is this repo and whose TAGS name another."""
    if not __debug__:
        print("⛔ ESTABLISHED NOTHING — run without -O. Assertions are this suite.")
        return 2

    D = ("nforma-ai", "nforma-next")
    cases = [
        ("✅ KNOWN-POSITIVE  a tag naming the declared repo, with a date",
         ("nForma-NEXT", " 2026-08-19"), D, "OWN"),
        # ⛔ THE FIXTURE NAMES A SYNTHETIC ESTATE, NOT A REAL ONE. `check-tools-index.py`
        # flagged an earlier draft that used a real sibling's name here: a string literal
        # is EXECUTABLE POSITION, and a tool naming another estate there is how the
        # quarantine leg detects contamination. The real instance belongs in the
        # docstring, where it is a citation; in `cases` it would be a claim of belonging.
        ("⛔ KNOWN-NEGATIVE  #502 D: declared here, MEASURED in a sibling estate",
         ("Sibling-Estate", " 2026-08-19"), D, "ELSEWHERE"),
        ("✅ the owner/repo form also matches",
         ("nForma-AI/nForma-NEXT", " 2026-08-19"), D, "OWN"),
        ("⚠ a placeholder date is UNDATED even when the repo is right",
         ("nForma-NEXT", " <date>"), D, "UNDATED"),
        ("⚠ UNDATED is checked FIRST — a foreign repo with no date is still UNDATED",
         ("Sibling-Estate", " <date>"), D, "UNDATED"),
        ("⛔ a file with no parseable Repository line yields UNREADABLE, never OWN",
         ("nForma-NEXT", " 2026-08-19"), None, "UNREADABLE"),
        ("✅ a tail carrying an issue and a session still counts as dated",
         ("nForma-NEXT", " 2026-08-19, session `bd19196d`, #80"), D, "OWN"),
        ("⛔ case is not significant — a repo is not two repos for being shouted",
         ("NFORMA-NEXT", " 2026-08-19"), D, "OWN"),
    ]
    ok = True
    for label, (repo, tail), dec, want in cases:
        got, _ = classify(repo, tail, dec)
        good = got == want
        ok &= good
        print(f"{'✅' if good else '❌'} {label}\n     want {want:10} got {got}")

    _extra = 0
    _extra += 1
    t = tags("prose [measured: nForma-NEXT 2026-08-19] more [measured: Sibling-Estate x] end")
    good = t == [("nForma-NEXT", " 2026-08-19"), ("Sibling-Estate", " x")]
    ok &= good
    print(f"{'✅' if good else '❌'} ✅ CONTROL both tags on one line are found, in order — got {t}")

    _extra += 1
    # ⛔ USE vs MENTION, the trap this whole tool is about: the WORD is not the TAG.
    none = tags("This was measured: nForma-NEXT, 2026-08-19. Also measured elsewhere.")
    good = none == []
    ok &= good
    print(f"{'✅' if good else '❌'} ⛔ CONTROL the bare word 'measured:' is NOT a tag — "
          f"got {len(none)} (must be 0). A grep for the word finds 12 files; the tag, 0.")

    _extra += 1
    good = tags("") == [] and tags("no tags at all here") == []
    ok &= good
    print(f"{'✅' if good else '❌'} ⛔ CONTROL empty and tagless input yield no tags, so the "
          f"caller reports VOID rather than a clean file")

    n = len(cases) + _extra
    print(f"\n{'all ' + str(n) + ' checks passed' if ok else 'FAILED'}")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(guard("measured-elsewhere", main))
