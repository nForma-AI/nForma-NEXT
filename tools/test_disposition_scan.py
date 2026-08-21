#!/usr/bin/env python3
"""Hermetic suite for tools/disposition-scan.py. No repository, no network.

⛔ The load-bearing case is test_a_docstring_MENTION_is_not_a_disposition. The first version of the
predicate fell back to "does the form appear ANYWHERE in the source" and credited three real files
on a mention. It was caught by a plant, never by re-reading, and this pins it.
"""
import importlib.util
import io
import os
import unittest

_P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disposition-scan.py")
_spec = importlib.util.spec_from_file_location("disposition_scan", _P)
ds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ds)


class Classifier(unittest.TestCase):
    def test_named_in_the_printed_refusal(self):
        self.assertEqual(ds.classify('print("⛔ VOID: x. ADDABLE — DEVOPS: y")'), ds.NAMED)

    def test_NO_REMEDY_also_counts(self):
        self.assertEqual(ds.classify('print("VOID. NO REMEDY — the refusal is the verdict")'), ds.NAMED)

    def test_a_bare_refusal_is_unnamed(self):
        self.assertEqual(ds.classify('print("⛔ VOID — established nothing")'), ds.UNNAMED)

    def test_a_docstring_MENTION_is_not_a_disposition(self):
        """⛔ #73's own use-versus-mention trap, in the tool built to find it."""
        src = '"""We use ADDABLE — OWNER: what."""\nprint("⛔ VOID: established nothing")'
        self.assertEqual(ds.classify(src), ds.UNNAMED)

    def test_no_printed_refusal_is_its_own_bucket(self):
        self.assertEqual(ds.classify('print("all good")'), ds.NO_PATH)

    def test_a_refusal_in_a_COMMENT_is_not_a_refusal_path(self):
        """⚠ Two-sided: the classifier must also refuse to invent a refusal."""
        self.assertEqual(ds.classify('# VOID: established nothing\nx = 1'), ds.NO_PATH)


class Scanning(unittest.TestCase):
    def test_an_empty_root_is_VOID_not_all_named(self):
        buf = io.StringIO()
        rc = ds.scan("/nonexistent-zzz", out=buf)
        self.assertEqual(rc, 2)
        self.assertIn("ESTABLISHED NOTHING", buf.getvalue())
        self.assertNotIn("name a disposition", buf.getvalue())

    def test_a_real_scan_exits_0_and_says_it_is_not_a_verdict(self):
        """⛔ The design commitment: it NEVER gates, whatever the count."""
        buf = io.StringIO()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rc = ds.scan(root, out=buf)
        self.assertEqual(rc, 0)
        self.assertIn("NOT A VERDICT", buf.getvalue())
        self.assertIn("PARTITION", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
