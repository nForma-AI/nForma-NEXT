#!/usr/bin/env python3
"""Does the label you are about to query actually EXIST? Asked separately from "does it match".

⛔ WHY THIS EXISTS. Every role in this fleet finds its work with one command:

    gh issue list -R <repo> --state open --limit 100 --label <mine>

⚠ Measured 2026-08-20 against nForma-AI/nForma-NEXT: a label that does NOT EXIST and a label that
exists with NO OPEN ISSUES produce **byte-identical output and identical exit 0**. Both print
nothing. ⇒ `role:dev1` (which is not a label here) and `dev:5` + `role:OPERATOR` (which are, and
match nothing today) are indistinguishable at the call site.

★ THAT IS THIS REPOSITORY'S DOMINANT DEFECT CLASS SITTING INSIDE THE FLEET'S OWN QUEUE QUERY —
two states a decision depends on telling apart, collapsed to one value at a boundary. And the
decision downstream is standing doctrine: *if it returns nothing, say NOTHING QUEUED.* ⇒ A single
typo makes an agent CONFIDENTLY REPORT AN EMPTY QUEUE AND GO IDLE, which is the failure this fleet
has already had once across every pane at the same time.

⛔ THE SAME COLLAPSE ONE LAYER UP, AND IT IS NOT REPAIRED BY ACCIDENT. "This label does not exist"
and "I could not reach the forge to find out" must not be one answer either. An unreachable or
unauthenticated forge is exit 2 — established nothing — NEVER "the label is missing".

★ NEAR MISSES ARE REPORTED, because the useful output is not "no" but "did you mean". Two label
schemes coexist here (`dev:1 … dev:5` and `role:ARCHITECT … role:TEAMLEAD`), and `role:dev1` is a
plausible blend of both that matches neither. A bare "not found" leaves the caller where it found
them.

★ HOW IT IS MEASURED — stated as an ACT, not a noun (#437). "Does this label exist" is the same
kind of noun as "file-open event", which three panes measured three ways and got 1,619 / 7,166 /
17,395. The act here is:

    1. fetch the repository's label set with `gh label list --limit 500 --json name`
    2. ⛔ if it returns AT the bound, treat the set as possibly TRUNCATED and refuse (exit 2) —
       a partial set manufactures false ABSENTs, and a false ABSENT is the answer this tool
       exists to prevent
    3. compare each requested label case-insensitively, because GitHub does
    4. on a miss, offer same-referent candidates by TOKEN SUFFIX before falling back to spelling
       similarity, and label which of the two produced the suggestion

⚠ Every one of those steps changes the answer, and three of them were invisible from outside this
docstring until #437 was adopted — they lived in code comments, which a caller reading `--help`
never sees.

⚠ WHAT THIS DOES NOT DO. It does not say whether a label has issues, or whether they are yours, or
whether the routing is correct. It answers exactly one question — is this string a label in this
repository — and a `0` from it is NOT a statement that your queue is non-empty.

Exit: 0 every requested label exists
      1 at least one does not — a finding
      2 established nothing (the forge was unreachable, unauthenticated, or answered unusably)
"""
import argparse
import difflib
import json
import re
import subprocess
import sys

DEFAULT_REPO = "nForma-AI/nForma-NEXT"


def _tokens(s):
    """Alphanumeric runs, split again at every letter/digit boundary. `role:dev1` -> role dev 1."""
    return [t for t in re.findall(r"[A-Za-z]+|[0-9]+", s.casefold()) if t]


def _same_referent(a, b):
    """Do these two labels name the same thing under different schemes?

    ⛔ SUFFIX, not "contains" and not similarity, and the asymmetry is the whole point. A caller
    who blends two schemes PREPENDS one onto a name that was already complete:

        role:dev1  ->  role dev 1
        dev:1      ->       dev 1    ← a SUFFIX. The same referent.
        role:DEV   ->  role dev      ← a PREFIX. A DIFFERENT referent, and allowing prefixes
                                       would rank it above the right answer on length alone.
    """
    ta, tb = _tokens(a), _tokens(b)
    if ta == tb or not ta or not tb:
        return False
    short, long = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    return long[-len(short):] == short


def check(requested, existing):
    """Pure. (rc, lines). `existing` is the repo's label set; None means it could not be read.

    ⛔ Separated from the network deliberately: the known-positive below drives THIS function with
    synthetic label sets, so it can never be silenced by the real repository changing (#26).
    """
    if existing is None:
        return 2, ["  VOID  the label set could not be read — established nothing. ⚠ This is NOT"
                   " 'the label is missing'."]
    if not requested:
        return 2, ["  VOID  no label was named — established nothing"]
    # ⚠ GitHub label matching is case-insensitive; comparing case-sensitively would manufacture a
    # false "does not exist" for `role:teamlead`. Reported at the label's REAL casing.
    fold = {e.casefold(): e for e in existing}
    lines, missing = [], []
    for r in requested:
        hit = fold.get(r.casefold())
        if hit is None:
            # ⛔ difflib ALONE FINDS THE WRONG NEIGHBOUR HERE, measured on the live case that
            # produced this tool: `role:dev1` scored `role:DEV`, `role:DEVOPS`, `role:DX` — and
            # missed `dev:1`, which is the label actually meant. The `role:` prefix dominates the
            # ratio and drowns the signal.
            # ★ The two schemes differ only in WHERE THE PUNCTUATION FALLS. Drop every
            #   non-alphanumeric and they become the same string: role:dev1 -> dev1 <- dev:1.
            # ⇒ Normalised EXACT matches first; fuzzy similarity only as a fallback, and labelled
            #   as the weaker evidence it is.
            exact = [fold[k] for k in fold if _same_referent(k, r)]
            if exact:
                suffix = f"  — did you mean {', '.join(exact)}? (same name, different scheme)"
            else:
                near = difflib.get_close_matches(r.casefold(), list(fold), n=3, cutoff=0.5)
                suffix = (f"  — nearest by spelling: {', '.join(fold[n] for n in near)}"
                          f" (⚠ similarity only, not a scheme match)") if near else ""
            lines.append(f"  ⛔ ABSENT   {r}{suffix}")
            missing.append(r)
        elif hit != r:
            lines.append(f"  ok        {r}  (matches `{hit}` — GitHub folds case)")
        else:
            lines.append(f"  ok        {r}")
    lines.append(f"  ----  {len(existing)} labels exist in this repository")
    lines.append("  note  EXISTENCE ONLY. A label that exists may still match no issues, and this"
                 " says nothing about whether any of them are yours.")
    if missing:
        lines.append("  ⛔ a `gh issue list --label` with an absent label prints NOTHING and exits"
                     " 0 — indistinguishable from an empty queue. Do not read it as NOTHING"
                     " QUEUED.")
    return (1 if missing else 0), lines


def repo_labels(repo):
    """The repo's label set, or None if it could not be established. Never a partial set."""
    try:
        r = subprocess.run(["gh", "label", "list", "-R", repo, "--limit", "500",
                            "--json", "name"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except ValueError:
        return None
    # ⚠ 500 is a bound, not a fact. If it came back full, the set may be TRUNCATED, and a
    # truncated set manufactures false ABSENTs — so refuse rather than answer from a partial read.
    if not isinstance(data, list) or len(data) >= 500:
        return None
    return [d["name"] for d in data if isinstance(d, dict) and "name" in d]


def self_test():
    """⛔ Synthetic label sets, never this repository's. A control keyed on `dev:1` existing would
    pass only while that label survives — #26's subtype."""
    ok = True
    cases = [
        ("an exact match is ok", ["a:1"], ["a:1", "b:2"], 0),
        ("an absent label is a FINDING, not silence", ["a:9"], ["a:1"], 1),
        ("case folds, as GitHub does", ["ROLE:x"], ["role:X"], 0),
        ("one absent among present is still 1", ["a:1", "zz"], ["a:1"], 1),
        ("⛔ an unreadable label set is VOID, not ABSENT", ["a:1"], None, 2),
        ("no label named is VOID, not clean", [], ["a:1"], 2),
    ]
    for name, req, ex, want in cases:
        rc, _ = check(req, ex)
        ok &= rc == want
        print(f"  {'ok  ' if rc == want else 'FAIL'}  {name} (got {rc}, want {want})")

    # ★ THE NEAR-MISS IS THE USEFUL HALF, and this is the live case: difflib alone answers
    # role:DEV / role:DEVOPS / role:DX here and misses `dev:1`, the label actually meant.
    _, lines = check(["role:dev1"], ["dev:1", "role:DEV", "role:DEVOPS", "role:DX"])
    hit = any("did you mean" in l and "dev:1" in l for l in lines)
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'}  a blend of two schemes resolves to the SAME-NAME label "
          f"(dev:1), not to the spelling-similar ones difflib prefers")

    _, lines = check(["role:dev1"], ["role:DEV"])
    hit = not any("did you mean" in l for l in lines)
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'}  a PREFIX (role:DEV) is NOT offered as the same referent"
          f" — allowing it would outrank the right answer on length alone")

    # ⚠ and the fallback must still fire when no scheme match exists, marked as weaker
    _, lines = check(["role:TEAMLEED"], ["role:TEAMLEAD"])
    hit = any("nearest by spelling" in l and "similarity only" in l for l in lines)
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'}  a true typo falls back to similarity, LABELLED as the "
          f"weaker evidence it is")

    # ⛔ VOID must not be reachable as 0. The two failure directions are separately controlled
    # because collapsing them is the defect one layer up from the one this tool exists for.
    rc, lines = check(["a:1"], None)
    hit = rc == 2 and any("NOT" in l for l in lines)
    ok &= hit
    print(f"  {'ok  ' if hit else 'FAIL'}  VOID says in words that it is not an ABSENT verdict")

    # ==================================================================================
    # ⛔ A POPULATION THIS AUTHOR DID NOT DRAW — criterion 5's population leg (#164 item 1).
    # Everything above runs on label sets I invented. `population-leg.py` scored this tool DRAWN,
    # and I wrote the sentence that says a DRAWN control wants either a real leg or a STATED
    # EXCEPTION. There is no exception available here: the undrawn population is one API call.
    #
    # ★ THE ASSERTION THAT ONLY A REAL POPULATION CAN MAKE. `_same_referent` collapses two
    # labelling schemes onto one name — `role dev 1` ends with `dev 1`. If TWO LABELS THAT REALLY
    # EXIST collapsed onto each other under that rule, the near-miss would confidently offer the
    # WRONG label as "the same referent, other scheme", and every fixture I could invent would
    # still pass. Only the repository's actual label set can answer it.
    # ==================================================================================
    live = repo_labels(DEFAULT_REPO)
    if live is None:
        # ⛔ NOT a failure, and NOT a pass. The forge was unreachable, so this leg measured
        # nothing — the same reading exit 2 protects everywhere else in this repository.
        print("  ----  NOT ESTABLISHED  the live label set could not be read, so the undrawn"
              " population was NOT exercised. ⛔ Untested, not correct.")
    else:
        rc, _ = check(live, live)
        ok &= rc == 0
        print(f"  {'ok  ' if rc == 0 else 'FAIL'}  all {len(live)} REAL labels check as present"
              f" against the real set — a population I did not draw (rc={rc})")

        collide = sorted({(a, b) for a in live for b in live if a < b and _same_referent(a, b)})
        ok &= not collide
        print(f"  {'ok  ' if not collide else 'FAIL'}  no two DISTINCT real labels collapse under"
              f" _same_referent — the near-miss cannot offer a wrong label as the same referent"
              f"{'' if not collide else ' — COLLISIONS: ' + str(collide)}")

        # ⚠ and the rule must still be able to FIRE on this population, or the line above passes
        # by matching nothing at all — the vacuous-control defect this repo files against.
        probe = "role:" + live[0]
        ok &= _same_referent(probe, live[0])
        print(f"  {'ok  ' if _same_referent(probe, live[0]) else 'FAIL'}  and it DOES fire on a"
              f" real label wearing a second scheme ({probe!r} -> {live[0]!r}) — the check above"
              f" is not passing by matching nothing")


    # ⛔ --help IS NOT A REFUSAL. argparse exits 0 after printing usage; catching every SystemExit
    # as "unrecognised arguments" made this tool print its help and then declare it established
    # nothing (#350). Controlled in BOTH directions, because a fix that returned 0 for everything
    # would pass the first half and destroy the refusal.
    import contextlib, io
    for _flag, _want in (("--help", 0), ("-h", 0), ("--zzz-not-a-real-flag", 2)):
        _buf = io.StringIO()
        with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
            _got = main(["x", _flag])
        ok &= _got == _want
        print(f"  {'ok  ' if _got == _want else 'FAIL'}  {_flag} -> {_got} (want {_want})"
              f"{' — help is not VOID' if _want == 0 else ' — a bogus flag is still VOID'}")
    return 0 if ok else 3


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("labels", nargs="*", help="label names to check for existence")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--self-test", action="store_true")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit as e:
        # ⛔ argparse EXITS 0 AFTER PRINTING --help / -h. Catching every SystemExit and calling it
        # "unrecognised arguments" makes the tool REFUSE ITS OWN HELP: it prints the usage text and
        # then declares, one line below, that it established nothing. Reported by ARCHITECT on #350
        # against verdict-census.py; measured here across all five instruments sharing this
        # pattern, which I copied between them.
        # ⛔ `VOID — established nothing` is this repository's most load-bearing string. Emitting it
        # for a SUCCESSFUL request is not a cosmetic defect: it is the refusal vocabulary spent on
        # a non-refusal, which is exactly what makes a real refusal readable.
        if e.code == 0:
            return 0
        print("  VOID  unrecognised arguments — established nothing", file=sys.stderr)
        return 2
    if a.self_test:
        return self_test()
    rc, lines = check(a.labels, repo_labels(a.repo))
    print(f"\nlabel existence — {a.repo}")
    for l in lines:
        print(l)
    print({0: "  every requested label exists",
           1: "  FINDING — a query on an absent label is silent, not empty",
           2: "  VOID"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
