#!/usr/bin/env python3
"""Exit-code contract for late-push.py.

⛔ `--self-test` covers classify(), which is pure. It cannot cover the paths a caller
reads as "the board is clean", and those are where a detector fails safe-looking:

    an empty patch-id set   every candidate then reads as LOST — a VOID, not a finding
    no PRs enumerated       "nothing was late" vs "nothing was looked at" (#317)
    an unreadable head ref  a deleted branch is UNCHECKED, never clean

★ Every case drives the real main() with `sh` stubbed, so the exit code under test is
the one the tool returns.
"""
import importlib.util, io, json, os, sys, unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
HERE = Path(__file__).resolve().parent


def load():
    s = importlib.util.spec_from_file_location("lp", HERE / "late-push.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def drive(mod, prs, mainlog, headlog, patchids, argv=None):
    """Stub `sh` by command shape. patchids maps rev -> patch-id."""
    def fake(args, allow_fail=False, stdin=None):
        if args[:2] == ["git", "fetch"]:
            return ""
        if args[:2] == ["gh", "pr"]:
            return json.dumps(prs if args[2] == "list" else prs[0])
        if args[:2] == ["git", "log"] and "origin/main" in args:
            return "\n".join(mainlog)
        if args[:2] == ["git", "log"]:
            return "\n".join(headlog)
        if args[:2] == ["git", "show"]:
            # ⚠ Distinguish by --stat, NOT by allow_fail: patch_id() calls `git show`
            # with allow_fail=True, so keying on that made the stub return the stat
            # block where the tool expected a diff, and the finding silently vanished.
            # My stub's defect, found by the test failing — which is the suite working.
            if "--stat" in args:
                return " f.md | 1 +\n 1 file changed"
            return f"DIFF-OF-{args[-1]}"
        if args[:2] == ["git", "patch-id"]:
            return f"{patchids.get((stdin or '').replace('DIFF-OF-', ''), 'none')} x"
        return ""
    mod.sh = fake
    old = sys.argv; sys.argv = ["late-push.py"] + (argv or [])
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = mod.main()
    finally:
        sys.argv = old
    return rc, out.getvalue(), err.getvalue()


PR = [{"number": 339, "mergedAt": "2026-08-20T19:56:18Z",
       "headRefName": "dev2/x", "headRefOid": "abc"}]


class ExitContract(unittest.TestCase):
    def setUp(self): self.mod = load()

    def test_late_and_absent_is_a_finding(self):
        rc, out, _ = drive(self.mod, PR, ["M1"], ["L1 2026-08-20T19:57:18+00:00"],
                           {"M1": "pidM", "L1": "pidL"})
        self.assertEqual(rc, 1)
        self.assertIn("#339", out)
        self.assertIn("60s AFTER", out)

    def test_late_but_content_landed_is_NOT_a_finding(self):
        """⛔ The known-negative. A squash gives every commit a new sha, so ancestry
        would report this lost; patch-id must not."""
        rc, out, _ = drive(self.mod, PR, ["M1"], ["L1 2026-08-20T19:57:18+00:00"],
                           {"M1": "same", "L1": "same"})
        self.assertEqual(rc, 0)
        self.assertIn("no late push lost content", out)

    def test_commit_before_merge_is_not_late(self):
        rc, _, _ = drive(self.mod, PR, ["M1"], ["L1 2026-08-20T19:00:00+00:00"],
                         {"M1": "a", "L1": "b"})
        self.assertEqual(rc, 0)

    def test_empty_main_patchid_set_is_VOID_not_a_finding(self):
        """⛔ The load-bearing refusal: with no comparison set every candidate reads as
        lost, which is the loudest possible wrong answer."""
        rc, _, err = drive(self.mod, PR, [], ["L1 2026-08-20T19:57:18+00:00"], {})
        self.assertEqual(rc, 2)
        self.assertIn("comparison set is EMPTY", err)

    def test_no_prs_is_VOID_not_clean(self):
        rc, _, err = drive(self.mod, [], ["M1"], [], {"M1": "p"})
        self.assertEqual(rc, 2)
        self.assertIn("nothing was enumerated", err)

    def test_unreadable_head_ref_is_counted_not_ignored(self):
        rc, out, _ = drive(self.mod, PR, ["M1"], [], {"M1": "p"})
        self.assertEqual(rc, 0)
        self.assertIn("unreadable (deleted or unfetched): 1", out)
        self.assertIn("UNCHECKED, not clean", out)

    def test_control_can_fail(self):
        mod = load()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(mod.self_test(), 0)
        mod.classify = lambda m, c, p: "IN-PR"      # never reports anything late
        with redirect_stdout(io.StringIO()):
            self.assertEqual(mod.self_test(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
