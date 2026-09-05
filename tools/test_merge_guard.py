#!/usr/bin/env python3
"""Exit-code contract for merge-guard.py.

⛔ `--self-test` covers leg 0 only — the holder check, which needs no forge. Legs 1-5
need a PR to exist, and those are exactly the legs that failed OPEN on #581: a parse
raised, every guard variable came back empty, every line printed a blank that read as
benign, and the merge proceeded.

⇒ So the case that matters here is `test_unparseable_gh_json_BLOCKS` — the reproduction
of that incident. A guard that returns 2 on garbage is the whole point of the file.

★ Every case drives the real `main()` with `pr_json` stubbed, so the exit code under
test is the one the tool actually returns.
"""
import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOLDER = "aaaaaaaa-1111-2222-3333-444444444444"
OTHER = "bbbbbbbb-5555-6666-7777-888888888888"
AUTH = f"HOLDER    session {HOLDER}\n"


def load():
    spec = importlib.util.spec_from_file_location("merge_guard", HERE / "merge-guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prd(base="main", gate="SUCCESS", reviews=None, state="OPEN",
        created="2020-01-01T00:00:00Z", sha="deadbee"):
    return {
        "baseRefName": base, "state": state, "headRefOid": sha, "createdAt": created,
        "reviews": reviews if reviews is not None else [],
        "statusCheckRollup": [{"name": "hermetic suites (gating)", "conclusion": gate}],
    }


def drive(mod, data, argv, numstat="10\t1\tf.py", session=HOLDER, auth=AUTH):
    mod.pr_json = lambda n, f: (data() if callable(data) else data)
    mod.sh = lambda a, allow_fail=False: numstat if a[:2] == ["git", "diff"] else ""
    tmp = HERE / ".test_authority.md"
    tmp.write_text(auth, encoding="utf-8")
    old = sys.argv
    sys.argv = ["merge-guard.py"] + argv + ["--session", session, "--authority", str(tmp)]
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = mod.main()
    finally:
        sys.argv = old
        tmp.unlink(missing_ok=True)
    return rc, out.getvalue(), err.getvalue()


class ExitContract(unittest.TestCase):

    def setUp(self):
        self.mod = load()

    # ── ⛔ the incident this file exists for ──

    def test_unparseable_gh_json_BLOCKS(self):
        """#581: a control character made json.load raise, the guard printed blanks,
        and the merge proceeded. It must now exit 2."""
        def boom(n, f):
            raise self.mod.Unestablished("gh --json was not parseable: control char")
        self.mod.pr_json = boom
        tmp = HERE / ".test_authority.md"
        tmp.write_text(AUTH, encoding="utf-8")
        old = sys.argv
        sys.argv = ["merge-guard.py", "1", "--session", HOLDER, "--authority", str(tmp)]
        out = io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                rc = self.mod.main()
        finally:
            sys.argv = old
            tmp.unlink(missing_ok=True)
        self.assertEqual(rc, 2, "an unparseable forge response must BLOCK, not print a blank")
        self.assertIn("UNESTABLISHED", out.getvalue())

    # ── leg 0 ──

    def test_non_holder_blocks(self):
        rc, out, _ = drive(self.mod, prd(), ["1"], session=OTHER)
        self.assertEqual(rc, 1)
        self.assertIn("REFUSE", out)

    def test_holder_clears(self):
        rc, out, _ = drive(self.mod, prd(), ["1"])
        self.assertEqual(rc, 0)
        self.assertIn("CLEAR", out)

    def test_last_holder_wins_and_first_is_stale(self):
        """⛔ The file appends successions; a grep -m1 returns the STALE holder."""
        two = f"HOLDER    session {HOLDER}\nprose\nHOLDER    session {OTHER}\n"
        rc_new, _, _ = drive(self.mod, prd(), ["1"], session=OTHER, auth=two)
        rc_old, _, _ = drive(self.mod, prd(), ["1"], session=HOLDER, auth=two)
        self.assertEqual(rc_new, 0, "the LAST holder is current")
        self.assertEqual(rc_old, 1, "the FIRST holder is stale and must be refused")

    def test_missing_authority_file_is_void(self):
        old = sys.argv
        sys.argv = ["merge-guard.py", "1", "--authority", "/nonexistent/AUTH.md"]
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = self.mod.main()
        finally:
            sys.argv = old
        self.assertEqual(rc, 2)

    # ── legs 1-5 ──

    def test_non_main_base_blocks(self):
        rc, out, _ = drive(self.mod, prd(base="dx/other"), ["1"])
        self.assertEqual(rc, 1)
        self.assertIn("1 base == main", out)

    def test_red_gate_blocks(self):
        rc, _, _ = drive(self.mod, prd(gate="FAILURE"), ["1"])
        self.assertEqual(rc, 1)

    def test_absent_gate_is_unestablished_not_a_pass(self):
        d = prd(); d["statusCheckRollup"] = []
        rc, out, _ = drive(self.mod, d, ["1"])
        self.assertEqual(rc, 1)
        self.assertIn("UNESTABLISHED", out)

    def test_changes_requested_blocks(self):
        rc, _, _ = drive(self.mod, prd(reviews=[{"state": "CHANGES_REQUESTED"}]), ["1"])
        self.assertEqual(rc, 1)

    def test_net_negative_three_dot_blocks(self):
        """#510: a stale branch merges as a revert with every check green."""
        rc, out, _ = drive(self.mod, prd(), ["1"], numstat="1\t900\tf.py")
        self.assertEqual(rc, 1)
        self.assertIn("net -899", out)

    def test_empty_numstat_is_unestablished(self):
        rc, out, _ = drive(self.mod, prd(), ["1"], numstat="")
        self.assertEqual(rc, 1)
        self.assertIn("UNESTABLISHED", out)

    def test_fresh_pr_blocks_on_age(self):
        """#224: 25 of 100 PRs merged inside 60s — the merger outran the author."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rc, out, _ = drive(self.mod, prd(created=now), ["1"])
        self.assertEqual(rc, 1)
        self.assertIn("5 age at merge", out)

    def test_merged_pr_is_unestablished(self):
        rc, _, _ = drive(self.mod, prd(state="MERGED"), ["1"])
        self.assertEqual(rc, 2)

    def test_no_pr_named_is_the_HOLDER_CHECK_not_a_refusal(self):
        """⛔ CONTRACT CHANGE, and the reason is #193/#296/#302/#304's own runnable
        check: it invokes this with `--session <id>` and NO pr. The first version
        returned 2 there, so the condition's own command could not be satisfied by the
        instrument written for it.

        ⚠ This test previously asserted `rc == 2`. It is REPLACED rather than deleted,
        and with MORE coverage than it had — both directions plus the VOID path — so
        the change is a contract move, not a test bent to fit new code."""
        rc_holder, out_h, _ = drive(self.mod, prd(), [], session=HOLDER)
        self.assertEqual(rc_holder, 0, "the recorded holder may merge")
        self.assertIn("MAY MERGE", out_h)

        rc_other, out_o, _ = drive(self.mod, prd(), [], session=OTHER)
        self.assertEqual(rc_other, 1, "a non-holder is REFUSED, not VOIDed")
        self.assertIn("REFUSED", out_o)

        # ⛔ VOID is still reachable — an unreadable authority file establishes nothing
        old = sys.argv
        sys.argv = ["merge-guard.py", "--session", HOLDER, "--authority", "/nonexistent/A.md"]
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc_void = self.mod.main()
        finally:
            sys.argv = old
        self.assertEqual(rc_void, 2, "an unreadable authority file is still VOID")

    # ── ⛔ criterion 4: shown to FAIL ──

    def test_control_can_fail(self):
        mod = load()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mod.self_test(), 0, "baseline passes before sabotage")
        mod.holder_check = lambda text, session: (True, "")   # authorise anyone
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mod.self_test(), 1, "a holder check that passes anyone must red")


if __name__ == "__main__":
    unittest.main(verbosity=2)
