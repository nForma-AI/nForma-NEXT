"""A 500's `error` field must never be empty (#1218).

★ THE DEFECT. `main.global_exception_handler` returned
``{"detail": "Internal server error", "error": str(exc)}``. ``str(exc)`` is ``''`` for ANY
exception raised without a message -- ``KeyError()``, ``RuntimeError()``, ``TimeoutError()``,
and every custom class constructed with no args. So the body kept the part that can be absent
and threw away ``type(exc).__name__``, the part that never is.

MEASURED: job 95883132086 (``D3: CockroachDB Resilience``, run 32189380431) failed on
``POST …/workloads/worker-blazing-rpg/exec`` with ``{"detail":"Internal server error",
"error":""}``. That red is still unattributed -- not because the server declined to say, but
because it said nothing and the caller could not distinguish those two.

⚠ THIS IS A PROPERTY TEST, NOT A STRING TEST. Asserting the source contains
``type(exc).__name__`` would pass on a branch that never runs, and would fail on an equivalent
rewrite. Each case DRIVES the handler and reads the body it produces.

⚠ NOT A DISCLOSURE CHANGE. ``str(exc)`` -- arbitrary, developer-authored, potentially far more
revealing -- was already on the wire. A class name is strictly less sensitive than the message
already being returned. The guard below pins that the *message* behaviour is unchanged.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent.parent
CONTROL_PLANE = API_DIR.parent
REPO_ROOT = CONTROL_PLANE.parent

for _p in (str(API_DIR), str(CONTROL_PLANE), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("ENVIRONMENT", "test")

import main  # noqa: E402


class _Boom(Exception):
    """A custom exception carrying no message -- the common shape in this codebase."""


def _body(resp) -> dict:
    return json.loads(bytes(resp.body).decode("utf-8"))


async def _handle(exc: Exception) -> dict:
    """Drive the REAL handler. It does not read `request`, so None is honest here."""
    resp = await main.global_exception_handler(None, exc)
    assert resp.status_code == 500
    return _body(resp)


# Every one of these has str(exc) == '' -- that is the whole point.
MESSAGELESS = [
    _Boom(),
    KeyError(),
    RuntimeError(),
    IndexError(),
    TimeoutError(),
    ValueError(),
]


@pytest.mark.parametrize("exc", MESSAGELESS, ids=lambda e: type(e).__name__)
async def test_a_messageless_exception_still_names_its_type(exc):
    """The regression. Every one of these produced `error: ""` before the fix."""
    assert str(exc) == "", "precondition of this test: the exception carries no message"

    body = await _handle(exc)

    assert body["error"], (
        f"a {type(exc).__name__} produced an EMPTY error field -- the caller cannot tell "
        "'the server declined to say' from 'there was nothing to say', which is how "
        "job 95883132086 became permanently unattributable"
    )
    assert type(exc).__name__ in body["error"], (
        "the error field is non-empty but does not identify the exception type, so it still "
        "cannot distinguish a TimeoutError from a KeyError"
    )


async def test_a_message_is_still_reported():
    """⚠ Guard the over-correction: naming the type must not DISCARD the message."""
    body = await _handle(RuntimeError("consul dataplane never became ready"))
    assert "consul dataplane never became ready" in body["error"], (
        "the message was dropped in favour of the type -- that trades one missing field for another"
    )
    assert "RuntimeError" in body["error"]


async def test_the_detail_field_is_unchanged():
    """The generic `detail` is a deliberate public-facing string. It is not what this fixes."""
    for exc in (_Boom(), RuntimeError("x")):
        body = await _handle(exc)
        assert body["detail"] == "Internal server error"


async def test_two_different_messageless_types_are_distinguishable():
    """The property the whole issue rests on, stated directly.

    Before the fix both bodies were byte-identical, so no downstream reader -- human or
    machine -- could tell these apart. That is the defect, not the wording.
    """
    a = await _handle(KeyError())
    b = await _handle(TimeoutError())
    assert a["error"] != b["error"], (
        "two unrelated failures produce identical 500 bodies -- the response carries no information about which one happened"
    )
