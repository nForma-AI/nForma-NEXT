#!/usr/bin/env python3
"""Is this tool's control a CONTROL, or has it only ever passed?

#26's acceptance test, mechanised: sabotage the tool, re-run its control, and see whether
the control notices. A control that has never been shown to fail is not a control.

⛔ THE FAILURE MODE THIS TOOL EXISTS TO AVOID, and it is measured, not hypothetical:
   a sabotaged copy that CRASHES exits non-zero, and a probe scoring `exit != 0` reads that
   as "the control detected it". Two published #26 figures were artifacts of exactly this.
   ⇒ So a mutant whose control dies on a Traceback is reported VOID, never DETECTED.

⛔ AND IT MUTATES THE ANALYSER, NOT THE DISPATCH. Inverting comparisons inside main() breaks
   argument handling, so the mutant never reaches the cases at all — which is the same
   artifact one layer up. Functions named main/dispatch/cli, and module scope, are left alone.

Exit codes:
  0  every tool examined has at least one MUTANT ITS CONTROL CAUGHT  (control demonstrated)
  1  at least one control is DECORATIVE — it passed every mutant
  2  ESTABLISHED NOTHING — no tool could be examined, or no mutant was viable
     ⚠ 2 is NOT "all clear". It is the absence of a measurement.
"""
import argparse, ast, os, shutil, subprocess, sys, tempfile

DISPATCH = {"main", "dispatch", "cli", "_main", "run_cli"}
INVERT = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt,
          ast.Gt: ast.LtE, ast.LtE: ast.Gt, ast.In: ast.NotIn, ast.NotIn: ast.In,
          ast.Is: ast.IsNot, ast.IsNot: ast.Is}


class Sites(ast.NodeVisitor):
    """Every comparison inside a non-dispatch function. Module scope is excluded too:
    a constant defined at import time is configuration, not analysis."""
    def __init__(self):
        self.sites, self.fn = [], None

    def visit_FunctionDef(self, node):
        outer, self.fn = self.fn, node.name
        self.generic_visit(node)
        self.fn = outer

    def visit_Compare(self, node):
        if self.fn and self.fn not in DISPATCH:
            for i, op in enumerate(node.ops):
                if type(op) in INVERT:
                    self.sites.append((node.lineno, node.col_offset, i, self.fn))
        self.generic_visit(node)


class Flip(ast.NodeTransformer):
    def __init__(self, target):
        self.target, self.fn = target, None

    def visit_FunctionDef(self, node):
        outer, self.fn = self.fn, node.name
        self.generic_visit(node)
        self.fn = outer
        return node

    def visit_Compare(self, node):
        for i, op in enumerate(node.ops):
            key = (node.lineno, node.col_offset, i, self.fn)
            if key == self.target and type(op) in INVERT:
                node.ops[i] = INVERT[type(op)]()
        return node


def mutants(src, limit):
    tree = ast.parse(src)
    s = Sites(); s.visit(tree)
    for site in s.sites[:limit]:
        t = Flip(site); m = t.visit(ast.parse(src))
        yield site, ast.unparse(ast.fix_missing_locations(m))


def run(cmd, cwd):
    """⚠ Read exit status directly. `$?` after a pipe is the pipe's, not the program's —
    the whole answer space collapses to {0} and every verdict reads the same.

    ⛔ AND DISABLE BYTECODE CACHING. Measured while writing this: `ast.unparse` can emit a
    mutant with the SAME BYTE LENGTH as the original, and CPython invalidates a `.pyc` on
    (mtime, size). Written inside the same second, the mutant is never compiled — the
    interpreter serves the ORIGINAL and every control scores DECORATIVE. The tool would have
    reported the whole board uncontrolled, confidently, having measured nothing."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for root, dirs, _ in os.walk(cwd):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120, env=env)
    return p.returncode, (p.stdout + p.stderr)


def examine(tool, control, sandbox, limit):
    src = open(os.path.join(sandbox, tool)).read()
    base_rc, base_out = run([sys.executable, control], sandbox)
    if base_rc != 0:
        return {"tool": tool, "verdict": "VOID", "why": f"control fails BEFORE mutation (exit {base_rc}) — nothing to compare against"}
    caught = passed = void = 0
    first = None
    for site, mutated in mutants(src, limit):
        path = os.path.join(sandbox, tool)
        open(path, "w").write(mutated)
        rc, out = run([sys.executable, control], sandbox)
        if "Traceback" in out:
            void += 1                      # ⛔ crashed, not detected
        elif rc != 0:
            caught += 1
            first = first or f"{site[3]}() line {site[0]}"
        else:
            passed += 1
        open(path, "w").write(src)         # restore before the next mutant
    total = caught + passed + void
    if total == 0:
        return {"tool": tool, "verdict": "VOID", "why": "no viable mutation site outside dispatch"}
    if caught == 0 and passed == 0:
        return {"tool": tool, "verdict": "VOID", "why": f"every mutant crashed ({void}) — establishes nothing"}
    v = "CONTROL" if caught else "DECORATIVE"
    return {"tool": tool, "verdict": v, "caught": caught, "passed": passed, "void": void,
            "total": total, "first": first}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", nargs="*", metavar="TOOL:CONTROL",
                    help="e.g. tools/discriminates.py:tools/test_discriminates.py")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--limit", type=int, default=12, help="mutants per tool")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if not a.pairs:
        print("⛔ no TOOL:CONTROL pair given — ESTABLISHED NOTHING.", file=sys.stderr)
        return 2

    sandbox = tempfile.mkdtemp(prefix="known-negative-")
    try:
        # ⚠ Pin the DIRECTORY, not the file. 8 of 26 tools import a sibling, and a
        # single-file pin dies on ImportError before the control ever runs. (DEV4)
        arch = subprocess.run(["git", "archive", a.ref, "tools/"], cwd=a.repo,
                              capture_output=True)
        if arch.returncode != 0:
            print(f"⛔ cannot pin {a.ref} — ESTABLISHED NOTHING.", file=sys.stderr)
            return 2
        subprocess.run(["tar", "-x", "-C", sandbox], input=arch.stdout, check=True)

        rows, decorative, examined = [], 0, 0
        for pair in a.pairs:
            tool, _, control = pair.partition(":")
            if not control or not os.path.exists(os.path.join(sandbox, tool)):
                rows.append({"tool": tool, "verdict": "VOID", "why": "tool or control not at this ref"})
                continue
            r = examine(tool, control, sandbox, a.limit)
            rows.append(r)
            if r["verdict"] != "VOID":
                examined += 1
                decorative += r["verdict"] == "DECORATIVE"

        print(f"known-negative sweep @ {a.ref}   {a.limit} mutants/tool max\n")
        for r in rows:
            if r["verdict"] == "VOID":
                print(f"  ⛔ VOID        {r['tool']:<34} {r['why']}")
            elif r["verdict"] == "CONTROL":
                print(f"  ✅ CONTROL     {r['tool']:<34} caught {r['caught']}/{r['total']}"
                      f"  (first: {r['first']}; {r['void']} crashed, excluded)")
            else:
                print(f"  ⛔ DECORATIVE  {r['tool']:<34} passed all {r['passed']} viable"
                      f"  ({r['void']} crashed, excluded)")

        if account(len(a.pairs), examined, len(rows) - examined, decorative) == 2:
            return 2
        print("\n⛔ A crashed mutant is VOID, never a detection — non-zero exit from a Traceback is")
        print("   what a naive `exit != 0` probe reads as success. ⚠ Sites are comparison flips")
        print("   outside dispatch only: a control this misses may still catch other sabotage.")
        if examined == 0:
            return 2
        return 1 if decorative else 0
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def account(pairs_given, examined, void, decorative, out=sys.stdout):
    """#466: print the partition, keep the SUBSET off its line, and refuse if it does not sum.

    ⛔ `decorative` counts a PROPERTY OF the examined rows. Printing it as a fourth bucket invites
    the reader to add it in, which over-counts the population -- that is the defect this fixes.

    ⚠ AND AN HONEST BOUND ON THE ASSERTION ITSELF. On today's control flow it CANNOT FIRE: every
    pair appends exactly one row on both branches, so examined + void == pairs_given by
    construction. It guards a future edit -- a `continue` that skips the append -- and nothing
    else. ⇒ It is split into this function precisely so a caller CAN reach the failing state and
    demonstrate the check is not decoration. A first draft asserted it inline, where no test could
    reach it, which is the same mistake this file's own docstring records one function below.
    """
    print(f"\n  pairs given {pairs_given}", file=out)
    print(f"    examined {examined} · void {void}   ⇒ {examined + void}", file=out)
    print(f"    of the {examined} examined: decorative {decorative} · "
          f"demonstrated {examined - decorative}   ⚠ a SUBSET, not a third bucket", file=out)
    if examined + void != pairs_given:
        print(f"⛔ VOID — the buckets sum to {examined + void} against {pairs_given} pairs given."
              f" A sweep that cannot account for every pair has established nothing about the"
              f" ones it dropped.", file=out)
        return 2
    return 0


def self_test():
    """⚠ Both directions, and both by EXECUTION. An earlier draft of this function asserted
    that a dict literal it had just written equalled 'DECORATIVE' — a check with no reachable
    failing state, inside the tool built to find checks with no reachable failing state.
    Recorded rather than quietly deleted."""
    ok = True
    src = ("def analyse(n):\n"
           "    if n == 3:\n"
           "        return 'HIT'\n"
           "    return 'MISS'\n"
           "def main():\n"
           "    if len('x') == 1:\n"
           "        return 0\n")
    found = Sites(); found.visit(ast.parse(src))
    fns = {f for _, _, _, f in found.sites}
    if "main" in fns:
        print("⛔ FAIL: a comparison inside main() was offered as a mutation site"); ok = False
    if "analyse" not in fns:
        print("⛔ FAIL: the analyser's comparison was not found"); ok = False
    muts = list(mutants(src, 5))
    if not muts or "n != 3" not in muts[0][1]:
        print("⛔ FAIL: expected the analyser's comparison inverted"); ok = False

    # ⇒ Both verdicts reached by RUNNING examine() against synthetic tools, one whose control
    #   reads the analyser and one whose control ignores it.
    box = tempfile.mkdtemp(prefix="known-negative-selftest-")
    try:
        os.makedirs(os.path.join(box, "tools"), exist_ok=True)
        open(os.path.join(box, "tools", "subject.py"), "w").write(src)
        watching = ("import sys; sys.path.insert(0, 'tools')\n"
                    "import subject\n"
                    "sys.exit(0 if subject.analyse(3) == 'HIT' else 1)\n")
        blind = "import sys\nprint('all checks passed')\nsys.exit(0)\n"
        open(os.path.join(box, "tools", "t_watch.py"), "w").write(watching)
        open(os.path.join(box, "tools", "t_blind.py"), "w").write(blind)

        a = examine("tools/subject.py", "tools/t_watch.py", box, 5)
        if a["verdict"] != "CONTROL":
            print(f"⛔ FAIL: a control that reads the analyser scored {a['verdict']}, not CONTROL"); ok = False
        b = examine("tools/subject.py", "tools/t_blind.py", box, 5)
        if b["verdict"] != "DECORATIVE":
            print(f"⛔ FAIL: a control that ignores the analyser scored {b['verdict']}, not DECORATIVE"); ok = False
    finally:
        shutil.rmtree(box, ignore_errors=True)

    print("all checks passed" if ok else "⛔ self-test FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
