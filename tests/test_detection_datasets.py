"""Tests for detection dataset loaders, adapters, schemas, and manifests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ateval.detection import (
    DatasetManifest,
    DetectionRecord,
    M4Adapter,
    RAIDAdapter,
    SpanAnnotation,
    SyntheticDetectionFixture,
    TXD22Adapter,
    compute_sha256,
)


class DetectionDatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "detection"
        self.txd22_fixture = self.fixtures_dir / "synthetic_txd22.csv"
        self.raid_fixture = self.fixtures_dir / "synthetic_raid.jsonl"
        self.m4_fixture = self.fixtures_dir / "synthetic_m4.jsonl"

    def test_record_validation_and_classification(self):
        rec = DetectionRecord(
            id="test_01",
            text="Valid scholarly text evaluating mathematical convergence.",
            label="human",
            original_label="Human",
            source_dataset="test_repo",
        )
        self.assertEqual(rec.validate(), [])
        self.assertEqual(rec.length_group(), "<100")

        # Invalid label
        bad_rec = DetectionRecord(
            id="test_bad",
            text="Some text",
            label="invalid_label",
            original_label="xyz",
            source_dataset="test",
        )
        self.assertTrue(any("must be one of: human, ai, mixed" in err for err in bad_rec.validate()))

        # Empty text
        empty_rec = DetectionRecord(
            id="test_empty",
            text="",
            label="human",
            original_label="Human",
            source_dataset="test",
        )
        self.assertTrue(any("must not be empty" in err for err in empty_rec.validate()))

    def test_span_annotation_validation(self):
        text = "First sentence here. Second sentence starts."
        span_good = SpanAnnotation(start_char=0, end_char=20, label="human")
        self.assertEqual(span_good.validate(len(text)), [])

        span_bad_bounds = SpanAnnotation(start_char=30, end_char=10, label="human")
        self.assertTrue(len(span_bad_bounds.validate(len(text))) > 0)

        span_out_of_bounds = SpanAnnotation(start_char=0, end_char=100, label="human")
        self.assertTrue(any("exceeds text length" in err for err in span_out_of_bounds.validate(len(text))))

    def test_synthetic_detection_fixture_generation(self):
        records = SyntheticDetectionFixture.create_fixture_records()
        self.assertGreaterEqual(len(records), 10)
        labels = {r.label for r in records}
        self.assertIn("human", labels)
        self.assertIn("ai", labels)
        self.assertIn("mixed", labels)

        # Confirm span labels are strictly checked
        span_records = [r for r in records if r.has_span_labels]
        self.assertEqual(len(span_records), 1)
        self.assertEqual(len(span_records[0].spans), 2)
        self.assertEqual(span_records[0].validate(), [])

    def test_txd22_adapter_loading_and_class_mapping(self):
        result = TXD22Adapter.load(self.txd22_fixture, verify_sha256=False)
        self.assertEqual(result.total_rows_read, 7)
        self.assertEqual(result.valid_count, 7)
        self.assertEqual(result.skipped_count, 0)

        labels = {r.label for r in result.records}
        self.assertEqual(labels, {"human", "ai", "mixed"})

        # Check AI generator preservation
        chatgpt_rec = next(r for r in result.records if r.original_label == "ChatGPT")
        self.assertEqual(chatgpt_rec.label, "ai")
        self.assertEqual(chatgpt_rec.generator_model, "ChatGPT")

        # Check mixed authorship
        mixed_rec = next(r for r in result.records if "AI-generated + Human-written" in r.original_label)
        self.assertEqual(mixed_rec.label, "mixed")
        self.assertIsNone(mixed_rec.generator_model)

    def test_raid_adapter_filtering_and_loading(self):
        # Filter for academic abstracts
        result = RAIDAdapter.load_jsonl_or_csv(self.raid_fixture, domain_filter="abstracts")
        self.assertEqual(result.valid_count, 2)
        self.assertEqual(result.skipped_count, 2)  # recipes filtered out
        for rec in result.records:
            self.assertEqual(rec.domain, "academic")

    def test_m4_adapter_filtering_and_loading(self):
        result = M4Adapter.load_jsonl(self.m4_fixture, domain_filter="arxiv")
        self.assertEqual(result.valid_count, 2)
        self.assertEqual(result.skipped_count, 1)  # wikihow filtered out
        for rec in result.records:
            self.assertEqual(rec.domain, "academic")

    def test_dataset_manifest_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_file = Path(temp_dir) / "manifest.json"
            manifest = DatasetManifest(
                name="TXD-22",
                version="1.0",
                source="Mendeley Data",
                doi="10.17632/prcjcggtjf.1",
                licence="CC BY 4.0",
                citation="Iqbal & Kashem (2026)",
                download_url="https://data.mendeley.com/public-files/datasets/prcjcggtjf/files/1e842f9d-4ff8-4986-bc7c-cde460f806ee/file_downloaded",
                download_date="2026-11-03",
                sha256_hash="232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d",
                file_size_bytes=121656267,
                total_samples=66000,
                class_distribution={"Human": 3000, "ChatGPT": 3000},
                transformations=["load_csv", "filter_task_a"],
                qualification_status="approved",
            )
            manifest.save(manifest_file)
            loaded = DatasetManifest.from_file(manifest_file)
            self.assertEqual(loaded.name, "TXD-22")
            self.assertEqual(loaded.doi, "10.17632/prcjcggtjf.1")
            self.assertEqual(loaded.qualification_status, "approved")


if __name__ == "__main__":
    unittest.main()

