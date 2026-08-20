#!/usr/bin/env python3
"""Hermetic suite for probe-validity.py. No network, no repo, no clock.

⚠ Deliberately NO `# SUITE-DEPENDS:` marker — every fixture is written to a temp
directory by the test itself.

★ `--self-test` asserts the VERDICTS. This asserts the CLI CONTRACT — exit codes,
markers, and the refusals — which is what a caller reads, and which can drift while
every verdict stays right.
"""
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("pv", HERE / "probe-validity.py")
pv = importlib.util.module_from_spec(_s)
_s.loader.exec_module(pv)


def cli(argv):
    real = sys.argv
    sys.argv = ["probe-validity.py"] + argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = pv.main()
    finally:
        sys.argv = real
    return code, out.getvalue(), err.getvalue()


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.yes = os.path.join(self.d, "yes.txt")
        self.no = os.path.join(self.d, "no.txt")
        open(self.yes, "w").write("the needle is here\n")
        open(self.no, "w").write("only hay\n")


class ExitContract(Fixtures):

    def test_working_probe_validates(self):
        code, out, _ = cli(["--probe", "grep -q needle {}",
                            "--present-case", self.yes, "--absent-case", self.no])
        self.assertEqual(code, 0, out)
        self.assertIn("VALIDATED", out)

    def test_probe_that_cannot_say_present_is_invalid(self):
        """⛔ The motivating case: DEV3's estate regex printed nothing and read as
        a clean sweep. Note the ABSENT control PASSES — which is why it looked fine."""
        code, out, _ = cli(["--probe", "grep -q NEVERMATCHES {}",
                            "--present-case", self.yes, "--absent-case", self.no])
        self.assertEqual(code, 1)
        self.assertIn("could not say PRESENT", out)

    def test_probe_that_cannot_say_absent_is_invalid(self):
        """⛔ DEV2's 13-of-13: a false PRESENT-for-everything. Harder to notice
        than a wrong negative, because its answer looks like a finding."""
        code, out, _ = cli(["--probe", "true # {}",
                            "--present-case", self.yes, "--absent-case", self.no])
        self.assertEqual(code, 1)
        self.assertIn("could not say ABSENT", out)

    def test_an_erroring_probe_is_not_read_as_absent(self):
        """A command that crashed did not report ABSENT. Collapsing exit>1 into
        'not found' is three of the six motivating instances."""
        self.assertEqual(pv.verdict_of(2, ""), "ERROR")
        self.assertEqual(pv.verdict_of(127, ""), "ERROR")
        code, _, _ = cli(["--probe", "exit 2 # {}",
                          "--present-case", self.yes, "--absent-case", self.no])
        self.assertEqual(code, 1)


class RefusesRatherThanGuesses(Fixtures):

    def test_missing_controls_are_unestablished_not_a_verdict(self):
        """⚠ THE HONEST LIMIT: for a genuinely new question there may be no case
        whose answer is known. That must be exit 2, never a pass."""
        code, _, err = cli(["--probe", "grep -q needle {}", "--target", self.yes])
        self.assertEqual(code, 2)
        self.assertIn("UNESTABLISHED", err)
        self.assertIn("genuinely new question", err)

    def test_probe_without_placeholder_is_refused(self):
        """A command that ignores its corpus is not reading one — running it three
        times would validate nothing while looking rigorous."""
        code, _, err = cli(["--probe", "grep -q needle somefile",
                            "--present-case", self.yes, "--absent-case", self.no])
        self.assertEqual(code, 2)
        self.assertIn("no {}", err)

    def test_identical_control_pair_is_refused(self):
        code, _, err = cli(["--probe", "grep -q needle {}",
                            "--present-case", self.yes, "--absent-case", self.yes])
        self.assertEqual(code, 2)
        self.assertIn("same path", err)


class SameTemplateByConstruction(Fixtures):
    """★ The hole discriminates.py DOCUMENTS and cannot close: 'the control pair is
    NOT verified to use the same check as --a/--b.' Here one template is substituted
    with each corpus, so a control cannot use a different check."""

    def test_one_template_reaches_every_corpus(self):
        seen = []
        real = pv.reading
        pv.reading = lambda probe, corpus: (seen.append((probe, corpus)),
                                            real(probe, corpus))[1]
        try:
            cli(["--probe", "grep -q needle {}", "--present-case", self.yes,
                 "--absent-case", self.no, "--target", self.yes])
        finally:
            pv.reading = real
        # ⚠ Scope the assertion to the USER'S corpora. `seen` also captures this
        # tool's own internal known-positive, which necessarily uses its own probes
        # against its own temp fixtures — asserting over the union was a population
        # error, and this suite caught it on its first run.
        mine = [(pr, c) for pr, c in seen if c in (self.yes, self.no)]
        probes = {pr for pr, _ in mine}
        self.assertEqual(len(probes), 1, f"more than one probe template used: {probes}")
        self.assertEqual({c for _, c in mine}, {self.yes, self.no})
        self.assertIn("{}", probes.pop())


class StatedBounds(Fixtures):
    def test_validated_output_disclaims_class_c(self):
        """A validated probe can still answer a proposition nobody asked. The
        output must say so — a caveat a reader must look up is one they will not."""
        _, out, _ = cli(["--probe", "grep -q needle {}",
                         "--present-case", self.yes, "--absent-case", self.no])
        self.assertIn("never", out)
        self.assertIn("Class C", out)


class Markers(Fixtures):
    def test_result_marker_on_every_controlled_path(self):
        for argv, expect in (
            (["--probe", "grep -q needle {}", "--present-case", "@Y",
              "--absent-case", "@N"], "VALIDATED"),
            (["--probe", "grep -q NOPE {}", "--present-case", "@Y",
              "--absent-case", "@N"], "INVALID"),
            (["--probe", "grep -q needle {}"], "UNESTABLISHED"),
            (["--self-test"], "SELF-TEST-PASS"),
        ):
            argv = [self.yes if a == "@Y" else self.no if a == "@N" else a
                    for a in argv]
            _, _, err = cli(argv)
            self.assertIn(f"NFORMA-RESULT {expect}", err, str(argv))


class ControlIsSharp(Fixtures):
    """⛔ #26 — a control with no reachable failing state is decoration."""

    def test_selftest_catches_a_validator_that_always_passes(self):
        real = pv.validate
        pv.validate = lambda p, a, b: (True, [])
        try:
            with redirect_stdout(io.StringIO()):
                rc = pv.self_test()
        finally:
            pv.validate = real
        self.assertEqual(rc, 3, "self-test passed a validator that approves everything")

    def test_selftest_catches_a_validator_that_always_fails(self):
        real = pv.validate
        pv.validate = lambda p, a, b: (False, [])
        try:
            with redirect_stdout(io.StringIO()):
                rc = pv.self_test()
        finally:
            pv.validate = real
        self.assertEqual(rc, 3, "self-test passed a validator that refuses everything")

    def test_intact_selftest_passes(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(pv.self_test(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
