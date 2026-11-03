from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from ateval.manuscript_analysis import analyze_manuscript, import_manuscript
from ateval.manuscript_analysis.exports import export_reviewed_manuscript
from ateval.revisions.academic_generation import (
    AcademicRevisionRequest,
    XtraGPTOllamaGenerator,
)


class HumanizerValidationTests(unittest.TestCase):
    def test_latex_export_changes_only_approved_edit_and_preserves_protected_source(self):
        source = (
            r"\documentclass{article}" "\n"
            r"\newcommand{\method}{ATEval}" "\n"
            r"\begin{document}" "\n"
            r"\section{Methods}" "\n"
            r"The method uses 12\% of the data." "\n"
            r"Prior work is relevant \cite{smith2024}." "\n"
            r"\begin{equation}x_1=2\end{equation}" "\n"
            r"\subsection{Results}" "\n"
            r"The unchanged paragraph contains a figure reference (Figure~\ref{fig:one})." "\n"
            r"\end{document}" "\n"
        ).encode()
        report = analyze_manuscript(import_manuscript("paper.tex", source))
        target = next(item for item in report["passages"] if item["text"].startswith("The method uses"))
        self.assertTrue(target["source_map"]["editable"])
        patch = {
            "source_text": target["text"],
            "replacement": r"The method uses 13\% of the data.",
            "source_map": target["source_map"],
            "protected_terms": [r"\cite{smith2024}"],
        }
        with self.assertRaisesRegex(ValueError, "protected"):
            export_reviewed_manuscript("paper.tex", source, [patch])

        safe_patch = {**patch, "replacement": r"The method uses 12\% of the dataset.", "protected_terms": [r"\cite{smith2024}"]}
        exported, _, _ = export_reviewed_manuscript("paper.tex", source, [safe_patch])
        text = exported.decode()
        self.assertIn(r"\begin{equation}x_1=2\end{equation}", text)
        self.assertIn(r"\newcommand{\method}{ATEval}", text)
        self.assertIn(r"Figure~\ref{fig:one}", text)
        self.assertIn("The unchanged paragraph", text)

    def test_multiple_approved_ranges_leave_rejected_proposal_and_unrelated_text_untouched(self):
        source = b"First paragraph needs clarity.\n\nSecond paragraph remains original.\n\nThird paragraph needs grammar."
        bundle = import_manuscript("paper.txt", source)
        passages = analyze_manuscript(bundle)["passages"]
        first, second, third = passages
        patches = [
            {"source_text": first["text"], "replacement": "First paragraph is clear.", "source_map": first["source_map"]},
            {"source_text": third["text"], "replacement": "Third paragraph has improved grammar.", "source_map": third["source_map"]},
        ]
        exported, _, _ = export_reviewed_manuscript("paper.txt", source, patches)
        self.assertEqual(
            exported.decode(),
            "First paragraph is clear.\n\nSecond paragraph remains original.\n\nThird paragraph has improved grammar.",
        )
        self.assertNotIn("needs clarity", exported.decode())
        self.assertNotIn("needs grammar", exported.decode())
        self.assertNotIn("Second paragraph remains original.", str(patches))
        self.assertEqual(second["text"], "Second paragraph remains original.")

    def test_ollama_adapter_rejects_empty_response_and_records_real_request_shape(self):
        request = AcademicRevisionRequest(
            original_text="The method is clear.",
            paragraph_context="The method is clear. This paragraph provides context.",
            document_section="Methods",
            editing_instruction="Improve clarity conservatively.",
        )
        generator = XtraGPTOllamaGenerator("local-model", model_file="/tmp/model.gguf", mode="ateval", timeout_seconds=1)

        class EmptyResponse:
            def read(self):
                return json.dumps({"message": {"content": " "}}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("ateval.revisions.academic_generation.urllib.request.urlopen", return_value=EmptyResponse()) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "empty"):
                generator.generate_raw(request)
        payload = json.loads(urlopen.call_args.args[0].data.decode())
        self.assertEqual(payload["model"], "local-model")
        self.assertFalse(payload["stream"])
        self.assertIn("<SELECTED_CONTENT>", payload["messages"][0]["content"])

    def test_ollama_published_response_remains_review_required_and_preserves_telemetry(self):
        request = AcademicRevisionRequest(original_text="The method is clear.", editing_instruction="Improve clarity.")
        generator = XtraGPTOllamaGenerator("local-model", model_file="/tmp/model.gguf", mode="published", timeout_seconds=1)

        class Response:
            def read(self):
                return json.dumps({
                    "message": {"content": "The method is clear and concise."},
                    "eval_count": 8,
                    "done_reason": "stop",
                }).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("ateval.revisions.academic_generation.urllib.request.urlopen", return_value=Response()):
            proposal = generator.generate(request)
        self.assertEqual(proposal.status, "review_required")
        self.assertTrue(proposal.author_review_required)
        self.assertEqual(generator.telemetry[-1]["eval_count"], 8)
