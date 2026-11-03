"""Tests for leakage-resistant evaluation splits and length matching."""

from __future__ import annotations

import unittest

from ateval.detection import (
    DetectionRecord,
    SplitConfig,
    SyntheticDetectionFixture,
    create_leakage_resistant_splits,
    create_length_matched_cohort,
)


class DetectionSplitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = SyntheticDetectionFixture.create_fixture_records()

    def test_invalid_split_ratios_raise(self):
        with self.assertRaises(ValueError):
            SplitConfig(train_ratio=0.5, val_ratio=0.3, test_ratio=0.3)

    def test_group_split_prevents_prompt_leakage(self):
        cfg = SplitConfig(
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
            seed=42,
            group_by="prompt",
        )
        result = create_leakage_resistant_splits(self.records, cfg)
        self.assertTrue(result.leakage_audit["clean"])
        self.assertFalse(result.leakage_audit["prompt_leakage"])
        self.assertFalse(result.leakage_audit["document_leakage"])

        train_prompts = {r.prompt.strip() for r in result.train if r.prompt}
        val_prompts = {r.prompt.strip() for r in result.val if r.prompt}
        test_prompts = {r.prompt.strip() for r in result.test if r.prompt}

        self.assertEqual(train_prompts & val_prompts, set())
        self.assertEqual(train_prompts & test_prompts, set())
        self.assertEqual(val_prompts & test_prompts, set())

    def test_unseen_model_holdout_in_test_only(self):
        # Hold out "gemini" and "mistral ai"
        cfg = SplitConfig(
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
            seed=42,
            group_by="prompt",
            unseen_models=("gemini", "mistral ai"),
        )
        result = create_leakage_resistant_splits(self.records, cfg)

        # Neither train nor val must contain unseen models
        train_models = {(r.generator_model or "").casefold() for r in result.train}
        val_models = {(r.generator_model or "").casefold() for r in result.val}

        self.assertNotIn("gemini", train_models)
        self.assertNotIn("mistral ai", train_models)
        self.assertNotIn("gemini", val_models)
        self.assertNotIn("mistral ai", val_models)

        # Confirm unseen models are in test
        test_models = {(r.generator_model or "").casefold() for r in result.test}
        self.assertTrue("gemini" in test_models or "mistral ai" in test_models)
        self.assertGreaterEqual(len(result.unseen_model_test), 1)

    def test_length_matched_cohort_balances_classes(self):
        matched = create_length_matched_cohort(self.records, bin_width=50, seed=42)
        self.assertGreater(len(matched), 0)
        human_count = sum(1 for r in matched if r.label == "human")
        ai_count = sum(1 for r in matched if r.label == "ai")
        self.assertEqual(human_count, ai_count)


if __name__ == "__main__":
    unittest.main()

