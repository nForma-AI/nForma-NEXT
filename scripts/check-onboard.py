#!/usr/bin/env python3
"""Re-measure onboard.md's claims about the reference recipe against the recipe.

⛔ WHY THIS EXISTS, and it is not tidiness. onboard.md step 8 told the reader to
report `NFORMA_GOAL coverage ... (reference recipe ships 1 of 9)`. Measured
2026-09-06: the recipe ships **9 of 10**. The number had been wrong long enough
for #502 to report it on 2026-08-21 and for it to survive 16 more days — and step
8 asks the reader to REPORT that number, so the doc trained every installer to
report a stale one upward.

⇒ A dated number in prose decays silently. This repo's rule (#272) is that a dated
claim needs a RE-MEASURING CALLER, not a warning to the reader. Writing "9 of 10,
measured 2026-09-06" and stopping would reproduce the defect with a fresher date.

The second leg is #502 A1: `.daintree/bootstrap.sh` was absent from the copy table
while 9 of 10 panes open their initialPrompt with `bash .daintree/bootstrap.sh`.
A reader copying exactly what the table names loses nine panes' first instruction.
⇒ The general form — a file the recipe depends on that the copy table omits — is
what leg 2 checks, so the NEXT omission is caught rather than this one only.

Exit: 0 claims match the recipe · 1 at least one is stale · 2 established nothing.
⚠ 2 is not a pass. If the recipe or the doc could not be read or parsed, this
script measured nothing, and folding that into 0 would report agreement from a run
that never opened a file.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "onboard.md"
RECIPE = ROOT / ".daintree" / "recipes" / "nforma-fleet.json"

COVERAGE = re.compile(r"reference recipe ships (\d+) of (\d+)")
# Backticked repo-relative token inside a table row. Same convention as
# check-orientation.py: a path here always contains "/". Templates and globs
# carry characters no real path does and are skipped.
# ⛔ A ROOT-LEVEL FILE IS A PATH TOO, AND REQUIRING "/" HID THE ONE THIS CHECK
# EXISTS FOR. The first form was `([^`\s]+/[^`\s]*)` -- borrowed from
# check-orientation.py, whose contract really is "always contains a /" because
# CLAUDE.md only points at nested paths. onboard.md's copy table does not: it
# lists `reference-implementations.md` at the repo root, and that file is one of
# the five referents #363 was filed about.
#
# ⇒ Measured 2026-09-07: moving reference-implementations.md away left this
# checker at exit 0. It never extracted the token, so it could not miss it.
# A zero from a predicate that cannot reach the subject is #363's own general
# form -- "a vendoring predicate ... derived over the wrong set" -- committed in
# the checker written to catch it.
#
# ⚠ The "/" was doing real work: it kept prose backticks (`gh`, `--self-test`)
# out. So the second branch requires a REAL EXTENSION rather than dropping the
# constraint -- a bare word still cannot be a path.
CELL = re.compile(
    r"`("
    r"[^`\s]+/[^`\s]*"                                  # nested: anything with a /
    r"|[A-Za-z0-9_.-]+\.(?:md|py|sh|json|ya?ml|txt)"      # root-level: needs an extension
    r")`")
SKIP = set("<>*$()[]{}|")


def _is_ref(tok):
    """Does this token resolve as a git ref here? Asked, not guessed.

    ⚠ Consulted ONLY for a token absent on disk — a path that exists is a path.
    On failure returns False, so an unanswerable token stays REPORTED rather than
    silently dropped.
    """
    import subprocess
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", tok + "^{commit}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def panes(recipe):
    """The recipe's pane list, under either key it has used."""
    return recipe.get("panes") or recipe.get("terminals") or []


def measure(recipe):
    p = panes(recipe)
    blob = [json.dumps(x) for x in p]
    return {
        "panes": len(p),
        "goal": sum(1 for b in blob if "NFORMA_GOAL" in b),
        "bootstrap": sum(1 for b in blob if "bootstrap.sh" in b),
    }


def copy_table_paths(text):
    """Paths the copy table tells an installer to copy."""
    out = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        for tok in CELL.findall(line):
            if SKIP & set(tok) or tok in out:
                continue
            out.append(tok)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true",
                    help="run the controls; reads no recipe")
    args = ap.parse_args()

    if args.self_test:
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
        
        # ⚠ Two-sided, and BOTH poles are named in the assertion text. A one-pole
        # test passes for a function that answers the same thing to everything.
        fake = {"panes": [{"env": {"NFORMA_GOAL": "g"}, "cmd": "bash .daintree/bootstrap.sh"},
                          {"cmd": "echo hi"}]}
        m = measure(fake)
        assert m == {"panes": 2, "goal": 1, "bootstrap": 1}, \
            f"KNOWN-POSITIVE FAILED: measure() must count 2/1/1, got {m}"
        assert measure({"panes": []}) == {"panes": 0, "goal": 0, "bootstrap": 0}, \
            "KNOWN-NEGATIVE FAILED: an empty recipe must measure zero, not raise"
        assert measure({"terminals": [{"env": {"NFORMA_GOAL": 1}}]})["goal"] == 1, \
            "KNOWN-POSITIVE FAILED: the 'terminals' key must be read too"

        assert copy_table_paths("| `a/b.md` | x |") == ["a/b.md"], \
            "KNOWN-POSITIVE FAILED: a backticked table path must be extracted"
        # ⛔ #363's referent. Root-level, no slash — invisible to the first form.
        assert copy_table_paths("| `reference-implementations.md` | x |") == \
            ["reference-implementations.md"], \
            "KNOWN-POSITIVE FAILED: a ROOT-LEVEL file is a path too (#363)"
        # ⚠ and the constraint the "/" was doing: a bare word is still not a path.
        assert copy_table_paths("| run `gh` and `--self-test` | x |") == [], \
            "KNOWN-NEGATIVE FAILED: a bare word with no extension is not a path"
        assert copy_table_paths("| `Makefile` | x |") == [], \
            "KNOWN-NEGATIVE FAILED: extensionless root file is not matched by this form"
        assert copy_table_paths("| `prompts/<ROLE>.md` | x |") == [], \
            "KNOWN-NEGATIVE FAILED: templates must be skipped"
        assert copy_table_paths("not a table row `a/b.md`") == [], \
            "KNOWN-NEGATIVE FAILED: only table rows are the copy table"

        assert COVERAGE.search("reference recipe ships 9 of 10").groups() == ("9", "10"), \
            "KNOWN-POSITIVE FAILED: the coverage claim must parse"
        assert COVERAGE.search("reference recipe ships some of them") is None, \
            "KNOWN-NEGATIVE FAILED: an unparseable claim must not yield a number"
        # ⚠ Same environmental trap as check-orientation.py's: origin/main is not
        # guaranteed to exist (shallow clone, differently-named remote, a vendored
        # install per #502). HEAD is. Its absence must be a SKIP, never a false red.
        assert _is_ref("HEAD"), \
            "KNOWN-POSITIVE FAILED: HEAD must resolve as a ref in any git repo"
        assert not _is_ref("onboard.md"), \
            "KNOWN-NEGATIVE FAILED: a real file must NOT be classified as a ref"
        print("self-test ok — measure(), the extractor and _is_ref each fail on "
              "their negative pole")
        return 0

    try:
        text = DOC.read_text(encoding="utf-8")
        recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"⛔ VOID — cannot read onboard.md or the recipe: {e}", file=sys.stderr)
        print("   This established NOTHING about the doc's claims. Exit 2, not a clean run.",
              file=sys.stderr)
        return 2

    m = measure(recipe)
    if m["panes"] == 0:
        print("⛔ VOID — the recipe declares 0 panes; neither key parsed.", file=sys.stderr)
        print("   The recipe schema changed, or the file is not a recipe. Established nothing.",
              file=sys.stderr)
        return 2

    findings = []
    print(f"  recipe: {m['panes']} panes · NFORMA_GOAL on {m['goal']} · "
          f"bootstrap.sh on {m['bootstrap']}")

    claim = COVERAGE.search(text)
    if claim is None:
        # ⛔ Not a pass. The sentence this script exists to check is gone or reworded,
        # so nothing was compared — the same shape as an unreadable file.
        print("⛔ VOID — onboard.md no longer carries a 'reference recipe ships N of M' "
              "claim; nothing was compared.", file=sys.stderr)
        return 2
    said = (int(claim.group(1)), int(claim.group(2)))
    real = (m["goal"], m["panes"])
    if said == real:
        print(f"  ok    NFORMA_GOAL coverage: doc says {said[0]} of {said[1]}, recipe agrees")
    else:
        findings.append(f"onboard.md says NFORMA_GOAL ships {said[0]} of {said[1]}; "
                        f"the recipe ships {real[0]} of {real[1]}")

    # ⇒ #502 A1 in its general form: a file the panes depend on that the copy
    # table does not name. Checking the class, not the one instance.
    listed = copy_table_paths(text)
    if m["bootstrap"] and not any("bootstrap.sh" in p for p in listed):
        findings.append(f"{m['bootstrap']} pane(s) invoke .daintree/bootstrap.sh and the "
                        f"copy table never names it — copying exactly what the table lists "
                        f"loses those panes' first instruction")
    else:
        print(f"  ok    every pane-invoked file the recipe names is in the copy table")

    # ⛔ NOT every backticked token with a "/" is a repo-relative path, and this
    # leg proved it by flagging `~/.daintree` and `origin/main` on its first run.
    # That is #502 C5a — the over-match this session had fixed in
    # check-orientation.py hours earlier, reproduced immediately in a new file.
    # ⇒ A named failure mode is not a fixed one. Two exclusions, each with a
    # reason rather than a shape guess:
    #   ~/...       a HOME path. Never repo-relative; the doc means the user's box.
    #   a git ref   onboard.md tells installers to push to origin/main, so refs
    #               appear in it by design. Asked of git, not guessed from shape.
    absent = [p for p in listed
              if not p.startswith("~")
              and "*" not in p
              and not (ROOT / p).exists()
              and not _is_ref(p)]
    if absent:
        findings.append("copy table names path(s) absent from this repo: " + ", ".join(absent))
    else:
        print(f"  ok    {len(listed)} copy-table path(s) all exist here")

    if findings:
        print("\n⛔ onboard.md disagrees with the recipe it describes:", file=sys.stderr)
        for f in findings:
            print(f"  · {f}", file=sys.stderr)
        return 1
    print("\n⇒ onboard.md's recipe claims match the recipe (re-measured, not dated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
