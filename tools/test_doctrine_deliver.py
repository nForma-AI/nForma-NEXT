#!/usr/bin/env python3
"""Exit-code contract for doctrine-deliver.py.

⛔ `--self-test` covers the DECISIONS — estate gate, role match, payload guard, send
precondition. It does not cover the paths a caller reads as "nothing to do", and those
are where a delivery tool fails safe-looking:

    no pane in this estate     the LIVE case today, and it must be exit 2, not exit 0
    zero panes enumerated      "nothing is behind" vs "nothing was enumerated" (#317)
    no roles named             this tool does not decide who is behind
    a payload that is not a pointer   the forgery channel, refused before any send

★ Every case drives the real `main()` with `list_panes` stubbed, so the exit code under
test is the one the tool actually returns — not a re-implementation of it.

⛔⛔ THE LOAD-BEARING CASE IS `test_send_is_gated_by_estate`. A delivery tool whose estate
gate can be bypassed is the fourth cross-estate misroute (#172, #301, #426) on a
schedule. It asserts that NOTHING is sent when the gate refuses — not merely that the
exit code is 2.
"""
import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = "/repo/nForma-NEXT"
AWAY = "/repo/lang-nextjs2"


def load():
    spec = importlib.util.spec_from_file_location("doctrine_deliver", HERE / "doctrine-deliver.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pane(pid, title, wt=HOME, state="waiting", locked=False):
    return {"id": pid, "title": title, "worktreeId": wt,
            "agentState": state, "isInputLocked": locked}


class FakeDC:
    """Records every rpc call so a test can assert that NOTHING was sent."""

    def __init__(self):
        self.calls = []

    def rpc(self, url, auth, method, params=None, sid=None):
        self.calls.append((method, params))
        return {"result": {}}

    def payload(self, res):
        return res.get("result", {})

    def sends(self):
        return [p for m, p in self.calls
                if m == "tools/call" and (p or {}).get("name") == "terminal.sendCommand"]


def drive(mod, panes, argv, dc=None):
    """Run the real main() with the network stubbed. Returns (rc, stdout, stderr, dc)."""
    dc = dc or FakeDC()
    mod.list_panes = lambda: (panes, ("url", "auth", "sid"), dc)
    mod.repo_root = lambda explicit=None: (explicit or HOME)
    old = sys.argv
    sys.argv = ["doctrine-deliver.py"] + argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = mod.main()
    finally:
        sys.argv = old
    return rc, out.getvalue(), err.getvalue(), dc


BASE = ["--roles", "DEV1", "--ref", "cf263fe", "--paths", "prompts/DEV.md"]


class ExitContract(unittest.TestCase):

    def setUp(self):
        self.mod = load()

    # ── VOID ──

    def test_no_pane_in_this_estate_is_void(self):
        """⛔ THE LIVE CASE, 2026-09-05: 7 panes addressable, every one another project's."""
        rc, _, err, _ = drive(self.mod, [pane("t1", "DEV1-lang", AWAY)], BASE)
        self.assertEqual(rc, 2, "a foreign-only fleet must VOID, never report nothing-to-do")
        self.assertIn("NO PANE IN THIS ESTATE", err)
        self.assertIn(AWAY, err, "the refusal must NAME the estates that were present")
        self.assertIn("ADDABLE", err, "an absence report must name its remedy (#73)")

    def test_zero_panes_is_void_not_a_quiet_fleet(self):
        rc, _, err, _ = drive(self.mod, [], BASE)
        self.assertEqual(rc, 2)
        self.assertIn("ZERO panes", err)

    def test_no_roles_named_is_void(self):
        """This tool does not decide who is behind; doctrine-watch does."""
        rc, _, err, _ = drive(self.mod, [pane("t1", "DEV1")],
                              ["--ref", "cf263fe", "--paths", "prompts/DEV.md"])
        self.assertEqual(rc, 2)
        self.assertIn("does not decide who is behind", err)

    def test_bad_ref_refuses_before_any_send(self):
        """A payload that is not a pointer is refused, and nothing is sent."""
        rc, _, err, dc = drive(self.mod, [pane("t1", "DEV1")],
                               ["--roles", "DEV1", "--ref", "not-a-sha",
                                "--paths", "prompts/DEV.md", "--send"])
        self.assertEqual(rc, 2)
        self.assertIn("refusing to send", err)
        self.assertEqual(dc.sends(), [], "nothing may be sent when the payload is refused")

    # ── the load-bearing one ──

    def test_send_is_gated_by_estate(self):
        """⛔ --send must send NOTHING when the estate gate refuses. Asserting the exit
        code alone would pass a tool that sent first and reported 2 afterwards."""
        rc, _, _, dc = drive(self.mod,
                             [pane("t1", "TEAMLEAD-lang", AWAY), pane("t2", "DEV1-lang", AWAY)],
                             BASE + ["--send"])
        self.assertEqual(rc, 2)
        self.assertEqual(dc.sends(), [], "a refused estate must produce ZERO sends")

    # ── verdicts ──

    def test_dry_run_is_the_default_and_sends_nothing(self):
        rc, out, _, dc = drive(self.mod, [pane("t1", "DEV1")], BASE)
        self.assertEqual(rc, 1, "a pending pointer is a finding")
        self.assertIn("WOULD SEND", out)
        self.assertEqual(dc.sends(), [], "the default must not write into another pane")

    def test_send_queues_the_pointer(self):
        rc, out, _, dc = drive(self.mod, [pane("t1", "DEV1")], BASE + ["--send"])
        self.assertEqual(rc, 1)
        self.assertIn("QUEUED", out)
        sends = dc.sends()
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0]["arguments"]["command"],
                         "doctrine ref=cf263fe paths=prompts/DEV.md")

    def test_queued_is_never_reported_as_delivered(self):
        """#8, #308: sendCommand returns on SUBMIT. DELIVERED is prompt-delivery.py's."""
        _, out, _, _ = drive(self.mod, [pane("t1", "DEV1")], BASE + ["--send"])
        self.assertIn("QUEUED is not DELIVERED", out)
        self.assertNotIn("DELIVERED  ", out, "must not emit DELIVERED as a per-role verdict")

    def test_collision_is_unestablished_not_a_pick(self):
        """#247: two live panes both rendered DEV4. #355: say so, never return one."""
        rc, out, _, dc = drive(self.mod, [pane("t1", "DEV1"), pane("t2", "DEV1")],
                               BASE + ["--send"])
        self.assertIn("UNESTABLISHED", out)
        self.assertEqual(dc.sends(), [], "a collided role must not be delivered to")
        self.assertEqual(rc, 0, "nothing pending: the collision is reported, not queued")

    def test_working_pane_is_held_not_overwritten(self):
        """#136: refuse if the box is busy — never overwrite."""
        rc, out, _, dc = drive(self.mod, [pane("t1", "DEV1", state="working")],
                               BASE + ["--send"])
        self.assertIn("HELD", out)
        self.assertEqual(dc.sends(), [])
        self.assertEqual(rc, 0)

    def test_nested_worktree_pane_is_in_this_estate(self):
        rc, out, _, _ = drive(self.mod, [pane("t1", "DEV1", HOME + "/.claude/worktrees/dev1")],
                              BASE)
        self.assertEqual(rc, 1)
        self.assertIn("WOULD SEND", out)

    def test_prefix_similar_sibling_estate_is_refused(self):
        """`/repo/nForma-NEXT-other` starts with `/repo/nForma-NEXT`. A string prefix
        would admit it; resolved-path containment must not."""
        rc, _, err, dc = drive(self.mod, [pane("t1", "DEV1", HOME + "-other")], BASE + ["--send"])
        self.assertEqual(rc, 2)
        self.assertEqual(dc.sends(), [])

    def test_output_states_the_unmeasured_gap(self):
        _, out, _, _ = drive(self.mod, [pane("t1", "DEV1")], BASE)
        self.assertIn("RE-READ", out)
        self.assertIn("UNMEASURED", out)

    # ── ⛔ criterion 4: shown to FAIL ──

    def test_control_can_fail(self):
        """Sabotage the payload guard; the self-test MUST go red. A control that cannot
        fail is not a control (#26, #372)."""
        mod = load()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mod.self_test(), 0, "baseline: controls pass before sabotage")
        mod.validate_payload = lambda text: (True, "")   # accept anything
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mod.self_test(), 1, "a payload guard that accepts prose must red")


if __name__ == "__main__":
    unittest.main(verbosity=2)
