#!/usr/bin/env python3
"""The three producers of `exit 2` must carry three distinct marker signatures.

⛔ Without this, the test is vacuous: every case exits 2, so a test asserting only
on the exit code passes whatever the markers say -- which is the defect (#58), not
a test of it. Every assertion here is on the MARKERS, and the exit code is recorded
only to show it does NOT discriminate.
"""
import os
import subprocess
import sys
import unittest

# ⛔ A STALE __pycache__ SILENTLY SERVES THE PRE-MUTATION MODULE, and the dangerous
# class is the COMMON one: Python invalidates a .pyc on mtime + SIZE, so a
# SIZE-PRESERVING mutation (==/!=, a flag flip, a token swap) applied in the same
# second leaves both unchanged and the cache is served. Measured with a
# 4-cell table: {clean,mutant} x {cache cleared,stale} -> the mutant PASSED on a stale
# cache and failed 3 checks once cleared. Every suite here loads its tool through
# spec_from_file_location, so a false SURVIVED sends you rewriting a correct test.
# CI is safe (fresh checkout, no cache); local mutation testing was not.
sys.dont_write_bytecode = True
# ⚠ and the env var too: a SUBPROCESS does not inherit sys.dont_write_bytecode,
# which is why three suites still produced a cache after the first fix.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

TOOLS = os.path.dirname(os.path.abspath(__file__))
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def run(args, cwd=None):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       cwd=cwd or os.path.dirname(TOOLS))
    marks = [l.split() for l in p.stderr.splitlines() if l.startswith("NFORMA-")]
    return p.returncode, [(m[0], m[1] if len(m) > 1 else "") for m in marks]


class ThreeProducersOfTwo(unittest.TestCase):
    """All three exit 2. Only the markers tell them apart."""

    def test_our_own_established_nothing(self):
        rc, m = run([f"{TOOLS}/grant-check.py", "--list", "--ref", EMPTY_TREE])
        self.assertEqual(rc, 2)
        self.assertIn(("NFORMA-RUN", "grant-check"), m)
        self.assertIn(("NFORMA-RESULT", "ESTABLISHED-NOTHING"), m)

    def test_argparse_rejects_the_arguments(self):
        rc, m = run([f"{TOOLS}/grant-check.py", "--no-such-flag"])
        self.assertEqual(rc, 2)
        self.assertIn(("NFORMA-RUN", "grant-check"), m)
        self.assertIn(("NFORMA-RESULT", "BAD-ARGS"), m)

    def test_runtime_refuses_the_file(self):
        rc, m = run([f"{TOOLS}/definitely-not-a-tool.py"])
        self.assertEqual(rc, 2)
        self.assertEqual(m, [], "a file the runtime never opened cannot emit a marker")

    def test_the_exit_code_does_not_discriminate(self):
        """⛔ The control. If this ever fails, exit 2 became informative and the
        markers may be redundant -- which would be worth knowing, so it is asserted
        rather than assumed."""
        codes = {run([f"{TOOLS}/grant-check.py", "--list", "--ref", EMPTY_TREE])[0],
                 run([f"{TOOLS}/grant-check.py", "--no-such-flag"])[0],
                 run([f"{TOOLS}/definitely-not-a-tool.py"])[0]}
        self.assertEqual(codes, {2}, "all three still collide on 2")


class StartedAndDied(unittest.TestCase):
    def test_crash_after_start_leaves_run_without_result(self):
        """The state the exit code cannot express at all."""
        src = open(f"{TOOLS}/pane-binding.py").read().replace(
            "def registry(root):", 'def registry(root):\n    raise RuntimeError("injected")', 1)
        tmp = os.path.join(TOOLS, "_tmp_crash_probe.py")
        open(tmp, "w").write(src)
        try:
            rc, m = run([tmp])
            self.assertEqual(rc, 1)
            self.assertIn(("NFORMA-RUN", "pane-binding"), m)
            self.assertFalse([x for x in m if x[0] == "NFORMA-RESULT"],
                             "a died-part-way run must NOT carry a terminal marker")
        finally:
            os.unlink(tmp)

    def test_import_time_crash_is_indistinguishable_from_a_refused_file(self):
        """⚠ A STATED BOUND, asserted so it cannot rot into a false claim.

        begin() runs inside the module, so a crash during IMPORT emits nothing --
        identical to a file the runtime refused. Both are correctly 'never reached
        our code'; stderr's first line separates them (Traceback vs can't open
        file). The markers do not, and this test exists to say so out loud."""
        src = open(f"{TOOLS}/pane-binding.py").read().replace(
            "import argparse", "import argparse, no_such_module_xyz", 1)
        tmp = os.path.join(TOOLS, "_tmp_import_probe.py")
        open(tmp, "w").write(src)
        try:
            rc, m = run([tmp])
            self.assertEqual(m, [], "import-time crash emits no marker — the bound")
        finally:
            os.unlink(tmp)


class SurvivesThePipe(unittest.TestCase):
    def test_markers_survive_the_construct_that_destroys_the_exit_code(self):
        """⛔ The whole point. `cmd | head` returns HEAD's status; stderr is not
        piped and arrives intact."""
        repo = os.path.dirname(TOOLS)
        p = subprocess.run(
            f'{sys.executable} tools/pane-binding.py 2>/tmp/_rm_err | head -2 >/dev/null; echo $?',
            shell=True, capture_output=True, text=True, cwd=repo)
        self.assertEqual(p.stdout.strip(), "0", "head's status masks the tool's — the defect")
        with open("/tmp/_rm_err") as fh:
            err = fh.read()
        self.assertIn("NFORMA-RUN", err)
        self.assertIn("NFORMA-RESULT", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
