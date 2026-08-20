#!/usr/bin/env python3
"""Exit-code contract for close-condition-scan.py.

⛔ `--self-test` covers CLASSIFICATION. It does not cover the three states that all
print a clean-looking zero unless they are separated: an empty board, a truncated
reading, and a broken control. Those are exactly the paths a caller reads as "all
clear", and they are what this file exercises.

★ Every case here drives the real `main()` with a stubbed `gh`, so the exit code
under test is the one the tool actually returns -- not a re-implementation of it.
"""
import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ccs", HERE / "close-condition-scan.py")
ccs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccs)


def issue(n, body="", comments=()):
    return {"number": n, "title": f"issue {n}", "body": body,
            "comments": [{"body": c} for c in comments], "labels": []}


def run(argv, total, issues):
    """Drive main() with gh stubbed. Returns (exit code, stdout, stderr)."""
    def fake_gh(args):
        if args[:2] == ["api", "-X"]:
            return f"{total}\n"
        return json.dumps(issues)
    real_gh, real_argv = ccs.gh, sys.argv
    ccs.gh = fake_gh
    sys.argv = ["close-condition-scan.py"] + argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = ccs.main()
    finally:
        ccs.gh, sys.argv = real_gh, real_argv
    return code, out.getvalue(), err.getvalue()


class ExitContract(unittest.TestCase):

    def test_clean_board_is_zero(self):
        code, out, _ = run([], 2, [issue(1, "## Done when\nx"),
                                   issue(2, "**Closes when** y")])
        self.assertEqual(code, 0, out)

    def test_a_missing_condition_is_a_finding(self):
        code, _, err = run([], 2, [issue(1, "## Done when\nx"), issue(2, "nothing")])
        self.assertEqual(code, 1)
        self.assertIn("NFORMA-RESULT FINDINGS", err)

    def test_buried_is_a_finding_not_a_pass(self):
        """⛔ The case the tool exists for. A condition that exists ONLY in a comment
        must not exit 0 -- a body-reader cannot see it."""
        code, out, _ = run([], 1, [issue(1, "no clause", ["## Done when\nx"])])
        self.assertEqual(code, 1, out)
        self.assertIn("BURIED", out)

    def test_empty_board_is_void_not_clean(self):
        """⚠ Zero open issues is what a MISTYPED LABEL returns. `gh issue list
        --label <nonexistent>` exits 0 with zero bytes on stdout and stderr, which is
        byte-identical to an empty queue. It must never read as 'all conditions
        present'."""
        code, _, err = run([], 0, [])
        self.assertEqual(code, 2)
        self.assertIn("NFORMA-RESULT ESTABLISHED-NOTHING", err)

    def test_truncated_reading_is_void_not_clean(self):
        """The stated population is 9; we received 1, and it happens to be clean.
        A verdict here would be a clean answer about a set never seen."""
        code, _, err = run([], 9, [issue(1, "## Done when\nx")])
        self.assertEqual(code, 2)
        self.assertIn("NFORMA-RESULT TRUNCATED", err)

    def test_gh_failure_is_void_not_clean(self):
        def boom(args):
            raise ccs.Void("gh exited 1: could not resolve to a Repository")
        real = ccs.gh
        ccs.gh = boom
        sys.argv = ["x"]
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = ccs.main()
        finally:
            ccs.gh = real
        self.assertEqual(code, 2)
        # ⚠ `.getvalue()`, not `err`. `assertIn(needle, StringIO)` does NOT raise:
        # StringIO iterates over LINES, so Python compares the needle to each line and
        # quietly returns False. It fails loudly only when the needle is not a whole
        # line — had stderr been exactly this string, the assertion would have PASSED
        # for the wrong reason. Caught by this suite on its first run.
        self.assertIn("ESTABLISHED NOTHING", err.getvalue())

    def test_broken_control_refuses_to_scan(self):
        """⛔ KNOWN-POSITIVE. If the classifier is broken, the tool must exit 3 and
        produce NO verdict -- a broken classifier that still reports findings is
        worse than one that crashes, because the findings look like data."""
        import re
        real = ccs.CONDITION
        ccs.CONDITION = re.compile(r"done when", re.IGNORECASE)   # naive: mention==use
        try:
            code, _, err = run([], 2, [issue(1, "nothing"), issue(2, "nothing")])
        finally:
            ccs.CONDITION = real
        self.assertEqual(code, 3)
        self.assertIn("NFORMA-RESULT CONTROL-FAILED", err)

    def test_self_test_control_is_sharp(self):
        """The negative control must FAIL on a plausible wrong implementation.
        A control that passes either way is decoration (#26)."""
        import re
        real = ccs.CONDITION
        ccs.CONDITION = re.compile(r"done when|completion condition", re.IGNORECASE)
        try:
            with redirect_stdout(io.StringIO()):
                rc = ccs.self_test()
        finally:
            ccs.CONDITION = real
        self.assertEqual(rc, 3, "the use-vs-mention control did not catch a naive matcher")


if __name__ == "__main__":
    unittest.main(verbosity=2)
