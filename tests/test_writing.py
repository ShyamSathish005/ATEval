import json
import tempfile
import unittest
from pathlib import Path

from ateval.cli import main
from ateval.writing import analyze_text, apply_accepted_suggestions, extract_document, validate_preservation


class WritingAnalysisTests(unittest.TestCase):
    def test_reports_descriptive_features_and_review_only_suggestions(self):
        text = """Introduction

We show that the method works in order to improve clarity. The results show strong performance.

The results show strong performance. A number of factors contribute to this finding."""
        report = analyze_text(text, document_name="fixture.tex", document_format="tex")
        self.assertEqual(report["schema_version"], "writing-analysis-v1")
        self.assertEqual(report["counts"]["sections"], 1)
        self.assertEqual(report["counts"]["paragraphs"], 3)
        self.assertTrue(report["suggestions"])
        self.assertTrue(all(item["review_required"] for item in report["suggestions"]))
        self.assertEqual(report["suggestions"][0]["context"]["paragraph"], "We show that the method works in order to improve clarity. The results show strong performance.")
        self.assertEqual(len(report["discourse"]["repeated_sentences"]), 1)
        self.assertIn("not an ideal or universal", report["interpretation_limits"][0])

    def test_protects_math_citations_references_numbers_and_code(self):
        text = r"""We compare 42.5 mg using \cite{smith2024} and Equation \ref{eq:loss}.
The score was 3.14 in order to preserve the result. $x = 3.14$ and \begin{equation}y=2\end{equation}."""
        report = analyze_text(text, document_format="tex")
        applied, changes = apply_accepted_suggestions(text, report["suggestions"], {item["id"] for item in report["suggestions"]})
        self.assertIn("42.5 mg", applied)
        self.assertIn(r"\cite{smith2024}", applied)
        self.assertIn(r"\ref{eq:loss}", applied)
        self.assertIn("$x = 3.14$", applied)
        self.assertIn(r"\begin{equation}y=2\end{equation}", applied)
        self.assertLessEqual(len(changes), 1)

    def test_apply_requires_exact_current_source_span(self):
        text = "in order to work"
        report = analyze_text(text)
        suggestion = report["suggestions"][0]
        self.assertEqual(apply_accepted_suggestions("already changed", [suggestion], {suggestion["id"]}), ("already changed", []))

    def test_preservation_validator_checks_protected_spans_but_abstains_on_meaning(self):
        original = r"The finding is 3.14 mg (\cite{smith2024}) in order to compare."
        revised = r"The finding is 3.14 mg (\cite{smith2024}) to compare."
        result = validate_preservation(original, revised)
        self.assertTrue(result["protected_span_sequence_preserved"])
        self.assertEqual(result["semantic_equivalence"], "not_assessed")
        changed = validate_preservation(original, r"The finding is 3.41 mg (\cite{smith2024}) to compare.")
        self.assertFalse(changed["protected_span_sequence_preserved"])

    def test_protects_common_author_year_citations(self):
        text = "We follow the prior method [Smith et al., 2021; Jones, 2024] and revise in order to compare."
        report = analyze_text(text)
        rewritten, _ = apply_accepted_suggestions(text, report["suggestions"], {item["id"] for item in report["suggestions"]})
        self.assertIn("[Smith et al., 2021; Jones, 2024]", rewritten)

    def test_txt_tex_ingestion_is_read_only_and_utf8_only(self):
        result = extract_document("paper.tex", b"\\section{Intro}\nText")
        self.assertEqual(result["format"], "tex")
        self.assertFalse(result["source_modified"])
        self.assertFalse(result["write_back_supported"])
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            extract_document("bad.txt", b"\xff")
        with self.assertRaisesRegex(ValueError, "Choose"):
            extract_document("paper.rtf", b"text")

    def test_cli_writes_new_report_without_overwriting_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "paper.txt"
            output = Path(directory) / "review.json"
            source.write_text("We show results in order to explain them.", encoding="utf-8")
            self.assertEqual(main(["writing", "analyze", str(source), "--output", str(output)]), 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(report["suggestions"])
            self.assertIn("in order to", source.read_text(encoding="utf-8"))
            with self.assertRaises(SystemExit) as error:
                main(["writing", "analyze", str(source), "--output", str(source)])
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
