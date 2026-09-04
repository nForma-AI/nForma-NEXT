#!/usr/bin/env python3
"""Exit-code contract for close-mechanism.py.

⛔ `--self-test` covers the PREDICATES. It cannot cover the paths that all print a
clean-looking zero unless they are separated, and those are exactly what a caller
reads as "the board is fine":

    an empty population   a mistyped label exits 0 with ZERO BYTES on stdout AND
                          stderr, byte-identical to an empty queue (#317)
    a truncated reading   `--limit` clamps silently; a prefix reads as a population
    a single-bucket census  every issue classified alike is a RELABELLING, not a
                          discrimination (branch-census.py's rule, #331)

★ Every case drives the real `main()` with `_load` stubbed, so the exit code under
test is the one the tool actually returns -- not a re-implementation of it.

⛔⛔ THE LOAD-BEARING CASE IS THE LAST ONE. #372 criterion 4: *break a control in an
instrument that currently passes, and show the gate red. If it cannot go red for a
broken control it is not gating them.* `test_control_can_fail` sabotages a predicate
and asserts `--self-test` returns 1. Without it, "the controls pass" and "the controls
cannot fail" are the same reading.
"""
import importlib.util
import io
import re
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("close_mechanism", HERE / "close-mechanism.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeVoid(Exception):
    pass


def fake_ccs(issues, stated=None):
    """A stand-in for close-condition-scan with the three functions this tool calls.

    ⚠ `classify` mirrors the real one rather than always returning BODY -- a stub that
    cannot produce NONE would make the NO-CONDITION leg untestable, which is the
    stub-measures-the-substitute defect."""
    CLAUSE = re.compile(r"(?im)^#+ *(?:⇒ *)?(?:Done when|Close condition)")

    class M:
        Void = FakeVoid

        @staticmethod
        def stated_total(repo, label):
            return len(issues) if stated is None else stated

        @staticmethod
        def fetch(repo, label, limit):
            return issues

        @staticmethod
        def classify(issue):
            if CLAUSE.search(issue.get("body") or ""):
                return "BODY"
            for c in issue.get("comments") or []:
                if CLAUSE.search(c.get("body") or ""):
                    return "BURIED"
            return "NONE"
    return M


def issue(n, body, comments=None):
    return {"number": n, "title": f"issue {n}", "body": body, "comments": comments or []}


CLEAN = "## Done when\nThe fix lands on main and the control fires."
OPERATORY = "## Done when\n⛔ **ADDABLE — OPERATOR.** harness config is reserved to the operator."
CAPTURE = "## Done when\n⚠ **This is a CAPTURE, not a defect report.** It can only be DISCHARGED."
NOCLAUSE = "Some prose with no completion clause anywhere in it."


def drive(mod, issues, stated=None, label=None):
    """Run the real main() and return (exit_code, stdout, stderr)."""
    mod._load = lambda stem: fake_ccs(issues, stated)
    argv = ["close-mechanism.py"] + (["--label", label] if label else [])
    out, err = io.StringIO(), io.StringIO()
    old = sys.argv
    sys.argv = argv
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = mod.main()
    finally:
        sys.argv = old
    return rc, out.getvalue(), err.getvalue()


class ExitContract(unittest.TestCase):

    def setUp(self):
        self.mod = load()

    # ── VOID: the three ways to print a clean-looking zero ──

    def test_empty_population_is_void_not_a_clean_board(self):
        """#317's specimen. A nonexistent label yields exit 0 and zero bytes from `gh`;
        reading that as an empty queue is the defect."""
        rc, _, err = drive(self.mod, [], stated=0, label="role:dev3")
        self.assertEqual(rc, 2, "an empty population must VOID, never report a clean board")
        self.assertIn("EMPTY", err)
        self.assertIn("nonexistent label", err)

    def test_truncated_reading_is_void(self):
        rc, _, err = drive(self.mod, [issue(1, CLEAN)], stated=50)
        self.assertEqual(rc, 2, "a reading shorter than the stated population must VOID")
        self.assertIn("TRUNCATED", err)

    def test_single_bucket_census_is_void(self):
        """A census with one bucket has relabelled the population, not discriminated it."""
        rc, _, err = drive(self.mod, [issue(1, CLEAN), issue(2, CLEAN), issue(3, CLEAN)])
        self.assertEqual(rc, 2, "an undiscriminating census must VOID")
        self.assertIn("relabelled", err)

    # ── the verdicts ──

    def test_unreachable_issue_is_a_finding(self):
        rc, out, _ = drive(self.mod, [issue(1, CLEAN), issue(2, OPERATORY)])
        self.assertEqual(rc, 1, "an operator-terminal issue has no pane-reachable close path")
        self.assertIn("#2", out)
        self.assertIn("OPERATOR", out)

    def test_reachable_board_exits_zero(self):
        """⛔ The known-NEGATIVE of the finding. Without it, "reports findings" and
        "reports a finding on everything" are the same reading."""
        rc, out, _ = drive(self.mod, [issue(1, CLEAN), issue(2, CAPTURE)])
        self.assertEqual(rc, 0, "DISCHARGE is a close path a pane CAN walk -- not unreachable")
        self.assertIn("(none)", out)

    def test_no_condition_is_unreachable(self):
        rc, out, _ = drive(self.mod, [issue(1, CLEAN), issue(2, NOCLAUSE)])
        self.assertEqual(rc, 1)
        self.assertIn("NO-CONDITION", out)

    def test_buried_is_distinct_from_no_condition(self):
        """A condition in a comment is PRESENT and UNREACHABLE -- a different repair."""
        _, out, _ = drive(self.mod, [issue(1, CLEAN),
                                     issue(2, NOCLAUSE, [{"body": "## Done when\nlanded"}])])
        self.assertIn("BURIED", out)
        self.assertNotIn("NO-CONDITION", out)

    # ── the output must state what it did not check ──

    def test_output_states_its_own_bounds(self):
        _, out, _ = drive(self.mod, [issue(1, CLEAN), issue(2, OPERATORY)])
        self.assertIn("NOT CHECKED", out)
        self.assertIn("FALSIFIABLE", out)
        self.assertIn("RESIDUAL", out)
        self.assertIn("SUM TO MORE THAN", out, "overlap must be stated, never implied")

    # ── ⛔ criterion 4: shown to FAIL ──

    def test_control_can_fail(self):
        """Sabotage a predicate; the self-test MUST go red. A control that cannot fail
        is not a control (#26, #372)."""
        mod = load()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mod.self_test(), 0, "baseline: the controls pass before sabotage")
        mod.OPERATOR = re.compile(r"zzzz-this-never-matches")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mod.self_test(), 1, "a broken predicate must turn the self-test red")

    def test_residual_is_reachable_in_both_directions(self):
        mod = self.mod
        self.assertEqual(mod.tags_for({"body": CLEAN}, "BODY"), ["ACTIONABLE"])
        self.assertNotIn("ACTIONABLE", mod.tags_for({"body": OPERATORY}, "BODY"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
