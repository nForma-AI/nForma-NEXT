#!/usr/bin/env python3
"""Does this file CALL `<pattern>`, or does it merely TALK ABOUT calling it?

⛔ THE DEFECT (#36), and the sub-class that makes it worse over time.

A grep for a command finds every sentence discussing that command. Measured, in a
sweep the author wrote minutes after working on this exact class:

    tools/stranded-branches.py:258   print(f"⛔ TRUNCATED SWEEP — `gh pr list` …")
    tools/test_wake_yield.py:62      bash("gh api … --method POST -f body=hi")

Both flagged as unbounded `gh` calls. Neither is a call.

★ AND THE FIRST ONE TRIPPED THE SWEEP *BECAUSE IT HANDLES THE DEFECT CORRECTLY*.
Its warning text must contain the pattern it warns about. ⇒ So a "does this code
handle X" scan gets WORSE as more code handles X properly: the better the estate,
the noisier the scan, and the noise concentrates in exactly the files that are
already correct.

    > THE POPULATION OF FALSE POSITIVES IS CREATED BY THE REMEDY.

That is why this class does not decay as the repository improves — it GROWS, and
the growth is proportional to how much of the estate is already right.

★ THE DISCRIMINATOR: RESOLVE THE SINK, DO NOT MATCH THE TEXT.

A mention cannot flow into an execution sink. So the question is never "does this
line contain the pattern" but "does this string reach something that RUNS it":

    sh("gh", "pr", "list", …)  ->  def sh(*args): subprocess.run(args, …)   CALL
    bash("gh api …")           ->  def bash(c): wake_yield.classify(…)      MENTION
    print(f"… `gh pr list` …") ->  print reaches no sink                    MENTION

⚠ NOTE THE MIDDLE ROW. Both FP2 and the real call pass a string to a LOCAL
WRAPPER. "String into a local function ⇒ indeterminate" would have classified the
REAL call as indeterminate — the under-report direction, which is safe for "did
this file comply" and unsafe for "how widespread is this", and #20's content is a
rate. So the wrapper must be RESOLVED, not avoided.

⛔ EXEC_SINKS IS A CLOSED SET DEFINED BY THE STANDARD LIBRARY, not an open list of
program names. That distinction is what keeps this from being the blocklist the
position rule refused elsewhere: `subprocess.run` executes because Python says so;
`bash` executes or does not depending on who wrote it.

⚠ BOUND, STATED: resolution is a FIXPOINT over FILE-LOCAL call edges. A chain of
wrappers inside one file resolves exactly. A wrapper whose callee is imported, or
reached through an attribute, is UNRESOLVABLE and reads INDETERMINATE — never
CALL and never MENTION. ⛔ The first version resolved ONE level and called an
unresolved chain a MENTION, which asserts "reaches no sink" about a chain that
reaches one. Its own control caught it.

⚠ AND IT IS PYTHON-ONLY. A shell script or a Markdown file cannot be parsed here
and returns VOID for that file — not "no calls found". An unparsed file is
ESTABLISHED NOTHING.

★ REACHABILITY IS A DESIGN CONSTRAINT, NOT A NICETY. A discriminator harder to
reach than `grep` loses to `grep` every time. So the interface is grep's:

    use-not-mention.py 'gh pr list' tools/*.py

Exit: 0 no CALL found · 1 at least one CALL · 2 ESTABLISHED NOTHING (nothing
      parsed) · 3 the known-positive control failed.
"""
import ast, sys

# Defined by the standard library. `subprocess.run` executes because Python says
# so — this is a specification, not a naming convention.
EXEC_SINKS = {
    ("subprocess", "run"), ("subprocess", "call"), ("subprocess", "check_call"),
    ("subprocess", "check_output"), ("subprocess", "Popen"),
    ("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "execvp"),
    ("os", "spawnv"), ("os", "spawnvp"),
}


def dotted(node):
    """`subprocess.run` -> ("subprocess","run"); `sh` -> (None,"sh")."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return (node.value.id, node.attr)
    if isinstance(node, ast.Name):
        return (None, node.id)
    return (None, None)


def local_calls(fn):
    """(names of local-looking functions this body calls, calls it cannot resolve)."""
    named, unresolved = set(), False
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call):
            continue
        mod, name = dotted(n.func)
        if (mod, name) in EXEC_SINKS:
            continue                       # handled by sink_reaching
        if mod is None and name:
            named.add(name)
        else:
            unresolved = True              # an attribute call we cannot follow
    return named, unresolved


def resolve_locals(tree):
    """Transitive sink-reachability over local functions. (reaches, unresolvable).

    ⛔ NOT a one-level walk. The first version resolved one level and classified
    `outer -> inner -> subprocess.run` as MENTION — a verdict asserting "reaches no
    execution sink" about a chain that reaches one. ⚠ That is the UNDER-REPORT
    direction: safe for "did this file comply", unsafe for "how widespread is
    this", and a rate is what this class is measured in. Caught by its own control,
    which is why the control exists.

    A fixpoint is exact for file-local chains and costs a few lines, so the bound
    the docstring used to state is gone rather than documented.
    """
    fns = {f.name: f for f in ast.walk(tree)
           if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
    reaches, unresolvable = set(), set()
    for name, fn in fns.items():
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and dotted(n.func) in EXEC_SINKS:
                reaches.add(name)
                break
    changed = True
    while changed:                          # fixpoint over local call edges
        changed = False
        for name, fn in fns.items():
            if name in reaches:
                continue
            called, _ = local_calls(fn)
            if called & reaches:
                reaches.add(name)
                changed = True
    for name, fn in fns.items():
        if name in reaches:
            continue
        called, unresolved = local_calls(fn)
        # Unknown callee, or a callee that is itself unresolvable, means this
        # function's sink-reachability is UNKNOWN — never "no".
        if unresolved or (called - set(fns)):
            unresolvable.add(name)
    changed = True
    while changed:
        changed = False
        for name, fn in fns.items():
            if name in reaches or name in unresolvable:
                continue
            called, _ = local_calls(fn)
            if called & unresolvable:
                unresolvable.add(name)
                changed = True
    return reaches, unresolvable


def strings_in(node):
    """Literal text carried by this node, including f-string literal parts."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    return out


def classify_file(path, pattern):
    """[(lineno, verdict, why, excerpt)] or None if the file could not be parsed."""
    try:
        src = open(path, errors="replace").read()
        tree = ast.parse(src)
    except Exception:
        return None
    locals_with_sink, locals_unresolvable = resolve_locals(tree)
    lines = src.splitlines()
    found, seen = [], set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        args_text = " ".join(t for a in node.args for t in strings_in(a))
        if pattern not in args_text:
            continue
        mod, name = dotted(node.func)
        ln = getattr(node, "lineno", 0)
        if (ln, name) in seen:
            continue
        seen.add((ln, name))
        excerpt = lines[ln - 1].strip()[:70] if 0 < ln <= len(lines) else ""
        if (mod, name) in EXEC_SINKS:
            found.append((ln, "CALL", f"argument of {mod}.{name} — a stdlib execution sink", excerpt))
        elif mod is None and name in locals_with_sink:
            found.append((ln, "CALL", f"argument of local {name}() which reaches a stdlib sink", excerpt))
        elif mod is None and name in locals_unresolvable:
            found.append((ln, "INDETERMINATE",
                          f"argument of local {name}() whose sink-reachability could not be "
                          f"resolved — UNKNOWN, not 'no sink'", excerpt))
        elif mod is None and name in {"print", "repr", "format"}:
            found.append((ln, "MENTION", f"argument of {name}() — reaches no execution sink", excerpt))
        elif mod is None and any(isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == name
                                 for f in ast.walk(tree)):
            found.append((ln, "MENTION", f"argument of local {name}() which reaches no execution sink", excerpt))
        else:
            found.append((ln, "INDETERMINATE",
                          f"argument of {('.'.join(x for x in (mod, name) if x)) or '?'}() — not "
                          f"resolvable to a sink in one level", excerpt))
    # Text carrying the pattern that is NOT an argument to any call is a mention
    # by construction: a docstring, a module constant, a bare literal.
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and pattern in node.value:
            ln = getattr(node, "lineno", 0)
            if not any(f[0] == ln for f in found):
                found.append((ln, "MENTION", "a literal that is not an argument to any call", ""))
    return sorted(found)


# ⚠ One line can carry nested calls — `check(name, bash("gh api …"))` reports twice.
# Keep the STRONGEST verdict per line: a line containing a real call is a call,
# whatever else surrounds it. Collapsing the other way would under-report.
RANK = {"CALL": 3, "INDETERMINATE": 2, "MENTION": 1}


def strongest_per_line(rows):
    best = {}
    for ln, v, why, ex in rows:
        if ln not in best or RANK[v] > RANK[best[ln][1]]:
            best[ln] = (ln, v, why, ex)
    return [best[k] for k in sorted(best)]


def self_test():
    """⛔ FIXTURES, NOT THE LIVE TREE. The live tree is homogeneous and a predicate
    validated on a homogeneous sample has been validated on the sample's
    homogeneity (DX, #16). These are built to differ in exactly one property."""
    import os, tempfile
    tmp = tempfile.mkdtemp(prefix="uvm-")

    call_src = ('import subprocess\n'
                'def sh(*a):\n    return subprocess.run(a)\n'
                'sh("gh", "pr", "list", "--state", "merged")\n')
    mention_src = ('def classify(c):\n    return len(c)\n'
                   'def bash(c):\n    return classify(c)\n'
                   'print("warning: gh pr list may truncate")\n'
                   'bash("gh pr list --limit 1")\n')
    direct_src = 'import subprocess\nsubprocess.run("gh pr list", shell=True)\n'
    deep_src = ('import subprocess\n'
                'def inner(*a):\n    return subprocess.run(a)\n'
                'def outer(*a):\n    return inner(*a)\n'
                'outer("gh", "pr", "list")\n')

    paths = {}
    for name, src in [("call", call_src), ("mention", mention_src),
                      ("direct", direct_src), ("deep", deep_src)]:
        p = os.path.join(tmp, f"{name}.py")
        open(p, "w").write(src)
        paths[name] = p

    def verdicts(p):
        return [v for _, v, _, _ in strongest_per_line(classify_file(p, "gh pr list") or [])]

    ok = True
    checks = [
        ("known-positive", "a real call through a local wrapper", "call", "CALL", True),
        ("known-positive", "a direct stdlib sink call", "direct", "CALL", True),
        ("known-negative", "print() + a wrapper reaching no sink", "mention", "CALL", False),
        ("known-positive", "TWO levels of wrapper, resolved by fixpoint", "deep", "CALL", True),
    ]
    for kind, label, key, want, present in checks:
        vs = verdicts(paths[key])
        good = (want in vs) == present
        ok = ok and good
        print(f"  {kind}  {'✅' if good else '⛔'} {want if present else 'no ' + want:<16} {label}")

    # ⛔ The VOID. A file this parser cannot read is not a file with no calls.
    bad = os.path.join(tmp, "notpython.sh")
    open(bad, "w").write('gh pr list --limit 1\n')
    ok_void = classify_file(bad, "gh pr list") is None
    print(f"  known-positive  {'✅' if ok_void else '⛔'} VOID             "
          f"an unparseable file — established nothing, not 'no calls'")
    ok = ok and ok_void

    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 3


def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("usage: use-not-mention.py '<pattern>' <file.py> [file.py …]", file=sys.stderr)
        return 2
    pattern, files = args[0], args[1:]
    calls = parsed = 0
    void = []
    for f in files:
        rows = classify_file(f, pattern)
        if rows is None:
            void.append(f)
            continue
        parsed += 1
        for ln, v, why, ex in strongest_per_line(rows):
            calls += v == "CALL"
            print(f"  {v:<14} {f}:{ln}  {why}")
            if ex:
                print(f"                 {ex}")
    if void:
        print(f"⛔ NOT PARSED (Python only) — established nothing about these, NOT 'no calls': "
              f"{', '.join(void)}", file=sys.stderr)
    if not parsed:
        print("⛔ nothing parsed — ESTABLISHED NOTHING.", file=sys.stderr)
        return 2
    print(f"\n{calls} CALL(s) across {parsed} parsed file(s). "
          f"MENTION means the string reaches no execution sink.", file=sys.stderr)
    print("⚠ Resolution is a fixpoint over FILE-LOCAL call edges. A callee that is imported "
          "or reached through an attribute is UNRESOLVABLE and reads INDETERMINATE — never "
          "MENTION.", file=sys.stderr)
    return 1 if calls else 0


if __name__ == "__main__":
    sys.exit(main())
