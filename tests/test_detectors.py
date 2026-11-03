from __future__ import annotations

import unittest

from ateval.detectors import evaluate_stylometric_baseline


class StylometricBaselineTests(unittest.TestCase):
    def test_is_deterministic_and_explicitly_uncalibrated(self):
        text = "Academic evidence requires context. Results should be interpreted conservatively."
        first = evaluate_stylometric_baseline(text)
        second = evaluate_stylometric_baseline(text)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "experimental_unvalidated")
        self.assertIsNone(first.get("authorship_probability"))
        self.assertIn("not an authorship classifier", first["interpretation"])

    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            evaluate_stylometric_baseline(" ")
