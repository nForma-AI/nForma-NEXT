"""The UNKNOWN 502 must not narrate a cause the sentinel cannot carry (#1177).

★ WHY THIS IS BEHAVIOURAL AND NOT A SOURCE-TEXT SCAN. The sibling suite
``test_kill_never_ran_sentinel.py`` asserts on ``inspect.getsource``. That catches a branch
being deleted, but it cannot catch the branch producing a *wrong sentence*, because the
sentence is a substring of the source either way. This file drives the handler and reads the
502 the CI operator actually receives.

★ WHAT THE BUG WAS. The branch asserted that ``exit=-1`` "on the measured path means the
command TIMED OUT rather than that it failed to reach the container". Measured on 8 of 8
occurrences (0.70 s - 6.06 s against a 30 s timeout), that clause was false. It is false by
CONSTRUCTION, not by luck: ``provider_shell_client.exec_command`` has seven routes to -1, and
the two that are timeouts BOTH append ``f"Timeout after {timeout}s"`` to stderr. So an
``exit=-1`` carrying an EMPTY stderr excludes the timeout branches outright, using evidence
already present in the same response.

★ WHY IT MATTERS RATHER THAN BEING A WORDING NIT. ``kill -9 1`` tears down PID 1, so a shell
session hanging up mid-command is the SUCCESS shape -- the handler says exactly this, and
``_classify_kill_outcome`` gates the non-delivery branch to avoid inverting the bug. The -1
check is NOT gated the same way, so this 502 fires hardest on the shape most consistent with
a kill that worked, and it accounted for 15-16 of 33 C/D reds (#1203).

⚠ The fix is NOT to claim delivery. UNKNOWN stays UNKNOWN -- "session ended before a result"
is also consistent with a socket that died before the command was delivered. What must go is
the invented cause; what must appear is the discriminator the handler already holds.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

API = Path(__file__).resolve().parents[1]
for _p in (str(API), str(API.parents[1])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import handlers.workloads as w  # noqa: E402

ORG = "org-1"
CLUSTER = "cluster-1"
DSEQ = "1787100113503"


class _Doc:
    exists = True

    @staticmethod
    def to_dict():
        return {
            "organization_id": ORG,
            "cluster_id": CLUSTER,
            "status": "active",
            "provider_address": "akash1aaul837r7en7hpk9wv2svg8u78fdq0t2j2e82z",
            "service_name": "web",
        }


class _DB:
    def collection(self, _name):
        return self

    def document(self, _id):
        return self

    def get(self):
        return _Doc()


async def _raise_kill_502(exec_result: dict) -> str:
    """Drive the real handler with a stubbed exec layer; return the 502 detail."""

    async def _fake_client(_mod):
        return _DB()

    async def _fake_exec(**_kwargs):
        return exec_result

    with patch.object(w, "_get_firestore_client", _fake_client), patch.object(w, "_exec_akash_deployment", _fake_exec):
        with pytest.raises(HTTPException) as exc:
            await w._kill_akash_deployment(
                organization_id=ORG,
                cluster_id=CLUSTER,
                deployment_id=DSEQ,
                grace_period=0,
            )
    assert exc.value.status_code == 502, "the indeterminate sentinel must not report a kill"
    return str(exc.value.detail)


# The exact shape measured in all eight occurrences: sentinel, empty stderr, sub-second.
_MEASURED_SHAPE = {"exit_code": -1, "stdout": "", "stderr": "", "duration_ms": 780}


async def test_the_502_does_not_claim_the_command_timed_out():
    """The regression itself. This is the sentence that was false 8 times out of 8."""
    detail = await _raise_kill_502(dict(_MEASURED_SHAPE))
    low = detail.lower()
    assert "means the command timed out" not in low, (
        "the UNKNOWN branch asserts a cause the sentinel cannot carry -- and asserts the ONE "
        "cause an empty stderr excludes, since both timeout routes write 'Timeout after <n>s'"
    )
    assert "rather than that it failed to reach the container" not in low, (
        "the branch still rules out non-delivery, which is the reading this shape most resembles"
    )


async def test_the_502_reports_the_discriminator_it_already_holds():
    """Not enough to delete the claim -- the reader needs what refutes it."""
    detail = await _raise_kill_502(dict(_MEASURED_SHAPE))
    assert "780ms" in detail, (
        "elapsed time is returned by every exec path as duration_ms and is dropped from the "
        "report; without it a reader cannot check the narration against the observation"
    )
    assert "EMPTY" in detail, "stderr emptiness is the load-bearing discriminator -- it EXCLUDES both timeout routes"


async def test_the_502_still_refuses_to_report_non_delivery():
    """⚠ Guard the over-correction. UNKNOWN must not become an assertion of failure."""
    detail = await _raise_kill_502(dict(_MEASURED_SHAPE))
    assert "may or may not" in detail, "the branch no longer states that the outcome is undetermined"
    assert "never reached the container" not in detail.lower(), "regressed to asserting non-delivery it cannot prove"
    assert "do not read a retry's success" in detail.lower(), (
        "the retry caveat was dropped -- it is the part that stops a green rerun laundering this"
    )


async def test_a_real_timeout_is_not_labelled_EMPTY():
    """The inverse case. A genuine timeout DOES populate stderr, and must read differently.

    This is the mutation that would kill a lazy fix: hardcoding "EMPTY" would satisfy every
    assertion above while destroying the distinction the change exists to make.
    """
    detail = await _raise_kill_502({"exit_code": -1, "stdout": "", "stderr": "Timeout after 30s", "duration_ms": 30001})
    assert "stderr EMPTY" not in detail, (
        "a timeout carries stderr and must not be reported with the empty-stderr shape -- "
        "collapsing the two rebuilds the defect one level up"
    )
    assert "Timeout after 30s" in detail, "the provider's own stderr must still reach the reader"
    assert "30001ms" in detail


async def test_a_delivered_kill_is_not_a_502():
    """Bound the change: it must not turn working kills into failures.

    `kill -9 1` tears down PID 1, so a NON-ZERO exit is the success shape here. This is the
    inversion `_classify_kill_outcome` exists to prevent, and the one a fix in this area is
    most likely to reintroduce.
    """

    async def _fake_client(_mod):
        return _DB()

    async def _fake_exec(**_kwargs):
        return {"exit_code": 137, "stdout": "", "stderr": "", "duration_ms": 900}

    with patch.object(w, "_get_firestore_client", _fake_client), patch.object(w, "_exec_akash_deployment", _fake_exec):
        got = await w._kill_akash_deployment(organization_id=ORG, cluster_id=CLUSTER, deployment_id=DSEQ, grace_period=0)
    assert got["status"] == "killed"
    assert got["exit_code"] == 137, "the evidence must be reported, not just the conclusion"
