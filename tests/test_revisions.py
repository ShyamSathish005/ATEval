import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from ateval.cli import main
from ateval.revisions.alignment import align_sentences, extract_edit_spans, split_sentences
from ateval.revisions.classification import MultinomialIntentModel
from ateval.revisions.datasets import load_arxivedits, load_iterater, split_leakage
from ateval.revisions.evaluation import classification_metrics, majority_baseline
from ateval.revisions.revision_depth import analyze_revision_depth
from ateval.revisions.schema import RevisionRecord
from ateval.revisions.taxonomy import canonical_intent


class RevisionResearchTests(unittest.TestCase):
    def fixture(self, root: Path, name: str, rows) -> Path:
        path = root / name
        path.write_text(json.dumps(rows), encoding="utf-8")
        return path

    def test_alignment_handles_identity_split_merge_insert_delete_and_offsets(self):
        self.assertEqual([unit.text for unit in split_sentences("First sentence. Second one!")], ["First sentence.", "Second one!"])
        self.assertEqual(align_sentences(["A method works."], ["A method works."])[0].operation, "match")
        self.assertEqual(align_sentences(["A method works."], ["A method", "works."])[0].operation, "split")
        self.assertEqual(align_sentences(["A method", "works."], ["A method works."])[0].operation, "merge")
        self.assertIn("delete", [item.operation for item in align_sentences(["Remove this.", "Keep this."], ["Keep this."])])
        self.assertIn("insert", [item.operation for item in align_sentences(["Keep this."], ["Add this.", "Keep this."])])
        spans = extract_edit_spans("We show 10 results.", "We report 10 results.")
        self.assertEqual("We show 10 results."[spans[0]["before_start"]:spans[0]["before_end"]], spans[0]["before"])

    def test_iterater_adapter_preserves_label_and_refuses_unverified_training(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.fixture(Path(temp), "human.json", [{"doc_id": "paper-a", "before_sent": "The result is not clear.", "after_sent": "The result is unclear.", "labels": ["CLARITY"], "raw_intents": ["CLARITY", "CLARITY", "FLUENCY"], "revision_depth": 1}])
            loaded = load_iterater(path, split="train", source_license="research-approved-local")
            self.assertEqual(len(loaded.records), 1)
            record = loaded.records[0]
            self.assertEqual(record.raw_labels, ("CLARITY",))
            self.assertEqual(record.canonical_labels, ("clarity_improvement",))
            self.assertEqual(record.annotation_confidence, 2 / 3)
            self.assertFalse(record.license_verified)
            with self.assertRaisesRegex(ValueError, "unverified license"):
                MultinomialIntentModel().fit(loaded.records)
            permitted = load_iterater(path, split="train", source_license="reviewed", license_verified=True)
            model = MultinomialIntentModel().fit(permitted.records)
            self.assertEqual(model.predict(record.original_text, record.revised_text)[0], "clarity_improvement")

    def test_json_extension_accepts_official_jsonl_and_adds_document_context(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sentence_path = root / "train.json"
            sentence_path.write_text("\n".join(json.dumps(row) for row in [
                {"doc_id": "paper-x", "revision_depth": 1, "before_sent": "First sentence.", "after_sent": "First sentence!", "labels": "fluency"},
                {"doc_id": "paper-x", "revision_depth": 1, "before_sent": "Second sentence.", "after_sent": "The second sentence.", "labels": "clarity"},
            ]), encoding="utf-8")
            documents_path = self.fixture(root, "documents.json", [{"doc_id": "paper-x", "revision_depth": 1, "before_revision": "First sentence. Second sentence. Third sentence.", "sents_char_pos": [0, 16, 33], "domain": "arxiv"}])
            loaded = load_iterater(sentence_path, split="train", license_verified=True, document_context_path=documents_path)
            self.assertEqual(len(loaded.records), 2)
            self.assertNotEqual(loaded.records[0].record_id, loaded.records[1].record_id)
            self.assertEqual(loaded.records[0].context_after, "Second sentence. Third sentence.")
            self.assertEqual(loaded.records[1].context_before, "First sentence.")
            self.assertEqual(loaded.records[1].section_type, "abstract")
            self.assertEqual(loaded.records[1].metadata["document_context"], "First sentence. Second sentence. Third sentence.")

    def test_arxivedits_adapter_requires_both_version_licenses_and_explicit_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.fixture(Path(temp), "edits.json", [{"arxiv-id": "2401.00001", "sentence-1-level": 1, "sentence-2-level": 2, "sentence-1": "A result is good .", "sentence-2": "A result is clear .", "edits-combination-0": {"0": {"type": "substitute", "intention": "Improve Language: Simplify", "sentence-1-token-indices": [3, 4], "sentence-2-token-indices": [3, 4]}}}])
            denied = load_arxivedits(path, split="train")
            self.assertEqual(denied.skipped["version_license_missing"], 1)
            manifest = {"2401.00001": {"versions": {"1": "CC-BY-4.0", "2": "CC-BY-4.0"}}}
            denied = load_arxivedits(path, split="train", license_manifest=manifest, permitted_licenses={"CC-BY-NC-4.0"})
            self.assertEqual(denied.skipped["license_not_permitted"], 1)
            loaded = load_arxivedits(path, split="train", license_manifest=manifest, permitted_licenses={"CC-BY-4.0"})
            self.assertEqual(len(loaded.records), 1)
            record = loaded.records[0]
            self.assertTrue(record.license_verified)
            self.assertEqual(record.edit_spans[0].before, "good")
            self.assertEqual(record.edit_spans[0].canonical_intent, "concision")

    def test_grouped_split_leakage_and_evaluator_hard_fail(self):
        self.assertFalse(split_leakage({"train": ["doc-a"], "test": ["doc-b"]})["overlaps"])
        self.assertFalse(split_leakage({"train": ["doc-a"], "test": ["doc-a"]})["leakage_free"])
        train = RevisionRecord("v1", "train", "fixture", "doc-a", 1, "train", "old words", "new words", canonical_labels=("clarity_improvement",), license_verified=True)
        test = RevisionRecord("v1", "test", "fixture", "doc-a", 2, "test", "before text", "after text", canonical_labels=("clarity_improvement",), license_verified=True)
        model = MultinomialIntentModel().fit([train])
        with self.assertRaisesRegex(ValueError, "leakage"):
            classification_metrics([test], model)

    def test_unknown_taxonomy_is_not_guessed_and_depth_is_descriptive(self):
        self.assertIsNone(canonical_intent("made_up_revision_goal"))
        rows = [RevisionRecord("v1", "a", "d", "one", 1, "train", "a", "b"), RevisionRecord("v1", "b", "d", "two", 3, "train", "a", "longer b")]
        summary = analyze_revision_depth(rows)
        self.assertEqual(summary["source_document_count"], 2)
        self.assertIn("stages", summary)

    def test_cli_inspect_and_model_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train_path = self.fixture(root, "train.json", [{"doc_id": "train-paper", "before_sent": "A vague statement.", "after_sent": "A clear statement.", "labels": ["CLARITY"]}])
            train = load_iterater(train_path, split="train", license_verified=True)
            model_path = root / "intent.json"
            model = MultinomialIntentModel().fit(train.records)
            model.save(model_path)
            self.assertEqual(MultinomialIntentModel.load(model_path).class_counts["clarity_improvement"], 1)
            with self.assertRaises(FileExistsError):
                model.save(model_path)
            self.assertEqual(main(["revisions", "inspect", "iterater", str(train_path), "--split", "train"]), 0)

    def test_cli_training_and_heldout_evaluation_report_baselines(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train_path = self.fixture(root, "train.json", [{"doc_id": "paper-train", "before_sent": "A vague statement.", "after_sent": "A clear statement.", "labels": ["CLARITY"]}])
            test_path = self.fixture(root, "test.json", [{"doc_id": "paper-test", "before_sent": "An unclear sentence.", "after_sent": "A lucid sentence.", "labels": ["CLARITY"]}])
            model_path = root / "model.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["revisions", "train-intent", "iterater", str(train_path), "--split", "train", "--license", "reviewed", "--license-verified", "--output", str(model_path)]), 0)
                self.assertEqual(main(["revisions", "evaluate-intent", str(model_path), "iterater", str(test_path), "--split", "test", "--license", "reviewed", "--license-verified"]), 0)
            with self.assertRaises(SystemExit) as error:
                main(["revisions", "evaluate-intent", str(model_path), "iterater", str(test_path), "--split", "train", "--license", "reviewed", "--license-verified"])
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
