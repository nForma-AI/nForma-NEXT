"""The empty-stderr discriminator is a PROPERTY, and must not be silently deletable (#1177).

★ WHY THIS FILE EXISTS. `_kill_akash_deployment`'s UNKNOWN 502 tells the reader that an
``exit=-1`` with EMPTY stderr rules a timeout OUT. That statement is true only because of a
property of ``exec_command``: every route to -1 that IS a timeout writes
``f"Timeout after {timeout}s"`` into stderr, and the session-ended routes write nothing. The
property is load-bearing -- it is the whole basis for the message -- and until this file it
was **an accident of the current code that any refactor could delete with no test failing**.
One ``stderr_parts.append(...)`` added to the ``ConnectionClosed`` handler would silently
turn the 502 back into a false statement.

⚠ THIS ASSERTS THE PROPERTY, NOT THE SOURCE TEXT. A scan for ``"Timeout after"`` in the file
would pass on a branch that can never run, and would fail on an equivalent rewrite. So each
producer is DRIVEN and its stderr read back.

⚠ WHAT THIS DOES NOT DO. It does not make the collapse acceptable. Distinguishing seven
producer states by whether one of them happened to write to a string is a workaround; the
repair is for ``exec_command`` to carry which producer fired (#1211). This file exists to
make sure the workaround cannot rot silently in the meantime.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

API = Path(__file__).resolve().parents[1]
for _p in (str(API), str(API.parents[1])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import services.provider_shell_client as psc  # noqa: E402


class _FakeWS:
    """Minimal websocket whose recv() behaviour is chosen per test."""

    def __init__(self, on_recv):
        self._on_recv = on_recv

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def send(self, _frame):
        return None

    async def recv(self):
        return await self._on_recv()

    async def close(self):
        return None


def _connect_returning(on_recv):
    def _connect(*_a, **_kw):
        return _FakeWS(on_recv)

    return _connect


async def _run(on_recv, timeout: int = 30) -> psc.LeaseShellResponse:
    client = psc.ProviderShellClient(provider_host="https://provider.example:8443")
    with patch.object(psc.websockets, "connect", _connect_returning(on_recv)):
        return await client.exec_command(
            dseq="1787100113503",
            service_name="web",
            command=["kill", "-9", "1"],
            timeout=timeout,
        )


# ---------------------------------------------------------------------------
# The two halves of the property.
# ---------------------------------------------------------------------------


async def test_a_timeout_route_always_leaves_evidence_in_stderr():
    """TIMEOUT half: the recv deadline fires -> stderr must say so.

    If this stops holding, an empty stderr no longer excludes a timeout, and the 502 in
    `_kill_akash_deployment` becomes a false statement again.
    """

    async def _hang():
        await asyncio.sleep(3600)

    resp = await _run(_hang, timeout=1)
    assert resp.exit_code == -1
    assert resp.stderr.strip(), (
        "the timeout route returned the sentinel with EMPTY stderr — that collapses it into "
        "the session-ended routes, and the kill-UNKNOWN 502 can no longer exclude a timeout"
    )
    assert "timeout" in resp.stderr.lower()


async def test_the_exhausted_budget_route_also_leaves_evidence():
    """The OTHER timeout route: the loop's own `remaining <= 0` guard, before any recv."""

    async def _never_called():  # pragma: no cover - must not be reached
        raise AssertionError("recv should not run when the budget is already spent")

    resp = await _run(_never_called, timeout=0)
    assert resp.exit_code == -1
    assert resp.stderr.strip(), "the exhausted-budget route returned the sentinel with EMPTY stderr"
    assert "timeout" in resp.stderr.lower()


async def test_a_dropped_session_leaves_stderr_empty():
    """SESSION-ENDED half: the socket dies before a result -> nothing added to stderr.

    ⚠ This is the assertion a refactor is most likely to break, and the one that would
    silently invalidate the 502's reasoning. For `kill -9 1` this is ALSO the success shape:
    PID 1 goes down, the shell hangs up. If a future change starts writing to stderr here,
    that is not a cosmetic difference — it destroys the only channel currently separating
    "the kill worked" from "the exec timed out".
    """

    async def _closed():
        raise psc.websockets.exceptions.ConnectionClosed(None, None)

    resp = await _run(_closed)
    assert resp.exit_code == -1
    assert resp.stderr == "", (
        "the dropped-session route now writes to stderr — the empty-stderr discriminator the "
        "kill-UNKNOWN 502 relies on is gone. Either restore it or land #1211 (an explicit "
        "`reason`) and rewrite the 502 to read that instead."
    )


async def test_the_two_producer_classes_are_distinguishable():
    """The property itself, stated as the disjointness the 502 actually depends on.

    Both classes return the SAME exit_code. The whole discrimination lives in stderr, so
    assert exactly that: same sentinel, different stderr emptiness. A single test that reads
    both outcomes together is what a reviewer needs, because the defect is not in either
    branch — it is in whether the pair stays separable.
    """

    async def _hang():
        await asyncio.sleep(3600)

    async def _closed():
        raise psc.websockets.exceptions.ConnectionClosed(None, None)

    timed_out = await _run(_hang, timeout=1)
    dropped = await _run(_closed)

    assert timed_out.exit_code == dropped.exit_code == -1, (
        "precondition of this whole issue: the sentinel does NOT distinguish these"
    )
    assert bool(timed_out.stderr.strip()) != bool(dropped.stderr.strip()), (
        "a timeout and a dropped session are now indistinguishable in EVERY channel the kill "
        "handler reads — exit_code was already the same, and stderr no longer differs"
    )


async def test_a_normal_result_is_not_the_sentinel():
    """Bound it: a provider that answers must not be swept into the -1 class."""
    frames = [psc.RESULT_FRAME_FOR_TEST] if hasattr(psc, "RESULT_FRAME_FOR_TEST") else None
    if frames is None:
        payload = b'{"exit_code": 0}'
        frame = bytes([psc.RESULT]) + payload

        async def _result():
            return frame

        resp = await _run(_result)
        assert resp.exit_code == 0, "a well-formed RESULT frame must be reported as itself"
        assert resp.stderr == ""
    else:  # pragma: no cover - defensive
        pytest.skip("module exposes a test frame constant; not exercised here")
