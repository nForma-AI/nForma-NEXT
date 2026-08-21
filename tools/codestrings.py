#!/usr/bin/env python3
"""String literals in EXECUTABLE position — not docstrings, not comments.

⛔ EXTRACTED FROM `scripts/check-tools-index.py`, NOT COPIED. DEVOPS wrote this and owns it;
it lives here so `tools/estate-provenance.py` can ask the same question without a second
implementation. Two guards disagreeing about the same file is worse than the gap either
fills, and a copy cannot inherit a correction (#78).

⚠ WHY IT EXISTS AT ALL. `estate-provenance.py` classified WHOLE FILE TEXT, so a docstring
that MENTIONS an estate scored identically to a line that USES one — in a tool whose entire
subject is use-vs-mention. Five of its seven self-trips were mentions.

⛔ THE DOCSTRING TEST IS BY NODE IDENTITY, NOT BY STRING, AND THAT IS LOAD-BEARING.
`ast.get_docstring()` returns a `cleandoc()`'d value while the `Constant` node holds the RAW
one, so comparing strings never matches and every docstring scores as executable. DEV2
shipped that exact predicate: 13 of 13, a discriminator that discriminated nothing. Hence
`clean=False` and `id(node.body[0].value)`. ⚠ Do not "simplify" either.

⚠ POSITION FILTERING IS `.py`-ONLY BY CONSTRUCTION. There is no executable position in
Markdown or JSON — a caller scanning `.md`/`.txt`/`.json` gets whole text and must SAY SO,
or a reader takes a clean prose scan for a position-filtered one.
"""
import ast
import re


def code_strings_from_source(src, suffix=".py"):
    """[str] in executable position. ⚠ A SyntaxError yields NO strings, which reads as CLEAN."""
    if suffix != ".py":
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


def code_strings(path):
    """Path-taking wrapper, so DEVOPS's call site is unchanged by the extraction.

    ⚠ A SyntaxError yields no strings, which reads as CLEAN. Stated rather than guarded:
    a file that will not parse is a defect the test suites own. It does mean quarantine
    cannot see inside an unparseable file.
    """
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return code_strings_from_source(src, path.suffix)


def _self_test():
    """Controls for the position filter itself. ⛔ Two-sided: it must EXCLUDE and INCLUDE."""
    src = ('"""module docstring naming estate-x"""\n'
           'import os\n'
           '# comment naming estate-y\n'
           'PATH = "executable-literal"\n'
           'def f():\n'
           '    """inner docstring naming estate-z"""\n'
           '    return "inner-literal"\n')
    got = code_strings_from_source(src, ".py")
    checks = {
        "executable literal INCLUDED": "executable-literal" in got,
        "inner literal INCLUDED": "inner-literal" in got,
        # ⛔ THE KNOWN-NEGATIVE. Without it the filter can stop excluding and every
        # docstring mention scores as a use, which is the defect it exists to prevent.
        "module docstring EXCLUDED": not any("estate-x" in g for g in got),
        "inner docstring EXCLUDED": not any("estate-z" in g for g in got),
        "comment EXCLUDED": not any("estate-y" in g for g in got),
        # A SyntaxError yields no strings, which reads as CLEAN — stated, not guarded.
        "unparseable yields nothing": code_strings_from_source("def (", ".py") == [],
        # Non-.py takes the coarse path and keeps whole lines.
        "shell path keeps lines": code_strings_from_source("echo hi # c\n", ".sh") == ["echo hi "],
    }
    for name, ok in checks.items():
        print("  %-4s %s" % ("PASS" if ok else "FAIL", name))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    import sys as _sys
    _args = [a for a in _sys.argv[1:] if a.startswith("-")]
    _unknown = [a for a in _args if a != "--self-test"]
    if _unknown:
        # ⛔ Equality over a known set. Membership accepts a flag without rejecting anything
        # else, so `--self-test --zzz` used to exit 0 and prove nothing (#321).
        print("⛔ VOID: unrecognised flag(s): %s. Known: --self-test" % ", ".join(_unknown),
              file=_sys.stderr)
        _sys.exit(2)
    if "--self-test" in _args:
        _sys.exit(_self_test())
    # ⚠ A bare run stays SILENT and exit 0, matching tools/runmarker.py. This is a module;
    # changing that would alter what scripts/exit-code-gate.sh sees for every module at once,
    # and that is DEVOPS's gate to re-scope, not mine to change from one file.
