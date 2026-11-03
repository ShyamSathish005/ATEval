from __future__ import annotations

import unittest

from ateval.revisions.academic_generation import AcademicRevisionProposal, XtraGPTOllamaGenerator
from ateval.revisions.protected_content import protect_content, validate_and_restore
from ateval.revisions.claim_validation import compare_claim_propositions
from ateval.revisions.scar import SCARRevisionEngine, _generation_was_capped, revision_necessity_gate


class FakeGenerator:
    provider = "fake"

    def __init__(self, transform):
        self.transform = transform
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        revised = self.transform(request.original_text)
        return AcademicRevisionProposal(
            request.original_text, revised, "", "", "", {"semantic_equivalence": "not_assessed"},
        )


class ProtectedContentTests(unittest.TestCase):
    def test_typed_placeholders_restore_exact_values_and_custom_terms(self):
        source = r"The model reached 95% CI with p = 0.04, cite [12, 14], use BERT and \cite{smith2020}; $x=0.5$; key term: causal effect."
        protected = protect_content(source, ("causal effect",))
        self.assertEqual(len(protected.mapping), len(set(item.sentinel for item in protected.mapping)))
        self.assertIn("⟪ATEVAL_STATISTIC_", protected.protected_text)
        self.assertIn("⟪ATEVAL_USER_TERM_", protected.protected_text)
        result = validate_and_restore(protected.protected_text, protected)
        self.assertTrue(result.passed)
        self.assertEqual(result.restored_text, source)
        self.assertEqual([item.start for item in protected.mapping], sorted(item.start for item in protected.mapping))
        self.assertTrue(all(item.expected_occurrence_count == 1 and len(item.sha256) == 64 for item in protected.mapping))

    def test_missing_duplicate_and_added_numeric_content_fail_closed(self):
        protected = protect_content("The effect was 12%.")
        sentinel = protected.mapping[0].sentinel
        missing = validate_and_restore("The effect was significant.", protected)
        duplicate = validate_and_restore(f"{sentinel} {sentinel}", protected)
        added_number = validate_and_restore(f"The effect was {sentinel} and increased by 20%.", protected)
        self.assertFalse(missing.passed)
        self.assertIsNone(missing.restored_text)
        self.assertIn("missing_protected_sentinel", missing.violations)
        self.assertIn("duplicate_protected_sentinel", duplicate.violations)
        self.assertIn("protected_span_sequence_changed", added_number.violations)
        self.assertIsNone(added_number.restored_text)


class LocalModelEndpointTests(unittest.TestCase):
    def test_ollama_endpoint_requires_exact_loopback_hostname(self):
        valid = XtraGPTOllamaGenerator("model", model_file="model.gguf", base_url="http://127.0.0.1:11434")
        self.assertEqual(valid.base_url, "http://127.0.0.1:11434")
        for base_url in (
            "http://127.0.0.1.attacker.example:11434",
            "http://localhost.attacker.example:11434",
            "http://user:pass@127.0.0.1:11434",
            "https://127.0.0.1:11434",
            "http://127.0.0.1:11434/api",
        ):
            with self.subTest(base_url=base_url):
                with self.assertRaisesRegex(ValueError, "loopback"):
                    XtraGPTOllamaGenerator("model", model_file="model.gguf", base_url=base_url)

    def test_reordered_typed_sentinels_fail_closed(self):
        protected = protect_content("We measured 12% for 3 days.")
        reordered = " and ".join(item.sentinel for item in reversed(protected.mapping))
        result = validate_and_restore(reordered, protected)
        self.assertFalse(result.passed)
        self.assertIn("protected_sentinel_order_changed", result.violations)
        self.assertIsNone(result.restored_text)

    def test_added_unbalanced_latex_environment_fails_closed(self):
        protected = protect_content(r"Keep \begin{equation}x=2\end{equation} unchanged.")
        result = validate_and_restore(protected.protected_text + r" \begin{align}", protected)
        self.assertFalse(result.passed)
        self.assertIn("latex_environment_sequence_changed", result.violations)
        self.assertIn("latex_environment_unbalanced", result.violations)
        self.assertIsNone(result.restored_text)

    def test_adversarial_protection_cases_fail_closed(self):
        cases = (
            ("missing", lambda s: s.replace(s, "edited")),
            ("duplicate", lambda s: f"{s} {s}"),
            ("reordered", lambda s: " ".join(reversed(s.split(" "))) if " " in s else s),
            ("modified", lambda s: s.replace(s[:8], s[:7] + "X")),
        )
        protected = protect_content(
            r"Values ranged from -2.5 to 4.0e-3 kg at 95%; "
            r"\begin{equation}x \geq 0.5\end{equation}; [12, 14].",
        )
        self.assertGreaterEqual(len(protected.mapping), 5)
        for name, transform in cases[:2]:
            with self.subTest(name=name):
                result = validate_and_restore(transform(protected.protected_text), protected)
                self.assertFalse(result.passed)
        sentinels = [item.sentinel for item in protected.mapping]
        with self.subTest(name="reordered"):
            result = validate_and_restore(" ".join(reversed(sentinels)), protected)
            self.assertFalse(result.passed)
            self.assertIn("protected_sentinel_order_changed", result.violations)
        with self.subTest(name="modified"):
            result = validate_and_restore(protected.protected_text.replace(sentinels[0], sentinels[0][:-2] + "XX"), protected)
            self.assertFalse(result.passed)
            self.assertIn("missing_protected_sentinel", result.violations)

    def test_repeated_terms_and_multiple_citations_restore_exact_source(self):
        source = r"BERT and BERT report 95% [12, 14] (Smith, 2020) \cite{a,b}."
        protected = protect_content(source, ("BERT",))
        result = validate_and_restore(protected.protected_text, protected)
        self.assertTrue(result.passed)
        self.assertEqual(result.restored_text, source)
        self.assertEqual([item.original for item in protected.mapping].count("BERT"), 2)


class GenerationCompletenessTests(unittest.TestCase):
    def test_length_finish_reason_and_token_cap_are_rejected(self):
        self.assertTrue(_generation_was_capped({"done_reason": "length", "eval_count": 20}, 128))
        self.assertTrue(_generation_was_capped({"done_reason": "stop", "eval_count": 128}, 128))
        self.assertFalse(_generation_was_capped({"done_reason": "stop", "eval_count": 20}, 128))

    def test_url_placeholder_is_not_a_citation(self):
        from ateval.revisions.generation_baselines import CITATION
        self.assertEqual(CITATION.findall("Our code is available at [URL]."), [])
        self.assertEqual(CITATION.findall("Prior work reports this result [Smith et al., 2020]."), ["[Smith et al., 2020]"])


class RevisionGateTests(unittest.TestCase):
    def test_default_gate_returns_no_edit_without_model_confidence(self):
        gate = revision_necessity_gate(
            selected_text="A complete sentence.", paragraph_context="A complete sentence.",
            intention="clarity", author_requested_edit=False,
        )
        self.assertEqual(gate.decision, "NO_EDIT_REQUIRED")
        self.assertIsNone(gate.confidence)

    def test_missing_context_abstains_and_technical_review_does_not_generate(self):
        no_context = revision_necessity_gate(
            selected_text="A sentence.", paragraph_context="", intention="clarity", author_requested_edit=True,
        )
        self.assertEqual(no_context.decision, "INSUFFICIENT_CONTEXT")
        generator = FakeGenerator(lambda text: text)
        engine = SCARRevisionEngine(generator)
        paragraph = "We model the causal effect using Eq. (2). The equation defines the estimand."
        target = "We model the causal effect using Eq. (2)."
        result = engine.revise(
            paragraph, target_start=0, target_end=len(target), intention="technical_review",
            author_requested_edit=True,
        )
        self.assertEqual(result.review_decision, "REQUIRES_EXPERT_REVIEW")
        self.assertEqual(generator.calls, 0)

    def test_no_edit_gate_does_not_call_model(self):
        generator = FakeGenerator(lambda text: text + " revised")
        engine = SCARRevisionEngine(generator)
        paragraph = "The result may indicate a change."
        result = engine.revise(
            paragraph, target_start=0, target_end=len(paragraph), intention="no_edit", author_requested_edit=False,
        )
        self.assertEqual(result.review_decision, "NO_CHANGE")
        self.assertEqual(result.proposed_text, paragraph)
        self.assertEqual(generator.calls, 0)

    def test_added_number_is_rejected_and_negation_change_is_rejected(self):
        target = "The method may improve the result."
        paragraph = target + " The benchmark includes the baseline."
        source_end = len(paragraph)
        generator = FakeGenerator(lambda text: text + " It improved results by 20%.")
        result = SCARRevisionEngine(generator).revise(
            paragraph, target_start=0, target_end=len(target), intention="clarity", author_requested_edit=True,
        )
        self.assertEqual(result.review_decision, "REJECT_STRUCTURAL_CHANGE")
        self.assertIn("protected_span_sequence_changed", result.structural_validation["violations"])

        generator = FakeGenerator(lambda text: text.replace("may", "will"))
        result = SCARRevisionEngine(generator).revise(
            paragraph, target_start=0, target_end=len(target), intention="clarity", author_requested_edit=True,
        )
        self.assertEqual(result.review_decision, "REJECT_POTENTIAL_MEANING_CHANGE")
        self.assertIn("modality", result.claim_integrity.cue_differences)

    def test_safe_candidate_is_only_accepted_for_author_review(self):
        target = "The method improves clarity."
        paragraph = target + " This section introduces the result."
        generator = FakeGenerator(lambda text: text.replace("improves", "supports"))
        result = SCARRevisionEngine(generator).revise(
            paragraph, target_start=0, target_end=len(target), intention="clarity", author_requested_edit=True,
        )
        self.assertEqual(result.review_decision, "ACCEPT_FOR_AUTHOR_REVIEW")
        self.assertTrue(result.plan.author_approval_required)
        self.assertEqual(result.to_dict()["semantic_equivalence"], "not_assessed")


class ClaimValidationTests(unittest.TestCase):
    def test_quantitative_change_is_rejected(self):
        result = compare_claim_propositions("The effect was 12%.", "The effect was 15%.")
        self.assertEqual(result.status, "REJECT_QUANTITATIVE_CHANGE")

    def test_lexical_claim_change_abstains(self):
        result = compare_claim_propositions("The result may improve clarity.", "The result will improve clarity.")
        self.assertEqual(result.status, "ABSTAIN_REQUIRES_HUMAN_REVIEW")

    def test_equivalent_nonclaim_edit_has_no_diagnostic_difference(self):
        result = compare_claim_propositions("The method improves clarity.", "The method improves clarity.")
        self.assertEqual(result.status, "NO_DIAGNOSTIC_DIFFERENCE")


if __name__ == "__main__":
    unittest.main()
