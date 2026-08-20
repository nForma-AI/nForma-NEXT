#!/usr/bin/env python3
"""Hermetic suite for truncation-guard.py. No network, no subprocess, no clock.

⚠ Deliberately NO `# SUITE-DEPENDS:` marker. This suite genuinely needs nothing —
every specimen is a string plus an integer, which is the property that let the guard
be built and verified while the API budget was exhausted.

★ What `--self-test` covers and this does not: `--self-test` asserts the VERDICTS.
This asserts the CLI CONTRACT — the exit codes, the markers, and the refusals — which
is what a caller actually reads, and which can drift while every verdict stays right.
"""
import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("tg", HERE / "truncation-guard.py")
tg = importlib.util.module_from_spec(_s)
_s.loader.exec_module(tg)


def cli(argv):
    """Drive main() exactly as the CLI does. Returns (code, stdout, stderr)."""
    real = sys.argv
    sys.argv = ["truncation-guard.py"] + argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = tg.main()
    finally:
        sys.argv = real
    return code, out.getvalue(), err.getvalue()


def v(count, cmd):
    return tg.verdict(tg.Reading(count, cmd))[0]


class RealSpecimens(unittest.TestCase):
    """⛔ CRITERION 4 — the guard must FAIL on real data, and both readings below
    were actually taken against this repository, ninety minutes apart."""

    S1 = ("gh issue list --repo nForma-AI/nForma-NEXT --state open --json number "
          "--jq 'length'")
    S2 = ("gh issue list --repo nForma-AI/nForma-NEXT --state open --limit 1000 "
          "--json number")

    def test_the_reading_that_said_30_is_truncated(self):
        code, out, _ = cli(["--count", "30", "--command", self.S1])
        self.assertEqual(code, 1, out)
        self.assertIn("TRUNCATED", out)

    def test_the_corrected_reading_is_safe(self):
        code, out, _ = cli(["--count", "85", "--command", self.S2])
        self.assertEqual(code, 0, out)

    def test_the_two_specimens_disagree(self):
        """⇒ The whole point. Same command family, same repository, opposite
        verdicts. A guard that cannot produce both is not discriminating."""
        self.assertNotEqual(v(30, self.S1), v(85, self.S2))

    def test_second_measured_instance(self):
        """`gh run list --limit 5` reported 5 against a real population of 100."""
        self.assertEqual(v(5, "gh run list --limit 5"), "TRUNCATED")


class UnknownNeverCollapses(unittest.TestCase):
    """⛔ The state that must not become SAFE. An unstated limit is the common case
    and 'probably fine' is the reading that produced both instances."""

    def test_no_bound_is_unknown_and_exits_2(self):
        code, out, _ = cli(["--count", "4213", "--command",
                            "git log --oneline | wc -l"])
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", out)

    def test_unknown_output_says_it_is_not_fine(self):
        _, out, _ = cli(["--count", "9", "--command", "curl -s x | jq length"])
        self.assertIn("NOT 'fine'", out)

    def test_stated_total_is_not_a_page(self):
        """⛔ Found by dogfooding this guard on close-condition-scan.py's own
        truncation cross-check. `--jq .total_count` extracts the population size the
        API DECLARES; per_page bounds the array beside it. The naive reading flags
        the correct anti-truncation idiom as truncated at every page size — a guard
        that cries wolf on the right answer teaches its reader to mute it."""
        code, out, _ = cli(["--count", "85", "--command",
                            "gh api -X GET search/issues -F per_page=1 "
                            "--jq .total_count"])
        self.assertEqual(code, 2)
        self.assertIn("STATED TOTAL", out)
        # and it must not depend on the count coinciding with per_page
        self.assertEqual(v(1, "gh api search/issues -F per_page=1 --jq .total_count"),
                         "UNKNOWN")

    def test_paginate_does_not_prove_completion(self):
        self.assertEqual(v(85, "gh api repos/o/r/issues --paginate"), "UNKNOWN")

    def test_self_contradictory_reading_is_refused(self):
        """A count above its own bound means the count and the command are not
        describing each other. Picking a side would be a confident wrong answer."""
        code, out, _ = cli(["--count", "200", "--command",
                            "gh issue list --limit 30"])
        self.assertEqual(code, 2)
        self.assertIn("EXCEEDS", out)

    def test_missing_count_is_void_not_safe(self):
        code, _, err = cli(["--command", "gh issue list --limit 100"])
        self.assertEqual(code, 2)
        self.assertIn("ESTABLISHED-NOTHING", err)

    def test_missing_command_is_void_not_safe(self):
        code, out, _ = cli(["--count", "30"])
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN", out)


class BoundArithmetic(unittest.TestCase):

    def test_effective_bound_is_the_minimum(self):
        self.assertEqual(v(30, "gh issue list --limit 1000 | head -30"), "TRUNCATED")

    def test_the_non_binding_bound_does_not_win(self):
        self.assertEqual(v(1000, "gh issue list --limit 1000 | head -30"), "UNKNOWN")

    def test_per_page_above_100_is_clamped(self):
        """GitHub clamps per_page>100 to 100 and says nothing — this guard's own
        defect class, one layer down."""
        self.assertEqual(v(100, "gh api -X GET search/issues -F per_page=1000"),
                         "TRUNCATED")

    def test_gh_api_rest_default_is_30(self):
        self.assertEqual(v(29, "gh api repos/o/r/issues"), "SAFE")
        self.assertEqual(v(30, "gh api repos/o/r/issues"), "TRUNCATED")
        # 31 EXCEEDS the default it was subject to — the reading contradicts itself.
        self.assertEqual(v(31, "gh api repos/o/r/issues"), "UNKNOWN")

    def test_prefix_resolution_is_longest_match(self):
        """⚠ Covered DIRECTLY, because no key in the shipped IMPLICIT_DEFAULTS is a
        prefix of another — so longest-match and first-match are indistinguishable
        on real input, and the branch would otherwise be asserted by nothing. It is
        kept because a future key like `gh api graphql` would need it, and a guard
        whose prefix logic silently degrades is the defect class it exists for."""
        real = tg.IMPLICIT_DEFAULTS
        tg.IMPLICIT_DEFAULTS = {"gh api": 30, "gh api graphql": 5}
        try:
            self.assertEqual(tg._normalised_prefix("gh api graphql --foo"),
                             "gh api graphql")
            self.assertEqual(tg._normalised_prefix("gh api repos/o/r"), "gh api")
            self.assertIsNone(tg._normalised_prefix("git log"))
        finally:
            tg.IMPLICIT_DEFAULTS = real

    def test_head_forms(self):
        for cmd in ("gh pr list | head -5", "gh pr list | head -n 5",
                    "gh pr list | head -n5"):
            self.assertEqual(v(5, cmd), "TRUNCATED", cmd)

    def test_below_bound_is_safe(self):
        self.assertEqual(v(29, "gh issue list"), "SAFE")


class StatedBounds(unittest.TestCase):
    """⚠ The refusals must be in the OUTPUT, not only in the README. A caveat a
    caller has to go and look up is one they will not look up."""

    def test_every_verdict_names_the_uncovered_mechanism(self):
        for count, cmd in ((29, "gh issue list"), (30, "gh issue list"),
                           (4213, "git log | wc -l")):
            _, out, _ = cli(["--count", str(count), "--command", cmd])
            self.assertIn("RULES OUT ONE MECHANISM", out, cmd)
            self.assertIn("server-side filtering", out.lower().replace("server-",
                                                                       "server-"), cmd)

    def test_safe_never_claims_complete(self):
        _, out, _ = cli(["--count", "29", "--command", "gh issue list"])
        self.assertIn("never 'complete'", out)

    def test_zero_count_carries_the_empty_filter_note(self):
        """Zero is not truncated, and conflating it with the mistyped-label defect
        would overclaim — so it is a NOTE, not a verdict change."""
        code, out, _ = cli(["--count", "0", "--command",
                            "gh issue list --label nope --limit 100"])
        self.assertEqual(code, 0)
        self.assertIn("COUNT IS ZERO", out)


class Markers(unittest.TestCase):

    def test_result_marker_on_every_controlled_path(self):
        for argv, expect in (
            (["--count", "30", "--command", "gh issue list"], "TRUNCATED"),
            (["--count", "29", "--command", "gh issue list"], "SAFE"),
            (["--count", "1", "--command", "wc -l"], "UNKNOWN"),
            (["--self-test"], "SELF-TEST-PASS"),
        ):
            _, _, err = cli(argv)
            self.assertIn(f"NFORMA-RESULT {expect}", err, str(argv))


class ControlIsSharp(unittest.TestCase):
    """⛔ #26 — a control with no reachable failing state is decoration. Each break
    below is a plausible implementation someone would actually write."""

    def _selftest_under(self, patch):
        real_verdict, real_defaults = tg.verdict, tg.IMPLICIT_DEFAULTS
        patch()
        try:
            with redirect_stdout(io.StringIO()):
                return tg.self_test()
        finally:
            tg.verdict, tg.IMPLICIT_DEFAULTS = real_verdict, real_defaults

    def test_break_unknown_collapsing_into_safe_is_caught(self):
        real = tg.verdict
        def patch():
            tg.verdict = lambda r: (lambda t: ("SAFE", t[1], t[2])
                                    if t[0] == "UNKNOWN" else t)(real(r))
        self.assertEqual(self._selftest_under(patch), 3)

    def test_break_dropping_implicit_defaults_is_caught(self):
        """The load-bearing one: without the implicit table, TEAMLEAD's real
        specimen reads UNKNOWN instead of TRUNCATED — so the table is what makes
        this work on the actual measured defect."""
        self.assertEqual(self._selftest_under(
            lambda: setattr(tg, "IMPLICIT_DEFAULTS", {})), 3)

    def test_intact_guard_passes_its_own_controls(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tg.self_test(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
