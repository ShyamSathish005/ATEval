import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ateval.cli import main
from ateval.config import load_config
from ateval.registry import DETECTORS, detector_by_name
from ateval.schema import DatasetRecord


class FoundationTests(unittest.TestCase):
    def test_default_config_is_local_first(self):
        self.assertTrue(load_config().offline)

    def test_config_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('[app]\nseed=9\noffline=true\noutput_dir="out"\n')
            cfg = load_config(path)
            self.assertEqual(cfg.seed, 9)
            self.assertEqual(cfg.output_dir, "out")

    def test_dataset_record_valid_and_metadata_preserved(self):
        row = DatasetRecord.from_mapping({"sample_id":"s1", "text":"Body", "label":"human", "source_id":"src", "dataset":"demo", "domain":"cs", "metadata":{"split":"test"}})
        self.assertEqual(row.domain, "cs")
        self.assertEqual(row.metadata["split"], "test")

    def test_dataset_record_rejects_missing_and_invalid_labels(self):
        with self.assertRaisesRegex(ValueError, "missing required"):
            DatasetRecord.from_mapping({"sample_id":"s"})
        with self.assertRaisesRegex(ValueError, "label must"):
            DatasetRecord.from_mapping({"sample_id":"s", "text":"x", "label":"maybe", "source_id":"src", "dataset":"d"})

    def test_registry_does_not_claim_unimplemented_methods(self):
        self.assertEqual(len(DETECTORS), 9)
        self.assertEqual(detector_by_name("detectgpt").status, "planned")
        with self.assertRaises(KeyError):
            detector_by_name("made-up")

    def test_cli_detector_list_and_doctor(self):
        self.assertEqual(main(["detector", "list"]), 0)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["doctor"]), 0)
        report = json.loads(output.getvalue().split("\nINFO ")[0])
        self.assertIn("packages", report)
        self.assertIn("backend", report)
        self.assertIn("frontend", report)
        self.assertIn("ollama", report)
        self.assertIn("latex", report)
        self.assertIn("storage", report)


if __name__ == "__main__":
    unittest.main()
