#!/usr/bin/env python3
"""Can any CI invocation actually collect this test, or does a marker exclude it everywhere?

⛔ THE MEASURED CASE. `tests/test_cluster_spec_drift.py` in DigitalFrontier-infra sets
`pytestmark = pytest.mark.network` at module scope. Its repository has exactly two `-m`
selectors, and I read both rather than trusting the report:

    ci-pr.yml:558  pytest compiler/tests/ tests/ ... -m "not e2e and not network"
    ci-pr.yml:615  pytest "${testfile}"        ... -m "not e2e"

The first covers `tests/` and excludes `network`. The second takes a shell variable. ⇒ The
guard has never been collected by CI. It was filed as Blazing-Back#1115 and reported by two
agents; **the finding existed and the instrument did not**, so the next one like it is found
by accident again.

★ THIS IS THE STATIC HALF OF nForma-NEXT#2, WHICH SPECIFIES THE PROPERTY BETTER THAN THIS
DOCSTRING COULD — five states from run history, including NEVER-CONCLUDED (22 runs, zero
verdicts). But #2's states are derived from RUN HISTORY, and a test excluded by every
selector generates no runs to query. ⇒ You cannot ask "has this gate ever spoken?" about
something you do not know exists. **This supplies that population, from the repository
alone: no API, no rate limit, and it can gate in CI.**

⚠ THREE STATES, AND THE THIRD IS THE POINT:

  REACHABLE     some invocation's paths cover the file AND its -m admits the markers
  UNREACHABLE   every invocation either misses the path or excludes a marker
  UNKNOWN-PATH  an invocation's path is a shell variable (`"${testfile}"`) and cannot be
                resolved statically

⛔ UNKNOWN-PATH IS NOT UNREACHABLE. Treating it as such manufactures findings against tests
that a loop does run; treating it as REACHABLE hides real ones. It is reported separately and
counted in neither, because a guard that resolves its own ambiguity in either direction is
making the claim its evidence cannot support.

Exit: 0 all reachable · 1 something is unreachable · 2 established nothing.
"""
import argparse, ast, glob, os, re, sys

PYTEST_CALL = re.compile(r"(?<![\w/-])pytest\b")
VARIABLE = re.compile(r"\$\{?\w+\}?")


def unfold(text):
    """Join backslash continuations. A pytest invocation in a workflow is usually five
    lines, and a line-at-a-time scanner sees a bare `pytest` with no arguments at all —
    which reads as an invocation collecting everything."""
    return re.sub(r"\\\s*\n\s*", " ", text)


COMMENT = re.compile(r"(?<!\\)#.*$")


def command_position(line):
    """Where does a REAL `pytest` command start on this line, if anywhere?

    ⛔ THIS FUNCTION EXISTS BECAUSE ITS ABSENCE PRODUCED A CLEAN, WRONG ANSWER. The first
    version matched the token `pytest` anywhere. Run against a 50-workflow estate it
    reported **870 test files, 0 unreachable** — and every "invocation" it found outside
    ci-pr.yml's real ones was a COMMENT or an `echo`:

        # (32Gi) on 2026-06-13: the runner only hosts lint / unit-tests (pytest
        echo "A2: using ${WORKER_COUNT} pytest workers (cgroup-aware)"
        #      pytest stops walking up at the `tests/` package). One combined

    Each parsed to `paths=[] -m=None`, which the reachability rule reads as *collects
    everything*, so **one comment marks the whole repository reachable.** The known
    positive — a guard two agents had already reported as never collected — was reported
    REACHABLE by a tool written to find exactly it.

    ★ Two defects compounding, and either alone would have been survivable: a matcher that
    finds its token in the prose ABOUT the token, and a FAIL-OPEN default where an
    unparseable invocation means *everything is covered*. This fleet has now recorded that
    prose-matching defect three times in one night, in three different agents' work.
    """
    line = COMMENT.sub("", line)
    for m in PYTEST_CALL.finditer(line):
        before = line[:m.start()]
        # command position: start of line, or after a shell separator. Anything else —
        # `echo "... pytest ..."`, `pip install pytest` — is a mention, not a call.
        if re.search(r"(^|[|;&(]|&&|\|\||^\s*-\s+run:\s*)\s*$", before):
            return m.end()
        if re.match(r"^\s*$", before):
            return m.end()
    return None


def invocations(workflow_text):
    """Every pytest invocation, as (paths, marker_expr, has_variable_path)."""
    out = []
    for line in unfold(workflow_text).splitlines():
        pos = command_position(line)
        if pos is None:
            continue
        seg = line[pos:]
        m = re.search(r'-m\s+"([^"]+)"|-m\s+\'([^\']+)\'', seg)
        expr = (m.group(1) or m.group(2)) if m else None
        # ⛔ STRIP QUOTED FLAG VALUES BEFORE TOKENISING. `-m "not e2e and not network"`
        # splits into six tokens, and a skip-one-token rule leaves `e2e`, `and`, `not`,
        # `network` behind as PATHS. Caught by the self-test, which is why `paths
        # recovered` asserts the exact list rather than "contains tests/": a superset
        # would have passed a looser assertion and then matched a directory named
        # `network` on some other repository.
        stripped = re.sub(r"-\S+\s+\"[^\"]*\"|-\S+\s+'[^']*'", " ", seg)
        paths, var = [], False
        toks = stripped.split()
        skip_next = False
        for i, t in enumerate(toks):
            if skip_next:
                skip_next = False
                continue
            if t.startswith("-"):
                # flags that consume a value
                if t in {"-m", "-n", "-k", "-p", "--timeout", "--junitxml"}:
                    skip_next = "=" not in t
                continue
            if VARIABLE.search(t):
                var = True
                continue
            if t.startswith(("&&", "||", "|", ";", ")")):
                break
            paths.append(t.strip('"\''))
        out.append((paths, expr, var))
    return out


# ⚠ `run:` is in the prefix set because a one-line step writes `- run: python3 x.py`,
# where the command follows a YAML key rather than a shell separator. Without it the rule
# matched only commands inside `run: |` blocks — which is how the real estate happened to
# be written, so the omission passed against live data and failed against the fixture.
# A test that agrees with production is not thereby correct.
DIRECT_RUN = re.compile(
    r"(?:^|[|;&(]|&&|run:)\s*(?:python3?|uv\s+run\s+python3?)\s+([^\s|;&]+\.py)")


def directly_run(workflow_text):
    """Files executed as SCRIPTS rather than collected by pytest.

    ⛔ Without this the tool asks "can pytest collect it?" and reports "no" for 11 e2e
    files that are run as `python3 e2e/test_z_blazing_pg_e2e.py` in their own workflows.
    The answer was true and the QUESTION was wrong — which is the harder failure, because
    a true answer to the wrong question survives review.

    ⇒ The question this tool exists to answer is *is this test run at all*, so a direct
    invocation counts, and a file named by one is not unreachable.
    """
    out = set()
    for line in unfold(COMMENT.sub("", workflow_text)).splitlines():
        for m in DIRECT_RUN.finditer(line):
            out.add(m.group(1).strip("\"'"))
    return out


def module_markers(path):
    """Module-scope markers only.

    ⛔ Not decorators. `@pytest.mark.network` on ONE test excludes that test; the question
    here is whether the FILE can be collected at all, and only a module-level `pytestmark`
    answers it. Conflating them would report a file as unreachable because one of its
    thirty tests is marked.
    """
    try:
        tree = ast.parse(open(path, errors="replace").read())
    except (OSError, SyntaxError):
        return None
    marks = set()
    for node in tree.body:                       # module scope ONLY
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in targets):
            continue
        for sub in ast.walk(node.value) if node.value else []:
            if isinstance(sub, ast.Attribute):
                marks.add(sub.attr)
    marks.discard("mark")
    # ⛔ NOT EVERY `pytest.mark.X` IS A SELECTOR. `skipif`, `skip`, `xfail` and
    # `parametrize` change what happens once a test IS collected; they say nothing about
    # whether `-m` admits the file. Counting them made
    # `control-plane/api/tests/test_billing_stripe_integration.py` read as UNREACHABLE
    # while `billing-stripe-gate.yml` names it explicitly, twice.
    return marks - {"skipif", "skip", "xfail", "parametrize", "usefixtures", "filterwarnings"}


def admits(expr, marks):
    """Does this -m expression admit a file carrying `marks`?

    Supports the forms this estate actually uses — `not X`, `X and Y`, `not X and not Y`,
    `or`. ⚠ An expression it cannot parse returns None, which the caller must treat as
    UNKNOWN rather than as either answer.
    """
    if expr is None:
        return True                              # no -m collects everything
    tokens = re.findall(r"\bnot\b|\band\b|\bor\b|\(|\)|[A-Za-z_][A-Za-z0-9_]*", expr)
    py = []
    for t in tokens:
        if t in {"not", "and", "or", "(", ")"}:
            py.append(t)
        else:
            py.append("True" if t in marks else "False")
    try:
        return bool(eval(" ".join(py), {"__builtins__": {}}, {}))   # noqa: S307
    except Exception:
        return None


def covers(paths, relpath):
    """Would these path arguments collect this file?"""
    if not paths:
        return True                              # bare `pytest` collects from rootdir
    for p in paths:
        p = p.rstrip("/")
        if relpath == p or relpath.startswith(p + "/"):
            return True
    return False


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="UNKNOWN-PATH is counted in neither column. A variable path cannot be "
               "resolved statically, and resolving it in either direction would make a "
               "claim the evidence does not support.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    wf = sorted(glob.glob(os.path.join(args.root, ".github", "workflows", "*.y*ml")))
    if not wf:
        print(f"⛔ no workflows under {args.root}/.github/workflows — this is a fact about "
              "the PATH, not about coverage. ESTABLISHED NOTHING.", file=sys.stderr)
        return 2

    invs, direct = [], set()
    for f in wf:
        text = open(f, errors="replace").read()
        invs += [(os.path.basename(f), *i) for i in invocations(text)]
        direct |= directly_run(text)
    if not invs:
        print(f"⛔ {len(wf)} workflow(s) and not one pytest invocation. Either this project "
              "does not use pytest in CI, or the parser missed them. Both make every verdict "
              "below meaningless. ESTABLISHED NOTHING.", file=sys.stderr)
        return 2

    tests = [p for p in glob.glob(os.path.join(args.root, "**", "test_*.py"), recursive=True)
             if ".venv" not in p and "node_modules" not in p and "/.claude/" not in p
             and ".worktrees" not in p]

    unreachable, unknown, reachable = [], [], 0
    for t in tests:
        marks = module_markers(t)
        if marks is None or not marks:
            reachable += 1                        # unmarked files are collected by anything
            continue
        rel = os.path.relpath(t, args.root)
        if rel in direct:
            reachable += 1        # run as a script, not collected — still run
            continue
        verdict, why = "UNREACHABLE", []
        for wfname, paths, expr, var in invs:
            if not covers(paths, rel):
                continue
            if var:
                verdict = "UNKNOWN"
                why.append(f"{wfname}: variable path")
                continue
            a = admits(expr, marks)
            if a is None:
                verdict = "UNKNOWN"
                why.append(f"{wfname}: unparsed -m {expr!r}")
            elif a:
                verdict = "REACHABLE"
                break
            else:
                why.append(f"{wfname}: -m {expr!r} excludes {sorted(marks)}")
        if verdict == "REACHABLE":
            reachable += 1
        elif verdict == "UNKNOWN":
            unknown.append((rel, sorted(marks), why))
        else:
            unreachable.append((rel, sorted(marks), why))

    for rel, marks, why in unreachable:
        print(f"⛔ UNREACHABLE  {rel}\n    markers: {marks}")
        for w in why[:3]:
            print(f"    {w}")
    for rel, marks, why in unknown:
        print(f"⚠ UNKNOWN-PATH {rel}  markers: {marks}")

    print(f"\n{len(tests)} test file(s), {len(invs)} pytest invocation(s) across {len(wf)} "
          f"workflow(s): {reachable} reachable, {len(unreachable)} UNREACHABLE, "
          f"{len(unknown)} unknown.", file=sys.stderr)
    print("⚠ UNKNOWN is counted in neither column — a shell-variable path cannot be resolved "
          "statically, and deciding it either way would overstate the evidence.",
          file=sys.stderr)
    return 1 if unreachable else 0


def self_test():
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        wfd = os.path.join(td, ".github", "workflows"); os.makedirs(wfd)
        os.makedirs(os.path.join(td, "tests"))
        # the real shape: one selector excluding `network` over tests/, one variable path
        open(os.path.join(wfd, "ci.yml"), "w").write(
            "jobs:\n  a:\n    steps:\n      - run: |\n"
            "          pytest compiler/tests/ tests/ \\\n"
            "            -n 4 \\\n"
            '            -m "not e2e and not network" \\\n'
            "            --timeout=60\n")
        open(os.path.join(td, "tests", "test_marked.py"), "w").write(
            "import pytest\npytestmark = pytest.mark.network\n\ndef test_a():\n    pass\n")
        open(os.path.join(td, "tests", "test_plain.py"), "w").write(
            "def test_b():\n    pass\n")
        open(os.path.join(td, "tests", "test_decorated.py"), "w").write(
            "import pytest\n\n@pytest.mark.network\ndef test_c():\n    pass\n")

        text = open(os.path.join(wfd, "ci.yml")).read()
        invs = invocations(text)
        ok &= _c("unfolds a 4-line invocation into one", len(invs), 1)
        paths, expr, var = invs[0]
        ok &= _c("paths recovered", paths, ["compiler/tests/", "tests/"])
        ok &= _c("marker expression recovered", expr, "not e2e and not network")
        ok &= _c("no variable path here", var, False)

        ok &= _c("module marker read", module_markers(os.path.join(td, "tests", "test_marked.py")),
                 {"network"})
        ok &= _c("DECORATOR is not a module marker",
                 module_markers(os.path.join(td, "tests", "test_decorated.py")), set())

        ok &= _c("excluded marker is not admitted", admits(expr, {"network"}), False)
        ok &= _c("unmarked file is admitted", admits(expr, set()), True)
        ok &= _c("path coverage", covers(paths, "tests/test_marked.py"), True)
        ok &= _c("path miss", covers(paths, "other/test_x.py"), False)

        # ⛔ Control on the control: a variable path must NOT resolve to a verdict.
        open(os.path.join(wfd, "loop.yml"), "w").write(
            'jobs:\n  b:\n    steps:\n      - run: pytest "${testfile}" -m "not e2e"\n')
        _p, _e, v = invocations(open(os.path.join(wfd, "loop.yml")).read())[0]
        ok &= _c("variable path detected", v, True)

    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


def _c(name, got, want):
    good = got == want
    print(f"  {'ok  ' if good else 'FAIL'} {name}: got {got!r} want {want!r}")
    return good


if __name__ == "__main__":
    sys.exit(main())
