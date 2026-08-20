#!/usr/bin/env python3
"""Pins stranded-branches.py's population and the asymmetry it applies to verdicts.

Written from the DOCSTRING. Its stated contract:

    Exit: 0 clean · 1 stranded refs found · 2 ESTABLISHED NOTHING.
    "[] and 'the query failed' must not share a representation."
    "EQUIVALENT-UPSTREAM proves the work landed; NO-UPSTREAM-MATCH proves NOTHING."
    "A denominator that silently excludes part of its population is how '0 stranded'
     gets believed."

⛔ That last sentence is right and was one level too shallow. The function enumerating
merged PRs asked `gh pr list --limit 100`, and `gh` answers a request for more than exists
with everything and a request for less with a **silent prefix**. Measured 2026-08-20:

    nForma-AI/nForma-NEXT           69 merged  ->  69 seen
    Digital-Frontier-LDA/df-wiki   178 merged  -> 100 seen
    Borduas-Holdings/Blazing-Back  775 merged  -> 100 seen

⇒ On the repository with the actual branch churn it inspected **13% of the population** and
reported `0 stranded, exit 0` about the rest — absence read as success, inside a check
written to catch absence read as success. It guarded the ERROR path and left TRUNCATION open.

★ The repair applies the file's own asymmetry to the population: **a positive finding
survives a partial sweep; a negative one does not.**

Run: python3 tools/test_stranded_branches.py
"""
import importlib.util
import os
import subprocess
import sys

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE, and the dangerous
# class is the COMMON one: Python invalidates a .pyc on mtime + SIZE, so a
# SIZE-PRESERVING mutation (==/!=, a flag flip, a token swap) applied in the same
# second leaves both unchanged and the cache is served. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

_here = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(_here, "stranded-branches.py")
_spec = importlib.util.spec_from_file_location("sb", TOOL)
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)


def run(*args):
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True,
                       cwd=os.path.dirname(_here))
    return p.returncode, p.stdout + p.stderr


def check(name, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{name}: got {got!r}, want {want!r}")
    return ok


def main():
    f = 0
    ve = getattr(sb, "verdict_exit", None)

    print("★ the asymmetry — a positive survives a partial sweep, a negative does not:")
    if ve is None:
        print("  FAIL  verdict_exit is missing — this version cannot express the asymmetry")
        f += 1
    else:
        f += not check("nothing found, complete sweep -> clean", ve(0, False), 0)
        f += not check("nothing found, TRUNCATED -> established nothing", ve(0, True), 2)
        f += not check("findings, complete -> findings", ve(3, False), 1)
        f += not check("findings, TRUNCATED -> still findings", ve(3, True), 1)

    print("truncation is detected locally, without a second API call:")
    # A request for MORE than exists returns everything; a request for LESS returns a
    # silent prefix. `len(rows) >= limit` is the only signal, and it needs no network
    # beyond the call already being made.
    try:
        rows, err, truncated = sb.merged_refs(3)
        f += not check("asking for 3 flags truncation", truncated, True)
        f += not check("and returns rows", isinstance(rows, list) and len(rows) == 3, True)
        rows, err, truncated = sb.merged_refs(sb.DEFAULT_LIMIT)
        f += not check("asking for the default does not", truncated, False)
    except TypeError as exc:
        print(f"  FAIL  merged_refs does not report truncation: {exc}")
        f += 2

    print("a failed query is never an empty one:")
    # ⚠ Guarded. An older signature raises TypeError here and would abort the suite
    # BEFORE the remaining checks — a break that stops early under-reports, which is
    # the quieter cousin of a break that prints nothing at all.
    try:
        f += not check("returns a 3-tuple", len(sb.merged_refs(1)), 3)
    except TypeError as exc:
        print(f"  FAIL  merged_refs has the old signature: {exc}")
        f += 1

    print("the tool's own self-test still proves its three states reachable:")
    rc, out = run("--self-test")
    f += not check("exit", rc, 0)
    f += not check("known-positive stranded", "known-positive" in out, True)
    f += not check("unreadable is not zero", "unreadable is not zero" in out, True)

    print("a truncated run says so, loudly, before any count:")
    rc, out = run("--limit", "5")
    f += not check("banner present", "TRUNCATED SWEEP" in out, True)
    f += not check("does not exit clean", rc != 0, True)

    print("--limit needs a number:")
    rc, out = run("--limit", "abc")
    f += not check("exit", rc, 2)

    print()
    if f:
        print(f"{f} FAILED")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
