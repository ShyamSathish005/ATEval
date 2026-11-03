"""Tests for detector baseline evaluation engine, metrics, and task isolation."""

from __future__ import annotations

import unittest

from ateval.detection import (
    DetectionRecord,
    SpanAnnotation,
    SyntheticDetectionFixture,
    TaskDefinitionError,
    analyze_feature_associations,
    bootstrap_ci,
    calculate_auprc,
    calculate_auroc,
    calculate_classification_metrics,
    evaluate_by_subgroup,
    evaluate_mixed_authorship_cohort,
    evaluate_records,
    find_optimal_threshold,
    prepare_task_a_cohort,
    prepare_task_b_cohort,
    prepare_task_c_domain_cohort,
    prepare_task_d_passage_cohort,
)


class DetectionEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = SyntheticDetectionFixture.create_fixture_records()

    def test_calculate_auroc_exactness(self):
        # Perfect separation
        scores_perf = [0.1, 0.2, 0.3, 0.8, 0.9, 0.95]
        labels_perf = [0, 0, 0, 1, 1, 1]
        self.assertEqual(calculate_auroc(scores_perf, labels_perf), 1.0)

        # Inverted separation
        scores_inv = [0.9, 0.8, 0.7, 0.2, 0.1]
        labels_inv = [0, 0, 0, 1, 1]
        self.assertEqual(calculate_auroc(scores_inv, labels_inv), 0.0)

        # Single class fallback
        self.assertEqual(calculate_auroc([0.5, 0.6], [1, 1]), 0.5)

    def test_calculate_auprc_bounds(self):
        scores = [0.1, 0.4, 0.7, 0.9]
        labels = [0, 0, 1, 1]
        auprc = calculate_auprc(scores, labels)
        self.assertGreater(auprc, 0.0)
        self.assertLessEqual(auprc, 1.0)

    def test_threshold_selection_on_validation(self):
        val_scores = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
        val_labels = [0, 0, 0, 1, 1, 1]
        thresh_f1 = find_optimal_threshold(val_scores, val_labels, metric="f1")
        self.assertGreaterEqual(thresh_f1, 0.3)
        self.assertLessEqual(thresh_f1, 0.7)

    def test_evaluate_records_on_synthetic_cohort(self):
        task_a = prepare_task_a_cohort(self.records)
        metrics, details = evaluate_records(task_a, threshold=0.5, run_bootstrap=True, seed=42)

        self.assertGreater(metrics.total_samples, 0)
        self.assertEqual(metrics.positive_count, 5)  # 5 AI
        self.assertEqual(metrics.negative_count, 5)  # 5 Human
        self.assertGreaterEqual(metrics.auroc, 0.0)
        self.assertLessEqual(metrics.auroc, 1.0)
        self.assertEqual(len(details), 10)

        # Check CI validity
        low_auroc, high_auroc = metrics.ci_auroc
        self.assertLessEqual(low_auroc, high_auroc)

    def test_feature_associations_computes_point_biserial(self):
        task_a = prepare_task_a_cohort(self.records)
        _, details = evaluate_records(task_a, threshold=0.5, run_bootstrap=False)
        associations = analyze_feature_associations(details)

        self.assertIn("type_token_ratio", associations)
        self.assertIn("sentence_length_variation", associations)
        self.assertIn("function_word_ratio", associations)
        for feat, stats in associations.items():
            self.assertIn("point_biserial_correlation", stats)
            self.assertIn("difference", stats)

    def test_subgroup_evaluation(self):
        task_a = prepare_task_a_cohort(self.records)
        by_length = evaluate_by_subgroup(task_a, lambda r: r.length_group())
        self.assertTrue(any("<100" in k for k in by_length.keys()))

    def test_mixed_authorship_evaluation_task_b(self):
        task_b = prepare_task_b_cohort(self.records)
        result = evaluate_mixed_authorship_cohort(task_b)
        self.assertGreater(result["total_mixed"], 0)
        self.assertIn("results_by_subtype", result)

    def test_task_c_domain_separation(self):
        in_d, out_d = prepare_task_c_domain_cohort(self.records, target_domain="academic")
        self.assertGreater(len(in_d), 0)
        for r in in_d:
            self.assertIn("academic", (r.domain or "").casefold())

    def test_task_d_rejects_records_without_span_annotations(self):
        # Passing records without span ground truth MUST raise TaskDefinitionError
        no_span_records = [r for r in self.records if not r.has_span_labels]
        with self.assertRaises(TaskDefinitionError):
            prepare_task_d_passage_cohort(no_span_records)

        # Passing records with verified spans succeeds
        span_records = [r for r in self.records if r.has_span_labels]
        cohort = prepare_task_d_passage_cohort(span_records)
        self.assertEqual(len(cohort), 1)
        self.assertEqual(cohort[0].id, "syn_passage_001")


if __name__ == "__main__":
    unittest.main()

