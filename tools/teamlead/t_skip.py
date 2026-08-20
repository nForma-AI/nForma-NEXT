"""A skip must report the reason it was RAISED with, never an invented one (#1230).

★ THE DEFECT. `_print_summary` ended every skipped run with the same hardcoded sentence —
``SKIPPED — provider unavailable (no bid/delivery); not a code failure`` — for every leg and
every skip reason. MEASURED on `C1: StatefulSet Recovery (dfc)`, job 96237491081, where it
appeared TWO LINES BELOW its own refutation::

    [PASS] Phase 2: Deploy Single-Region PG (296.61s)   <- a provider BID and DELIVERED
    [PASS] Phase 3: StatefulSet Ready (1/1)             <- the pod is RUNNING
    [SKIP] Phase 4 — exec transport is not answering (exit=-1 on 3 consecutive attempts)
    SKIPPED — provider unavailable (no bid/delivery)    <- false, and disproved above

⚠ THE COST IS NOT A WRONG STRING. It gives OUR defect a third party's alibi: a triager reading
*"provider unavailable, not a code failure"* correctly stops looking. This repo has already
retracted false provider accusations, and `Coverage Guard (chronic-skip honesty)` reds on
exactly this shape -- it cross-checks a CLAIMED outage against whether a real one coincided.

★ The correct reason already existed. `PhaseResult.message` carries it and the ``[SKIP]`` line
already prints it. The summary discarded it and substituted a guess.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


_ROOT = Path(__file__).resolve().parents[2]
# `e2e/` for the `lib` package; `tests/lib` supplies the `api_client` stub base_e2e imports
# at module level. ⚠ `e2e/lib` is deliberately NOT added — it contains logging.py and types.py,
# which would shadow two stdlib modules for every test imported afterwards.
for _p in (_ROOT / "e2e", _ROOT / "tests" / "lib", _ROOT / "tests" / "helpers"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from lib import base_e2e  # noqa: E402
from lib.types import PhaseResult  # noqa: E402

EXEC_DEAD = (
    "exec transport is not answering (indeterminate sentinel exit=-1 on 3 consecutive "
    "attempts) BEFORE the kill was attempted. No pod was killed."
)
CAPACITY = "no vetted provider bid or delivered a pod"


class _Harness:
    """Minimal stand-in carrying only what `_print_summary` reads."""

    _print_summary = base_e2e.BaseE2ETest._print_summary

    def __init__(self, results):
        self.results = results


def _summary_lines(results) -> str:
    captured = []
    with patch.object(base_e2e, "log", lambda msg, *a, **k: captured.append(str(msg))):
        _Harness(results)._print_summary()
    return "\n".join(captured)


def _verdict_line(results) -> str:
    """The FINAL verdict line only — not the whole transcript.

    ⚠ Asserting against the whole output is VACUOUS here: the per-phase ``[SKIP]`` lines
    already print each phase's message, so a reason appears in the transcript whether or not
    the summary carries it. Caught by mutation-running these tests against origin/main, where
    a whole-output assertion passed while the summary still said "provider unavailable".
    """
    captured = []
    with patch.object(base_e2e, "log", lambda msg, *a, **k: captured.append(str(msg))):
        _Harness(results)._print_summary()
    verdicts = [c for c in captured if c.lstrip().startswith(("SKIPPED", "All ")) or "phase(s) FAILED" in c]
    assert verdicts, f"no verdict line was emitted; got {captured!r}"
    return verdicts[-1]


def _skipped(message: str) -> PhaseResult:
    return PhaseResult(
        name="Phase 4: Kill Primary Pod",
        passed=True,
        duration_seconds=7.65,
        message=message,
        skipped=True,
    )


def _passed(name: str) -> PhaseResult:
    return PhaseResult(name=name, passed=True, duration_seconds=1.0)


def test_the_summary_reports_the_raised_reason_not_a_capacity_story():
    """The regression. This is the sentence that was false on job 96237491081."""
    out = _verdict_line([_passed("Phase 2: Deploy"), _skipped(EXEC_DEAD)])

    assert "exec transport is not answering" in out, (
        "the summary's VERDICT line discarded the reason the skip was actually raised with"
    )
    assert "provider unavailable (no bid/delivery)" not in out, (
        "the summary still asserts a provider capacity outage — that sentence gives our own "
        "exec defect a third party's alibi, and a triager reading it correctly stops looking"
    )


def test_a_genuine_capacity_skip_still_says_so():
    """⚠ Guard the over-correction: the fix must not stop capacity skips reading as capacity.

    ~11 of the 12 `ProviderUnavailableSkip` call sites are genuine no-bid/no-delivery cases.
    Carrying the reason must preserve those, not blanket-replace them.
    """
    out = _verdict_line([_skipped(CAPACITY)])
    assert "no vetted provider bid or delivered a pod" in out


def test_two_skips_both_reasons_survive():
    """A run can skip more than one phase; neither reason may be dropped."""
    out = _verdict_line([_skipped(EXEC_DEAD), _skipped(CAPACITY)])
    assert "exec transport is not answering" in out
    assert "no vetted provider bid or delivered a pod" in out


def test_a_reasonless_skip_says_so_rather_than_inventing_one():
    """⛔ The failure mode this whole issue is about: filling a gap with a plausible guess.

    If no phase recorded a message, the honest output is that none was recorded — NOT a
    default cause that happens to be right for one call site.
    """
    out = _verdict_line([_skipped("")])
    assert "no reason was recorded" in out
    assert "provider unavailable" not in out


def test_a_passing_run_is_unaffected():
    """Bound the change."""
    out = _verdict_line([_passed("Phase 1: Setup"), _passed("Phase 2: Deploy")])
    assert "All 2 phases PASSED" in out
    assert "SKIPPED" not in out


# --- the interface guard -----------------------------------------------------


def test_the_exit_line_still_carries_the_EXIT_SKIP_marker():
    """★ A LOG STRING WITH A PARSER IS AN INTERFACE, and rewording one breaks it silently.

    `scripts/tier_truth.py` classifies a run by grepping SKIP_MARKERS, which includes
    ``EXIT_SKIP``. C1's exit line is reworded by this change, so assert the marker survives --
    a consumer that greps a log has no way to announce that it stopped matching.

    ⚠ Verified separately that `scripts/ci_chronic_skip_guard.py` does NOT read log text: it
    classifies from `job.conclusion` only, so it is unaffected either way.
    """
    src = (_ROOT / "e2e" / "test_z_single_region_recovery_e2e.py").read_text()
    i = src.find("if self.test_skipped():")
    assert i != -1, "the EXIT_SKIP branch moved — this guard is testing nothing"
    block = src[i : i + 700]

    assert "EXIT_SKIP" in block, "C1's skip exit no longer emits the EXIT_SKIP marker that tier_truth.py greps for"
    assert "provider unavailable (no bid/delivery)" not in block, (
        "C1's exit still hardcodes the capacity story instead of the raised reason"
    )


def test_tier_truth_still_declares_the_marker_this_change_relies_on():
    """Pins the other side of that interface, so the pair cannot drift apart silently."""
    src = (_ROOT / "scripts" / "tier_truth.py").read_text()
    assert "SKIP_MARKERS" in src
    assert '"EXIT_SKIP"' in src, "tier_truth.py no longer greps EXIT_SKIP — the marker the exit line preserves for it"
