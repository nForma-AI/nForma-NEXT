#!/usr/bin/env python3
"""Hermetic suite for tools/label-precedence.py. No forge, no network.

⛔ The load-bearing case is `test_319_historical_state_is_a_hazard`. The live board returns
HAZARD=0 -- but only because the hazard was REMOVED at 2026-08-21T04:47:53Z. A zero from a board
that has already been repaired demonstrates nothing about whether the tool can find one.
⇒ So the real historical label set is replayed here, from the forge's own timeline, and it is
pinned as a regression: if the classifier ever stops calling it a HAZARD, this fails.
"""
import importlib.util
import io
import os
import sys
import unittest

_P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "label-precedence.py")
_spec = importlib.util.spec_from_file_location("label_precedence", _P)
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)


def row(n, *labels):
    return {"number": n, "labels": [{"name": x} for x in labels], "title": "t"}


class Classifier(unittest.TestCase):
    def test_319_historical_state_is_a_hazard(self):
        """REAL labels, from repos/.../issues/319/timeline:
             2026-08-20T19:11:23Z labeled   dev:2
             2026-08-21T04:25:14Z labeled   role:OPERATOR   <- hazard opens here
             2026-08-21T04:47:53Z unlabeled dev:2           <- and closes here, 22m39s later
        """
        self.assertEqual(lp.classify(row(319, "role:OPERATOR", "dev:2"))[0], "HAZARD")

    def test_319_current_state_is_not(self):
        """The other side of the same pair, on the same real issue."""
        self.assertEqual(lp.classify(row(319, "role:OPERATOR"))[0], "NO-DEV-LABEL")

    def test_role_dev_does_not_rescue_a_reserved_queue(self):
        """⚠ A reserved queue outranks a legitimate address. Order of checks matters."""
        self.assertEqual(
            lp.classify(row(7, "dev:4", "role:DEV", "role:OPERATOR"))[0], "HAZARD")

    def test_dev_n_with_role_dev_is_an_address(self):
        self.assertEqual(lp.classify(row(2, "dev:3", "role:DEV"))[0], "ADDRESS")

    def test_dev_n_with_another_role_is_provenance(self):
        self.assertEqual(lp.classify(row(3, "dev:5", "role:DEVOPS"))[0], "PROVENANCE")

    def test_dev_n_with_no_role_is_unrouted(self):
        self.assertEqual(lp.classify(row(4, "dev:1"))[0], "UNROUTED")

    def test_an_issue_with_no_dev_label_still_gets_a_NAMED_bucket(self):
        """⛔ #466: the complement must be NAMED, not silent. A row that falls out of every bucket
        is the 79 issues this tool used to print a 110-population line about and never count."""
        self.assertEqual(lp.classify(row(5, "role:DX"))[0], "NO-DEV-LABEL")
        self.assertEqual(lp.classify(row(6))[0], "NO-DEV-LABEL")


class Reporting(unittest.TestCase):
    def _report(self, rows, ok=True):
        real, buf = lp.fetch, io.StringIO()
        lp.fetch = lambda repo: (ok, rows)
        try:
            rc = lp.report("x/y", out=buf)
        finally:
            lp.fetch = real
        return rc, buf.getvalue()

    def test_unreadable_forge_is_void_not_zero(self):
        """⛔ The whole exit-2 convention: 'could not read' must not render as 'nothing found'."""
        rc, out = self._report([], ok=False)
        self.assertEqual(rc, 2)
        self.assertIn("ESTABLISHED NOTHING", out)
        self.assertNotIn("no HAZARD collisions", out)

    def test_hazard_exits_1_and_names_the_issue(self):
        rc, out = self._report([row(319, "role:OPERATOR", "dev:2")])
        self.assertEqual(rc, 1)
        self.assertIn("#319", out)

    def test_provenance_alone_exits_0_and_is_not_called_a_defect(self):
        rc, out = self._report([row(403, "role:ARCHITECT", "dev:5")])
        self.assertEqual(rc, 0)
        self.assertIn("PROVENANCE is not a defect", out)

    def test_a_clean_board_and_an_unreadable_one_differ(self):
        """The pair the exit-2 convention exists for, asserted directly."""
        clean, _ = self._report([row(9, "role:DX")])
        void, _ = self._report([], ok=False)
        self.assertNotEqual(clean, void)

    def test_a_bucket_the_printer_does_not_know_makes_it_REFUSE(self):
        """#466 leg 3 — the KNOWN-NEGATIVE, run by this caller on every suite run.

        ⛔ The invariant is not decoration. Its live failure mode is #39's: the classifier gains a
        state and the printer keeps the old space. Planting exactly that -- a kind the print list
        does not enumerate -- must produce exit 2 ESTABLISHED NOTHING, never a verdict.
        """
        real = lp.classify
        lp.classify = lambda r: ("A-KIND-NOBODY-PRINTS", [], [])
        try:
            rc, out = self._report([row(1, "dev:1"), row(2, "role:DX")])
        finally:
            lp.classify = real
        self.assertEqual(rc, 2)
        self.assertIn("ESTABLISHED NOTHING", out)
        self.assertNotIn("no HAZARD collisions", out)

    def test_the_same_run_WITHOUT_the_plant_reports_normally(self):
        """⚠ The other side. A control that only ever fails proves the check is stuck, not working."""
        rc, out = self._report([row(1, "dev:1"), row(2, "role:DX")])
        self.assertEqual(rc, 0)
        self.assertIn("PARTITION", out)

    def test_partition_line_states_the_sum(self):
        rc, out = self._report([row(1, "dev:5", "role:DX"), row(2, "role:DX")])
        self.assertIn("PARTITION", out)
        self.assertEqual(rc, 0)

    def test_states_flag_matches_the_codes_report_can_return(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            lp.main(["--states"])
        finally:
            sys.stdout = old
        for code in ("0", "1", "2"):
            self.assertIn(code, buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
