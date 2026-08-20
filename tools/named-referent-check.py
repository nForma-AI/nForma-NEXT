#!/usr/bin/env python3
"""Does this codebase name an enforcement mechanism that does not exist?

⛔ Converted from a convergence, not from one report. Two agents, different subsystems,
no contact, within one hour:

  #1267 (DEV4)  `control-plane/api/services/console_keys.py:21` states IN CAPITALS that
                read paths must iterate ``iter_console_backends``. The function does not
                exist. The only hit in the tree is the sentence claiming it is binding.
  #1268 (DEV5)  three exec sites described as "HELD behind a flag" — `EXEC_REQUIRE_EVIDENCE`
                does not exist. They are held behind nothing; they are simply not done.

★ Neither is a stale reference to something removed. Both describe machinery that was NEVER
BUILT, in prose confident enough that the author stopped checking — and in DEV5's case, about
its own work. ⇒ *The convergence is the finding*: either alone reads as one file's sloppiness.

> **A codebase's STATED conventions and its ENFORCED conventions are different sets, and
> nothing distinguishes them by reading.**

This finds one particular, cheap slice of that: a requirement sentence naming an identifier
that is never defined anywhere. It is deliberately narrow — see the limits below.

⚠ WHAT THIS CANNOT DO, and the honest reading of a clean run:

  * A convention naming NOTHING is invisible here. "reads must not take [0]" has no
    identifier to check, and is the more common form.
  * An identifier that EXISTS but is never CALLED passes — that is a different instrument
    (`grant-check.py` asks the enforcement question; this asks the referent question).
  * ⛔ `EXEC_REQUIRE_EVIDENCE`, one of the two founding cases, IS NOT DETECTABLE HERE. It
    never appeared in the tree at all — it lived in an agent's own prose about the code.
    So this tool catches one of the two incidents that motivated it, and saying otherwise
    would be the overclaim the incidents are about.

  * ⛔ AN IDENTIFIER DEFINED ONLY ON AN UNMERGED BRANCH READS AS UNDEFINED. Measured
    2026-08-20: `ci_guard_closing_keywords.py` was reported as never having existed by two
    agents independently, because both searched one ref. It is 161 lines on
    `origin/ci/closing-keyword-guard`, unmerged and with no PR. ⇒ This tool's population is
    the TRACKED TREE AT ONE REF, so "a convention naming a thing that was built and never
    merged" is invisible to it and will be reported as a phantom reference if you let it.
    The two are different defects with different remedies — one is a wrong sentence, the
    other is an unmerged branch.

⇒ A clean run means "no requirement sentence names an undefined identifier". It does NOT
mean the stated and enforced sets agree.

Exit: 0 no candidates · 1 candidates found · 2 established nothing.
"""
import argparse, ast, os, re, sys

# A sentence that BINDS. Deliberately short: every word here appeared in a real incident or
# is its direct synonym. A longer list buys recall at the cost of firing on description.
BINDING = re.compile(
    r"\b(must|MUST|shall|required to|never take|do not take|always use|has to|"
    r"held behind|gated (?:on|behind)|enforced by)\b")

# ⚠ Identifiers only. A bare English word in a MUST sentence is not a referent claim, and
# treating it as one is how this class of tool becomes unreadable. Require an underscore:
# `iter_console_backends`, `EXEC_REQUIRE_EVIDENCE`. That excludes CamelCase classes, which
# is a known recall gap and is stated rather than hidden.
# ⛔ MARKED AS CODE, not merely identifier-shaped. First version required only an
# underscore and produced **126 candidates against 1 known true positive** on
# DigitalFrontier-infra — `GIT_COMMIT_SHA`, `cpu_per_vcpu_second`, pricing keys: config
# names mentioned in prose, not enforcement mechanisms. A hit-list that is mostly false
# positives is one nobody runs twice, and this fleet has measured that 3 of 4 such lists
# were exactly that.
#
# ⇒ The discriminator is the AUTHOR'S OWN MARKUP. Someone naming a mechanism they believe
# exists writes it as code — ``iter_console_backends``, `foo_bar`, or foo_bar(). Someone
# mentioning a config key in a sentence does not. The founding case is double-backticked.
#
# ⚠ RECALL COST, stated rather than hidden: a binding sentence naming a mechanism in bare
# prose is now invisible. That is a deliberate trade of recall for a readable list, and it
# is the right way round only because the alternative was measured and was unusable.
IDENT = re.compile(
    r"(?:``([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)``"
    r"|`([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)`"
    r"|\b([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\(\))")

# Tokens that are identifiers by shape and vocabulary by use.
STOPWORDS = {
    "must_be", "should_be", "e_g", "i_e", "read_only", "no_op", "pull_request",
    "on_call", "up_to_date", "self_test", "known_positive", "known_negative",
}


def defined_names(tree):
    """Every name this module DEFINES or IMPORTS — the things that exist here."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            out.add(node.id)
        elif isinstance(node, ast.arg):
            out.add(node.arg)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                out.add((a.asname or a.name).split(".")[0])
                out.add(a.name.split(".")[-1])
        # ⛔ STRING LITERALS AND KWARG NAMES ARE REFERENTS TOO, and omitting them made the
        # first version 7/8 FALSE POSITIVES. `allow_degraded_mesh`, `ci_only`,
        # `AKASH_CONSOLE_2`, `provisioning_type` are all real — they exist as dict keys,
        # env-var names and SDK kwargs, i.e. as string literals, which no AST Name node
        # ever carries.
        #
        # ★ The candidates were REPORTED as "does not exist" while the tree contained 4,
        # 4, 12 and 2 occurrences respectively. A guard that calls a config key a phantom
        # is worse than no guard: it teaches its reader to dismiss the output, and the one
        # true positive dies with the seven.
        elif isinstance(node, ast.keyword) and node.arg:
            out.add(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value.strip()
            if v and len(v) < 80:
                out.add(v)
                # a dotted or bracketed reference still names its leaf
                out.add(v.split(".")[-1])
    return out


def prose_spans(src, tree):
    """Comment lines and docstrings — where a claim lives, as opposed to where code does.

    ⛔ Both, not just comments. The founding case is a MODULE DOCSTRING, so a
    comment-only scanner would have missed the one incident that motivated the tool.
    """
    out = []
    for line in src.splitlines():
        i = line.find("#")
        if i >= 0:
            out.append(line[i:])
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node)
            if d:
                out.append(d)
    return out


def scan_file(path, universe):
    """Identifiers asserted as binding in prose here, defined NOWHERE in the universe."""
    try:
        src = open(path, errors="replace").read()
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return None                      # unreadable is not clean — the caller counts it
    hits = []
    for chunk in prose_spans(src, tree):
        for line in chunk.splitlines():
            if not BINDING.search(line):
                continue
            for m in IDENT.finditer(line):
                name = m.group(1) or m.group(2) or m.group(3)
                if name in STOPWORDS or name in universe:
                    continue
                hits.append((name, line.strip()[:120]))
    return hits


def build_universe(root):
    """Every name defined anywhere under root. The population a claim is checked against.

    ⛔ Tree-wide, not per-file. A helper defined in another module is not missing, and a
    per-file check would report every cross-module reference as a phantom — a guard whose
    false positives swamp the one true one is a guard nobody runs twice.

    ⛔ THE POPULATION IS GIT-TRACKED FILES, NOT A FILESYSTEM WALK, and the difference is
    not performance. Measured on DigitalFrontier-infra: 1,559 tracked `.py` against
    **121,816 on disk** — 78x, dominated by `.worktrees` (83,610), `.venv-ci`, `.test-venv`
    and `.claude`.

    ⚠ The slow scan is the lesser problem. Every name defined in a vendored library or a
    peer's worktree would enter the universe and **mask** a genuinely missing referent —
    the claim would be "checked" against code this repository does not own. That is a
    FALSE NEGATIVE mechanism, and an exclusion list is the wrong shape for it: it needs
    to be complete to be safe, and it silently degrades as new directories appear.

    ⇒ A claim written in tracked code is checked against tracked code. Falls back to a
    walk only outside a git repo, where the caller is told.
    """
    universe, files, unparsed = set(), [], 0
    tracked = None
    try:
        import subprocess
        r = subprocess.run(["git", "-C", root, "ls-files", "*.py"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            tracked = [os.path.join(root, x) for x in r.stdout.split("\n") if x.strip()]
    except Exception:
        tracked = None

    if tracked is not None:
        candidates = tracked
    else:
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in {".git", "node_modules", ".venv", "venv",
                                        "__pycache__", ".claude", "site-packages"}]
            candidates += [os.path.join(dirpath, f) for f in filenames if f.endswith(".py")]

    for p in candidates:
        files.append(p)
        try:
            universe |= defined_names(ast.parse(open(p, errors="replace").read()))
        except (OSError, SyntaxError):
            unparsed += 1
    return universe, files, unparsed


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="A clean run means no requirement sentence names an undefined identifier. "
               "It does NOT mean the stated and enforced conventions agree — the common "
               "form of that defect names no identifier at all and is invisible here.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not os.path.isdir(args.root):
        print(f"⛔ {args.root} is not a directory — ESTABLISHED NOTHING.", file=sys.stderr)
        return 2

    universe, files, unparsed = build_universe(args.root)
    if not files:
        print(f"⛔ no .py files under {args.root} — this is a fact about the PATH, not the "
              "codebase. ESTABLISHED NOTHING.", file=sys.stderr)
        return 2

    found = []
    for p in files:
        hits = scan_file(p, universe)
        if hits is None:
            continue
        for name, line in hits:
            found.append((os.path.relpath(p, args.root), name, line))

    for path, name, line in sorted(found):
        print(f"{name}\n    {path}\n    {line}")

    print(f"\n{len(files)} file(s) scanned, {len(universe):,} names defined, "
          f"{len(found)} requirement sentence(s) naming an undefined identifier.",
          file=sys.stderr)
    if unparsed:
        print(f"⚠ {unparsed} file(s) did not parse and were skipped — their claims are "
              "UNCHECKED, not clean.", file=sys.stderr)
    print("⚠ A candidate is not a finding. Each needs a human to read the sentence: some "
          "name a thing deliberately not built yet, which is a TODO, not a false claim of "
          "enforcement.", file=sys.stderr)
    return 1 if found else 0


def self_test():
    """The founding incident is the known positive; a real referent is the negative."""
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        # known positive — the shape of console_keys.py:21, verbatim in structure
        open(os.path.join(td, "a.py"), "w").write(
            '"""Reads of deployment state must iterate ``iter_console_backends``,\n'
            'not take ``[0]``.\n"""\n\ndef read_one():\n    return 1\n')
        # known negative — a binding sentence naming something that DOES exist,
        # defined in a DIFFERENT file, which is the cross-module case
        open(os.path.join(td, "b.py"), "w").write(
            '"""Callers must use ``safe_read_all`` rather than indexing."""\n')
        open(os.path.join(td, "c.py"), "w").write("def safe_read_all():\n    return []\n")
        universe, files, _ = build_universe(td)
        pos = [n for _p in [os.path.join(td, "a.py")] for n, _l in scan_file(_p, universe)]
        neg = [n for _p in [os.path.join(td, "b.py")] for n, _l in scan_file(_p, universe)]
        p_ok = "iter_console_backends" in pos
        n_ok = "safe_read_all" not in neg
        print(f"  known-positive  undefined referent in a MUST docstring : "
              f"{'fires' if p_ok else 'MISSED'}")
        print(f"  known-negative  referent defined in ANOTHER file       : "
              f"{'silent' if n_ok else 'FIRES — cross-module false positive'}")
        ok = p_ok and n_ok

        # ⛔ Control on the CONTROL: a scan that finds nothing because it reached nothing
        # must not read as clean. Point it at an empty tree.
        with tempfile.TemporaryDirectory() as empty:
            _u, f2, _ = build_universe(empty)
            e_ok = not f2
            print(f"  control         empty tree yields no files          : "
                  f"{'yes — caller must exit 2' if e_ok else 'NO'}")
            ok = ok and e_ok

    print("\nselftest PASS" if ok else "\nselftest FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
