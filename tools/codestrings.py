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
