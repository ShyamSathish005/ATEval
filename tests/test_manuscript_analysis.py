from __future__ import annotations

import io
import importlib.util
import json
import stat
import unittest
import zipfile
from unittest.mock import patch

from ateval.manuscript_analysis import analyze_manuscript, import_manuscript
from ateval.manuscript_analysis.exports import export_reviewed_manuscript


class ManuscriptImportTests(unittest.TestCase):
    def test_text_source_map_is_exact_and_detector_state_is_unavailable(self):
        source = b"Introduction\n\nThe method uses 12% of the data."
        bundle = import_manuscript("paper.txt", source)
        report = analyze_manuscript(bundle)
        passage = next(item for item in report["passages"] if item["text"].startswith("The method"))
        self.assertTrue(passage["source_map"]["editable"])
        self.assertEqual(source.decode()[passage["source_map"]["start"]:passage["source_map"]["end"]], passage["text"])
        self.assertEqual(report["detector_summary"]["available_method_count"], 0)
        self.assertEqual(report["detector_summary"]["overall_authorship_probability"], None)
        self.assertEqual(report["coverage"]["ai_signal_prose_coverage"], 0.0)
        self.assertTrue(all(item["highlight_state"] == "grey" for item in report["passages"]))

    def test_long_document_and_repeated_passages_keep_distinct_stable_ids(self):
        source = ("Repeated sentence is included in the manuscript.\n\n" * 1000).encode()
        bundle = import_manuscript("long.txt", source)
        first = analyze_manuscript(bundle)
        second = analyze_manuscript(import_manuscript("long.txt", source))
        ids = [item["segment_id"] for item in first["passages"]]
        self.assertEqual(len(ids), 1000)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [item["segment_id"] for item in second["passages"]])
        self.assertEqual(first["document"]["words_in_prose_projection"], 7000)

    def test_latex_math_excluded_and_markup_crossing_passage_read_only(self):
        content = b"\\documentclass{article}\n\\begin{document}\n\\section{Methods}\nThe value is $x_1$ in the model.\n\\begin{equation}x_1=2\\end{equation}\n\\end{document}"
        bundle = import_manuscript("paper.tex", content)
        report = analyze_manuscript(bundle)
        sentence = next(item for item in report["passages"] if "The value" in item["text"])
        self.assertEqual(sentence["section"], "Methods")
        self.assertFalse(sentence["source_map"]["editable"])
        self.assertTrue(any(item["kind"] == "excluded_math" for item in bundle.unsupported))
        self.assertTrue(any(item["kind"] == "excluded_latex_environment" for item in bundle.unsupported))

    def test_zip_project_resolves_nested_input_and_preserves_binary_assets_on_export(self):
        project = io.BytesIO()
        with zipfile.ZipFile(project, "w") as archive:
            archive.writestr("main.tex", "\\documentclass{article}\n\\begin{document}\n\\section{Intro}\n\\input{sections/methods}\n\\end{document}\n")
            archive.writestr("sections/methods.tex", "The method is effective.\n")
            archive.writestr("figures/plot.png", b"binary-image-placeholder")
            archive.writestr("refs.bib", "@article{paper, title={Example}}")
        raw = project.getvalue()
        bundle = import_manuscript("project.zip", raw)
        report = analyze_manuscript(bundle)
        target = next(item for item in report["passages"] if item["text"] == "The method is effective.")
        self.assertEqual(bundle.root_file, "main.tex")
        self.assertTrue(target["source_map"]["editable"])
        self.assertEqual(target["source_map"]["path"], "sections/methods.tex")
        patch = {"source_text": target["text"], "replacement": "The method performs effectively.", "source_map": target["source_map"]}
        exported, media_type, output_name = export_reviewed_manuscript("project.zip", raw, [patch])
        self.assertEqual(media_type, "application/zip")
        self.assertEqual(output_name, "project-reviewed.zip")
        with zipfile.ZipFile(io.BytesIO(exported)) as archive:
            self.assertIn("The method performs effectively.", archive.read("sections/methods.tex").decode())
            self.assertEqual(archive.read("figures/plot.png"), b"binary-image-placeholder")
            self.assertEqual(archive.read("refs.bib"), b"@article{paper, title={Example}}")

    def test_ambiguous_root_and_unsafe_zip_paths_fail(self):
        ambiguous = io.BytesIO()
        with zipfile.ZipFile(ambiguous, "w") as archive:
            archive.writestr("a.tex", "\\begin{document}A\\end{document}")
            archive.writestr("b.tex", "\\begin{document}B\\end{document}")
        with self.assertRaisesRegex(ValueError, "unique LaTeX root"):
            import_manuscript("project.zip", ambiguous.getvalue())
        unsafe = io.BytesIO()
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("../escape.tex", "bad")
        with self.assertRaisesRegex(ValueError, "unsafe file path"):
            import_manuscript("project.zip", unsafe.getvalue())

    def test_zip_symlink_is_rejected(self):
        symlink = io.BytesIO()
        with zipfile.ZipFile(symlink, "w") as archive:
            item = zipfile.ZipInfo("linked.tex")
            item.create_system = 3
            item.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(item, "../outside.tex")
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            import_manuscript("project.zip", symlink.getvalue())

    def test_zip_file_count_and_expanded_size_limits_are_enforced(self):
        project = io.BytesIO()
        with zipfile.ZipFile(project, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("main.tex", "\\begin{document}ok\\end{document}")
            archive.writestr("large.txt", "x" * 10000)
        from ateval.manuscript_analysis import documents
        with patch.object(documents, "MAX_PROJECT_FILES", 1):
            with self.assertRaisesRegex(ValueError, "file limit"):
                import_manuscript("project.zip", project.getvalue())
        with patch.object(documents, "MAX_PROJECT_EXPANDED_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "expands beyond"):
                import_manuscript("project.zip", project.getvalue())

    def test_malformed_include_is_reported_without_repair(self):
        bundle = import_manuscript("paper.tex", b"\\begin{document}Text.\\input{broken\\end{document}")
        self.assertTrue(any(item["kind"] == "malformed_include" for item in bundle.unsupported))
        self.assertIn(r"\input{broken", bundle.source_texts["paper.tex"])

    def test_stale_and_overlapping_edits_are_rejected(self):
        content = b"This is a source sentence."
        bundle = import_manuscript("draft.txt", content)
        report = analyze_manuscript(bundle)
        passage = report["passages"][0]
        source_map = passage["source_map"]
        stale = {"source_text": "Wrong", "replacement": "Changed", "source_map": source_map}
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            export_reviewed_manuscript("draft.txt", content, [stale])
        first = {"source_text": "This", "replacement": "That", "source_map": {"editable": True, "path": "draft.txt", "start": 0, "end": 4}}
        second = {"source_text": "This is", "replacement": "That was", "source_map": {"editable": True, "path": "draft.txt", "start": 0, "end": 7}}
        with self.assertRaisesRegex(ValueError, "overlap"):
            export_reviewed_manuscript("draft.txt", content, [first, second])

    @unittest.skipUnless(importlib.util.find_spec("docx"), "python-docx optional dependency is unavailable")
    def test_docx_run_mapping_and_export_preserve_run_style(self):
        from docx import Document
        source = io.BytesIO()
        document = Document()
        paragraph = document.add_paragraph()
        run = paragraph.add_run("This sentence is clear.")
        run.bold = True
        document.save(source)
        raw = source.getvalue()
        bundle = import_manuscript("paper.docx", raw)
        report = analyze_manuscript(bundle)
        passage = report["passages"][0]
        self.assertTrue(passage["source_map"]["editable"])
        patch = {"source_text": passage["text"], "replacement": "This sentence is precise.", "source_map": passage["source_map"]}
        output, _, _ = export_reviewed_manuscript("paper.docx", raw, [patch])
        revised = Document(io.BytesIO(output))
        self.assertEqual(revised.paragraphs[0].text, "This sentence is precise.")
        self.assertTrue(revised.paragraphs[0].runs[0].bold)

    @unittest.skipUnless(importlib.util.find_spec("docx"), "python-docx optional dependency is unavailable")
    def test_docx_cross_run_passage_is_read_only(self):
        from docx import Document
        source = io.BytesIO()
        document = Document()
        paragraph = document.add_paragraph()
        paragraph.add_run("This sentence ")
        paragraph.add_run("crosses runs.").italic = True
        document.save(source)
        bundle = import_manuscript("paper.docx", source.getvalue())
        report = analyze_manuscript(bundle)
        passage = report["passages"][0]
        self.assertFalse(passage["source_map"]["editable"])

    def test_pdf_cannot_be_exported_as_source_preserved(self):
        with self.assertRaises((ValueError, RuntimeError)):
            import_manuscript("paper.pdf", b"not a pdf")


if __name__ == "__main__":
    unittest.main()
