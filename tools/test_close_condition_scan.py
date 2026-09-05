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
import os
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# ⛔ A STALE .pyc SURVIVES A SIZE-PRESERVING EDIT, and this suite was bitten by it.
# The --states fix MOVED a block: same bytes, same length, so mtime+size — the key
# CPython caches on — did not change enough to invalidate. The suite kept executing
# the PRE-fix bytecode and reported FAILED against a file that was already correct.
# ⇒ Two readings of one run: 'the fix does not work' and 'the cache is stale' are
# byte-identical in the output. 32 of 54 suites here already carry this guard; this
# was one of the 22 without it. (The same preamble #572 deletes from 14 files.)
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

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

    def test_the_accepted_form_prints_BESIDE_a_NONE_finding(self):
        """⛔ DEV2's finding: both requirements were discoverable only by READING THE
        REGEX. Nothing in the template, goals/README.md, or this tool's output said a
        comment scores BURIED or that the pattern is line-anchored — which is how
        TEAMLEAD produced twelve BURIED and ARCHITECT four prose ones, neither
        carelessly. The remedy must reach the writer AT THE MOMENT OF THE FINDING."""
        code, out, _ = run([], 2, [issue(1, "## Done when\nx"), issue(2, "nothing")])
        self.assertEqual(code, 1)
        self.assertIn("WHAT COUNTS", out)
        self.assertIn("must start a LINE", out)
        self.assertIn("scores BURIED", out)

    def test_the_accepted_form_is_SILENT_when_there_is_no_NONE(self):
        """The other direction — advice printed on a clean board is noise, and a
        remedy that always prints teaches its reader to skip it."""
        code, out, _ = run([], 2, [issue(1, "## Done when\nx"),
                                   issue(2, "**Closes when** y")])
        self.assertEqual(code, 0)
        self.assertNotIn("WHAT COUNTS", out)

    def test_the_BURIED_remedy_warns_about_superseded_dispositions(self):
        """⚠ Promoting the FIRST clause can promote a WITHDRAWN one — two issues on
        this board carry corrected dispositions."""
        code, out, _ = run([], 1, [issue(1, "no clause", ["## Done when\nx"])])
        self.assertEqual(code, 1)
        self.assertIn("LAST comment", out)
        self.assertIn("WITHDRAWN", out)

    def test_states_DECLARES_the_space_and_conforms_to_the_index_contract(self):
        """⛔ `--states` is the DECLARE relation, matching doctrine-version.py and
        runnable-condition.py. It must emit TAB-separated VERDICT and EXIT lines so
        tools/states-index-check.py can GENERATE a row instead of returning VOID."""
        code, out, _ = run([], 2, [issue(1, "x")] )
        # --states short-circuits before any query; drive it directly
        import sys as _s
        real = _s.argv
        _s.argv = ["close-condition-scan.py", "--states"]
        import io as _io
        from contextlib import redirect_stdout as _rs
        buf = _io.StringIO()
        try:
            with _rs(buf):
                rc = ccs.main()
        finally:
            _s.argv = real
        o = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertEqual(len([l for l in o.splitlines() if l.startswith("EXIT\t")]), 4)
        self.assertEqual(len([l for l in o.splitlines() if l.startswith("VERDICT\t")]), 3)
        for l in o.splitlines():
            self.assertEqual(len(l.split("\t")), 3, l)

    def test_by_state_REPORTS_subjects_and_is_a_different_relation(self):
        """⚠ The two must not be the same flag. `--by-state` names subjects; `--states`
        names the space. One flag answering both is the collision #498 recorded."""
        code, out, _ = run(["--by-state"], 2, [issue(1, "## Done when\nx"),
                                               issue(2, "nothing")])
        self.assertEqual(code, 1)
        self.assertIn("NONE 2", out)
        self.assertNotIn("VERDICT", out)

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
