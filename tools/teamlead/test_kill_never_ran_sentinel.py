"""An ambiguous kill status must be reported as UNKNOWN — not as either confident answer.

⚠ THE FILENAME IS STALE AND IS NOT THE CONTRACT. `test_kill_never_ran_sentinel.py` predates
the UNKNOWN reclassification and still says "never ran", which is the semantic this file now
exists to REFUTE. It is kept only to avoid churning history for cosmetics — read the module
docstring, not the name. `-1` does not mean "never ran": it means the exec's outcome is NOT
KNOWN, covering never-reached-the-container AND timeouts AND transport failures, and the whole
point is that those cannot be told apart from the sentinel alone.

★ MEASURED (#968). `_kill_akash_deployment` returned ``{"status": "killed"}`` whenever the
stderr denylist did not recognise a phrase, so run 31514389709 (C0: Pod Recovery, dfc) logged::

    17:21:57  Soft-killed Akash deployment 1786468883565 service=tetris exit=-1

and the leg reported PASS — while its own ``poll_until(pod leaves Running state)`` FAILED. The
pod never moved. A denylist of known failure phrases is incomplete by construction, so every
new transport-error wording is one more silent pass.

★★ WHY NOT SIMPLY FAIL ON -1. The first version of this fix asserted that ``exit=-1`` proves
the command "never ran", on the grounds that ``ExecResult.error()`` defaults to -1. Two things
are wrong with that, and both were found by reading the call site:

  1. ``ExecResult`` / ``container_exec`` is the WORKERS layer. ``handlers/workloads.py`` does
     not reference it at all — the cited evidence describes different code.
  2. A timeout is not evidence of non-delivery; it is evidence the client stopped waiting.
     And ``kill -9 1`` tears down PID 1, so a hung client is a plausible shape of the SUCCESS
     case.

     ⚠ CORRECTED (#1177). This paragraph used to say "the only literal -1 is its
     ``asyncio.TimeoutError`` handler", and the conclusion below was drawn from that. The
     premise is false, and it is the false premise that put "means the command TIMED OUT"
     into the 502. ``_exec_akash_deployment`` delegates to
     ``provider_shell_client.exec_command`` for Console-backed (DFC) deployments, which has
     SEVEN routes to -1; its CLI path can also emit -1 without any timeout, because
     ``process.returncode or 0`` passes through ``-1`` and in ``asyncio.subprocess`` a
     negative returncode is *killed by signal N* (-1 = SIGHUP). Only the timeout routes write
     ``Timeout after <n>s`` into stderr, so an EMPTY stderr EXCLUDES a timeout. The
     conclusion (do not fail on -1) survives; the reasoning that reached it did not.

Asserting non-delivery would therefore 502 on kills that worked — the same fail-wrong pointed
the other way.

⚠ NOT ESTABLISHED, and deliberately not claimed: that no other path can yield -1.
``_resp.exit_code`` (the Console-shell path) is delegated and untraced. The verified claims are
narrow — ``:3556`` is the sole LITERAL -1 in ``_exec_akash_deployment``, and ``ExecResult`` is
absent from this file. Enough to forbid "exit=-1 ⇒ never reached"; not a proof of the converse.

★★★ SO: THREE STATES. The correct resolution of an ambiguous status is a third state, not a
coin flip between the two confident ones. A false FAIL beats a hollow PASS, and UNKNOWN is how
to get that honesty without inventing a certainty we do not have.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

API = Path(__file__).resolve().parents[1]
for _p in (str(API), str(API.parents[1])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import handlers.workloads as w  # noqa: E402

SRC = API / "handlers" / "workloads.py"


# ---------------------------------------------------------------------------
# BEHAVIOURAL — the classifier is imported and run, not pattern-matched.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exit_code,stderr,expected",
    [
        # ★ THE FIX: indeterminate sentinel with nothing else to go on.
        (-1, "Command timed out after 120s", w._KILL_UNKNOWN),
        (-1, "", w._KILL_UNKNOWN),
        (-1, "some phrasing nobody has seen before", w._KILL_UNKNOWN),
        # POSITIVE evidence of non-delivery wins over the sentinel — order matters.
        (-1, "Error: key not found", w._KILL_NOT_REACHED),
        (1, "unauthorized", w._KILL_NOT_REACHED),
        (2, "remote server returned 404", w._KILL_NOT_REACHED),
        # ⚠ SUCCESS SHAPES. `kill -9 1` tears down PID 1, so a non-zero exit or a dead
        # session is what a WORKING kill looks like. Requiring 0 would invert the bug.
        (0, "", w._KILL_DELIVERED),
        (None, "", w._KILL_DELIVERED),
        (137, "session closed by remote host", w._KILL_DELIVERED),
        (255, "connection reset", w._KILL_DELIVERED),
    ],
)
def test_kill_outcome_is_three_valued(exit_code, stderr, expected):
    assert w._classify_kill_outcome(exit_code, stderr) == expected


def test_the_three_states_are_distinct():
    """Non-vacuity: a classifier collapsing to two values would pass many cases above."""
    assert len({w._KILL_DELIVERED, w._KILL_NOT_REACHED, w._KILL_UNKNOWN}) == 3


def test_unknown_is_reachable_and_is_not_delivered():
    """★ THE INVARIANT. -1 with unrecognised stderr must be neither PASS nor 'never reached'.

    Before this change it returned DELIVERED (the hollow pass). The first attempted fix made
    it NOT_REACHED (the over-confident fail). It must be neither.
    """
    got = w._classify_kill_outcome(-1, "a phrase the denylist does not know")
    assert got == w._KILL_UNKNOWN
    assert got != w._KILL_DELIVERED, "regressed to the hollow pass"
    assert got != w._KILL_NOT_REACHED, "regressed to asserting non-delivery it cannot prove"


def test_a_successful_kill_is_never_unknown():
    """Non-vacuity the other way: a classifier returning UNKNOWN always would pass the above."""
    for code in (0, None, 137, 143):
        assert w._classify_kill_outcome(code, "") == w._KILL_DELIVERED


# ---------------------------------------------------------------------------
# The handler must ACT on all three — a classifier nothing branches on is decoration.
# ---------------------------------------------------------------------------


def _handler_src() -> str:
    tree = ast.parse(SRC.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "kill" in node.name and "akash" in node.name:
            seg = ast.get_source_segment(SRC.read_text(), node)
            if seg and "_classify_kill_outcome" in seg:
                return seg
    raise AssertionError("no kill handler calls _classify_kill_outcome — the classifier is unused")


def _reachable_if_tests(src: str, name: str) -> list[ast.expr]:
    """`if` tests that reference `name` AND are not disabled by a constant.

    ⚠ PRESENCE IS NOT REACHABILITY. `if False and _outcome == _KILL_UNKNOWN:` still contains
    the string, so a substring assertion passes on a branch that can never run — verified by
    mutation, which is how this test was found to be vacuous. Same shape as #1072 (a guard
    unreachable under `bash -e`) and #938 (a suite passing on workflows it could not parse):
    the control is there, and it does nothing.
    """
    out = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.If):
            continue
        names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        if name not in names:
            continue
        consts = [c for c in ast.walk(node.test) if isinstance(c, ast.Constant) and c.value in (False, None, 0)]
        if consts:
            continue  # short-circuited to dead by a falsy constant
        out.append(node.test)
    return out


def test_the_handler_branches_on_all_three_outcomes():
    src = _handler_src()
    assert "_KILL_NOT_REACHED" in src, "handler does not act on the non-delivery verdict"
    assert "_KILL_UNKNOWN" in src, "handler does not act on the UNKNOWN verdict — it would fall through to 'killed'"


def test_the_UNKNOWN_branch_is_REACHABLE_not_merely_present():
    """★ The mutation that beat the first version of this file: a dead-but-present branch."""
    src = "def _f():\n" + "\n".join("    " + ln for ln in _handler_src().splitlines())
    assert _reachable_if_tests(src, "_KILL_UNKNOWN"), (
        "the handler has no REACHABLE `if` on _KILL_UNKNOWN — the branch is present but "
        "disabled by a constant, so an indeterminate kill falls through and reports 'killed'"
    )
    assert _reachable_if_tests(src, "_KILL_NOT_REACHED"), "the non-delivery branch is present but unreachable"


def test_the_unknown_response_does_not_claim_non_delivery():
    """The message must not resolve the ambiguity it exists to preserve."""
    src = _handler_src()
    i = src.find("_KILL_UNKNOWN")
    block = src[i : i + 1200]
    assert "UNKNOWN" in block, "the UNKNOWN branch does not say UNKNOWN"
    assert "may or may not" in block, "the UNKNOWN branch does not state that the outcome is undetermined"
    assert "never reached the container" not in block, (
        "the UNKNOWN branch claims non-delivery — that is the assertion this fix removes. ⚠ Do "
        "not restore the old rationale here ('-1 means TIMED OUT on the measured path'): -1 is "
        "emitted by seven routes and an empty stderr rules the timeout ones OUT (#1177)."
    )


def _executable_lines() -> str:
    """Source with comment lines removed.

    ⚠ WITHOUT THIS THIS TEST IS WRONG IN BOTH DIRECTIONS. The rationale comment mentions
    `container_exec` precisely to say the file does NOT use it, so a bare `"container_exec"
    not in text` fails on correct code. The mirror of the trap that made an earlier guard pass
    on its own explanatory prose (#1066): a source-text assertion cannot tell a mention from a
    use. Check code.
    """
    return "\n".join(ln for ln in SRC.read_text().splitlines() if not ln.lstrip().startswith("#"))


def test_the_execresult_justification_is_not_load_bearing():
    """The old rationale cited the WORKERS layer as evidence about THIS file.

    `ExecResult` / `container_exec` live in control-plane/workers/container_exec.py. This
    handler does not import them, so they could never have been evidence for its behaviour.
    """
    code = _executable_lines()
    assert "container_exec" not in code, "workloads.py now USES container_exec — the layer boundary moved"
    assert "ExecResult" not in code, "workloads.py now USES ExecResult — re-check whether -1 still means timeout here"
