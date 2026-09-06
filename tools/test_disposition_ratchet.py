#!/usr/bin/env python3
"""Paired suite for disposition-ratchet.py — the legs --self-test structurally cannot reach.

★ `--self-test` drives `verdict()` with synthetic counts and needs no filesystem. Everything
here needs a TREE: the census, the baseline file, the delegation to disposition-scan, and the
one property that matters most and is invisible to a pure function — that running the check
TWICE gives the same answer.

⛔ THAT LAST ONE IS THE POINT. #598: `index-watch.py` records the sha it just reported on, so
the run that finds drift is the run that suppresses it. A ratchet with the same shape would
lower its own floor on the DROPPED path and silently ratify whatever it just saw. The
idempotence test below fails if this tool ever grows that behaviour.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.dont_write_bytecode = True          # ⛔ a size-preserving edit defeats mtime+size caching

HERE = Path(__file__).resolve().parent

# A file whose PRINTED refusal names no disposition -> UNNAMED
UNNAMED_SRC = '''#!/usr/bin/env python3
"""A tool that refuses without saying what kind of refusal it is."""
import sys
def main():
    print("VOID - established nothing", file=sys.stderr)
    return 2
'''

# ⚠ The disposition must be IN the printed refusal. A docstring mention must NOT count —
# that is the use-versus-mention bug disposition-scan already caught in itself.
NAMED_SRC = '''#!/usr/bin/env python3
"""A tool that names the kind of its refusal."""
import sys
def main():
    print("VOID - established nothing. ADDABLE - the operator: add the config", file=sys.stderr)
    return 2
'''

MENTION_ONLY_SRC = '''#!/usr/bin/env python3
"""This docstring says ADDABLE - but the refusal below names nothing."""
import sys
def main():
    print("VOID - established nothing", file=sys.stderr)
    return 2
'''

NO_PATH_SRC = '''#!/usr/bin/env python3
"""A tool with no printed refusal at all."""
def main():
    return 0
'''


def load():
    p = HERE / "disposition-ratchet.py"
    spec = importlib.util.spec_from_file_location("disposition_ratchet", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Tree:
    """A throwaway repo carrying a real disposition-scan.py, because the tool DELEGATES to it
    and a stub would test the stub. ⚠ Measurement by substitution measures the substitute."""

    def __init__(self, files):
        self.d = tempfile.mkdtemp()
        t = Path(self.d) / "tools"
        t.mkdir()
        (t / "disposition-scan.py").write_text(
            (HERE / "disposition-scan.py").read_text(encoding="utf-8"), encoding="utf-8")
        for name, src in files.items():
            (t / name).write_text(src, encoding="utf-8")
        self.tools = t

    def __enter__(self):
        return self

    def __exit__(self, *a):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)


def run(mod, root, baseline, argv_record=False):
    """Drive report()/record() with BASELINE pointed at a temp file."""
    old = mod.BASELINE
    mod.BASELINE = baseline
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = mod.record(root) if argv_record else mod.report(root)
    except Exception as exc:                       # Void included — main() maps it to 2
        mod.BASELINE = old
        return type(exc).__name__, out.getvalue(), str(exc)
    mod.BASELINE = old
    return rc, out.getvalue(), err.getvalue()


class Ratchet(unittest.TestCase):

    def setUp(self):
        self.mod = load()

    # ── the transition it exists for ──────────────────────────────────────────────

    def test_a_NEW_unnamed_refusal_makes_it_GROW(self):
        """⛔ THE KNOWN-POSITIVE. Floor of 1, two UNNAMED files present -> exit 1."""
        with Tree({"a.py": UNNAMED_SRC, "b.py": UNNAMED_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 1}), encoding="utf-8")
            rc, out, _ = run(self.mod, t.d, b)
        self.assertEqual(rc, 1)
        self.assertIn("THE COUNT GREW", out)
        self.assertIn("1 -> 2", out)

    def test_holding_at_the_floor_PASSES(self):
        """★ KNOWN-NEGATIVE. The same two files with a floor of 2 must NOT fail — a ratchet
        that reds on history teaches that the gate is noise, which is #73's whole argument."""
        with Tree({"a.py": UNNAMED_SRC, "b.py": UNNAMED_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 2}), encoding="utf-8")
            rc, out, _ = run(self.mod, t.d, b)
        self.assertEqual(rc, 0)
        self.assertIn("held at the floor", out)

    def test_a_DROP_passes_and_says_the_floor_can_be_lowered(self):
        with Tree({"a.py": UNNAMED_SRC, "ok.py": NAMED_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 5}), encoding="utf-8")
            rc, out, _ = run(self.mod, t.d, b)
        self.assertEqual(rc, 0)
        self.assertIn("floor CAN be lowered", out)

    # ── ⛔ #598's property: the check must be RE-RUNNABLE ──────────────────────────

    def test_reporting_a_DROP_does_NOT_write_the_baseline(self):
        """⛔ THE REGRESSION THAT MATTERS. index-watch (#598) records what it reports, so its
        second run says 'quiet' having checked nothing — a SKIP that reads as a PASS, and it
        destroys the finding it just made. This asserts byte-identical baseline and
        byte-identical output across two runs."""
        with Tree({"a.py": UNNAMED_SRC, "ok.py": NAMED_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 5}), encoding="utf-8")
            before = b.read_bytes()
            rc1, out1, _ = run(self.mod, t.d, b)
            after = b.read_bytes()
            rc2, out2, _ = run(self.mod, t.d, b)
        self.assertEqual(before, after, "reporting must not rewrite the floor")
        self.assertEqual(rc1, rc2, "the second run must reach the same verdict")
        self.assertIn("floor CAN be lowered", out2,
                      "the finding must survive being confirmed")

    # ── --record is a commitment, and only tightens ────────────────────────────────

    def test_record_REFUSES_to_raise_the_floor(self):
        """⛔ A ratchet that can be loosened is not a ratchet."""
        with Tree({"a.py": UNNAMED_SRC, "b.py": UNNAMED_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 1}), encoding="utf-8")
            rc, _, err = run(self.mod, t.d, b, argv_record=True)
            kept = json.loads(b.read_text(encoding="utf-8"))["unnamed"]
        self.assertEqual(rc, 1)
        self.assertIn("REFUSED", err)
        self.assertEqual(kept, 1, "the floor must be untouched after a refusal")

    def test_record_DOES_lower_the_floor(self):
        """★ The other direction, without which the refusal above proves nothing."""
        with Tree({"a.py": UNNAMED_SRC, "ok.py": NAMED_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 9}), encoding="utf-8")
            rc, out, _ = run(self.mod, t.d, b, argv_record=True)
            got = json.loads(b.read_text(encoding="utf-8"))["unnamed"]
        self.assertEqual(rc, 0)
        self.assertEqual(got, 1)

    # ── use-versus-mention, inherited from the delegated predicate ─────────────────

    def test_a_docstring_MENTION_does_not_count_as_naming(self):
        """⚠ The bug disposition-scan caught in its own first version. Asserted here so the
        delegation cannot silently regress it: a file that says ADDABLE in a DOCSTRING while
        its printed refusal names nothing must still count as UNNAMED."""
        with Tree({"m.py": MENTION_ONLY_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 0}), encoding="utf-8")
            rc, out, _ = run(self.mod, t.d, b)
        self.assertEqual(rc, 1, "a mention must not be credited as a disposition")
        self.assertIn("0 -> 1", out)

    def test_a_file_with_no_refusal_path_is_not_counted(self):
        with Tree({"n.py": NO_PATH_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 0}), encoding="utf-8")
            rc, out, _ = run(self.mod, t.d, b)
        self.assertEqual(rc, 0)
        self.assertIn("NO-REFUSAL-PATH  1", out)

    # ── ⛔ VOID is reachable, and is never a pass ──────────────────────────────────

    def test_no_baseline_is_VOID_not_a_floor_of_zero(self):
        """⛔ 'no floor recorded' and 'floor of 0' are different states. Treating the first as
        the second would fail every tree on its first run — exactly the noisy gate #73 argues
        against — and treating it as a pass would gate nothing while looking green."""
        with Tree({"a.py": UNNAMED_SRC}) as t:
            rc, _, msg = run(self.mod, t.d, Path(t.d) / "absent.json")
        self.assertEqual(rc, "Void")
        self.assertIn("not 'floor of zero'", msg)

    def test_a_missing_predicate_is_VOID_not_a_guess(self):
        """⛔ The delegated module is the definition. Without it there is no count."""
        with Tree({"a.py": UNNAMED_SRC}) as t:
            (t.tools / "disposition-scan.py").unlink()
            b = Path(t.d) / "base.json"
            b.write_text(json.dumps({"unnamed": 0}), encoding="utf-8")
            rc, _, msg = run(self.mod, t.d, b)
        self.assertEqual(rc, "Void")
        self.assertIn("ADDABLE", msg, "even its own refusal names a disposition")

    def test_an_empty_population_is_VOID_not_clean(self):
        """⛔ Zero files scanned is the shape that reads as a perfect score.

        ⚠ Driven through census() rather than report(). The first version of this test
        deleted every *.py to empty the population — INCLUDING disposition-scan.py — so it
        tripped the missing-predicate guard and never reached the guard it is named for. It
        asserted VOID, got VOID, and passed for the wrong reason. Two different VOIDs are
        exactly what #73 is about, so a test that cannot tell them apart is the wrong test."""
        with Tree({"test_only.py": UNNAMED_SRC}) as t:
            (t.tools / "disposition-scan.py").unlink()      # not needed: mod passed directly
            mod = load()
            spec = importlib.util.spec_from_file_location("ds", HERE / "disposition-scan.py")
            ds = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ds)
            with self.assertRaises(mod.Void) as cm:
                mod.census(t.d, ds)                          # tools/ holds only test_*.py
        self.assertIn("EMPTY population", str(cm.exception))
        self.assertIn("clean board", str(cm.exception))

    def test_an_unparseable_baseline_is_VOID_and_is_not_rewritten(self):
        with Tree({"a.py": UNNAMED_SRC}) as t:
            b = Path(t.d) / "base.json"
            b.write_text("{not json", encoding="utf-8")
            rc, _, msg = run(self.mod, t.d, b)
            self.assertEqual(b.read_text(encoding="utf-8"), "{not json",
                             "a baseline it could not parse must survive untouched")
        self.assertEqual(rc, "Void")

    # ── the tool's own refusals obey the rule it enforces ─────────────────────────

    def test_this_tool_passes_its_OWN_predicate(self):
        """★ A check that would fail its own rule has no standing to apply it to 45 files
        owned by other roles."""
        spec = importlib.util.spec_from_file_location(
            "ds", HERE / "disposition-scan.py")
        ds = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ds)
        src = (HERE / "disposition-ratchet.py").read_text(encoding="utf-8")
        self.assertEqual(ds.classify(src), ds.NAMED,
                         "every printed refusal here must name ADDABLE or NO REMEDY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
